CREATE TABLE IF NOT EXISTS rag_documents (
    doc_id text PRIMARY KEY,
    doc_type text NOT NULL,
    title text NOT NULL,
    content_markdown text NOT NULL,
    metadata_json jsonb NOT NULL,
    source_record_ids text[] NOT NULL DEFAULT '{}',
    source_record_hashes text[] NOT NULL DEFAULT '{}',
    account_id text REFERENCES accounts(account_id) ON DELETE CASCADE,
    opportunity_id text REFERENCES opportunities(opportunity_id) ON DELETE SET NULL,
    contract_id text REFERENCES contracts(contract_id) ON DELETE SET NULL,
    owner_id text REFERENCES users_or_owners(user_id),
    session_id text,
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
CREATE INDEX IF NOT EXISTS idx_rag_documents_opportunity_id ON rag_documents(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_rag_documents_contract_id ON rag_documents(contract_id);
CREATE INDEX IF NOT EXISTS idx_rag_documents_session ON rag_documents(session_id);
CREATE INDEX IF NOT EXISTS idx_rag_documents_metadata ON rag_documents USING gin(metadata_json);
CREATE INDEX IF NOT EXISTS idx_rag_documents_search ON rag_documents USING gin(search_vector);
CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding ON rag_documents USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_accounts_account_name_trgm ON accounts USING gin (account_name gin_trgm_ops);
