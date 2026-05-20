from __future__ import annotations

from datetime import datetime, timezone

from company_ai.ingestion.ai_ready_documents import DocumentBuilder
from company_ai.models import Account, RawArtifact, SyntheticDataset


def test_source_artifact_chunks_are_generated_for_visible_artifact_types() -> None:
    account = Account(account_id="ACC_1", account_name="Example Client")
    now = datetime(2026, 5, 15, tzinfo=timezone.utc)
    artifacts = [
        _artifact("email:ACC_1:msg_1", "email", "Security email", "Can we resolve security approval?", now),
        _artifact(
            "pdf:ACC_1:mutual_nda",
            "pdf",
            "Mutual NDA",
            "Page one confidentiality.\n\nPage two term and signatures.",
            now,
            metadata={"text_per_page": ["Page one confidentiality.", "Page two term and signatures."]},
        ),
        _artifact(
            "docx:ACC_1:account_plan",
            "docx",
            "Account plan",
            "# Account Plan\n\n## Next steps\n\nSend the audit posture note.",
            now,
        ),
        _artifact(
            "meeting:ACC_1:pilot_review",
            "meeting_transcript",
            "Pilot review",
            "Daniel: We reviewed scope.\nJordan: Security approval is the blocker.",
            now,
        ),
    ]
    dataset = SyntheticDataset(accounts=[account], raw_artifacts=artifacts)

    docs = DocumentBuilder(dataset, raw_artifacts=artifacts).build_all()
    chunk_docs = [doc for doc in docs if doc.doc_type == "source_artifact_chunk"]
    labels = {citation.source_object for doc in chunk_docs for citation in doc.citations}

    assert {"Email", "PDF", "WordDocument", "Meeting"} <= labels
    assert sum(1 for doc in chunk_docs if doc.metadata_json["source_artifact_id"] == "pdf:ACC_1:mutual_nda") == 2
    assert all(doc.citations for doc in chunk_docs)
    assert not any(
        citation.source_object in {"Account", "Contact", "Opportunity", "Contract", "Task", "Event"}
        for doc in docs
        for citation in doc.citations
    )


def test_markdown_meeting_turns_are_chunked() -> None:
    account = Account(account_id="ACC_1", account_name="Example Client")
    now = datetime(2026, 5, 15, tzinfo=timezone.utc)
    turns = "\n".join(f"**Speaker {index}:** Turn {index}." for index in range(1, 9))
    meeting = _artifact(
        "meeting:ACC_1:long_review",
        "meeting_transcript",
        "Long review",
        turns,
        now,
    )
    dataset = SyntheticDataset(accounts=[account], raw_artifacts=[meeting])

    docs = DocumentBuilder(dataset, raw_artifacts=[meeting]).build_all()

    assert len(docs) == 2
    assert {doc.metadata_json["chunk_label"] for doc in docs} == {"turn group 1", "turn group 2"}


def _artifact(
    artifact_id: str,
    artifact_type: str,
    title: str,
    text: str,
    created_at: datetime,
    *,
    metadata: dict | None = None,
) -> RawArtifact:
    return RawArtifact(
        artifact_id=artifact_id,
        account_id="ACC_1",
        artifact_type=artifact_type,
        title=title,
        mime_type="text/plain",
        source_path=f"synthetic/{artifact_id}",
        extracted_text=text,
        metadata=metadata or {},
        extraction_method="plain_text" if artifact_type != "docx" else "docx_xml",
        created_at=created_at,
        ingested_at=created_at,
    )
