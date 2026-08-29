from __future__ import annotations

from fastapi import APIRouter

from app.schemas.design import (
    DesignArtifactRequest,
    DesignArtifactResponse,
    DesignChatRequest,
    DesignChatResponse,
)
from app.services import design_agent


router = APIRouter(prefix="/agent-design", tags=["agent design"])


@router.post("/chat", response_model=DesignChatResponse)
async def design_chat(body: DesignChatRequest) -> DesignChatResponse:
    return await design_agent.design_chat(body)


@router.post("/artifact", response_model=DesignArtifactResponse)
async def design_artifact(body: DesignArtifactRequest) -> DesignArtifactResponse:
    return await design_agent.design_artifact(body)
