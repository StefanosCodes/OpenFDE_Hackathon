CREATE TABLE IF NOT EXISTS github_connections (
    owner_user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    installation_id BIGINT NULL,
    account_login TEXT NULL,
    account_type TEXT NULL,
    status TEXT NOT NULL CONSTRAINT github_connections_status_check
        CHECK (status IN (
            'disconnected', 'connecting', 'awaiting_repository', 'connected', 'error'
        )),
    selected_repository_id BIGINT NULL,
    selected_repository_full_name TEXT NULL,
    selected_repository_private BOOLEAN NULL,
    selected_default_branch TEXT NULL,
    last_error TEXT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS github_connections_installation_idx
ON github_connections (installation_id)
WHERE installation_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS github_connection_repositories (
    owner_user_id UUID NOT NULL REFERENCES github_connections(owner_user_id) ON DELETE CASCADE,
    repository_id BIGINT NOT NULL,
    full_name TEXT NOT NULL,
    private BOOLEAN NOT NULL DEFAULT false,
    default_branch TEXT NOT NULL DEFAULT 'main',
    PRIMARY KEY (owner_user_id, repository_id)
);

CREATE INDEX IF NOT EXISTS github_connection_repositories_owner_name_idx
ON github_connection_repositories (owner_user_id, full_name);
