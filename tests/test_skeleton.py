from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import psycopg

from company_ai.config import Settings
from company_ai.migrations import apply_migrations
from company_ai.models import (
    Account,
    ConversationMessage,
    ConversationThread,
    DemoNote,
    RagDocument,
    RawArtifact,
    Session,
    SourceCitation,
    SyntheticDataset,
    UserOwner,
)


EXPECTED_TABLES = {
    "schema_migrations",
    "users_or_owners",
    "accounts",
    "raw_artifacts",
    "rag_documents",
    "source_citations",
    "sessions",
    "conversation_threads",
    "conversation_messages",
    "demo_notes",
    "daily_budget_usage",
}
DROPPED_CRM_TABLES = {"contacts", "opportunities", "contracts", "activities"}


def _settings(db_url: str) -> Settings:
    return Settings(
        database_url=db_url,
        llm_api_key=None,
        llm_base_url="https://openrouter.ai/api/v1",
        llm_model="qwen/qwen-2.5-7b-instruct",
        llm_reasoning_effort="low",
        embedding_model="qwen/qwen3-embedding-8b",
        embedding_dimensions=1536,
        app_title="The Company Knowledge AI",
        http_referer=None,
        log_level="INFO",
        log_color=False,
        session_cookie_name="company_ai_session",
        session_ttl_days=7,
        session_secret="test-secret",
        rate_limit_per_ip_per_minute=20,
        rate_limit_per_session_per_hour=50,
        daily_token_budget=1_500_000,
    )


def test_apply_migrations_runs_and_is_idempotent(empty_db: str) -> None:
    settings = _settings(empty_db)

    first = apply_migrations(settings)
    second = apply_migrations(settings)

    assert first == [
        "0001_init",
        "0002_pgvector_pgtrgm",
        "0003_normalized_crm_tables",
        "0004_raw_artifacts",
        "0005_rag_documents",
        "0006_source_citations",
        "0007_conversation",
        "0008_demo_notes",
        "0009_proactive_alerts",
        "0010_daily_budget_usage",
        "0011_demo_note_artifact_types",
        "0012_session_scoped_cascade",
        "0013_drop_proactive_alerts",
        "0014_delete_crm_source_citations",
        "0015_drop_crm_tables",
    ]
    assert second == []


def test_expected_tables_and_extensions_exist(empty_db: str) -> None:
    settings = _settings(empty_db)
    apply_migrations(settings)

    with psycopg.connect(empty_db) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                """
            ).fetchall()
        }
        extensions = {
            row[0]
            for row in conn.execute(
                """
                SELECT extname
                FROM pg_extension
                WHERE extname IN ('vector', 'pg_trgm')
                """
            ).fetchall()
        }

    assert EXPECTED_TABLES <= tables
    assert tables.isdisjoint(DROPPED_CRM_TABLES)
    assert extensions == {"vector", "pg_trgm"}


def test_pydantic_models_round_trip_json() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    today = date(2026, 1, 1)
    later = now + timedelta(days=7)

    citation = SourceCitation(
        citation_id="cit_1",
        doc_id="doc_1",
        source_object="Email",
        source_record_id="artifact_1",
        title="Renewal email",
        source_date=today,
        excerpt="The customer asked about rollout timing.",
    )
    models = [
        UserOwner(user_id="user_1", name="Avery Stone", email="avery@example.com"),
        Account(account_id="acct_1", account_name="Northstar Robotics", owner_id="user_1"),
        citation,
        RagDocument(
            doc_id="doc_1",
            doc_type="source_artifact_chunk",
            title="Source artifact chunk",
            content_markdown="Customer wants a security review.",
            source_hash="hash_1",
            citations=[citation],
        ),
        RawArtifact(
            artifact_id="artifact_1",
            account_id="acct_1",
            artifact_type="email",
            title="Renewal email",
            mime_type="message/rfc822",
            source_path="data/synthetic/email.eml",
            extracted_text="Can we review rollout timing?",
            extraction_method="plain_text",
            created_at=now,
            ingested_at=now,
        ),
        DemoNote(
            note_id="note_1",
            session_id="session_1",
            account_id="acct_1",
            note_type="docx",
            title="Call note",
            body="Customer asked for a pricing summary.",
            note_date=today,
            created_at=now,
        ),
        ConversationThread(
            thread_id="thread_1",
            session_id="session_1",
            account_id="acct_1",
            account_name="Northstar Robotics",
            title="Call briefing",
            workflow_seed="call_briefing",
            created_at=now,
            updated_at=now,
        ),
        ConversationMessage(
            message_id="message_1",
            thread_id="thread_1",
            role="assistant",
            content="They need a security review.",
            account_id="acct_1",
            account_name="Northstar Robotics",
            citations=[{"doc_id": "doc_1"}],
            metadata={"workflow": "call_briefing"},
            created_at=now,
        ),
        Session(session_id="session_1", created_at=now, last_seen_at=now, expires_at=later),
        SyntheticDataset(),
    ]

    for model in models:
        reconstructed = type(model).model_validate_json(model.model_dump_json())
        assert reconstructed == model
