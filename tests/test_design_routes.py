from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.settings import Settings, get_settings
from app.integrations.github.repository import (
    GitHubConnectionRecord,
    get_github_connection_repository,
)
from app.routers import design
from app.schemas.design import DesignChatResponse
from app.schemas.github import GitHubRepository
from tests.conftest import USER_A


class FakeRepository:
    def __init__(self, record):
        self.record = record

    async def get(self, owner_user_id):
        assert owner_user_id == USER_A.id
        return self.record


def connected_record():
    return GitHubConnectionRecord(
        owner_user_id=USER_A.id,
        status="connected",
        installation_id=55,
        repository=GitHubRepository(
            id=101,
            full_name="openfde/example",
            private=True,
            default_branch="main",
        ),
    )


def create_client(repository):
    app = FastAPI()
    app.include_router(design.router, prefix="/v1")
    app.dependency_overrides[get_current_user] = lambda: USER_A
    app.dependency_overrides[get_settings] = lambda: Settings(openai_api_key=None)
    app.dependency_overrides[get_github_connection_repository] = lambda: repository
    return TestClient(app)


def test_chat_exposes_codebase_tool_only_for_connected_repository(monkeypatch):
    offered = []

    async def fake_design_chat(_body, *, inspect_codebase=None):
        offered.append(inspect_codebase is not None)
        return DesignChatResponse(
            assistant_message="What outcome should the agent produce?",
            suggested_agent_name="Test Agent",
            readiness_score=25,
            missing_information=[],
            can_generate_design=False,
        )

    monkeypatch.setattr(design.design_agent, "design_chat", fake_design_chat)
    body = {
        "messages": [{"role": "user", "content": "Inspect our API."}],
        "enabled_connector_ids": ["github"],
    }

    connected = create_client(FakeRepository(connected_record()))
    disconnected = create_client(FakeRepository(None))

    assert connected.post("/v1/agent-design/chat", json=body).status_code == 200
    assert disconnected.post("/v1/agent-design/chat", json=body).status_code == 200
    assert offered == [True, False]
