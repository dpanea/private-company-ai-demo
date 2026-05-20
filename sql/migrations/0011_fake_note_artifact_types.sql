ALTER TABLE demo_notes
    DROP CONSTRAINT IF EXISTS demo_notes_note_type_check;

ALTER TABLE demo_notes
    ADD CONSTRAINT demo_notes_note_type_check
    CHECK (note_type IN (
        'meeting_transcript', 'docx', 'pdf', 'email',
        'meeting_summary', 'email_summary', 'task', 'risk', 'general'
    ));
