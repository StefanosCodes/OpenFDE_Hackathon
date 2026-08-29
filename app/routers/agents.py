from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.agents_runtime.openai_adapter import OpenAIAdapter, get_openai_adapter
from app.core.auth import CurrentUser, get_current_user
from app.schemas.agents import (
    AgentCreate,
    AgentDesignPreviewRequest,
    AgentDesignPreviewResponse,
    AgentResponse,
    AgentRunRequest,
    AgentRunResponse,
)
from app.services import agents as agent_service


router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreate,
    user: CurrentUser = Depends(get_current_user),
    openai: OpenAIAdapter = Depends(get_openai_adapter),
) -> AgentResponse:
    return await agent_service.create_agent(user=user, name=body.name, openai=openai)


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    limit: int = Query(default=20, ge=1, le=50),
    user: CurrentUser = Depends(get_current_user),
) -> list[AgentResponse]:
    return await agent_service.list_agents(user=user, limit=limit)


@router.post("/design-preview", response_model=AgentDesignPreviewResponse)
async def preview_agent_design_from_draft(
    body: AgentDesignPreviewRequest,
) -> AgentDesignPreviewResponse:
    return await agent_service.preview_agent_design_from_draft(body=body)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> AgentResponse:
    return await agent_service.get_agent(user=user, agent_id=agent_id)


@router.get("/{agent_id}/design-preview", response_model=AgentDesignPreviewResponse)
async def preview_agent_design(
    agent_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> AgentDesignPreviewResponse:
    return await agent_service.preview_agent_design(user=user, agent_id=agent_id)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    openai: OpenAIAdapter = Depends(get_openai_adapter),
) -> Response:
    await agent_service.delete_agent(user=user, agent_id=agent_id, openai=openai)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{agent_id}/run", response_model=AgentRunResponse)
async def run_agent(
    agent_id: UUID,
    body: AgentRunRequest,
    user: CurrentUser = Depends(get_current_user),
) -> AgentRunResponse:
    answer = await agent_service.run_agent(user=user, agent_id=agent_id, message=body.message)
    return AgentRunResponse(agent_id=agent_id, answer=answer)
