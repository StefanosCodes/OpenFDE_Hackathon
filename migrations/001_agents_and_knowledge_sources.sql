CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO users (id, email, name)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'user-a@example.com', 'Seeded User A'),
    ('22222222-2222-2222-2222-222222222222', 'user-b@example.com', 'Seeded User B')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY,
    owner_user_id UUID NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    openai_vector_store_id TEXT NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS agents_owner_created_idx
ON agents (owner_user_id, created_at, id);

CREATE TABLE IF NOT EXISTS knowledge_sources (
    id UUID PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    created_by_user_id UUID NOT NULL REFERENCES users(id),
    source_type TEXT NOT NULL CONSTRAINT knowledge_sources_source_type_check
        CHECK (source_type IN (
            'markdown', 'pdf', 'url', 'text', 'csv', 'json', 'yaml',
            'xml', 'html', 'rtf', 'email', 'code', 'word', 'excel',
            'powerpoint', 'opendocument', 'epub', 'audio', 'video', 'image'
        )),
    status TEXT NOT NULL CHECK (status IN ('ready', 'failed')),
    title TEXT NOT NULL,
    original_filename TEXT NULL,
    source_url TEXT NULL,
    content_preview TEXT NULL,
    openai_file_id TEXT NULL,
    byte_size INTEGER NULL CHECK (byte_size >= 0),
    error_message TEXT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS knowledge_sources_agent_created_idx
ON knowledge_sources (agent_id, created_at, id);
