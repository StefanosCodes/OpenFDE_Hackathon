from __future__ import annotations

from uuid import UUID, uuid4

import asyncpg
from fastapi import HTTPException, status

from app.agents_runtime.openai_adapter import OpenAIAdapter
from app.agents_runtime.runner import run_agent_with_file_search
from app.core.auth import CurrentUser
from app.core.database import get_pool, transaction
from app.core.http import not_found
from app.schemas.agents import AgentDesignPreviewRequest, AgentDesignPreviewResponse, AgentDesignTool, AgentResponse


def _agent_from_record(row: asyncpg.Record) -> AgentResponse:
    return AgentResponse(
        id=row["id"],
        owner_user_id=row["owner_user_id"],
        name=row["name"],
        openai_vector_store_id=row["openai_vector_store_id"],
        created_at=row["created_at"],
    )


async def create_agent(
    *,
    user: CurrentUser,
    name: str,
    openai: OpenAIAdapter,
) -> AgentResponse:
    vector_store = await openai.create_vector_store(name=f"agent:{user.id}:{name}")
    agent_id = uuid4()
    try:
        row = await get_pool().fetchrow(
            """
            INSERT INTO agents (id, owner_user_id, name, openai_vector_store_id)
            VALUES ($1, $2, $3, $4)
            RETURNING id, owner_user_id, name, openai_vector_store_id, created_at
            """,
            agent_id,
            user.id,
            name,
            vector_store.id,
        )
    except Exception:
        await openai.delete_vector_store(vector_store.id)
        raise
    return _agent_from_record(row)


async def list_agents(*, user: CurrentUser, limit: int) -> list[AgentResponse]:
    rows = await get_pool().fetch(
        """
        SELECT id, owner_user_id, name, openai_vector_store_id, created_at
        FROM agents
        WHERE owner_user_id = $1
        ORDER BY created_at DESC, id DESC
        LIMIT $2
        """,
        user.id,
        limit,
    )
    return [_agent_from_record(row) for row in rows]


async def get_agent(*, user: CurrentUser, agent_id: UUID) -> AgentResponse:
    row = await get_pool().fetchrow(
        """
        SELECT id, owner_user_id, name, openai_vector_store_id, created_at
        FROM agents
        WHERE id = $1
          AND owner_user_id = $2
        """,
        agent_id,
        user.id,
    )
    if row is None:
        raise not_found()
    return _agent_from_record(row)


async def delete_agent(
    *,
    user: CurrentUser,
    agent_id: UUID,
    openai: OpenAIAdapter,
) -> None:
    agent = await get_agent(user=user, agent_id=agent_id)
    await openai.delete_vector_store(agent.openai_vector_store_id)
    async with transaction() as conn:
        deleted = await conn.execute(
            """
            DELETE FROM agents
            WHERE id = $1
              AND owner_user_id = $2
            """,
            agent_id,
            user.id,
        )
    if deleted == "DELETE 0":
        raise not_found()


async def run_agent(
    *,
    user: CurrentUser,
    agent_id: UUID,
    message: str,
) -> str:
    agent = await get_agent(user=user, agent_id=agent_id)
    try:
        return await run_agent_with_file_search(
            agent_name=agent.name,
            vector_store_id=agent.openai_vector_store_id,
            message=message,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent run failed",
        ) from exc


async def preview_agent_design_from_draft(
    *,
    body: AgentDesignPreviewRequest,
) -> AgentDesignPreviewResponse:
    source_counts = {source_type: 0 for source_type in _dedupe(body.source_types)}
    return _build_design_preview(
        agent_name=body.name,
        goal=body.goal,
        instructions=body.instructions,
        vector_store_id=None,
        source_counts=source_counts,
        enabled_tools=body.enabled_tools,
    )


async def preview_agent_design(
    *,
    user: CurrentUser,
    agent_id: UUID,
) -> AgentDesignPreviewResponse:
    agent = await get_agent(user=user, agent_id=agent_id)
    rows = await get_pool().fetch(
        """
        SELECT ks.source_type, COUNT(*) AS source_count
        FROM knowledge_sources ks
        JOIN agents a ON a.id = ks.agent_id
        WHERE ks.agent_id = $1
          AND a.owner_user_id = $2
        GROUP BY ks.source_type
        ORDER BY ks.source_type
        """,
        agent_id,
        user.id,
    )
    source_counts = {row["source_type"]: row["source_count"] for row in rows}
    return _build_design_preview(
        agent_name=agent.name,
        goal=None,
        instructions=None,
        vector_store_id=agent.openai_vector_store_id,
        source_counts=source_counts,
        enabled_tools=["file_search"],
    )


def _build_design_preview(
    *,
    agent_name: str,
    goal: str | None,
    instructions: str | None,
    vector_store_id: str | None,
    source_counts: dict[str, int],
    enabled_tools: list[str],
) -> AgentDesignPreviewResponse:
    source_types = sorted(source_counts) or ["markdown", "pdf", "url"]
    tool_names = set(enabled_tools)
    tools = [
        AgentDesignTool(
            name="file_search",
            kind="OpenAI hosted tool",
            purpose="Search only this agent's OpenAI Vector Store.",
            enabled="file_search" in tool_names,
        )
    ]
    if "audio" in source_types:
        tools.append(
            AgentDesignTool(
                name="audio_transcription",
                kind="ingest adapter",
                purpose="Convert audio files into transcript text before retrieval.",
            )
        )
    if "video" in source_types:
        tools.append(
            AgentDesignTool(
                name="video_transcription",
                kind="ingest adapter",
                purpose="Convert supported video files into transcript text before retrieval.",
            )
        )
    if "image" in source_types:
        tools.append(
            AgentDesignTool(
                name="image_understanding",
                kind="ingest adapter",
                purpose="Convert image text and visual content into searchable notes.",
            )
        )
    tools.append(
        AgentDesignTool(
            name="design_preview",
            kind="planning artifact",
            purpose="Expose the agent, source, and tool-calling graph to FDE before handoff.",
        )
    )

    flow_steps = [
        "User selects or drafts an agent.",
        "Knowledge sources are scoped to that agent_id.",
        "Each source is validated and converted when needed.",
        "Searchable text or supported files are attached to the agent vector store.",
        "Agent run loads FileSearchTool with only this vector_store_id.",
        "The model answers with retrieval constrained to this agent.",
    ]
    if goal:
        flow_steps.insert(1, f"Goal: {goal}")
    if instructions:
        flow_steps.insert(2, "Custom instructions are included in the final agent configuration.")

    summary = (
        f"{agent_name} is an agent-scoped RAG design using one OpenAI Vector Store. "
        "Postgres stores ownership and source metadata; OpenAI handles chunking, embeddings, and file search."
    )
    return AgentDesignPreviewResponse(
        agent_name=agent_name,
        summary=summary,
        source_types=source_types,
        source_counts=source_counts,
        tools=tools,
        flow_steps=flow_steps,
        mermaid=_build_mermaid(agent_name, source_counts, vector_store_id),
        fde_notes=[
            "Render this preview before creating or handing off the agent.",
            "Do not expose vector_store_id as user-editable input.",
            "Use agent_id as the only client-visible knowledge scope.",
            "Show source status and previews from Postgres metadata.",
        ],
    )


def _build_mermaid(agent_name: str, source_counts: dict[str, int], vector_store_id: str | None) -> str:
    source_label = ", ".join(f"{key}({value})" for key, value in sorted(source_counts.items())) or "planned sources"
    vector_label = vector_store_id or "new vector store on create"
    return "\n".join(
        [
            "flowchart TD",
            f"    FDE[FDE Preview] --> A[Agent: {_mermaid_label(agent_name)}]",
            f"    A --> KB[Knowledge Scope: agent_id]",
            f"    KB --> S[Sources: {_mermaid_label(source_label)}]",
            "    S --> V[Validate type / size / SSRF]",
            "    V --> C{Conversion needed?}",
            "    C -->|audio| T[Transcribe to text]",
            "    C -->|video| VT[Transcribe video audio track to text]",
            "    C -->|image| I[Describe / OCR-style notes]",
            "    C -->|document/data| U[Upload file or extracted text]",
            "    T --> U",
            "    VT --> U",
            "    I --> U",
            f"    U --> VS[OpenAI Vector Store: {_mermaid_label(vector_label)}]",
            "    Q[User question] --> R[Agent Runtime]",
            "    R --> FS[FileSearchTool]",
            "    FS --> VS",
            "    VS --> R",
            "    R --> O[Answer constrained to this agent]",
        ]
    )


def _mermaid_label(value: str) -> str:
    return value.replace("[", "(").replace("]", ")").replace("\n", " ")[:120]


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        key = value.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(key)
    return result
