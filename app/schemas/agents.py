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
