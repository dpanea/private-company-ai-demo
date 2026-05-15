"""End-to-end route tests against a real Postgres via FastAPI's TestClient.

The app is started for real (the `lifespan` runs, the SessionMiddleware does
its real DB work, the rate limiter runs in process). The only substituted
component is the LLM — replaced with `DeterministicLlm` so streaming-chat
endpoints can be exercised without paying tokens.
"""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from pcad.agent.conversation_service import ConversationService
from pcad.api.app import create_app
from pcad.db import connect_dict
from pcad.llm.deterministic import DeterministicLlm

from tests._seed import (
    make_settings,
    seed_account,
    seed_rag_document,
    seed_user,
)


def _app_with_deterministic_llm(settings, llm: DeterministicLlm | None = None):
    """Build the FastAPI app and swap in a DeterministicLlm-backed service.

    `app.state.conversation_service` is replaced *before* TestClient enters the
    lifespan, so every request goes through the substituted service. Nothing
    else is mocked.
    """
    llm = llm or DeterministicLlm()
    app = create_app(settings)
    app.state.conversation_service = ConversationService(settings, llm_client=llm)
    return app, llm


def _seed_minimal_account(settings) -> str:
    seed_user(settings, user_id="USR_R")
    seed_account(
        settings,
        account_id="ACC_R1",
        account_name="Routes Test Account",
        owner_id="USR_R",
    )
    seed_rag_document(
        settings,
        doc_id="source_artifact_chunk:email:ACC_R1:msg_1:message",
        account_id="ACC_R1",
        doc_type="source_artifact_chunk",
        title="Route test email",
        content="Account memory used by route tests.",
        citations=[
            {
                "source_object": "Email",
                "source_record_id": "msg_1",
                "title": "Route test email",
            }
        ],
    )
    return "ACC_R1"


# ---------------------------------------------------------------------------
# Smoke + listing endpoints
# ---------------------------------------------------------------------------


def test_health_endpoint(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    app, _ = _app_with_deterministic_llm(settings)
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"ok": "true"}


def test_session_cookie_is_issued_and_reused(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    app, _ = _app_with_deterministic_llm(settings)
    with TestClient(app) as client:
        first = client.get("/api/session")
        second = client.get("/api/session")
    assert first.status_code == 200
    assert first.json()["session_id"]
    # Same cookie → same session id on the next request.
    assert first.json()["session_id"] == second.json()["session_id"]


def test_reset_session_deletes_session_scoped_rows(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    _seed_minimal_account(settings)
    app, _ = _app_with_deterministic_llm(settings)

    with TestClient(app) as client:
        first = client.get("/api/session")
        old_session_id = first.json()["session_id"]
        note_response = client.post(
            "/api/accounts/ACC_R1/fake-notes",
            json={
                "note_type": "docx",
                "title": "Visitor note",
                "body": "There is a new procurement question to track.",
                "note_date": date(2026, 5, 14).isoformat(),
            },
        )
        assert note_response.status_code == 200
        note_id = note_response.json()["note"]["note_id"]

        reset = client.delete("/api/session")
        assert reset.status_code == 200
        assert reset.json() == {"ok": True}

        next_session = client.get("/api/session").json()["session_id"]

    assert next_session != old_session_id
    with connect_dict(settings) as conn:
        counts = conn.execute(
            """
            SELECT
                (SELECT count(*) FROM sessions WHERE session_id = %s)::int AS sessions,
                (SELECT count(*) FROM fake_notes WHERE note_id = %s)::int AS fake_notes,
                (SELECT count(*) FROM rag_documents WHERE doc_id = %s)::int AS rag_documents,
                (SELECT count(*) FROM source_citations WHERE doc_id = %s)::int AS source_citations
            """,
            (old_session_id, note_id, f"fake_note:{note_id}", f"fake_note:{note_id}"),
        ).fetchone()
    assert dict(counts) == {
        "sessions": 0,
        "fake_notes": 0,
        "rag_documents": 0,
        "source_citations": 0,
    }


def test_accounts_endpoint_returns_seeded_accounts(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    _seed_minimal_account(settings)
    app, _ = _app_with_deterministic_llm(settings)
    with TestClient(app) as client:
        response = client.get("/api/accounts")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["account_id"] == "ACC_R1"
    assert payload[0]["account_name"] == "Routes Test Account"


def test_account_detail_returns_account_metadata(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    _seed_minimal_account(settings)
    app, _ = _app_with_deterministic_llm(settings)
    with TestClient(app) as client:
        response = client.get("/api/accounts/ACC_R1")
        missing = client.get("/api/accounts/NOPE")
    assert response.status_code == 200
    detail = response.json()
    assert detail["account_id"] == "ACC_R1"
    assert detail["account_name"] == "Routes Test Account"
    assert "contacts" not in detail
    assert "opportunities" not in detail
    assert missing.status_code == 404


# ---------------------------------------------------------------------------
# Conversation threads + SSE stream
# ---------------------------------------------------------------------------


def test_create_thread_then_send_message_via_sse_stream(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    _seed_minimal_account(settings)
    app, _ = _app_with_deterministic_llm(settings)

    with TestClient(app) as client:
        thread_response = client.post(
            "/api/threads",
            json={"account_id": "ACC_R1", "workflow_seed": None},
        )
        assert thread_response.status_code == 200
        thread_id = thread_response.json()["thread_id"]

        # New thread starts with no messages.
        messages_resp = client.get(f"/api/threads/{thread_id}/messages")
        assert messages_resp.status_code == 200
        assert messages_resp.json() == []

        stream_resp = client.post(
            f"/api/threads/{thread_id}/messages/stream",
            json={"message": "Brief me before a call about open risks"},
        )
        assert stream_resp.status_code == 200
        assert stream_resp.headers["content-type"].startswith("text/event-stream")
        body = stream_resp.text
        assert "event: user_message" in body
        assert "event: token" in body
        assert "event: done" in body

        # The exchange should now be persisted on the thread.
        messages_after = client.get(f"/api/threads/{thread_id}/messages").json()

    roles = [m["role"] for m in messages_after]
    assert roles == ["user", "assistant"]
    assert "[Source: Email msg_1]" in messages_after[-1]["content"]


# ---------------------------------------------------------------------------
# Fake notes + background task
# ---------------------------------------------------------------------------


def test_fake_note_post_persists_and_triggers_background_task(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    _seed_minimal_account(settings)
    app, _ = _app_with_deterministic_llm(settings)

    with TestClient(app) as client:
        response = client.post(
            "/api/accounts/ACC_R1/fake-notes",
            json={
                "note_type": "docx",
                "title": "Visitor note",
                "body": "There is a new procurement question to track.",
                "note_date": date(2026, 5, 14).isoformat(),
            },
        )
        assert response.status_code == 200
        note = response.json()["note"]
        assert note["title"] == "Visitor note"
        assert "alerts" not in response.json()

        # GET returns the note we just posted.
        list_resp = client.get("/api/accounts/ACC_R1/fake-notes")
        assert list_resp.status_code == 200
        listed = list_resp.json()
        assert [item["note_id"] for item in listed] == [note["note_id"]]

        artifacts_resp = client.get("/api/accounts/ACC_R1/artifacts")
        assert artifacts_resp.status_code == 200
        assert any(item["artifact_id"] == f"test-note:{note['note_id']}" for item in artifacts_resp.json())


def test_fake_note_post_on_unknown_account_returns_404(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    app, _ = _app_with_deterministic_llm(settings)

    with TestClient(app) as client:
        response = client.post(
            "/api/accounts/NOPE/fake-notes",
            json={
                "note_type": "docx",
                "title": "x",
                "body": "y",
                "note_date": date(2026, 5, 14).isoformat(),
            },
        )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


def test_per_ip_rate_limit_returns_429_after_quota(migrated_db: str) -> None:
    """The in-memory token-bucket limiter blocks the second non-GET in the same
    window when limit=1."""
    settings = make_settings(migrated_db, rate_limit_per_ip_per_minute=1)
    _seed_minimal_account(settings)
    app, _ = _app_with_deterministic_llm(settings)

    with TestClient(app) as client:
        first = client.post(
            "/api/threads", json={"account_id": "ACC_R1", "workflow_seed": None}
        )
        second = client.post(
            "/api/threads", json={"account_id": "ACC_R1", "workflow_seed": None}
        )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == "Rate limit exceeded"


# ---------------------------------------------------------------------------
# Embedding-dimension startup assertion (test 8)
# ---------------------------------------------------------------------------


def test_embedding_dimension_mismatch_raises_on_lifespan_startup(migrated_db: str) -> None:
    """If EMBEDDING_DIMENSIONS no longer matches rag_documents.embedding's
    declared dim, the lifespan must refuse to start."""
    settings = make_settings(migrated_db, embedding_dimensions=512)
    app, _ = _app_with_deterministic_llm(settings)

    with pytest.raises(RuntimeError, match="EMBEDDING_DIMENSIONS.*512"):
        with TestClient(app):
            pass
