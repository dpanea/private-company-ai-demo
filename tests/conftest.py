from __future__ import annotations

import os
from typing import Iterator

import psycopg
import pytest

from company_ai.db import close_pools


APPLICATION_TABLES = [
    "demo_notes",
    "conversation_messages",
    "conversation_threads",
    "sessions",
    "source_citations",
    "rag_documents",
    "raw_artifacts",
    "accounts",
    "users_or_owners",
]
# Legacy CRM tables removed by migration 0015. Listed so `empty_db` can also
# clear them on a database that pre-dates the drop.
LEGACY_CRM_TABLES = ["activities", "contracts", "opportunities", "contacts"]


@pytest.fixture(scope="session")
def db_url() -> str:
    return os.environ.get(
        "COMPANY_AI_TEST_DATABASE_URL",
        os.environ.get("DATABASE_URL", "postgresql://company_ai:company_ai@localhost:5432/company_ai"),
    )


@pytest.fixture(scope="session")
def postgres_available(db_url: str) -> str:
    try:
        with psycopg.connect(db_url, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres is unavailable: {exc}")
    return db_url


@pytest.fixture()
def empty_db(postgres_available: str) -> str:
    with psycopg.connect(postgres_available) as conn:
        for table in [*APPLICATION_TABLES, *LEGACY_CRM_TABLES]:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.execute("DROP TABLE IF EXISTS schema_migrations CASCADE")
        conn.execute("DROP TABLE IF EXISTS daily_budget_usage CASCADE")
    return postgres_available


@pytest.fixture()
def clean_db(postgres_available: str) -> str:
    with psycopg.connect(postgres_available) as conn:
        existing = {
            row[0]
            for row in conn.execute(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                """
            ).fetchall()
        }
        tables = [table for table in APPLICATION_TABLES if table in existing]
        if tables:
            conn.execute(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE")
    return postgres_available


@pytest.fixture()
def migrated_db(empty_db: str) -> Iterator[str]:
    """An empty database with all migrations applied. Closes pools on teardown."""
    from company_ai.migrations import apply_migrations
    from tests._seed import make_settings

    apply_migrations(make_settings(empty_db))
    try:
        yield empty_db
    finally:
        close_pools()


@pytest.fixture(autouse=True)
def _reset_rate_limiters() -> Iterator[None]:
    """Wipe in-memory rate limiters between tests so they don't leak state."""
    from company_ai.api.rate_limit import ip_rate_limiter, session_message_limiter

    ip_rate_limiter._buckets.clear()
    session_message_limiter._buckets.clear()
    try:
        yield
    finally:
        ip_rate_limiter._buckets.clear()
        session_message_limiter._buckets.clear()


@pytest.fixture(scope="session", autouse=True)
def _final_pool_close() -> Iterator[None]:
    yield
    close_pools()
