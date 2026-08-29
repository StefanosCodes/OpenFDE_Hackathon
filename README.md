# OpenFDE Agent Knowledge API

Agent-scoped RAG knowledge base backend slice for the OpenFDE hackathon scaffold.

## What This Builds

- One logged-in seeded user can create agents.
- Each agent owns exactly one OpenAI Vector Store.
- Markdown, PDF, HTTPS URL, text, CSV/TSV, JSON/YAML/XML, HTML/RTF, Email, code files, Word, Excel, PowerPoint, OpenDocument, EPUB, audio, video, and image sources can be attached to one agent.
- Agent runs use `FileSearchTool` with only that agent's vector store.
- Agent designs can be previewed before FDE handoff with a structured summary and Mermaid tool-calling graph.
- PostgreSQL stores metadata only. It does not store embeddings, chunks, or vectors.
- A read-only GitHub App connector lets each OpenFDE user install the shared app,
  choose an exposed repository, and make that repository available to the future runner.

## Not In This Slice

- `pgvector`
- SQLAlchemy or another ORM
- Redis, Celery, or background workers
- MCP, Linear, Atlassian, artifact generation, F2E handoff

## GitHub App connector

Local GitHub App settings live only in the hidden `.env.github-app` file. That file,
`.secrets/`, and private key files are ignored by git. The connector loader does not
override variables already supplied by the shell or deployment platform.

The file uses these keys:

```dotenv
APP_BASE_URL=http://localhost:8001
FRONTEND_BASE_URL=http://localhost:5173
COOKIE_SECURE=false
GITHUB_APP_ID=
GITHUB_APP_SLUG=
GITHUB_APP_CLIENT_ID=
GITHUB_APP_CLIENT_SECRET=
GITHUB_APP_PRIVATE_KEY_PATH=.secrets/openfde-demo.pem
GITHUB_STATE_SECRET=
GITHUB_WEBHOOK_SECRET=
```

`GITHUB_WEBHOOK_SECRET` is optional while webhooks are disabled. Run migration
`005_github_connections.sql` before testing the connector against the normal API.
The frontend defaults to `http://localhost:8001`; deployments can set
`VITE_API_BASE_URL` and `VITE_DEMO_AUTH_TOKEN` during the frontend build.

Disconnecting in OpenFDE removes the OpenFDE connection. It intentionally does not
uninstall the GitHub App from the GitHub account or organization.

## Setup

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

If the local pip is old and does not support editable pyproject installs, use `pip install ".[dev]"`.

Set environment:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/openfde"
export OPENAI_API_KEY="..."
```

Run migrations:

```bash
npm run migrate
```

Start the API:

```bash
npm run dev
```

The API is mounted under `/v1`. A small browser demo is available at `http://localhost:8000/demo`.

For a UI-only demo that does not require PostgreSQL or an OpenAI key, serve the static demo page directly:

```bash
python3 -m http.server 8765 -d app/static
```

Then open `http://localhost:8765/demo.html`. The page starts in Browser Demo mode and stores sample agents and sources in `localStorage`. Switch Mode to Live API when the FastAPI backend, PostgreSQL, and `OPENAI_API_KEY` are ready.

Supported file upload formats in Live API mode:

- Text: `.md`, `.markdown`, `.txt`, `.log`, `.rst`, `.tex`
- Data: `.csv`, `.tsv`, `.json`, `.jsonl`, `.ndjson`, `.yaml`, `.yml`, `.xml`
- Web/email/code: `.html`, `.htm`, `.xhtml`, `.rtf`, `.eml`, common source-code extensions
- Documents: `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`, `.odt`, `.ods`, `.odp`, `.epub`
- Audio: `.mp3`, `.m4a`, `.wav`, `.webm`, `.mp4`
- Video: `.mp4`, `.mpeg`, `.mpg`, `.webm`, `.m4v`
- Images: `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`

For audio, the backend transcribes the file and uploads the transcript to the agent's vector store. For video, the backend transcribes the audio track and uploads that transcript; it does not yet analyze video frames. For images, it asks the model for readable text and a concise visual description, then uploads that text to the vector store. HTML, RTF, email, EPUB, and OpenDocument files are converted to cleaner text when possible before indexing.

## Dummy Auth

Use seeded bearer tokens:

```bash
Authorization: Bearer user-a
Authorization: Bearer user-b
```

These map to the seeded users created by `migrations/001_agents_and_knowledge_sources.sql`.

## Example Curl Flow

Create an agent:

```bash
curl -s http://localhost:8000/v1/agents \
  -H "Authorization: Bearer user-a" \
  -H "Content-Type: application/json" \
  -d '{"name":"Ray KB"}'
```

Upload Markdown:

```bash
curl -s http://localhost:8000/v1/agents/$AGENT_ID/knowledge-sources/markdown \
  -H "Authorization: Bearer user-a" \
  -F "file=@notes.md;type=text/markdown"
```

Upload a common file:

```bash
curl -s http://localhost:8000/v1/agents/$AGENT_ID/knowledge-sources/files \
  -H "Authorization: Bearer user-a" \
  -F "file=@deck.pptx"
```

Preview a draft agent design before creating it:

```bash
curl -s http://localhost:8000/v1/agents/design-preview \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Due Diligence Agent",
    "goal": "Answer questions from uploaded deal files.",
    "source_types": ["pdf", "excel", "audio", "image"],
    "enabled_tools": ["file_search"]
  }'
```

Preview an existing agent design and tool-calling graph:

```bash
curl -s http://localhost:8000/v1/agents/$AGENT_ID/design-preview \
  -H "Authorization: Bearer user-a"
```

Run the agent:

```bash
curl -s http://localhost:8000/v1/agents/$AGENT_ID/run \
  -H "Authorization: Bearer user-a" \
  -H "Content-Type: application/json" \
  -d '{"message":"What does the knowledge base say about the unique phrase?"}'
```

## Tests

```bash
pytest
```

The tests cover Markdown ingest, generic file ingest, audio/image text conversion paths, expanded structured/web file types, design preview graph generation, owner isolation, bad file type handling, URL SSRF validation, PDF validation, deletion cleanup, and OpenAPI route presence.
