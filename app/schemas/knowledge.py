from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class UrlSourceCreate(BaseModel):
    url: HttpUrl
    title: str | None = Field(default=None, max_length=500)


class KnowledgeSourceResponse(BaseModel):
    id: UUID
    agent_id: UUID
    source_type: str
    status: str
    title: str
    original_filename: str | None
    source_url: str | None
    content_preview: str | None
    openai_file_id: str | None
    byte_size: int | None
    error_message: str | None
    created_at: datetime
