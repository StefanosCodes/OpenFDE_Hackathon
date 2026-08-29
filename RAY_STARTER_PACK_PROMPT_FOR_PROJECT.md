# Ray starter pack prompt for project

Copy everything below the line into Ray's prompt.

---

You are extending an existing FastAPI + React + Postgres hackathon scaffold. Do not start a second backend. Do not touch the React app.

## Your job

A logged-in seeded user can create an **agent**, attach **Markdown, PDF, and URL** sources to that agent, and when they talk to that agent it can search **only that agent's sources**.

An agent **is** the project. Knowledge is scoped to `agent_id`. No `projects` table. No shared KB.

**Retrieval is OpenAI Vector Stores + `FileSearchTool`. Do not use pgvector.** Postgres holds metadata IDs only. Do not add embedding columns, chunk tables, similarity SQL, or a local RAG pipeline.

## SQL path (non-negotiable)

Copy OpenFDE Nexus. Persistence is:

- PostgreSQL
- `asyncpg` connection pool
- numbered raw `.sql` migrations
- SQL strings in service functions with `$1, $2` placeholders
- `asyncpg.Record` mapped to Pydantic response models

There is **no ORM**. Do not add SQLAlchemy, SQLModel, Alembic, Prisma, or query builders. Do not put SQL in routers. Routers call services. Services own SQL and OpenAI file/store calls.

A query looks like this:

```sql
SELECT id, email, name, created_at
FROM users
WHERE id = $1
```

Not `session.query(User)`, not `User.objects.get()`, not SQLAlchemy `select()`.

Reference implementation:

`/Users/stefanossophocleous/Desktop/dev/OpenFDE/services/nexus`

Especially:

- `app/core/database.py` — pool + transaction
- `app/migrate.py` — numbered SQL files
- `migrations/*.sql` — schema
- `app/services/*.py` — raw SQL
- `app/schemas/*.py` — public response models

**Docker is not required.** Native Postgres. The scaffold README is the run path (`npm run dev` at repo root). Match whatever dummy login/session the scaffold already shipped. Never take `user_id` from the request body as identity.

## Data

### `agents`

```text
id                      UUID PK
owner_user_id           UUID NOT NULL → users.id
name                    TEXT NOT NULL
openai_vector_store_id  TEXT NOT NULL
created_at              timestamptz NOT NULL DEFAULT now()
```

Index: `(owner_user_id, created_at, id)`

Creating an agent creates one OpenAI vector store and stores the id. Deleting an agent deletes its sources and that vector store.

### `knowledge_sources`

```text
id                      UUID PK
agent_id                UUID NOT NULL → agents.id ON DELETE CASCADE
created_by_user_id      UUID NOT NULL → users.id
source_type             TEXT NOT NULL CHECK IN ('markdown', 'pdf', 'url')
status                  TEXT NOT NULL CHECK IN ('ready', 'failed')
title                   TEXT NOT NULL
original_filename       TEXT NULL
source_url              TEXT NULL
content_preview         TEXT NULL
openai_file_id          TEXT NULL
byte_size               INTEGER NULL CHECK >= 0
error_message           TEXT NULL
created_at              timestamptz NOT NULL DEFAULT now()
```

Index: `(agent_id, created_at, id)`

Every SELECT/UPDATE/DELETE of an agent or its sources must include owner scope (`agents.owner_user_id = current user`), not load-by-id-then-filter. Other user's agent → `404`, not `403`.

## API

All under `/v1`. Same auth as the scaffold. Same error envelope (`{"detail": "..."}`).

Collection list: `limit` default 20, max 50, order `created_at, id`.

### Agents (only if the scaffold does not already expose this)

| Method | Path | Result |
| --- | --- | --- |
| POST | `/v1/agents` | `201` `{name}` → agent + new vector store |
| GET | `/v1/agents` | owner's agents |
| GET | `/v1/agents/{agent_id}` | one agent, owner only |
| DELETE | `/v1/agents/{agent_id}` | owner only; cascade sources + vector store |

### Knowledge sources

| Method | Path | Result |
| --- | --- | --- |
| POST | `/v1/agents/{agent_id}/knowledge-sources/markdown` | multipart `file` (`.md`); optional `title` |
| POST | `/v1/agents/{agent_id}/knowledge-sources/pdf` | multipart `file` (`application/pdf`); optional `title` |
| POST | `/v1/agents/{agent_id}/knowledge-sources/url` | JSON `{ "url": "https://...", "title": "..." }` |
| GET | `/v1/agents/{agent_id}/knowledge-sources` | list for that agent |
| GET | `/v1/agents/{agent_id}/knowledge-sources/{source_id}` | one source |
| DELETE | `/v1/agents/{agent_id}/knowledge-sources/{source_id}` | Postgres row + OpenAI file |

**201 body** (create):

```json
{
  "id": "uuid",
  "agent_id": "uuid",
  "source_type": "markdown",
  "status": "ready",
  "title": "onboarding.md",
  "original_filename": "onboarding.md",
  "source_url": null,
  "content_preview": "# Onboarding...",
  "byte_size": 1234,
  "error_message": null,
  "created_at": "2026-08-29T20:00:00Z"
}
```

Failed ingest: `422` with `detail`, **no row left half-created**. Unknown / other-user `agent_id`: `404`.

## Ingest

- **Markdown:** UTF-8, max 2MB, `.md` / `text/markdown` / `text/plain`. Upload to that agent's vector store. Store ~4k preview in Postgres.
- **PDF:** sniff content, max 10MB. Do not parse it. OpenAI File Search indexes it. Preview may be null.
- **URL:** `https` only, 10s timeout, 2MB cap, no private/loopback/link-local/metadata IPs, no non-https redirects. Accept `text/html`, `text/plain`, `text/markdown`, `application/pdf`. HTML → simple visible text. Then same vector-store path. Persist original URL.
- **Delete:** remove from vector store, then delete the Postgres row, in one service function.

Keep ingest in-request. No Redis, Celery, or job queue. Bound size and time.

## Agent run

Hook the scaffold hello-world run endpoint. It takes `agent_id` and attaches:

```text
FileSearchTool(vector_store_ids=[agent.openai_vector_store_id])
```

Agents SDK stays behind the existing adapter. Vector store ids live in Postgres, not in prompts. Proof: upload markdown with a unique phrase, ask that agent, get the phrase back.

## Layout

```text
app/routers/knowledge.py
app/schemas/knowledge.py
app/services/knowledge.py
app/services/agents.py          # if scaffold does not already have it
migrations/00N_knowledge_sources.sql
```

Controllers do not fetch URLs or call OpenAI. Services do not return ORM objects (there is no ORM). Tests hit the API with the seeded user.

## Security

- Identity from dummy session / bearer the scaffold already uses. Never `user_id` in the body as proof.
- Every query includes `owner_user_id` (or join through `agents.owner_user_id`).
- Cross-user agent id → `404`.
- Upload size and type checked **before** OpenAI.
- URL fetch: scheme + private-IP block + timeout + size cap.
- Do not log file bodies, URL query strings with secrets, or API keys.

## Do not build

React UI, chat artifacts, mermaid/canvas, F2E, audio/transcription, Linear/MCP, pgvector, embedding columns, chunk tables, custom RAG, website crawlers, OAuth/SSO.

## Done when

1. Seeded user A creates an agent, uploads `.md` + `.pdf` + one `https` URL; list returns 3 sources.
2. `curl` agent-run with a question whose answer is only in the markdown; response contains that fact.
3. User B cannot list or attach to A's agent (`404`).
4. `.exe` / oversized file / `http://127.0.0.1/` → `422` and no source row.
5. Delete source; it leaves the list; the agent no longer retrieves it.
6. OpenAPI shows the knowledge endpoints with request/response models.
7. `pytest` covers happy ingest, owner isolation, bad type, SSRF URL, delete.

## Implementation order

1. Migration + agent vector-store create (if needed)
2. Markdown ingest + list/get/delete
3. Attach `FileSearchTool` to agent run; prove retrieval with markdown
4. PDF ingest (same pipeline, different type/limit)
5. URL ingest + SSRF tests
6. Isolation tests and OpenAPI check

Stop after 6. Do not start audio, MCP, or chat artifacts.
