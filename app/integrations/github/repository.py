from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

import asyncpg

from app.core.database import get_pool
from app.schemas.github import GitHubConnectionStatus, GitHubRepository


@dataclass(frozen=True)
class GitHubConnectionRecord:
    owner_user_id: UUID
    status: GitHubConnectionStatus
    installation_id: int | None = None
    account_login: str | None = None
    account_type: str | None = None
    repository: GitHubRepository | None = None
    last_error: str | None = None
    updated_at: datetime | None = None


class GitHubConnectionRepository(Protocol):
    async def begin(self, owner_user_id: UUID) -> None: ...

    async def get(self, owner_user_id: UUID) -> GitHubConnectionRecord | None: ...

    async def save_installation(
        self,
        *,
        owner_user_id: UUID,
        installation_id: int,
        account_login: str,
        account_type: str,
        repositories: list[GitHubRepository],
    ) -> GitHubConnectionRecord: ...

    async def list_repositories(self, owner_user_id: UUID) -> list[GitHubRepository]: ...

    async def select_repository(
        self, *, owner_user_id: UUID, repository_id: int
    ) -> GitHubConnectionRecord: ...

    async def disconnect(self, owner_user_id: UUID) -> None: ...

    async def disconnect_installation(self, installation_id: int, *, reason: str) -> None: ...

    async def remove_repositories(self, installation_id: int, repository_ids: set[int]) -> None: ...


class PostgresGitHubConnectionRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def begin(self, owner_user_id: UUID) -> None:
        await self.pool.execute(
            """
            INSERT INTO github_connections (owner_user_id, status)
            VALUES ($1, 'connecting')
            ON CONFLICT (owner_user_id) DO UPDATE SET
                status = 'connecting',
                last_error = NULL,
                updated_at = now()
            """,
            owner_user_id,
        )

    async def get(self, owner_user_id: UUID) -> GitHubConnectionRecord | None:
        row = await self.pool.fetchrow(
            """
            SELECT owner_user_id, status, installation_id, account_login, account_type,
                   selected_repository_id, selected_repository_full_name,
                   selected_repository_private, selected_default_branch,
                   last_error, updated_at
            FROM github_connections
            WHERE owner_user_id = $1
            """,
            owner_user_id,
        )
        return self._record(row) if row else None

    async def save_installation(
        self,
        *,
        owner_user_id: UUID,
        installation_id: int,
        account_login: str,
        account_type: str,
        repositories: list[GitHubRepository],
    ) -> GitHubConnectionRecord:
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                row = await connection.fetchrow(
                    """
                    INSERT INTO github_connections (
                        owner_user_id, installation_id, account_login, account_type, status
                    )
                    VALUES ($1, $2, $3, $4, 'awaiting_repository')
                    ON CONFLICT (owner_user_id) DO UPDATE SET
                        installation_id = EXCLUDED.installation_id,
                        account_login = EXCLUDED.account_login,
                        account_type = EXCLUDED.account_type,
                        status = 'awaiting_repository',
                        selected_repository_id = NULL,
                        selected_repository_full_name = NULL,
                        selected_repository_private = NULL,
                        selected_default_branch = NULL,
                        last_error = NULL,
                        updated_at = now()
                    RETURNING owner_user_id, status, installation_id, account_login, account_type,
                              selected_repository_id, selected_repository_full_name,
                              selected_repository_private, selected_default_branch,
                              last_error, updated_at
                    """,
                    owner_user_id,
                    installation_id,
                    account_login,
                    account_type,
                )
                await connection.execute(
                    "DELETE FROM github_connection_repositories WHERE owner_user_id = $1",
                    owner_user_id,
                )
                if repositories:
                    await connection.executemany(
                        """
                        INSERT INTO github_connection_repositories (
                            owner_user_id, repository_id, full_name, private, default_branch
                        ) VALUES ($1, $2, $3, $4, $5)
                        """,
                        [
                            (
                                owner_user_id,
                                repository.id,
                                repository.full_name,
                                repository.private,
                                repository.default_branch,
                            )
                            for repository in repositories
                        ],
                    )
        return self._record(row)

    async def list_repositories(self, owner_user_id: UUID) -> list[GitHubRepository]:
        rows = await self.pool.fetch(
            """
            SELECT repository_id, full_name, private, default_branch
            FROM github_connection_repositories
            WHERE owner_user_id = $1
            ORDER BY lower(full_name), repository_id
            """,
            owner_user_id,
        )
        return [
            GitHubRepository(
                id=int(row["repository_id"]),
                full_name=row["full_name"],
                private=row["private"],
                default_branch=row["default_branch"],
            )
            for row in rows
        ]

    async def select_repository(
        self, *, owner_user_id: UUID, repository_id: int
    ) -> GitHubConnectionRecord:
        row = await self.pool.fetchrow(
            """
            UPDATE github_connections AS connection
            SET status = 'connected',
                selected_repository_id = repository.repository_id,
                selected_repository_full_name = repository.full_name,
                selected_repository_private = repository.private,
                selected_default_branch = repository.default_branch,
                last_error = NULL,
                updated_at = now()
            FROM github_connection_repositories AS repository
            WHERE connection.owner_user_id = $1
              AND repository.owner_user_id = connection.owner_user_id
              AND repository.repository_id = $2
            RETURNING connection.owner_user_id, connection.status,
                      connection.installation_id, connection.account_login,
                      connection.account_type, connection.selected_repository_id,
                      connection.selected_repository_full_name,
                      connection.selected_repository_private,
                      connection.selected_default_branch, connection.last_error,
                      connection.updated_at
            """,
            owner_user_id,
            repository_id,
        )
        if row is None:
            raise KeyError("Repository is not available to this GitHub connection")
        return self._record(row)

    async def disconnect(self, owner_user_id: UUID) -> None:
        await self.pool.execute(
            "DELETE FROM github_connections WHERE owner_user_id = $1",
            owner_user_id,
        )

    async def disconnect_installation(self, installation_id: int, *, reason: str) -> None:
        await self.pool.execute(
            """
            UPDATE github_connections
            SET status = 'disconnected',
                selected_repository_id = NULL,
                selected_repository_full_name = NULL,
                selected_repository_private = NULL,
                selected_default_branch = NULL,
                last_error = $2,
                updated_at = now()
            WHERE installation_id = $1
            """,
            installation_id,
            reason,
        )

    async def remove_repositories(self, installation_id: int, repository_ids: set[int]) -> None:
        if not repository_ids:
            return
        ids = list(repository_ids)
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    DELETE FROM github_connection_repositories AS repository
                    USING github_connections AS connection
                    WHERE repository.owner_user_id = connection.owner_user_id
                      AND connection.installation_id = $1
                      AND repository.repository_id = ANY($2::bigint[])
                    """,
                    installation_id,
                    ids,
                )
                await connection.execute(
                    """
                    UPDATE github_connections
                    SET status = 'disconnected',
                        selected_repository_id = NULL,
                        selected_repository_full_name = NULL,
                        selected_repository_private = NULL,
                        selected_default_branch = NULL,
                        last_error = 'repository_access_removed',
                        updated_at = now()
                    WHERE installation_id = $1
                      AND selected_repository_id = ANY($2::bigint[])
                    """,
                    installation_id,
                    ids,
                )

    @staticmethod
    def _record(row: asyncpg.Record) -> GitHubConnectionRecord:
        repository = None
        if row["selected_repository_id"] is not None:
            repository = GitHubRepository(
                id=int(row["selected_repository_id"]),
                full_name=row["selected_repository_full_name"],
                private=row["selected_repository_private"],
                default_branch=row["selected_default_branch"],
            )
        return GitHubConnectionRecord(
            owner_user_id=row["owner_user_id"],
            status=row["status"],
            installation_id=int(row["installation_id"]) if row["installation_id"] else None,
            account_login=row["account_login"],
            account_type=row["account_type"],
            repository=repository,
            last_error=row["last_error"],
            updated_at=row["updated_at"],
        )


def get_github_connection_repository() -> GitHubConnectionRepository:
    return PostgresGitHubConnectionRepository(get_pool())
