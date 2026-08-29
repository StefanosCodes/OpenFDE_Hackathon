import asyncio
from pathlib import Path

import asyncpg

from app.core.settings import settings


MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


async def migrate() -> None:
    conn = await asyncpg.connect(dsn=settings.database_url)
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = path.name
            already_applied = await conn.fetchval(
                "SELECT 1 FROM schema_migrations WHERE version = $1",
                version,
            )
            if already_applied:
                continue
            async with conn.transaction():
                await conn.execute(path.read_text())
                await conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES ($1)",
                    version,
                )
                print(f"Applied {version}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
