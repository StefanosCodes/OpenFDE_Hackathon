from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status

from app.agents_runtime.openai_adapter import OpenAIAdapter, get_openai_adapter
from app.core.auth import CurrentUser, get_current_user
from app.schemas.knowledge import KnowledgeSourceResponse, UrlSourceCreate
from app.services import knowledge as knowledge_service


router = APIRouter(prefix="/agents/{agent_id}/knowledge-sources", tags=["knowledge sources"])


@router.post("/markdown", response_model=KnowledgeSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_markdown_source(
    agent_id: UUID,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    openai: OpenAIAdapter = Depends(get_openai_adapter),
) -> KnowledgeSourceResponse:
    return await knowledge_service.create_markdown_source(
        user=user,
        agent_id=agent_id,
        file=file,
        title=title,
        openai=openai,
    )


@router.post("/pdf", response_model=KnowledgeSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_pdf_source(
    agent_id: UUID,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    openai: OpenAIAdapter = Depends(get_openai_adapter),
) -> KnowledgeSourceResponse:
    return await knowledge_service.create_pdf_source(
        user=user,
        agent_id=agent_id,
        file=file,
        title=title,
        openai=openai,
    )


@router.post("/files", response_model=KnowledgeSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_file_source(
    agent_id: UUID,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    openai: OpenAIAdapter = Depends(get_openai_adapter),
) -> KnowledgeSourceResponse:
    return await knowledge_service.create_file_source(
        user=user,
        agent_id=agent_id,
        file=file,
        title=title,
        openai=openai,
    )


@router.post("/url", response_model=KnowledgeSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_url_source(
    agent_id: UUID,
    body: UrlSourceCreate,
    user: CurrentUser = Depends(get_current_user),
    openai: OpenAIAdapter = Depends(get_openai_adapter),
) -> KnowledgeSourceResponse:
    return await knowledge_service.create_url_source(
        user=user,
        agent_id=agent_id,
        url=str(body.url),
        title=body.title,
        openai=openai,
    )


@router.get("", response_model=list[KnowledgeSourceResponse])
async def list_sources(
    agent_id: UUID,
    limit: int = Query(default=20, ge=1, le=50),
    user: CurrentUser = Depends(get_current_user),
) -> list[KnowledgeSourceResponse]:
    return await knowledge_service.list_sources(user=user, agent_id=agent_id, limit=limit)


@router.get("/{source_id}", response_model=KnowledgeSourceResponse)
async def get_source(
    agent_id: UUID,
    source_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> KnowledgeSourceResponse:
    return await knowledge_service.get_source(user=user, agent_id=agent_id, source_id=source_id)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    agent_id: UUID,
    source_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    openai: OpenAIAdapter = Depends(get_openai_adapter),
) -> Response:
    await knowledge_service.delete_source(
        user=user,
        agent_id=agent_id,
        source_id=source_id,
        openai=openai,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
