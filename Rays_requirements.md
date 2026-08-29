# Ray's requirements

**Owner:** Ray
**Stack:** FastAPI + PostgreSQL (`asyncpg`, raw SQL) + OpenAI Agents SDK
**Depends on:** the repo scaffold (seeded users, dummy login, hello-world agent, `npm run dev`)
**Not Ray's job:** React UI, chat-to-artifact, visual flows, Linear/MCP, audio transcription

## Retrieval (locked)

**Use OpenAI Vector Stores + `FileSearchTool`. Do not use pgvector.**

Postgres stores metadata only (`openai_vector_store_id`, `openai_file_id`, preview, owner). OpenAI owns chunking, embeddings, and search.

Do not install `pgvector`. Do not add `embedding` columns, chunk tables, similarity SQL, or a local RAG pipeline. If a library or migration would store vectors in Postgres, it is out of scope.

## Outcome

A logged-in seeded user can create an **agent**, attach **Markdown, PDF, and URL** sources to that agent, and when they talk to that agent it can use **only that agent's sources**.

That is the whole slice. Product vision (chat → diagram/markdown artifact → handoff to F2E) is why this exists later. Do not build any of that now.

## Locked meaning of "project"

**An agent is the project.** Knowledge is scoped to `agent_id`.

- No `projects` table
- No sharing one KB across agents
- Opening agent X sees only sources with `agent_id = X`
- Another user's agent is invisible (`404`, not `403`)

If we later want a shared project KB, we add a `projects` table then. Not now.

## Current state

| Fact | Evidence |
| --- | --- |
| Hackathon repo starts empty except `.gitignore` | `OpenFDE_Hackathon` |
| Scaffold (users, dummy login, Agents hello-world) is being built separately | Parallel thread |
| House style is OpenFDE Nexus: FastAPI, `asyncpg`, SQL migrations, Pydantic response models, feature routers | `/Users/stefanossophocleous/Desktop/dev/OpenFDE/services/nexus` |
| Agents SDK retrieval for files is `FileSearchTool` over an OpenAI vector store | OpenAI Agents docs |
| Local pgvector RAG is forbidden for this slice | Locked decision below |

**Assumption:** Ray extends the scaffold app. He does not start a second backend.

## In scope (Ray)

1. SQL for `agents` (if scaffold doesn't have it yet) and `knowledge_sources`
2. One OpenAI **vector store per agent** (created with the agent, stored on the agent row)
3. Ingest APIs: Markdown upload, PDF upload, URL fetch
4. List / get / delete sources for that agent
5. Authorization: owner-only, identity from the session, not from a body field
6. Wire the existing agent-run path so that agent's `FileSearchTool` uses that vector store
7. Tests + OpenAPI that match the rest of the API

## Out of scope (do not start)

| Parked | Why |
| --- | --- |
| Audio / MP4 / transcription | Nice-to-have after this works |
| Linear / Atlassian MCP | Nice-to-have after this works |
| Chat that designs agents | Later product slice |
| Visual diagrams / mermaid canvas | Later product slice |
| Markdown artifacts from chat | Later product slice |
| F2E handoff | Later product slice |
| pgvector, `vector` columns, chunk tables, local embeddings | **Forbidden.** OpenAI Vector Store only |
| Redis / Celery / job queue | Keep ingest in-request with hard limits |
| Real OAuth, SSO, multi-tenant orgs | Dummy login only |
| Website crawlers, sitemaps, recursive URL follow | One URL = one source |
| React upload UI | API + `curl` is enough; frontend stacks later |

If a requirement is not in **In scope**, Ray does not build it.

## Constraints

- Match OpenFDE backend habits: feature routers, Pydantic schemas, service functions, raw SQL, no ORM
- `asyncpg` only for Postgres. No SQLAlchemy.
- Domain code does not import FastAPI `Request`
- Agents SDK stays behind a small adapter. OpenAI vector store IDs live in Postgres, not in prompts. Postgres never stores embeddings.
- Secrets from env only
- No new abstraction "for later"
- Ingest finishes inside the request. Bound size and time instead of adding workers

## Data

### `agents` (create only if scaffold didn't)

```text
id                      UUID PK
owner_user_id           UUID NOT NULL  → users.id
name                    TEXT NOT NULL
openai_vector_store_id  TEXT NOT NULL
created_at              timestamptz NOT NULL DEFAULT now()
```

Index: `(owner_user_id, created_at, id)`

Creating an agent **creates** the OpenAI vector store and stores its id. Deleting an agent deletes its sources and the vector store.

### `knowledge_sources`

```text
id                      UUID PK
agent_id                UUID NOT NULL → agents.id ON DELETE CASCADE
created_by_user_id      UUID NOT NULL → users.id
source_type             TEXT NOT NULL   CHECK IN ('markdown', 'pdf', 'url')
status                  TEXT NOT NULL   CHECK IN ('ready', 'failed')
title                   TEXT NOT NULL
original_filename       TEXT NULL
source_url              TEXT NULL
content_preview         TEXT NULL       -- first ~4k chars of extracted text
openai_file_id          TEXT NULL
byte_size               INTEGER NULL    CHECK >= 0
error_message           TEXT NULL
created_at              timestamptz NOT NULL DEFAULT now()
```

Index: `(agent_id, created_at, id)`

Uniqueness: none extra. Same URL may be added twice; don't over-engineer.

### Source of truth

| Fact | Owner |
| --- | --- |
| Who owns the agent | `agents.owner_user_id` |
| Which files belong to the agent | `knowledge_sources.agent_id` |
| What the model can search | that agent's OpenAI vector store |
| Display list / preview | Postgres row |

Do not keep a writable copy of "what the agent knows" in a third place.

## API contract

All under `/v1`. Same auth as the scaffold login. Same error envelope as the rest of the app (`{"detail": "..."}`).

Collection list: `limit` default 20, max 50, `created_at, id` order.

### Agents (only if scaffold doesn't already expose this)

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

Failed ingest: `422` with `detail`, **no row left half-created**. Prefer no row + `422` so the list stays clean.

Unknown / other-user `agent_id`: `404`.

### Agent run (thin hook, not a new product)

Whatever hello-world run endpoint the scaffold already has, take `agent_id` and attach:

```text
FileSearchTool(vector_store_ids=[agent.openai_vector_store_id])
```

No extra chat product. Proof is: upload a markdown file with a unique phrase, ask the agent that phrase, get it back.

## Ingest rules

### Markdown

- Extension `.md` or `text/markdown` / `text/plain`
- UTF-8, max **2 MB**
- Title = form `title` or filename
- Upload bytes to the agent's vector store **and** store preview in Postgres

### PDF

- `application/pdf` (sniff content; do not trust the filename)
- Max **10 MB**
- Do not parse PDFs ourselves. OpenAI File Search indexes the file
- Preview may be empty for PDFs; that is fine

### URL

- `https` only
- No redirects to non-https
- Block loopback, link-local, private, and metadata IPs (SSRF)
- Timeout **10s**, response body max **2 MB**
- Accept `text/html`, `text/plain`, `text/markdown`, `application/pdf`
- HTML: strip to visible text (simple, not a full reader)
- Then same path as markdown/pdf into the vector store
- Persist the original URL on the row

### Delete

Remove from the vector store first, then delete the Postgres row, in one service function. If OpenAI delete fails after DB delete, log it; don't leave the API hanging.

## Layout (follow the scaffold; do not invent a parallel app)

```text
app/
  main.py                 # lifespan, exception handlers, include v1
  api.py                  # /v1 router
  core/                   # settings, database, auth, exceptions, deps
  routers/knowledge.py    # HTTP only
  schemas/knowledge.py    # public request/response
  services/knowledge.py   # ingest + authz + OpenAI file/store calls
  services/agents.py      # if not already there
  agents_runtime/         # SDK adapter; FileSearchTool wiring only
migrations/
  00N_knowledge_sources.sql
```

Controllers do not fetch URLs or call OpenAI. Services do not return ORM objects (there is no ORM). Tests hit the API with the seeded user.

## Security (required, still small)

- Identity from dummy session / bearer the scaffold already uses. Never `user_id` in the body as proof
- Every query includes `owner_user_id` (or join through `agents.owner_user_id`). Do not load by id then filter
- Cross-user agent id → `404`
- Upload size and type checked **before** OpenAI
- URL fetch: scheme + private-IP block + timeout + size cap
- Do not log file bodies, URL query strings with secrets, or API keys
- CORS: scaffold allowlist only

## Verification (Ray is done when all of these pass)

1. Seeded user A creates agent, uploads `.md`, `.pdf`, adds an `https` URL; `GET` list returns 3 sources
2. `curl` the agent-run endpoint with a question whose answer is only in the markdown; response contains that fact
3. User B's token cannot list or attach to user A's agent (`404`)
4. `.exe` / huge file / `http://127.0.0.1/` URL → `422`, no source row
5. Delete source; list no longer includes it; agent no longer retrieves that content
6. OpenAPI shows the six knowledge endpoints with request/response models
7. `pytest` covers: happy ingest, owner isolation, bad type, SSRF URL, delete

No frontend required for done.

## Implementation order

1. Migration + agent vector-store create (if needed)
2. Markdown ingest + list/get/delete
3. Attach `FileSearchTool` to agent run; prove retrieval with markdown
4. PDF ingest (same pipeline, different type/limit)
5. URL ingest + SSRF tests
6. Isolation tests and OpenAPI check

Stop after 6. Do not start audio, MCP, or chat artifacts.

## Later (explicitly not this ticket)

1. **Audio:** MP3/MP4 → transcript → same `knowledge_sources` as `source_type=transcript`
2. **MCP:** Linear/Atlassian as a hosted MCP tool on the agent, still agent-scoped
3. **Designer chat:** talk → mermaid/visual flow + markdown artifact → F2E handoff

Those stack **on this contract**. They do not change it.

## Open decisions (do not block Ray)

- Dummy auth mechanism is whatever the scaffold already shipped
- PDF preview text can be null
- Failed ingest = no row + `422`

No other decisions needed to start.
