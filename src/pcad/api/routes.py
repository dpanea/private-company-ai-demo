from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from psycopg.types.json import Jsonb

from pcad.agent.conversation_service import ConversationService
from pcad.config import Settings
from pcad.db import connect_dict
from pcad.ingestion.embeddings import index_pending_embeddings
from pcad.models import FakeNote
from pcad.retrieval.alerts import ProactiveAlertGenerator

from .schemas import AccountOut, FakeNoteCreateIn, SendMessageIn, ThreadCreateIn


logger = logging.getLogger(__name__)
router = APIRouter()


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session_id(request: Request) -> str:
    return request.state.session.session_id


@router.get("/health")
def health() -> dict[str, str]:
    return {"ok": "true"}


@router.get("/session")
def session(request: Request) -> dict[str, Any]:
    current = request.state.session
    return {"session_id": current.session_id, "created_at": current.created_at}


@router.delete("/session")
def reset_session(request: Request) -> dict[str, bool]:
    session_id = get_session_id(request)
    with connect_dict(get_settings(request)) as conn:
        conn.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))
        conn.commit()
    request.state.session_reset = True
    return {"ok": True}


@router.get("/accounts", response_model=list[AccountOut])
def accounts(request: Request) -> list[dict[str, Any]]:
    session_id = get_session_id(request)
    with connect_dict(get_settings(request)) as conn:
        rows = conn.execute(
            """
            SELECT
                a.account_id,
                a.account_name,
                a.account_type,
                a.industry,
                a.website,
                a.owner_id,
                a.billing_country,
                a.billing_city,
                count(DISTINCT r.artifact_id)::int AS artifact_count,
                count(DISTINCT p.alert_id)::int AS alert_count,
                GREATEST(
                    0,
                    (CURRENT_DATE - COALESCE(max(act.activity_date), max(a.updated_at)::date, CURRENT_DATE))::int
                ) AS days_since_activity
            FROM accounts a
            LEFT JOIN raw_artifacts r ON r.account_id = a.account_id
            LEFT JOIN proactive_alerts p
                ON p.account_id = a.account_id
               AND (p.session_id IS NULL OR p.session_id = %s)
            LEFT JOIN activities act ON act.account_id = a.account_id
            GROUP BY a.account_id, a.account_name, a.account_type, a.industry, a.website, a.owner_id, a.billing_country, a.billing_city
            ORDER BY a.account_name
            """,
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]


@router.get("/accounts/{account_id}")
def account(account_id: str, request: Request) -> dict[str, Any]:
    with connect_dict(get_settings(request)) as conn:
        row = conn.execute("SELECT * FROM accounts WHERE account_id = %s", (account_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
        contacts = conn.execute("SELECT * FROM contacts WHERE account_id = %s ORDER BY name", (account_id,)).fetchall()
        opportunities = conn.execute("SELECT * FROM opportunities WHERE account_id = %s ORDER BY close_date NULLS LAST", (account_id,)).fetchall()
        contracts = conn.execute("SELECT * FROM contracts WHERE account_id = %s ORDER BY contract_number", (account_id,)).fetchall()
    return {**dict(row), "contacts": [dict(item) for item in contacts], "opportunities": [dict(item) for item in opportunities], "contracts": [dict(item) for item in contracts]}


@router.get("/accounts/{account_id}/artifacts")
def account_artifacts(account_id: str, request: Request) -> list[dict[str, Any]]:
    session_id = get_session_id(request)
    with connect_dict(get_settings(request)) as conn:
        rows = conn.execute(
            "SELECT artifact_id, account_id, artifact_type, title, mime_type, source_path, rendered_path, metadata, extraction_method, created_at, ingested_at FROM raw_artifacts WHERE account_id = %s ORDER BY created_at DESC",
            (account_id,),
        ).fetchall()
        fake_note_rows = conn.execute(
            """
            SELECT *
            FROM fake_notes
            WHERE account_id = %s AND session_id = %s
            ORDER BY created_at DESC
            """,
            (account_id, session_id),
        ).fetchall()
    artifacts = [_serialize_artifact_row(dict(row)) for row in rows]
    artifacts.extend(_fake_note_artifact(dict(row)) for row in fake_note_rows)
    return sorted(artifacts, key=lambda item: item["created_at"], reverse=True)


@router.get("/accounts/{account_id}/alerts")
def account_alerts(account_id: str, request: Request) -> list[dict[str, Any]]:
    session_id = get_session_id(request)
    with connect_dict(get_settings(request)) as conn:
        rows = conn.execute(
            """
            SELECT alert_id, account_id, alert_type, severity, title, body_markdown, evidence_doc_ids, evidence_artifact_ids, created_at
            FROM proactive_alerts
            WHERE account_id = %s AND (session_id IS NULL OR session_id = %s)
            ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END, created_at DESC
            """,
            (account_id, session_id),
        ).fetchall()
    return [dict(row) for row in rows]


@router.get("/artifacts/{artifact_id}")
def artifact(artifact_id: str, request: Request) -> dict[str, Any]:
    with connect_dict(get_settings(request)) as conn:
        row = conn.execute("SELECT * FROM raw_artifacts WHERE artifact_id = %s", (artifact_id,)).fetchone()
    if not row:
        virtual = _virtual_crm_artifact(artifact_id, request)
        if virtual:
            return virtual
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    data = dict(row)
    data = _serialize_artifact_row(data)
    rendered_paths = data.get("metadata", {}).get("rendered_image_paths") or []
    data["page_urls"] = [f"/api/artifacts/{artifact_id}/page/{index}" for index, _ in enumerate(rendered_paths)]
    return data


@router.get("/artifacts/{artifact_id}/page/{page_number}")
def artifact_page(artifact_id: str, page_number: int, request: Request) -> FileResponse:
    with connect_dict(get_settings(request)) as conn:
        row = conn.execute("SELECT metadata FROM raw_artifacts WHERE artifact_id = %s", (artifact_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    rendered_paths = row["metadata"].get("rendered_image_paths") or []
    if page_number < 0 or page_number >= len(rendered_paths):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rendered page not found")
    path = Path(rendered_paths[page_number])
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rendered page file not found")
    return FileResponse(path)


@router.get("/threads")
def threads(request: Request) -> list[dict[str, Any]]:
    service: ConversationService = request.app.state.conversation_service
    return [thread.model_dump(mode="json") for thread in service.list_threads(get_session_id(request))]


@router.post("/threads")
def create_thread(payload: ThreadCreateIn, request: Request) -> dict[str, Any]:
    service: ConversationService = request.app.state.conversation_service
    thread = service.create_thread(get_session_id(request), account_id=payload.account_id, workflow_seed=payload.workflow_seed)
    return thread.model_dump(mode="json")


@router.get("/threads/{thread_id}")
def get_thread(thread_id: str, request: Request) -> dict[str, Any]:
    service: ConversationService = request.app.state.conversation_service
    try:
        return service.get_thread(get_session_id(request), thread_id).model_dump(mode="json")
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found") from exc


@router.get("/threads/{thread_id}/messages")
def get_messages(thread_id: str, request: Request) -> list[dict[str, Any]]:
    service: ConversationService = request.app.state.conversation_service
    try:
        return [message.model_dump(mode="json") for message in service.get_messages(get_session_id(request), thread_id)]
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found") from exc


@router.post("/threads/{thread_id}/messages/stream")
def stream_message(thread_id: str, payload: SendMessageIn, request: Request) -> StreamingResponse:
    service: ConversationService = request.app.state.conversation_service
    return StreamingResponse(
        service.send_message_stream(get_session_id(request), thread_id, payload.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/accounts/{account_id}/fake-notes")
def create_fake_note(
    account_id: str,
    payload: FakeNoteCreateIn,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    settings = get_settings(request)
    session_id = get_session_id(request)
    note = FakeNote(
        note_id=str(uuid4()),
        session_id=session_id,
        account_id=account_id,
        note_type=payload.note_type,
        title=payload.title,
        body=payload.body,
        note_date=payload.note_date,
        created_at=datetime.now(timezone.utc),
    )
    with connect_dict(settings) as conn:
        account = conn.execute("SELECT account_name FROM accounts WHERE account_id = %s", (account_id,)).fetchone()
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
        conn.execute(
            """
            INSERT INTO fake_notes (note_id, session_id, account_id, note_type, title, body, note_date, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (note.note_id, note.session_id, note.account_id, note.note_type, note.title, note.body, note.note_date, note.created_at),
        )
        _insert_fake_note_doc(conn, note, account["account_name"])
        conn.commit()
    # Embedding the new doc and re-running alert heuristics can each take seconds,
    # so defer them to a background task. The note is durable in fake_notes by now.
    background_tasks.add_task(_finalize_fake_note, settings, account_id, session_id)
    return {"note": note.model_dump(mode="json"), "alerts": []}


def _finalize_fake_note(settings: Settings, account_id: str, session_id: str) -> None:
    try:
        index_pending_embeddings(settings, batch_limit=20)
    except Exception:
        logger.exception("fake_note.embedding_index.failed account=%s", account_id)
    try:
        ProactiveAlertGenerator(settings).generate_for_account(account_id, session_id=session_id)
    except Exception:
        logger.exception("fake_note.alerts.failed account=%s", account_id)


@router.get("/accounts/{account_id}/fake-notes")
def fake_notes(account_id: str, request: Request) -> list[dict[str, Any]]:
    with connect_dict(get_settings(request)) as conn:
        rows = conn.execute(
            "SELECT * FROM fake_notes WHERE account_id = %s AND session_id = %s ORDER BY note_date DESC, created_at DESC",
            (account_id, get_session_id(request)),
        ).fetchall()
    return [dict(row) for row in rows]


@router.delete("/fake-notes/{note_id}")
def delete_fake_note(note_id: str, request: Request) -> dict[str, bool]:
    settings = get_settings(request)
    session_id = get_session_id(request)
    with connect_dict(settings) as conn:
        note = conn.execute("SELECT account_id FROM fake_notes WHERE note_id = %s AND session_id = %s", (note_id, session_id)).fetchone()
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fake note not found")
        conn.execute("DELETE FROM fake_notes WHERE note_id = %s AND session_id = %s", (note_id, session_id))
        conn.execute("DELETE FROM rag_documents WHERE doc_id = %s AND session_id = %s", (_fake_doc_id(note_id), session_id))
        conn.commit()
    ProactiveAlertGenerator(settings).generate_for_account(note["account_id"], session_id=session_id)
    return {"ok": True}


def _insert_fake_note_doc(conn: Any, note: FakeNote, account_name: str) -> None:
    doc_id = _fake_doc_id(note.note_id)
    source_hash = "sha256:" + hashlib.sha256(f"{note.note_id}\n{note.body}".encode("utf-8")).hexdigest()
    doc_type = {
        "meeting_transcript": "meeting_summary",
        "email": "email_thread_summary",
        "pdf": "recent_activity_timeline",
        "docx": "recent_activity_timeline",
        "meeting_summary": "meeting_summary",
        "email_summary": "email_thread_summary",
        "risk": "risk_summary",
    }.get(note.note_type, "recent_activity_timeline")
    source_object = "FakeNote"
    content = (
        f"# Visitor note: {note.title}\n\n"
        f"- Account: {account_name}\n"
        f"- Note date: {note.note_date}\n"
        f"- Note type: {note.note_type}\n"
        f"- Details: {note.body} [Source: {source_object} {note.note_id}]\n"
    )
    conn.execute(
        """
        INSERT INTO rag_documents (doc_id, doc_type, title, content_markdown, metadata_json, source_record_ids, source_record_hashes, account_id, session_id, generated_at, source_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (doc_id) DO UPDATE
        SET content_markdown = EXCLUDED.content_markdown, metadata_json = EXCLUDED.metadata_json, source_hash = EXCLUDED.source_hash
        """,
        (
            doc_id,
            doc_type,
            note.title,
            content,
            Jsonb({"doc_type": doc_type, "source_system": "visitor_fake_note", "account_id": note.account_id, "account_name": account_name, "note_id": note.note_id}),
            [note.note_id],
            [source_hash],
            note.account_id,
            note.session_id,
            datetime.now(timezone.utc),
            source_hash,
        ),
    )
    conn.execute(
        """
        INSERT INTO source_citations (citation_id, doc_id, source_system, source_object, source_record_id, title, source_date, excerpt)
        VALUES (%s, %s, 'visitor_fake_note', %s, %s, %s, %s, %s)
        ON CONFLICT (citation_id) DO UPDATE SET excerpt = EXCLUDED.excerpt
        """,
        (f"{doc_id}:FakeNote:{note.note_id}", doc_id, source_object, note.note_id, note.title, note.note_date, note.body[:300]),
    )


def _serialize_artifact_row(row: dict[str, Any]) -> dict[str, Any]:
    # Legacy `email_thread` rows from older ingestions are surfaced as `email` for the UI.
    if row.get("artifact_type") == "email_thread":
        return {**row, "artifact_type": "email"}
    return dict(row)


def _fake_note_artifact(note: dict[str, Any]) -> dict[str, Any]:
    artifact_type = _fake_note_artifact_type(str(note.get("note_type") or ""))
    created_at = note.get("created_at") or datetime.now(timezone.utc)
    return {
        "artifact_id": f"crm:FakeNote:{note['note_id']}",
        "account_id": note["account_id"],
        "artifact_type": artifact_type,
        "title": note["title"],
        "mime_type": _artifact_mime_type(artifact_type),
        "source_path": f"session/fake-notes/{note['note_id']}",
        "rendered_path": None,
        "extracted_text": _fake_note_markdown(note),
        "metadata": {
            "source_system": "visitor_fake_note",
            "source_object": "FakeNote",
            "source_record_id": note["note_id"],
            "date": note["note_date"],
            "synthetic": True,
        },
        "extraction_method": _artifact_extraction_method(artifact_type),
        "created_at": created_at,
        "ingested_at": created_at,
        "page_urls": [],
    }


def _virtual_crm_artifact(artifact_id: str, request: Request) -> dict[str, Any] | None:
    parts = artifact_id.split(":", 2)
    if len(parts) != 3 or parts[0] != "crm":
        return None
    source_object, record_id = parts[1], parts[2]
    session_id = get_session_id(request)
    with connect_dict(get_settings(request)) as conn:
        row = _fetch_crm_record(conn, source_object, record_id, session_id)
    if not row:
        return None
    record = dict(row)
    title = _crm_record_title(source_object, record)
    account_id = record.get("account_id")
    artifact_type = "crm_record"
    mime_type = "text/markdown"
    extraction_method = "csv_row"
    source_path = f"synthetic/crm/{source_object}/{record_id}"
    extracted_text = _crm_record_markdown(source_object, title, record)
    metadata = {"source_object": source_object, "source_record_id": record_id}
    if source_object == "FakeNote":
        artifact_type = _fake_note_artifact_type(str(record.get("note_type") or ""))
        mime_type = _artifact_mime_type(artifact_type)
        extraction_method = _artifact_extraction_method(artifact_type)
        source_path = f"session/fake-notes/{record_id}"
        extracted_text = _fake_note_markdown(record)
        metadata = {
            "source_system": "visitor_fake_note",
            "source_object": source_object,
            "source_record_id": record_id,
            "date": record.get("note_date"),
            "synthetic": True,
        }
    return {
        "artifact_id": artifact_id,
        "account_id": account_id,
        "artifact_type": artifact_type,
        "title": title,
        "mime_type": mime_type,
        "source_path": source_path,
        "rendered_path": None,
        "extracted_text": extracted_text,
        "metadata": metadata,
        "extraction_method": extraction_method,
        "created_at": record.get("created_at") or datetime.now(timezone.utc),
        "ingested_at": datetime.now(timezone.utc),
        "page_urls": [],
    }


def _fetch_crm_record(conn: Any, source_object: str, record_id: str, session_id: str) -> Any | None:
    if source_object == "Account":
        return conn.execute("SELECT * FROM accounts WHERE account_id = %s", (record_id,)).fetchone()
    if source_object == "Contact":
        return conn.execute("SELECT * FROM contacts WHERE contact_id = %s", (record_id,)).fetchone()
    if source_object == "Opportunity":
        return conn.execute("SELECT * FROM opportunities WHERE opportunity_id = %s", (record_id,)).fetchone()
    if source_object == "Contract":
        return conn.execute("SELECT * FROM contracts WHERE contract_id = %s", (record_id,)).fetchone()
    if source_object in {"Task", "Event"}:
        return conn.execute(
            "SELECT * FROM activities WHERE activity_id = %s AND source_object = %s",
            (record_id, source_object),
        ).fetchone()
    if source_object == "FakeNote":
        return conn.execute(
            "SELECT * FROM fake_notes WHERE note_id = %s AND session_id = %s",
            (record_id, session_id),
        ).fetchone()
    return None


def _crm_record_title(source_object: str, record: dict[str, Any]) -> str:
    if source_object == "Account":
        return str(record.get("account_name") or record.get("account_id") or "Account")
    if source_object == "Contact":
        return str(record.get("name") or record.get("contact_id") or "Contact")
    if source_object == "Opportunity":
        return str(record.get("name") or record.get("opportunity_id") or "Opportunity")
    if source_object == "Contract":
        return str(record.get("contract_number") or record.get("contract_id") or "Contract")
    if source_object in {"Task", "Event"}:
        return str(record.get("subject") or record.get("activity_id") or source_object)
    if source_object == "FakeNote":
        return str(record.get("title") or record.get("note_id") or "Visitor note")
    return source_object


def _crm_record_markdown(source_object: str, title: str, record: dict[str, Any]) -> str:
    hidden = {"raw_record_hash", "embedding", "session_id"}
    lines = [f"# {source_object}: {title}", ""]
    for key, value in record.items():
        if key in hidden or value in (None, "", []):
            continue
        label = key.replace("_", " ").title()
        lines.append(f"- {label}: {value}")
    return "\n".join(lines).strip() + "\n"


def _fake_note_artifact_type(note_type: str) -> str:
    return {
        "meeting_summary": "meeting_transcript",
        "email_summary": "email",
        "task": "docx",
        "risk": "pdf",
        "general": "docx",
    }.get(note_type, note_type if note_type in {"meeting_transcript", "docx", "pdf", "email"} else "docx")


def _artifact_mime_type(artifact_type: str) -> str:
    return {
        "email": "message/rfc822",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "meeting_transcript": "text/markdown",
    }.get(artifact_type, "text/markdown")


def _artifact_extraction_method(artifact_type: str) -> str:
    return "docx_xml" if artifact_type == "docx" else "plain_text"


def _fake_note_markdown(note: dict[str, Any]) -> str:
    note_type = _fake_note_artifact_type(str(note.get("note_type") or ""))
    label = {
        "email": "Email",
        "pdf": "PDF",
        "docx": "Word document",
        "meeting_transcript": "Meeting",
    }.get(note_type, "Document")
    return (
        f"# Synthetic {label}: {note.get('title')}\n\n"
        f"- Date: {note.get('note_date')}\n"
        f"- Source: Session-scoped synthetic note\n\n"
        f"{note.get('body')}\n"
    )


def _fake_doc_id(note_id: str) -> str:
    return f"fake_note:{note_id}"
