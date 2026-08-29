# OpenFDE Agent Knowledge API

Agent-scoped RAG knowledge base backend slice for the OpenFDE hackathon scaffold.

## What This Builds

- One logged-in seeded user can create agents.
- Each agent owns exactly one OpenAI Vector Store.
- Markdown, PDF, HTTPS URL, text, CSV, Word, Excel, PowerPoint, audio, and image sources can be attached to one agent.
- Agent runs use `FileSearchTool` with only that agent's vector store.
- PostgreSQL stores metadata only. It does not store embeddings, chunks, or vectors.

## Not In This Slice

- React UI
- `pgvector`
- SQLAlchemy or another ORM
- Redis, Celery, or background workers
- MCP, Linear, Atlassian, artifact generation, F2E handoff

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

- Text: `.md`, `.markdown`, `.txt`, `.log`, `.csv`, `.tsv`
- Documents: `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`
- Audio: `.mp3`, `.m4a`, `.wav`, `.webm`, `.mp4`
- Images: `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`

For audio, the backend transcribes the file and uploads the transcript to the agent's vector store. For images, it asks the model for readable text and a concise visual description, then uploads that text to the vector store.

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

The tests cover Markdown ingest, generic file ingest, audio/image text conversion paths, owner isolation, bad file type handling, URL SSRF validation, PDF validation, deletion cleanup, and OpenAPI route presence.
