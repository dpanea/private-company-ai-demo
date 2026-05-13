CREATE TABLE IF NOT EXISTS proactive_alerts (
    alert_id text PRIMARY KEY,
    account_id text NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
    session_id text,
    alert_type text NOT NULL CHECK (alert_type IN (
        'unresolved_objection', 'stalled_account', 'approaching_close_date',
        'missing_followup', 'champion_positive_signal', 'data_inconsistency'
    )),
    severity text NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    title text NOT NULL,
    body_markdown text NOT NULL,
    evidence_doc_ids text[] NOT NULL DEFAULT '{}',
    evidence_artifact_ids text[] NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_proactive_alerts_account
    ON proactive_alerts(account_id, session_id, severity);
