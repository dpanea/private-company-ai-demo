-- Drop CRM tables. Demo source artifacts (raw_artifacts) carry the
-- visible source-of-truth; CRM-style summaries are no longer generated.
-- The accounts table is kept for account routing/clarification.

DROP INDEX IF EXISTS idx_rag_documents_opportunity_id;
DROP INDEX IF EXISTS idx_rag_documents_contract_id;

ALTER TABLE rag_documents DROP COLUMN IF EXISTS opportunity_id;
ALTER TABLE rag_documents DROP COLUMN IF EXISTS contract_id;

DROP TABLE IF EXISTS activities;
DROP TABLE IF EXISTS contracts;
DROP TABLE IF EXISTS opportunities;
DROP TABLE IF EXISTS contacts;

DELETE FROM raw_artifacts WHERE artifact_type = 'crm_record';
