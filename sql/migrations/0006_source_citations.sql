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
