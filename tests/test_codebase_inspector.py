from types import SimpleNamespace

import pytest

from app.integrations.github.repository import GitHubConnectionRecord
from app.schemas.codebase import CodexInspectionOutput
from app.schemas.github import GitHubRepository
from app.services import codebase_inspector
from tests.conftest import USER_A


class FakeRepositoryStore:
    def __init__(self, record):
        self.record = record

    async def get(self, owner_user_id):
        assert owner_user_id == USER_A.id
        return self.record


class FakeGitHub:
    def __init__(self):
        self.requests = []

    async def create_repository_token(self, *, installation_id, repository_id):
        self.requests.append((installation_id, repository_id))
        return "short-lived-test-token"


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


def runner_settings():
    return SimpleNamespace(
        openai_api_key="test-key",
        codex_clone_timeout_seconds=30,
        codex_max_repository_bytes=1_000_000,
        codex_model="gpt-5.6-terra",
        codex_reasoning_effort="medium",
        codex_runner_timeout_seconds=30,
    )


@pytest.mark.anyio
async def test_inspector_uses_scoped_token_verifies_evidence_and_cleans_clone(
    monkeypatch,
):
    checkout_paths = []

    async def fake_clone(**kwargs):
        checkout = kwargs["destination"]
        checkout_paths.append(checkout)
        checkout.mkdir()
        (checkout / "app.py").write_text(
            "def health():\n    return {'status': 'ok'}\n", encoding="utf-8"
        )
        assert kwargs["repository"] == "openfde/example"
        assert kwargs["token"] == "short-lived-test-token"

    async def fake_git_output(_checkout, *arguments):
        if arguments == ("rev-parse", "HEAD"):
            return "b" * 40
        if arguments[0] == "status":
            return ""
        raise AssertionError(arguments)

    async def fake_codex(**kwargs):
        assert kwargs["question"] == "Where is the health check?"
        return CodexInspectionOutput(
            summary="The health check is defined in app.py.",
            findings=["It returns an ok status."],
            references=[
                {
                    "path": "app.py",
                    "start_line": 1,
                    "end_line": 2,
                    "relevance": "Defines the health check.",
                },
                {
                    "path": "missing.py",
                    "start_line": 1,
                    "end_line": 1,
                    "relevance": "This citation should be rejected.",
                },
            ],
            files_inspected=["app.py"],
            limitations=[],
        )

    monkeypatch.setattr(codebase_inspector, "_clone_repository", fake_clone)
    monkeypatch.setattr(codebase_inspector, "_git_output", fake_git_output)
    monkeypatch.setattr(codebase_inspector, "_run_codex_sdk", fake_codex)
    github = FakeGitHub()

    packet = await codebase_inspector.inspect_connected_codebase(
        owner_user_id=USER_A.id,
        question="Where is the health check?",
        github=github,
        repository_store=FakeRepositoryStore(connected_record()),
        config=runner_settings(),
    )

    assert github.requests == [(55, 101)]
    assert packet.repository == "openfde/example"
    assert packet.commit_sha == "b" * 40
    assert [reference.path for reference in packet.references] == ["app.py"]
    assert "missing.py" in packet.limitations[0]
    assert checkout_paths and not checkout_paths[0].exists()


def test_evidence_filter_rejects_sensitive_paths(tmp_path):
    (tmp_path / ".env").write_text("SECRET=value\n", encoding="utf-8")
    output = CodexInspectionOutput(
        summary="No secret values are included.",
        findings=[],
        references=[
            {
                "path": ".env",
                "start_line": 1,
                "end_line": 1,
                "relevance": "Should never be exposed.",
            }
        ],
        files_inspected=[".env"],
        limitations=[],
    )

    verified = codebase_inspector._verify_evidence(output, tmp_path)

    assert verified.references == []
    assert verified.files_inspected == []
    assert "sensitive-file" in verified.limitations[0]


@pytest.mark.anyio
async def test_inspector_requires_connected_selected_repository():
    with pytest.raises(
        codebase_inspector.CodebaseInspectionError,
        match="Connect GitHub",
    ):
        await codebase_inspector.inspect_connected_codebase(
            owner_user_id=USER_A.id,
            question="What does the API do?",
            github=FakeGitHub(),
            repository_store=FakeRepositoryStore(None),
            config=runner_settings(),
        )
