CREATE TABLE IF NOT EXISTS raw_artifacts (
    artifact_id text PRIMARY KEY,
    account_id text REFERENCES accounts(account_id) ON DELETE CASCADE,
    artifact_type text NOT NULL CHECK (artifact_type IN (
        'email', 'email_thread', 'pdf', 'docx', 'meeting_transcript', 'crm_record'
    )),
    title text NOT NULL,
    mime_type text NOT NULL,
    source_path text NOT NULL,
    rendered_path text,
    extracted_text text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    extraction_method text NOT NULL CHECK (extraction_method IN (
        'plain_text', 'ocr', 'docx_xml', 'mbox_parse', 'csv_row'
    )),
    created_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_artifacts_account ON raw_artifacts(account_id, artifact_type);
CREATE INDEX IF NOT EXISTS idx_raw_artifacts_metadata ON raw_artifacts USING gin(metadata);
