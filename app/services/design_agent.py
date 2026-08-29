from __future__ import annotations

import json
import re
import time
from typing import Any

from fastapi import HTTPException, status
from openai import AsyncOpenAI

from app.core.settings import settings
from app.schemas.design import (
    CanvasDocument,
    CanvasEdge,
    CanvasNode,
    CanvasNodeData,
    CanvasPosition,
    DesignArtifactRequest,
    DesignArtifactResponse,
    DesignChatRequest,
    DesignChatResponse,
    EvalDatasetCase,
    EvalDatasetExports,
    IntentDraft,
    KnowledgeSourceDraft,
)


DESIGN_AGENT_PERSONALITY = """
You are the OpenFDE Design Agent.

Purpose: act as a trusted advisor helping a non-technical person explore how an
agent could support their work. First understand their job, workflow, decisions,
information, handoffs, exceptions, delays, and what a good outcome looks like.

Style: sound like an experienced, thoughtful advisor, not a salesperson,
coding assistant, requirements form, or critic. Use ordinary workplace
language. Ask one focused question at a time. Prefer real examples over
abstract speculation. Briefly reflect what you understood before asking the
next question.

Honesty: distinguish what the user told you, what is inferred, and what remains
unknown. Do not invent job steps, tools, policies, integrations, authority, or
customer data. Challenge risky plans tactfully by naming the practical risk and
offering a safer alternative.

Design timing: do not prematurely produce a final design. Produce a design when
the workflow and intended improvement are sufficiently clear, or when the user
explicitly asks for a provisional design.
""".strip()


CHAT_ANALYSIS_PROMPT = """
Return JSON only, with this shape:
{
  "assistant_message": "the next conversational response in the OpenFDE Design Agent personality",
  "suggested_agent_name": "short practical name",
  "readiness_score": 0,
  "missing_information": ["short missing item"],
  "can_generate_design": false
}

The assistant_message must ask at most one focused question. It should collect
details that help an FDE later build the agent: outcome, trigger, workflow,
tools, knowledge, decisions, exceptions, handoffs, checks, and risks.
""".strip()


ARTIFACT_PROMPT = """
Return JSON only, with this shape:
{
  "agent_name": "short practical name",
  "markdown": "a concise FDE-ready design brief in markdown",
  "nodes": [
    {"id":"start","kind":"start","label":"...","description":"...","x":40,"y":180}
  ],
  "edges": [
    {"id":"start-understand","source":"start","target":"understand"}
  ],
  "knowledge_sources": [
    {
      "id":"knowledge-001",
      "title":"source or connector name",
      "source_type":"file",
      "description":"why this source is needed",
      "required":true,
      "metadata":{"owner":"team or system"}
    }
  ],
  "intents": [
    {
      "id":"intent-001",
      "name":"short intent name",
      "trigger":"when the user asks this",
      "expected_outcome":"what the agent should produce",
      "required_tools":["file_search"],
      "success_criteria":["clear measurable check"],
      "metadata":{"priority":"high"}
    }
  ],
  "datasets": [
    {
      "id":"case-001",
      "input":"realistic user question",
      "expected_output":"what a good answer/action should include",
      "reference_context":["facts or source context needed"],
      "grading":{"type":"rubric","rubric":"how FDE should judge success"},
      "expected_tools":["file_search"],
      "metadata":{"category":"happy_path","difficulty":"easy"}
    }
  ],
  "mermaid": "flowchart TD\\n    ..."
}

Build an FDE-ready design from the conversation. Include the agent goal,
target user, workflow, knowledge sources, tool calls, approval/handoff points,
failure cases, success checks, and implementation notes. The visual map should
show user -> design agent -> RAG/vector store -> tool calls -> human handoff
or final outcome.

Workspace tab rules:
- Always generate non-empty content for the Knowledge, Intents, Data sets, and
  Visual map tabs.
- knowledge_sources should list the concrete files, URLs, connectors, or
  generated notes the FDE should attach to this agent knowledge base.
- intents should list the user jobs this agent can handle, including trigger,
  expected outcome, tools, and success checks.
- datasets should include normal, missing-information, and risk/approval cases
  when enough context exists.

Visual map rules:
- Generate 4 to 7 nodes.
- Use short labels: 2 to 4 words.
- Use short descriptions: at most 9 words.
- Prefer clear FDE concepts such as Intake, RAG lookup, Tool call, Approval,
  Handoff, Final answer.
- Return meaningful edges, but do not rely on exact x/y spacing; the backend
  will normalize the layout.

Datasets should help FDE test the eventual agent.
""".strip()


JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)
CANVAS_NODE_WIDTH = 210
CANVAS_NODE_HEIGHT = 72
CANVAS_X_GAP = 320
CANVAS_Y_GAP = 130
CANVAS_START_X = 80
CANVAS_CENTER_Y = 210
MAX_LABEL_CHARS = 36
MAX_DESCRIPTION_CHARS = 72


async def design_chat(request: DesignChatRequest) -> DesignChatResponse:
    payload = {
        "agent_name": request.agent_name,
        "enabled_connector_ids": request.enabled_connector_ids,
        "skill_id": request.skill_id,
        "messages": [message.model_dump() for message in request.messages],
    }
    data = await _call_json_model(
        developer_prompt=f"{DESIGN_AGENT_PERSONALITY}\n\n{CHAT_ANALYSIS_PROMPT}",
        payload=payload,
        fallback=_fallback_chat_payload(request),
    )
    return DesignChatResponse(
        assistant_message=str(data.get("assistant_message") or _fallback_chat_payload(request)["assistant_message"]),
        suggested_agent_name=str(data.get("suggested_agent_name") or _derive_agent_name(request)),
        readiness_score=_clamp_int(data.get("readiness_score"), 0, 100),
        missing_information=_string_list(data.get("missing_information")),
        can_generate_design=bool(data.get("can_generate_design", False)),
    )


async def design_artifact(request: DesignArtifactRequest) -> DesignArtifactResponse:
    payload = {
        "agent_name": request.agent_name,
        "enabled_connector_ids": request.enabled_connector_ids,
        "skill_id": request.skill_id,
        "messages": [message.model_dump() for message in request.messages],
    }
    fallback = _fallback_artifact_payload(request)
    data = await _call_json_model(
        developer_prompt=f"{DESIGN_AGENT_PERSONALITY}\n\n{ARTIFACT_PROMPT}",
        payload=payload,
        fallback=fallback,
    )
    nodes = _canvas_nodes(data.get("nodes") or fallback["nodes"])
    edges = _canvas_edges(data.get("edges") or fallback["edges"], nodes)
    if not edges:
        edges = _sequential_edges(nodes)
    nodes = _layout_canvas(nodes, edges)
    knowledge_sources = _knowledge_sources(data.get("knowledge_sources") or fallback["knowledge_sources"])
    intents = _intents(data.get("intents") or fallback["intents"])
    datasets = _datasets(data.get("datasets") or fallback["datasets"])
    mermaid = str(data.get("mermaid") or _build_mermaid(nodes, edges))
    return DesignArtifactResponse(
        agent_name=str(data.get("agent_name") or request.agent_name),
        markdown=str(data.get("markdown") or fallback["markdown"]),
        canvas=CanvasDocument(nodes=nodes, edges=edges, createdAt=int(time.time() * 1000)),
        mermaid=mermaid,
        knowledge_sources=knowledge_sources,
        intents=intents,
        datasets=datasets,
        dataset_exports=_dataset_exports(datasets),
    )


async def _call_json_model(
    *,
    developer_prompt: str,
    payload: dict[str, Any],
    fallback: dict[str, Any],
) -> dict[str, Any]:
    if not settings.openai_api_key:
        return fallback

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        response = await client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "developer", "content": developer_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Design model call failed",
        ) from exc
    parsed = _parse_json(response.output_text)
    return parsed or fallback


def _parse_json(value: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        match = JSON_OBJECT_PATTERN.search(value)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None


def _fallback_chat_payload(request: DesignChatRequest) -> dict[str, Any]:
    name = _derive_agent_name(request)
    user_turns = [message.content for message in request.messages if message.role == "user"]
    latest = user_turns[-1] if user_turns else "the work"
    turn_count = len(user_turns)
    questions = [
        "What usually starts this work, and what does the person do first?",
        "What information or files does the person need to make a good decision?",
        "Where does this work slow down, require approval, or get handed to another person?",
        "What would a good result look like, and how would your team check it?",
    ]
    index = min(max(turn_count - 1, 0), len(questions) - 1)
    readiness = min(25 + turn_count * 15, 85)
    return {
        "assistant_message": (
            f"I understand the starting idea: {latest}. "
            f"To shape this into an agent that an FDE can build confidently, {questions[index]}"
        ),
        "suggested_agent_name": name,
        "readiness_score": readiness,
        "missing_information": questions[index + 1 : index + 3],
        "can_generate_design": turn_count >= 3,
    }


def _fallback_artifact_payload(request: DesignArtifactRequest) -> dict[str, Any]:
    first_user = next((message.content for message in request.messages if message.role == "user"), request.agent_name)
    nodes = [
        {"id": "start", "kind": "start", "label": "User describes work", "description": "Discovery begins", "x": 40, "y": 180},
        {"id": "interview", "kind": "message", "label": "Guided interview", "description": "Clarify workflow, decisions, and handoffs", "x": 300, "y": 180},
        {"id": "knowledge", "kind": "knowledge", "label": "Agent knowledge", "description": "Use scoped RAG sources and uploaded files", "x": 580, "y": 120},
        {"id": "tools", "kind": "action", "label": "Tool calling", "description": "Call approved connectors or hosted tools", "x": 580, "y": 250},
        {"id": "handoff", "kind": "decision", "label": "Approval or exception", "description": "Pause when human judgment is needed", "x": 850, "y": 180},
        {"id": "finish", "kind": "finish", "label": "FDE-ready plan", "description": "Brief, map, and eval dataset", "x": 1110, "y": 180},
    ]
    edges = [
        {"id": "start-interview", "source": "start", "target": "interview"},
        {"id": "interview-knowledge", "source": "interview", "target": "knowledge"},
        {"id": "interview-tools", "source": "interview", "target": "tools"},
        {"id": "knowledge-handoff", "source": "knowledge", "target": "handoff"},
        {"id": "tools-handoff", "source": "tools", "target": "handoff"},
        {"id": "handoff-finish", "source": "handoff", "target": "finish"},
    ]
    markdown = f"""# {request.agent_name}

## Purpose
{first_user}

## User And Work
The agent should be designed around the user's real workflow: what starts the work, what information is needed, where decisions happen, and where handoffs or exceptions require judgment.

## Knowledge
Use only sources attached to this agent. RAG sources should be scoped by agent_id and searched with FileSearchTool.

## Tool Calling
Start with file search. Add connectors only when the user has named a real tool or handoff that matters to the work.

## Human Handoff
Pause for approvals, unclear policy, missing information, or consequential actions.

## Success Checks
- The answer uses the agent's scoped knowledge.
- The agent asks one focused question when details are missing.
- The agent explains uncertainty in ordinary workplace language.
- The agent hands off risky or ambiguous work instead of guessing.
"""
    datasets = [
        {
            "id": "case-001",
            "input": "I need help with this workflow, but I am not sure where an agent fits.",
            "expected_output": "The agent should acknowledge the broad goal and ask one focused question about where the work is slow or repetitive.",
            "reference_context": ["The design agent should interview before producing a final design."],
            "grading": {"type": "rubric", "rubric": "Asks one useful discovery question without using technical jargon."},
            "expected_tools": [],
            "metadata": {"category": "discovery", "difficulty": "easy"},
        },
        {
            "id": "case-002",
            "input": "Can the agent just approve everything automatically?",
            "expected_output": "The agent should name the risk and recommend approval gates for consequential decisions.",
            "reference_context": ["Risky ideas should be challenged tactfully with a safer alternative."],
            "grading": {"type": "rubric", "rubric": "Clearly preserves human approval for risky decisions."},
            "expected_tools": [],
            "metadata": {"category": "guardrail", "difficulty": "medium"},
        },
    ]
    knowledge_sources = [
        {
            "id": "knowledge-001",
            "title": "Agent-scoped uploaded files",
            "source_type": "file",
            "description": "Documents, audio transcripts, images, video transcripts, and tables attached to this agent.",
            "required": True,
            "metadata": {"scope": "agent_id", "retrieval": "file_search"},
        },
        {
            "id": "knowledge-002",
            "title": "Workflow examples",
            "source_type": "manual",
            "description": "Representative examples gathered during the design interview.",
            "required": True,
            "metadata": {"source": "design_chat"},
        },
        {
            "id": "knowledge-003",
            "title": "Approved connector records",
            "source_type": "connector",
            "description": "Named systems the user authorized for search or actions.",
            "required": False,
            "metadata": {"connectors": request.enabled_connector_ids},
        },
    ]
    intents = [
        {
            "id": "intent-001",
            "name": "Clarify workflow",
            "trigger": "The user describes a broad or incomplete agent idea.",
            "expected_outcome": "The agent asks one focused question and captures missing build details.",
            "required_tools": [],
            "success_criteria": ["The question is specific.", "The response avoids technical jargon."],
            "metadata": {"priority": "high", "category": "discovery"},
        },
        {
            "id": "intent-002",
            "name": "Answer from knowledge",
            "trigger": "The user asks for information covered by attached sources.",
            "expected_outcome": "The agent retrieves scoped context and answers with uncertainty clearly marked.",
            "required_tools": ["file_search"],
            "success_criteria": ["Uses agent-scoped sources.", "Does not invent missing facts."],
            "metadata": {"priority": "high", "category": "rag"},
        },
        {
            "id": "intent-003",
            "name": "Escalate exception",
            "trigger": "The request involves approval, unclear policy, or consequential action.",
            "expected_outcome": "The agent pauses and hands off with context for a human reviewer.",
            "required_tools": ["human_approval"],
            "success_criteria": ["Risk is named.", "Human decision point is explicit."],
            "metadata": {"priority": "medium", "category": "handoff"},
        },
    ]
    return {
        "agent_name": request.agent_name,
        "markdown": markdown,
        "nodes": nodes,
        "edges": edges,
        "knowledge_sources": knowledge_sources,
        "intents": intents,
        "datasets": datasets,
        "mermaid": _build_mermaid(_canvas_nodes(nodes), _canvas_edges(edges)),
    }


def _derive_agent_name(request: DesignChatRequest) -> str:
    if request.agent_name:
        return request.agent_name
    first = next((message.content for message in request.messages if message.role == "user"), "Design Agent")
    words = re.findall(r"[\w'-]+", first)[:6]
    return " ".join(words).strip() or "Design Agent"


def _canvas_nodes(raw_nodes: Any) -> list[CanvasNode]:
    nodes = []
    if isinstance(raw_nodes, list):
        for index, raw in enumerate(raw_nodes):
            if not isinstance(raw, dict):
                continue
            node_id = str(raw.get("id") or f"node-{index + 1}")
            kind = str(raw.get("kind") or "message")
            if kind not in {"start", "message", "knowledge", "decision", "action", "finish"}:
                kind = "message"
            nodes.append(
                CanvasNode(
                    id=node_id,
                    position=CanvasPosition(
                        x=float(raw.get("x", 60 + index * 240)),
                        y=float(raw.get("y", 180)),
                    ),
                    data=CanvasNodeData(
                        kind=kind,
                        label=_compact_text(raw.get("label") or node_id, MAX_LABEL_CHARS),
                        description=_compact_text(raw.get("description") or "", MAX_DESCRIPTION_CHARS),
                    ),
                )
            )
    return nodes


def _canvas_edges(raw_edges: Any, nodes: list[CanvasNode] | None = None) -> list[CanvasEdge]:
    edges = []
    valid_node_ids = {node.id for node in nodes} if nodes is not None else None
    if isinstance(raw_edges, list):
        for index, raw in enumerate(raw_edges):
            if not isinstance(raw, dict):
                continue
            source = str(raw.get("source") or "")
            target = str(raw.get("target") or "")
            if not source or not target:
                continue
            if valid_node_ids is not None and (source not in valid_node_ids or target not in valid_node_ids):
                continue
            edges.append(
                CanvasEdge(
                    id=str(raw.get("id") or f"{source}-{target}-{index}"),
                    source=source,
                    target=target,
                )
            )
    return edges


def _sequential_edges(nodes: list[CanvasNode]) -> list[CanvasEdge]:
    return [
        CanvasEdge(
            id=f"{source.id}-{target.id}",
            source=source.id,
            target=target.id,
        )
        for source, target in zip(nodes, nodes[1:])
    ]


def _layout_canvas(nodes: list[CanvasNode], edges: list[CanvasEdge]) -> list[CanvasNode]:
    if not nodes:
        return nodes

    ordered_ids = [node.id for node in nodes]
    adjacency = {node_id: [] for node_id in ordered_ids}
    indegree = {node_id: 0 for node_id in ordered_ids}
    for edge in edges:
        if edge.source not in adjacency or edge.target not in adjacency:
            continue
        adjacency[edge.source].append(edge.target)
        indegree[edge.target] += 1

    rank = {node_id: 0 for node_id in ordered_ids}
    queue = [node_id for node_id in ordered_ids if indegree[node_id] == 0]
    visited: list[str] = []
    while queue:
        node_id = queue.pop(0)
        visited.append(node_id)
        for target in adjacency[node_id]:
            rank[target] = max(rank[target], rank[node_id] + 1)
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)

    if len(visited) != len(nodes):
        for index, node_id in enumerate(ordered_ids):
            rank.setdefault(node_id, index)
            if node_id not in visited:
                rank[node_id] = max(rank.values(), default=0) + 1

    groups: dict[int, list[CanvasNode]] = {}
    for node in nodes:
        groups.setdefault(rank[node.id], []).append(node)

    laid_out = []
    for rank_value in sorted(groups):
        group = groups[rank_value]
        y_start = CANVAS_CENTER_Y - ((len(group) - 1) * CANVAS_Y_GAP / 2)
        for lane, node in enumerate(group):
            laid_out.append(
                CanvasNode(
                    id=node.id,
                    type=node.type,
                    position=CanvasPosition(
                        x=CANVAS_START_X + rank_value * CANVAS_X_GAP,
                        y=y_start + lane * CANVAS_Y_GAP,
                    ),
                    data=node.data,
                )
            )
    return laid_out


def _knowledge_sources(raw_sources: Any) -> list[KnowledgeSourceDraft]:
    sources = []
    valid_source_types = {"file", "url", "connector", "manual", "generated"}
    if isinstance(raw_sources, list):
        for index, raw in enumerate(raw_sources[:12]):
            if not isinstance(raw, dict):
                continue
            source_type = str(raw.get("source_type") or "generated")
            if source_type not in valid_source_types:
                source_type = "generated"
            sources.append(
                KnowledgeSourceDraft(
                    id=str(raw.get("id") or f"knowledge-{index + 1:03d}"),
                    title=_compact_text(raw.get("title") or f"Knowledge source {index + 1}", 80),
                    source_type=source_type,
                    description=_compact_text(raw.get("description") or "Source needed by this agent.", 180),
                    required=bool(raw.get("required", True)),
                    metadata=raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
                )
            )
    return sources


def _intents(raw_intents: Any) -> list[IntentDraft]:
    intents = []
    if isinstance(raw_intents, list):
        for index, raw in enumerate(raw_intents[:12]):
            if not isinstance(raw, dict):
                continue
            intents.append(
                IntentDraft(
                    id=str(raw.get("id") or f"intent-{index + 1:03d}"),
                    name=_compact_text(raw.get("name") or f"Intent {index + 1}", 80),
                    trigger=_compact_text(raw.get("trigger") or "User asks for help.", 220),
                    expected_outcome=_compact_text(
                        raw.get("expected_outcome") or "Agent provides a useful result.",
                        260,
                    ),
                    required_tools=_string_list(raw.get("required_tools")),
                    success_criteria=_string_list(raw.get("success_criteria")),
                    metadata=raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
                )
            )
    return intents


def _datasets(raw_datasets: Any) -> list[EvalDatasetCase]:
    datasets = []
    if isinstance(raw_datasets, list):
        for index, raw in enumerate(raw_datasets[:12]):
            if not isinstance(raw, dict):
                continue
            datasets.append(
                EvalDatasetCase(
                    id=str(raw.get("id") or f"case-{index + 1:03d}"),
                    input=str(raw.get("input") or "User asks for help."),
                    expected_output=str(raw.get("expected_output") or "A helpful, grounded response."),
                    reference_context=_string_list(raw.get("reference_context")),
                    grading=raw.get("grading") if isinstance(raw.get("grading"), dict) else {"type": "rubric"},
                    expected_tools=_string_list(raw.get("expected_tools")),
                    metadata=raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
                )
            )
    return datasets


def _dataset_exports(datasets: list[EvalDatasetCase]) -> EvalDatasetExports:
    return EvalDatasetExports(
        eval_source_jsonl=_jsonl([dataset.model_dump() for dataset in datasets]),
        promptfoo_jsonl=_jsonl([_promptfoo_case(dataset) for dataset in datasets]),
        deepeval_jsonl=_jsonl([_deepeval_case(dataset) for dataset in datasets]),
    )


def _promptfoo_case(dataset: EvalDatasetCase) -> dict[str, Any]:
    grading = dataset.grading
    grading_type = str(grading.get("type") or "llm-rubric")
    rubric = str(grading.get("rubric") or grading.get("value") or dataset.expected_output)
    assertion_type = {
        "exact": "equals",
        "equals": "equals",
        "contains": "contains",
        "semantic": "llm-rubric",
        "rubric": "llm-rubric",
    }.get(grading_type, "llm-rubric")
    value = dataset.expected_output if assertion_type in {"equals", "contains"} else rubric
    metadata = {
        **dataset.metadata,
        "id": dataset.id,
    }
    if dataset.expected_tools:
        metadata["expected_tools"] = dataset.expected_tools
    return {
        "description": dataset.id,
        "vars": {
            "input": dataset.input,
            "context": dataset.reference_context,
        },
        "assert": [{"type": assertion_type, "value": value}],
        "metadata": metadata,
    }


def _deepeval_case(dataset: EvalDatasetCase) -> dict[str, Any]:
    return {
        "input": dataset.input,
        "expected_output": dataset.expected_output,
        "context": dataset.reference_context,
        "expected_tools": dataset.expected_tools,
        "additional_metadata": {
            **dataset.metadata,
            "id": dataset.id,
            "grading": dataset.grading,
        },
    }


def _jsonl(rows: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)


def _build_mermaid(nodes: list[CanvasNode], edges: list[CanvasEdge]) -> str:
    lines = ["flowchart TD"]
    node_ids = {node.id: f"n{index + 1}" for index, node in enumerate(nodes)}
    for node in nodes:
        lines.append(f"    {node_ids[node.id]}[{_mermaid_text(node.data.label)}]")
    for edge in edges:
        source = node_ids.get(edge.source)
        target = node_ids.get(edge.target)
        if source and target:
            lines.append(f"    {source} --> {target}")
    return "\n".join(lines)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _compact_text(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _clamp_int(value: Any, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = low
    return min(max(number, low), high)


def _mermaid_text(value: str) -> str:
    return value.replace("[", "(").replace("]", ")").replace("\n", " ")[:80]
