from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class AgentResponse(BaseModel):
    id: UUID
    owner_user_id: UUID
    name: str
    openai_vector_store_id: str
    created_at: datetime


class AgentRunRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)


class AgentRunResponse(BaseModel):
    agent_id: UUID
    answer: str


class AgentDesignPreviewRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    goal: str | None = Field(default=None, max_length=1000)
    instructions: str | None = Field(default=None, max_length=4000)
    source_types: list[str] = Field(default_factory=lambda: ["markdown", "pdf", "url"])
    enabled_tools: list[str] = Field(default_factory=lambda: ["file_search"])


class AgentDesignTool(BaseModel):
    name: str
    kind: str
    purpose: str
    enabled: bool = True


class AgentDesignPreviewResponse(BaseModel):
    agent_name: str
    summary: str
    source_types: list[str]
    source_counts: dict[str, int]
    tools: list[AgentDesignTool]
    flow_steps: list[str]
    mermaid: str
    fde_notes: list[str]
