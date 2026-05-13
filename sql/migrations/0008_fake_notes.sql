CREATE TABLE IF NOT EXISTS fake_notes (
    note_id text PRIMARY KEY,
    session_id text NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    account_id text NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
    note_type text NOT NULL CHECK (note_type IN (
        'meeting_summary', 'email_summary', 'task', 'risk', 'general'
    )),
    title text NOT NULL,
    body text NOT NULL,
    note_date date NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fake_notes_session_account
    ON fake_notes(session_id, account_id);
