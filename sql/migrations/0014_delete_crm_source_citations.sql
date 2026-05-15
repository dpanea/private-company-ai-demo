DELETE FROM source_citations
WHERE source_object IN ('Account', 'Contact', 'Opportunity', 'Contract', 'Task', 'Event', 'FakeNote', 'RiskEvidence');

DELETE FROM raw_artifacts
WHERE artifact_type = 'crm_record';
