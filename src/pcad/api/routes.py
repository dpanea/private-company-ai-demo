from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from psycopg.types.json import Jsonb

from pcad.agent.conversation_service import ConversationService
from pcad.config import Settings
from pcad.db import connect_dict
from pcad.ingestion.embeddings import index_pending_embeddings
from pcad.models import FakeNote
from pcad.retrieval.alerts import ProactiveAlertGenerator

from .schemas import FakeNoteCreateIn, ThreadCreateIn, SendMessageIn


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


@router.get("/accounts")
def accounts(request: Request) -> list[dict[str, Any]]:
    with connect_dict(get_settings(request)) as conn:
        rows = conn.execute(
            "SELECT account_id, account_name, account_type, industry, website, owner_id FROM accounts ORDER BY account_name"
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
    with connect_dict(get_settings(request)) as conn:
        rows = conn.execute(
            "SELECT artifact_id, account_id, artifact_type, title, mime_type, source_path, rendered_path, metadata, extraction_method, created_at, ingested_at FROM raw_artifacts WHERE account_id = %s ORDER BY created_at DESC",
            (account_id,),
        ).fetchall()
    return [dict(row) for row in rows]


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    data = dict(row)
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
def create_fake_note(account_id: str, payload: FakeNoteCreateIn, request: Request) -> dict[str, Any]:
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
    index_pending_embeddings(settings, batch_limit=20)
    alerts = ProactiveAlertGenerator(settings).generate_for_account(account_id, session_id=session_id)
    return {"note": note.model_dump(mode="json"), "alerts": [alert.model_dump(mode="json") for alert in alerts]}


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


def _fake_doc_id(note_id: str) -> str:
    return f"fake_note:{note_id}"
