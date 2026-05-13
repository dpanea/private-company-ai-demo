CREATE TABLE IF NOT EXISTS sessions (
    session_id text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

CREATE TABLE IF NOT EXISTS conversation_threads (
    thread_id text PRIMARY KEY,
    session_id text NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    account_id text REFERENCES accounts(account_id) ON DELETE SET NULL,
    account_name text,
    title text NOT NULL,
    workflow_seed text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversation_threads_session_updated
    ON conversation_threads(session_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS conversation_messages (
    message_id text PRIMARY KEY,
    thread_id text NOT NULL REFERENCES conversation_threads(thread_id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('user', 'assistant')),
    content text NOT NULL,
    account_id text,
    account_name text,
    citations jsonb NOT NULL DEFAULT '[]'::jsonb,
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_thread_created
    ON conversation_messages(thread_id, created_at);
