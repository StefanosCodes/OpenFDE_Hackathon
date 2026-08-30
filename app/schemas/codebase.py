from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class CodeEvidenceReference(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    relevance: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_line_range(self) -> "CodeEvidenceReference":
        if self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        if self.path.startswith(("/", "\\")) or ".." in self.path.split("/"):
            raise ValueError("evidence paths must be repository-relative")
        return self


class CodebaseEvidencePacket(BaseModel):
    repository: str
    commit_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    summary: str
    findings: list[str] = Field(default_factory=list, max_length=20)
    references: list[CodeEvidenceReference] = Field(default_factory=list, max_length=30)
    files_inspected: list[str] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(default_factory=list, max_length=20)
    generated_at: datetime


class CodexInspectionOutput(BaseModel):
    summary: str = Field(min_length=1, max_length=10000)
    findings: list[str] = Field(default_factory=list, max_length=20)
    references: list[CodeEvidenceReference] = Field(default_factory=list, max_length=30)
    files_inspected: list[str] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(default_factory=list, max_length=20)
