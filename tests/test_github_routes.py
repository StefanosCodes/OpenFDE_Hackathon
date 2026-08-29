from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.settings import Settings, get_settings
from app.integrations.github.repository import GitHubConnectionRecord
from app.routers.github import (
    get_github_client,
    get_github_connection_repository,
    router,
)
from app.schemas.github import GitHubRepository
from tests.conftest import USER_A


class FakeRepository:
    def __init__(self):
        self.record = None
        self.repositories = []

    async def begin(self, owner_user_id):
        self.record = GitHubConnectionRecord(owner_user_id=owner_user_id, status="connecting")

    async def get(self, owner_user_id):
        return self.record if self.record and self.record.owner_user_id == owner_user_id else None

    async def save_installation(
        self, *, owner_user_id, installation_id, account_login, account_type, repositories
    ):
        self.repositories = repositories
        self.record = GitHubConnectionRecord(
            owner_user_id=owner_user_id,
            status="awaiting_repository",
            installation_id=installation_id,
            account_login=account_login,
            account_type=account_type,
            updated_at=datetime.now(timezone.utc),
        )
        return self.record

    async def list_repositories(self, owner_user_id):
        return self.repositories

    async def select_repository(self, *, owner_user_id, repository_id):
        selected = next(item for item in self.repositories if item.id == repository_id)
        self.record = GitHubConnectionRecord(
            owner_user_id=owner_user_id,
            status="connected",
            installation_id=self.record.installation_id,
            account_login=self.record.account_login,
            repository=selected,
        )
        return self.record

    async def disconnect(self, owner_user_id):
        self.record = None

    async def disconnect_installation(self, installation_id, *, reason):
        return None

    async def remove_repositories(self, installation_id, repository_ids):
        return None


class FakeGitHub:
    def __init__(self):
        self.verified = []

    def oauth_authorize_url(self, *, state, code_challenge):
        return f"https://github.test/oauth?state={state}&challenge={code_challenge}"

    async def exchange_code(self, *, code, code_verifier):
        assert code == "oauth-code"
        assert code_verifier
        return "temporary-user-token"

    async def verify_installation_for_user(self, *, user_token, installation_id):
        assert user_token == "temporary-user-token"
        return {"id": installation_id, "account": {"login": "openfde-test", "type": "User"}}

    async def list_user_installation_repositories(self, *, user_token, installation_id):
        return [
            GitHubRepository(
                id=101,
                full_name="openfde-test/project",
                private=True,
                default_branch="main",
            )
        ]

    async def verify_repository_access(self, *, installation_id, repository):
        self.verified.append((installation_id, repository.id))


def configured_settings():
    return Settings(
        app_base_url="http://testserver",
        frontend_base_url="http://frontend.test",
        github_app_id="123",
        github_app_slug="openfde-test",
        github_client_id="client-id",
        github_client_secret="client-secret",
        github_private_key="fake-key",
        github_state_secret="a-secure-state-secret-with-enough-length",
    )


def create_client():
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    store = FakeRepository()
    github = FakeGitHub()
    config = configured_settings()
    app.dependency_overrides[get_current_user] = lambda: USER_A
    app.dependency_overrides[get_settings] = lambda: config
    app.dependency_overrides[get_github_connection_repository] = lambda: store
    app.dependency_overrides[get_github_client] = lambda: github
    return TestClient(app), store, github


def test_install_oauth_and_repository_selection_flow():
    client, store, github = create_client()

    connect = client.post("/v1/connectors/github/connect", params={"return_mode": "popup"})
    assert connect.status_code == 200
    assert connect.json()["status"] == "connecting"
    install_state = parse_qs(urlparse(connect.json()["connect_url"]).query)["state"][0]

    setup = client.get(
        "/v1/integrations/github/setup",
        params={"installation_id": 55, "state": install_state},
        follow_redirects=False,
    )
    assert setup.status_code == 303
    oauth_state = parse_qs(urlparse(setup.headers["location"]).query)["state"][0]
    assert client.cookies.get("openfde_github_pkce")

    callback = client.get(
        "/v1/integrations/github/oauth/callback",
        params={"code": "oauth-code", "state": oauth_state},
        follow_redirects=False,
    )
    assert callback.status_code == 303
    assert callback.headers["location"] == "http://frontend.test/connectors?github=installed&popup=1"

    repositories = client.get("/v1/connectors/github/repositories")
    assert repositories.json()[0]["full_name"] == "openfde-test/project"

    selected = client.put("/v1/connectors/github/repository", json={"repository_id": 101})
    assert selected.status_code == 200
    assert selected.json()["status"] == "connected"
    assert selected.json()["repository"]["full_name"] == "openfde-test/project"
    assert github.verified == [(55, 101)]

    disconnected = client.delete("/v1/connectors/github")
    assert disconnected.json()["status"] == "disconnected"
    assert store.record is None


def test_status_is_disconnected_before_installation():
    client, _store, _github = create_client()

    response = client.get("/v1/connectors/github")

    assert response.status_code == 200
    assert response.json()["status"] == "disconnected"
