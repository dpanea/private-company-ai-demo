ALTER TABLE fake_notes
    DROP CONSTRAINT IF EXISTS fake_notes_note_type_check;

ALTER TABLE fake_notes
    ADD CONSTRAINT fake_notes_note_type_check
    CHECK (note_type IN (
        'meeting_transcript', 'docx', 'pdf', 'email',
        'meeting_summary', 'email_summary', 'task', 'risk', 'general'
    ));
