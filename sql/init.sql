-- The Company Knowledge AI — initial schema.
--
-- A single idempotent file. `company-ai migrate` runs this against the
-- configured Postgres. Re-running is safe; every statement uses
-- `IF NOT EXISTS` or `CREATE OR REPLACE`.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- CRM-light surface used by the demo UI for account routing.
CREATE TABLE IF NOT EXISTS users_or_owners (
    user_id text PRIMARY KEY,
    name text NOT NULL,
    email text,
    is_active boolean NOT NULL DEFAULT true,
    profile_or_role text,
    created_at timestamptz,
    updated_at timestamptz
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id text PRIMARY KEY,
    account_name text NOT NULL,
    account_type text,
    industry text,
    website text,
    phone text,
    billing_country text,
    billing_city text,
    owner_id text REFERENCES users_or_owners(user_id),
    parent_account_id text REFERENCES accounts(account_id),
    created_at timestamptz,
    updated_at timestamptz,
    source_url text,
    raw_record_id text,
    raw_record_hash text
);

CREATE INDEX IF NOT EXISTS idx_accounts_account_name_trgm
    ON accounts USING gin (account_name gin_trgm_ops);

-- Parsed source artifacts (one row per email, PDF, meeting, or Word doc).
CREATE TABLE IF NOT EXISTS raw_artifacts (
    artifact_id text PRIMARY KEY,
    account_id text REFERENCES accounts(account_id) ON DELETE CASCADE,
    artifact_type text NOT NULL CHECK (artifact_type IN (
        'email', 'pdf', 'docx', 'meeting_transcript'
    )),
    title text NOT NULL,
    mime_type text NOT NULL,
    source_path text NOT NULL,
    rendered_path text,
    extracted_text text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    extraction_method text NOT NULL CHECK (extraction_method IN (
        'plain_text', 'ocr', 'docx_xml', 'mbox_parse'
    )),
    created_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_artifacts_account ON raw_artifacts(account_id, artifact_type);
CREATE INDEX IF NOT EXISTS idx_raw_artifacts_metadata ON raw_artifacts USING gin(metadata);

-- Anonymous visitor sessions (signed-cookie based).
CREATE TABLE IF NOT EXISTS sessions (
    session_id text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

-- Retrievable chunks ("AI-ready documents") with FTS and pgvector embeddings.
CREATE TABLE IF NOT EXISTS rag_documents (
    doc_id text PRIMARY KEY,
    doc_type text NOT NULL,
    title text NOT NULL,
    content_markdown text NOT NULL,
    metadata_json jsonb NOT NULL,
    source_record_ids text[] NOT NULL DEFAULT '{}',
    source_record_hashes text[] NOT NULL DEFAULT '{}',
    account_id text REFERENCES accounts(account_id) ON DELETE CASCADE,
    owner_id text REFERENCES users_or_owners(user_id),
    session_id text REFERENCES sessions(session_id) ON DELETE CASCADE,
    last_source_updated_at timestamptz,
    generated_at timestamptz NOT NULL,
    source_hash text NOT NULL,
    embedding vector(1536),
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(content_markdown, '')), 'B')
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_rag_documents_account_type ON rag_documents(account_id, doc_type);
CREATE INDEX IF NOT EXISTS idx_rag_documents_session ON rag_documents(session_id);
CREATE INDEX IF NOT EXISTS idx_rag_documents_metadata ON rag_documents USING gin(metadata_json);
CREATE INDEX IF NOT EXISTS idx_rag_documents_search ON rag_documents USING gin(search_vector);
CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding ON rag_documents USING hnsw (embedding vector_cosine_ops);

-- One row per visible citation back to a source artifact.
CREATE TABLE IF NOT EXISTS source_citations (
    citation_id text PRIMARY KEY,
    doc_id text NOT NULL REFERENCES rag_documents(doc_id) ON DELETE CASCADE,
    source_system text NOT NULL,
    source_object text NOT NULL,
    source_record_id text NOT NULL,
    source_url text,
    title text,
    source_date date,
    owner_id text,
    excerpt text
);

-- Anonymous chat threads and per-thread message history.
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

-- Visitor-added session-scoped notes (so the demo can show new info landing
-- in retrieval without persisting state across visitors).
CREATE TABLE IF NOT EXISTS demo_notes (
    note_id text PRIMARY KEY,
    session_id text NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    account_id text NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
    note_type text NOT NULL CHECK (note_type IN (
        'meeting_transcript', 'docx', 'pdf', 'email'
    )),
    title text NOT NULL,
    body text NOT NULL,
    note_date date NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_demo_notes_session_account
    ON demo_notes(session_id, account_id);

-- Per-day token-spend ledger used by the budget gate.
CREATE TABLE IF NOT EXISTS daily_budget_usage (
    usage_date date PRIMARY KEY,
    tokens_in integer NOT NULL DEFAULT 0,
    tokens_out integer NOT NULL DEFAULT 0,
    cost_estimate_eur numeric NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now()
);
