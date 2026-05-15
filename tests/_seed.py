"""Shared seeding helpers for DB-backed tests.

Everything in here writes to a real Postgres via `psycopg.connect` so tests
exercise the same SQL the application uses; nothing here is mocked.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from pcad.config import Settings


def make_settings(database_url: str, **overrides: Any) -> Settings:
    """Build a Settings instance for tests with safe defaults."""
    base = dict(
        database_url=database_url,
        openrouter_api_key=None,
        openrouter_base_url="https://openrouter.ai/api/v1",
        llm_model="qwen/qwen-2.5-7b-instruct",
        llm_reasoning_effort="low",
        embedding_model="qwen/qwen3-embedding-8b",
        embedding_dimensions=1536,
        app_title="Private Company Memory Demo",
        http_referer=None,
        log_level="WARNING",
        log_color=False,
        session_cookie_name="pcad_session",
        session_ttl_days=7,
        session_ttl_hours=4,
        session_secret="test-secret",
        rate_limit_per_ip_per_minute=1000,
        rate_limit_per_session_per_hour=1000,
        daily_token_budget=10_000_000,
        conversation_history_turns=6,
    )
    base.update(overrides)
    return Settings(**base)


def seed_user(settings: Settings, *, user_id: str = "USR_1", name: str = "Test Owner") -> str:
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            """
            INSERT INTO users_or_owners (user_id, name, is_active)
            VALUES (%s, %s, true)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (user_id, name),
        )
        conn.commit()
    return user_id


def seed_account(
    settings: Settings,
    *,
    account_id: str = "ACC_1",
    account_name: str = "Test Account",
    owner_id: str | None = None,
    updated_at: datetime | None = None,
) -> str:
    if owner_id is None:
        owner_id = seed_user(settings)
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            """
            INSERT INTO accounts (account_id, account_name, owner_id, updated_at)
            VALUES (%s, %s, %s, %s)
            """,
            (account_id, account_name, owner_id, updated_at or datetime.now(timezone.utc)),
        )
        conn.commit()
    return account_id


def seed_rag_document(
    settings: Settings,
    *,
    doc_id: str,
    account_id: str,
    doc_type: str,
    title: str,
    content: str,
    embedding: list[float] | None = None,
    metadata: dict[str, Any] | None = None,
    citations: Iterable[dict[str, Any]] | None = None,
    session_id: str | None = None,
    last_source_updated_at: datetime | None = None,
) -> str:
    """Insert a rag_document and any attached source_citations.

    `embedding` is written via a `%s::vector` cast so we can avoid pulling in
    the pgvector Python adapter.
    """
    metadata_payload = dict(metadata or {})
    metadata_payload.setdefault("doc_type", doc_type)
    embedding_literal = (
        "[" + ",".join(f"{value:.8f}" for value in embedding) + "]" if embedding else None
    )
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            """
            INSERT INTO rag_documents (
                doc_id, doc_type, title, content_markdown, metadata_json,
                source_record_ids, source_record_hashes, account_id, session_id,
                last_source_updated_at, generated_at, source_hash, embedding
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
            """,
            (
                doc_id,
                doc_type,
                title,
                content,
                Jsonb(metadata_payload),
                [],
                [],
                account_id,
                session_id,
                last_source_updated_at,
                datetime.now(timezone.utc),
                f"sha256:{doc_id}",
                embedding_literal,
            ),
        )
        for index, citation in enumerate(citations or [], start=1):
            conn.execute(
                """
                INSERT INTO source_citations (
                    citation_id, doc_id, source_system, source_object,
                    source_record_id, title, source_date, excerpt
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    f"{doc_id}:cit:{index}",
                    doc_id,
                    citation.get("source_system", "synthetic"),
                    citation["source_object"],
                    citation["source_record_id"],
                    citation.get("title"),
                    citation.get("source_date"),
                    citation.get("excerpt"),
                ),
            )
        conn.commit()
    return doc_id


def seed_session(settings: Settings, *, session_id: str | None = None) -> str:
    sid = session_id or str(uuid4())
    now = datetime.now(timezone.utc)
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            """
            INSERT INTO sessions (session_id, created_at, last_seen_at, expires_at)
            VALUES (%s, %s, %s, %s)
            """,
            (sid, now, now, now + timedelta(days=7)),
        )
        conn.commit()
    return sid

