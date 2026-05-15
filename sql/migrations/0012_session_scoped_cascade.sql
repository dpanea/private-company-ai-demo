DELETE FROM rag_documents r
WHERE r.session_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM sessions s WHERE s.session_id = r.session_id
  );

DELETE FROM proactive_alerts p
WHERE p.session_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM sessions s WHERE s.session_id = p.session_id
  );

ALTER TABLE rag_documents
    DROP CONSTRAINT IF EXISTS rag_documents_session_id_fkey;

ALTER TABLE rag_documents
    ADD CONSTRAINT rag_documents_session_id_fkey
    FOREIGN KEY (session_id)
    REFERENCES sessions(session_id)
    ON DELETE CASCADE;

ALTER TABLE proactive_alerts
    DROP CONSTRAINT IF EXISTS proactive_alerts_session_id_fkey;

ALTER TABLE proactive_alerts
    ADD CONSTRAINT proactive_alerts_session_id_fkey
    FOREIGN KEY (session_id)
    REFERENCES sessions(session_id)
    ON DELETE CASCADE;
