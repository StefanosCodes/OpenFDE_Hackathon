from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


GitHubConnectionStatus = Literal[
    "disconnected",
    "connecting",
    "awaiting_repository",
    "connected",
    "error",
]


class GitHubRepository(BaseModel):
    id: int
    full_name: str
    private: bool
    default_branch: str


class GitHubConnectResponse(BaseModel):
    status: Literal["connecting"]
    connect_url: str
    expires_in_seconds: int = 600


class GitHubRepositorySelection(BaseModel):
    repository_id: int = Field(gt=0)


class GitHubConnectionResponse(BaseModel):
    status: GitHubConnectionStatus
    account_login: str | None = None
    repository: GitHubRepository | None = None
    last_error: str | None = None
    updated_at: datetime | None = None

    @classmethod
    def disconnected(cls) -> "GitHubConnectionResponse":
        return cls(status="disconnected")
