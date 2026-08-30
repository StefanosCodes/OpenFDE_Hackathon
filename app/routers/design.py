from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.settings import Settings, get_settings
from app.integrations.github.client import GitHubClient
from app.integrations.github.repository import (
    GitHubConnectionRepository,
    get_github_connection_repository,
)
from app.schemas.codebase import CodebaseEvidencePacket
from app.schemas.design import (
    DesignArtifactRequest,
    DesignArtifactResponse,
    DesignChatRequest,
    DesignChatResponse,
)
from app.services import design_agent
from app.services.codebase_inspector import inspect_connected_codebase


router = APIRouter(prefix="/agent-design", tags=["agent design"])


@router.post("/chat", response_model=DesignChatResponse)
async def design_chat(
    body: DesignChatRequest,
    user: CurrentUser = Depends(get_current_user),
    config: Settings = Depends(get_settings),
    repository: GitHubConnectionRepository = Depends(
        get_github_connection_repository
    ),
) -> DesignChatResponse:
    inspector: design_agent.InspectCodebase | None = None
    if "github" in body.enabled_connector_ids:
        connection = await repository.get(user.id)
        if (
            connection is not None
            and connection.status == "connected"
            and connection.installation_id is not None
            and connection.repository is not None
        ):
            github = GitHubClient(config)

            async def inspect(question: str) -> CodebaseEvidencePacket:
                return await inspect_connected_codebase(
                    owner_user_id=user.id,
                    question=question,
                    github=github,
                    repository_store=repository,
                    config=config,
                )

            inspector = inspect
    return await design_agent.design_chat(body, inspect_codebase=inspector)


@router.post("/artifact", response_model=DesignArtifactResponse)
async def design_artifact(
    body: DesignArtifactRequest,
    _user: CurrentUser = Depends(get_current_user),
) -> DesignArtifactResponse:
    return await design_agent.design_artifact(body)
