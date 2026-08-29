from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DesignChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)


class DesignChatRequest(BaseModel):
    agent_name: str | None = Field(default=None, max_length=200)
    messages: list[DesignChatMessage] = Field(min_length=1, max_length=40)
    enabled_connector_ids: list[str] = Field(default_factory=list, max_length=20)
    skill_id: str | None = Field(default=None, max_length=100)


class DesignChatResponse(BaseModel):
    assistant_message: str
    suggested_agent_name: str
    readiness_score: int = Field(ge=0, le=100)
    missing_information: list[str]
    can_generate_design: bool


class CanvasNodeData(BaseModel):
    label: str
    description: str
    kind: Literal["start", "message", "knowledge", "decision", "action", "finish"]


class CanvasPosition(BaseModel):
    x: float
    y: float


class CanvasNode(BaseModel):
    id: str
    type: Literal["journey"] = "journey"
    position: CanvasPosition
    data: CanvasNodeData


class CanvasEdge(BaseModel):
    id: str
    source: str
    target: str


class CanvasDocument(BaseModel):
    nodes: list[CanvasNode]
    edges: list[CanvasEdge]
    createdAt: int


class EvalDatasetCase(BaseModel):
    id: str
    input: str
    expected_output: str
    reference_context: list[str] = Field(default_factory=list)
    grading: dict[str, Any]
    expected_tools: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalDatasetExports(BaseModel):
    eval_source_jsonl: str
    promptfoo_jsonl: str
    deepeval_jsonl: str


class KnowledgeSourceDraft(BaseModel):
    id: str
    title: str
    source_type: Literal["file", "url", "connector", "manual", "generated"]
    description: str
    required: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntentDraft(BaseModel):
    id: str
    name: str
    trigger: str
    expected_outcome: str
    required_tools: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DesignArtifactRequest(BaseModel):
    agent_name: str = Field(min_length=1, max_length=200)
    messages: list[DesignChatMessage] = Field(min_length=1, max_length=60)
    enabled_connector_ids: list[str] = Field(default_factory=list, max_length=20)
    skill_id: str | None = Field(default=None, max_length=100)


class DesignArtifactResponse(BaseModel):
    agent_name: str
    markdown: str
    canvas: CanvasDocument
    mermaid: str
    knowledge_sources: list[KnowledgeSourceDraft]
    intents: list[IntentDraft]
    datasets: list[EvalDatasetCase]
    dataset_exports: EvalDatasetExports
