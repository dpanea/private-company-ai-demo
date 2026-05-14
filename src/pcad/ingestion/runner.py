from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from psycopg import Connection
from psycopg.types.json import Jsonb

from pcad.config import Settings
from pcad.db import connect
from pcad.ingestion.ai_ready_documents import DocumentBuilder
from pcad.ingestion.embeddings import index_pending_embeddings
from pcad.ingestion.manifest import ManifestArtifact, load_manifest
from pcad.ingestion.normalize import EmailThread, MeetingSummaryInput, normalize_email_threads, normalize_meeting_for_summary
from pcad.ingestion.parsers.csv_crm import parse_crm_manifest_csvs
from pcad.ingestion.parsers.docx import parse_docx
from pcad.ingestion.parsers.mbox import ParsedEmail, parse_mbox
from pcad.ingestion.parsers.meeting_md import parse_meeting_md
from pcad.ingestion.parsers.pdf import parse_pdf
from pcad.models import RagDocument, RawArtifact, SourceCitation, SyntheticDataset
from pcad.retrieval.alerts import ProactiveAlertGenerator


logger = logging.getLogger(__name__)
APPLICATION_TABLES = [
    "proactive_alerts",
    "fake_notes",
    "conversation_messages",
    "conversation_threads",
    "sessions",
    "source_citations",
    "rag_documents",
    "raw_artifacts",
    "activities",
    "contracts",
    "opportunities",
    "contacts",
    "accounts",
    "users_or_owners",
]


@dataclass(frozen=True)
class IngestionReport:
    users: int = 0
    accounts: int = 0
    contacts: int = 0
    opportunities: int = 0
    contracts: int = 0
    activities: int = 0
    raw_artifacts: int = 0
    rag_documents: int = 0
    source_citations: int = 0
    ocr_runs: int = 0
    embedding_calls: int = 0
    elapsed_seconds: float = 0.0

    def as_dict(self) -> dict[str, int | float]:
        return asdict(self)


def run_demo_ingestion(
    settings: Settings,
    *,
    synthetic_dir: Path = Path("data/synthetic"),
    clean: bool = False,
    skip_embeddings: bool = False,
) -> IngestionReport:
    """One-shot ingestion of the synthetic corpus into Postgres."""
    started = time.monotonic()
    manifest = load_manifest(synthetic_dir)
    crm_paths = manifest.crm.model_dump()
    dataset = parse_crm_manifest_csvs(synthetic_dir, crm_paths)
    raw_artifacts: list[RawArtifact] = []
    email_threads: list[EmailThread] = []
    meeting_summaries: list[MeetingSummaryInput] = []
    ocr_runs = 0
    rendered_root = synthetic_dir.parent / "rendered"

    for account in manifest.accounts:
        for artifact in account.artifacts:
            parsed = _parse_artifact(
                synthetic_dir,
                rendered_root,
                account.account_id,
                artifact,
            )
            raw_artifacts.extend(parsed.raw_artifacts)
            email_threads.extend(parsed.email_threads)
            meeting_summaries.extend(parsed.meeting_summaries)
            ocr_runs += parsed.ocr_runs

    dataset.raw_artifacts = raw_artifacts
    docs = DocumentBuilder(
        dataset,
        email_threads=email_threads,
        meeting_summaries=meeting_summaries,
        raw_artifacts=raw_artifacts,
    ).build_all()
    dataset.rag_documents = docs
    dataset.source_citations = [citation for doc in docs for citation in doc.citations]

    with connect(settings) as conn:
        with conn.transaction():
            if clean:
                _clean_tables(conn)
            _insert_crm(conn, dataset)
            _insert_raw_artifacts(conn, raw_artifacts)
            _insert_rag_documents(conn, docs)

    embedding_calls = 0 if skip_embeddings else index_pending_embeddings(settings)
    alert_generator = ProactiveAlertGenerator(settings)
    for account in dataset.accounts:
        alert_generator.generate_for_account(account.account_id)
    elapsed = time.monotonic() - started
    report = IngestionReport(
        users=len(dataset.users),
        accounts=len(dataset.accounts),
        contacts=len(dataset.contacts),
        opportunities=len(dataset.opportunities),
        contracts=len(dataset.contracts),
        activities=len(dataset.activities),
        raw_artifacts=len(raw_artifacts),
        rag_documents=len(docs),
        source_citations=len(dataset.source_citations),
        ocr_runs=ocr_runs,
        embedding_calls=embedding_calls,
        elapsed_seconds=round(elapsed, 3),
    )
    logger.info(
        "ingestion.demo.done accounts=%s raw_artifacts=%s rag_documents=%s citations=%s ocr_runs=%s embeddings=%s elapsed_seconds=%.3f",
        report.accounts,
        report.raw_artifacts,
        report.rag_documents,
        report.source_citations,
        report.ocr_runs,
        report.embedding_calls,
        report.elapsed_seconds,
    )
    return report


@dataclass(frozen=True)
class ParsedArtifactBundle:
    raw_artifacts: list[RawArtifact]
    email_threads: list[EmailThread]
    meeting_summaries: list[MeetingSummaryInput]
    ocr_runs: int = 0


def _parse_artifact(
    synthetic_dir: Path,
    rendered_root: Path,
    account_id: str,
    artifact: ManifestArtifact,
) -> ParsedArtifactBundle:
    path = synthetic_dir / artifact.path
    if artifact.format == "mbox":
        return _parse_mbox_artifact(path, artifact.path, account_id)
    if artifact.format == "pdf":
        return _parse_pdf_artifact(path, artifact.path, rendered_root, account_id, artifact)
    if artifact.format == "docx":
        return _parse_docx_artifact(path, artifact.path, account_id)
    if artifact.format == "markdown":
        return _parse_meeting_artifact(path, artifact.path, account_id)
    raise ValueError(f"Unsupported artifact format {artifact.format!r} for {artifact.path}")


def _parse_mbox_artifact(path: Path, source_path: str, account_id: str) -> ParsedArtifactBundle:
    emails = parse_mbox(path)
    email_artifacts = [_email_raw_artifact(email, source_path, account_id) for email in emails]
    prefix = f"email:{account_id}"
    threads = normalize_email_threads(emails, artifact_prefix=prefix, account_id=account_id)
    return ParsedArtifactBundle(email_artifacts, threads, [])


def _parse_pdf_artifact(
    path: Path,
    source_path: str,
    rendered_root: Path,
    account_id: str,
    artifact: ManifestArtifact,
) -> ParsedArtifactBundle:
    artifact_id = f"pdf:{account_id}:{_safe_id(path.stem)}"
    parsed = parse_pdf(path, ocr_fallback=artifact.requires_ocr or artifact.has_text_layer is not True, rendered_root=rendered_root, artifact_id=artifact_id)
    raw = RawArtifact(
        artifact_id=artifact_id,
        account_id=account_id,
        artifact_type="pdf",
        title=path.stem.replace("_", " ").title(),
        mime_type="application/pdf",
        source_path=source_path,
        rendered_path=str(parsed.rendered_image_paths[0]) if parsed.rendered_image_paths else None,
        extracted_text="\n\n".join(parsed.text_per_page).strip(),
        metadata={
            "page_count": parsed.page_count,
            "rendered_image_paths": [str(item) for item in parsed.rendered_image_paths],
            "requires_ocr": artifact.requires_ocr,
        },
        extraction_method=parsed.extraction_method,
        created_at=_file_created_at(path),
        ingested_at=_now(),
    )
    return ParsedArtifactBundle([raw], [], [], ocr_runs=1 if parsed.extraction_method == "ocr" else 0)


def _parse_docx_artifact(path: Path, source_path: str, account_id: str) -> ParsedArtifactBundle:
    parsed = parse_docx(path)
    raw = RawArtifact(
        artifact_id=f"docx:{account_id}:{_safe_id(path.stem)}",
        account_id=account_id,
        artifact_type="docx",
        title=path.stem.replace("_", " ").title(),
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        source_path=source_path,
        extracted_text=parsed.text,
        metadata={"paragraph_count": parsed.paragraph_count},
        extraction_method="docx_xml",
        created_at=_file_created_at(path),
        ingested_at=_now(),
    )
    return ParsedArtifactBundle([raw], [], [])


def _parse_meeting_artifact(path: Path, source_path: str, account_id: str) -> ParsedArtifactBundle:
    parsed = parse_meeting_md(path)
    artifact_id = f"meeting:{account_id}:{_safe_id(path.stem)}"
    raw = RawArtifact(
        artifact_id=artifact_id,
        account_id=account_id,
        artifact_type="meeting_transcript",
        title=parsed.meeting_title,
        mime_type="text/markdown",
        source_path=source_path,
        extracted_text=parsed.full_text,
        metadata={
            "meeting_date": parsed.meeting_date.isoformat() if parsed.meeting_date else None,
            "attendees": parsed.attendees,
            "turn_count": len(parsed.turns),
        },
        extraction_method="plain_text",
        created_at=_file_created_at(path),
        ingested_at=_now(),
    )
    summary = normalize_meeting_for_summary(parsed, meeting_id=_safe_id(path.stem), account_id=account_id)
    summary = MeetingSummaryInput(
        account_id=summary.account_id,
        meeting_id=summary.meeting_id,
        meeting_title=summary.meeting_title,
        meeting_date=summary.meeting_date,
        attendees=summary.attendees,
        key_topics=summary.key_topics,
        action_items=summary.action_items,
        risks=summary.risks,
        source_artifact_id=artifact_id,
    )
    return ParsedArtifactBundle([raw], [], [summary])


def _email_raw_artifact(email: ParsedEmail, source_path: str, account_id: str) -> RawArtifact:
    return RawArtifact(
        artifact_id=f"email:{account_id}:{_safe_id(email.message_id)}",
        account_id=account_id,
        artifact_type="email",
        title=email.subject or f"Email {email.message_id}",
        mime_type="message/rfc822",
        source_path=source_path,
        extracted_text=email.body_text,
        metadata={
            "message_id": email.message_id,
            "from": email.from_addr,
            "to": email.to_addrs,
            "cc": email.cc_addrs,
            "date": email.date.isoformat() if email.date else None,
            "in_reply_to": email.in_reply_to,
            "references": email.references,
            "attachments": email.attachments,
        },
        extraction_method="mbox_parse",
        created_at=email.date or _now(),
        ingested_at=_now(),
    )


def _clean_tables(conn: Connection[Any]) -> None:
    conn.execute(f"TRUNCATE {', '.join(APPLICATION_TABLES)} RESTART IDENTITY CASCADE")


def _insert_crm(conn: Connection[Any], dataset: SyntheticDataset) -> None:
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT INTO users_or_owners (user_id, name, email, is_active, profile_or_role, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        [(u.user_id, u.name, u.email, u.is_active, u.profile_or_role, u.created_at, u.updated_at) for u in dataset.users],
    )
    cur.executemany(
        """
        INSERT INTO accounts (account_id, account_name, account_type, industry, website, phone, billing_country, billing_city, owner_id, parent_account_id, created_at, updated_at, source_url, raw_record_id, raw_record_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [(a.account_id, a.account_name, a.account_type, a.industry, a.website, a.phone, a.billing_country, a.billing_city, a.owner_id, a.parent_account_id, a.created_at, a.updated_at, a.source_url, a.raw_record_id, a.raw_record_hash) for a in dataset.accounts],
    )
    cur.executemany(
        """
        INSERT INTO contacts (contact_id, account_id, name, first_name, last_name, email, phone, mobile_phone, title, role_or_department, owner_id, created_at, updated_at, source_url, raw_record_id, raw_record_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [(c.contact_id, c.account_id, c.name, c.first_name, c.last_name, c.email, c.phone, c.mobile_phone, c.title, c.role_or_department, c.owner_id, c.created_at, c.updated_at, c.source_url, c.raw_record_id, c.raw_record_hash) for c in dataset.contacts],
    )
    cur.executemany(
        """
        INSERT INTO opportunities (opportunity_id, account_id, primary_contact_id, contract_id, name, stage, amount, currency, probability, close_date, is_closed, is_won, owner_id, record_type_id, created_at, updated_at, source_url, raw_record_id, raw_record_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [(o.opportunity_id, o.account_id, o.primary_contact_id, o.contract_id, o.name, o.stage, o.amount, o.currency, o.probability, o.close_date, o.is_closed, o.is_won, o.owner_id, o.record_type_id, o.created_at, o.updated_at, o.source_url, o.raw_record_id, o.raw_record_hash) for o in dataset.opportunities],
    )
    cur.executemany(
        """
        INSERT INTO contracts (contract_id, account_id, opportunity_id_if_available, contract_number, status, start_date, end_date, activated_date, customer_signed_contact_id, owner_id, created_at, updated_at, source_url, raw_record_id, raw_record_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [(c.contract_id, c.account_id, c.opportunity_id_if_available, c.contract_number, c.status, c.start_date, c.end_date, c.activated_date, c.customer_signed_contact_id, c.owner_id, c.created_at, c.updated_at, c.source_url, c.raw_record_id, c.raw_record_hash) for c in dataset.contracts],
    )
    cur.executemany(
        """
        INSERT INTO activities (activity_id, source_object, account_id, opportunity_id, contact_id, lead_id, contract_id, who_id, what_id, owner_id, subject, activity_type, subtype, status, priority, activity_date, start_datetime, end_datetime, description, created_at, updated_at, source_url, raw_record_id, raw_record_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [(a.activity_id, a.source_object, a.account_id, a.opportunity_id, a.contact_id, a.lead_id, a.contract_id, a.who_id, a.what_id, a.owner_id, a.subject, a.activity_type, a.subtype, a.status, a.priority, a.activity_date, a.start_datetime, a.end_datetime, a.description, a.created_at, a.updated_at, a.source_url, a.raw_record_id, a.raw_record_hash) for a in dataset.activities],
    )


def _insert_raw_artifacts(conn: Connection[Any], raw_artifacts: list[RawArtifact]) -> None:
    conn.cursor().executemany(
        """
        INSERT INTO raw_artifacts (artifact_id, account_id, artifact_type, title, mime_type, source_path, rendered_path, extracted_text, metadata, extraction_method, created_at, ingested_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [
            (
                artifact.artifact_id,
                artifact.account_id,
                artifact.artifact_type,
                artifact.title,
                artifact.mime_type,
                artifact.source_path,
                artifact.rendered_path,
                artifact.extracted_text,
                Jsonb(artifact.metadata),
                artifact.extraction_method,
                artifact.created_at,
                artifact.ingested_at,
            )
            for artifact in raw_artifacts
        ],
    )


def _insert_rag_documents(conn: Connection[Any], docs: list[RagDocument]) -> None:
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT INTO rag_documents (doc_id, doc_type, title, content_markdown, metadata_json, source_record_ids, source_record_hashes, account_id, opportunity_id, contract_id, owner_id, session_id, last_source_updated_at, generated_at, source_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [
            (
                doc.doc_id,
                doc.doc_type,
                doc.title,
                doc.content_markdown,
                Jsonb(doc.metadata_json),
                doc.source_record_ids,
                doc.source_record_hashes,
                doc.account_id,
                doc.opportunity_id,
                doc.contract_id,
                doc.owner_id,
                doc.session_id,
                doc.last_source_updated_at,
                doc.generated_at,
                doc.source_hash,
            )
            for doc in docs
        ],
    )
    all_citations = [citation for doc in docs for citation in doc.citations]
    if all_citations:
        _insert_citations(conn, all_citations)


def _insert_citations(conn: Connection[Any], citations: list[SourceCitation]) -> None:
    conn.cursor().executemany(
        """
        INSERT INTO source_citations (citation_id, doc_id, source_system, source_object, source_record_id, source_url, title, source_date, owner_id, excerpt)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [
            (
                citation.citation_id,
                citation.doc_id,
                citation.source_system,
                citation.source_object,
                citation.source_record_id,
                citation.source_url,
                citation.title,
                citation.source_date,
                citation.owner_id,
                citation.excerpt,
            )
            for citation in citations
        ],
    )


def _file_created_at(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_id(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_") or "unknown"
