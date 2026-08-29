from uuid import UUID, uuid4

import asyncpg
from fastapi import HTTPException, status

from app.agents_runtime.openai_adapter import OpenAIAdapter
from app.agents_runtime.runner import run_agent_with_file_search
from app.core.auth import CurrentUser
from app.core.database import get_pool, transaction
from app.core.http import not_found
from app.schemas.agents import AgentResponse


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
