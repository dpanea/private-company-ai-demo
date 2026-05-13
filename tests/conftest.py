from __future__ import annotations

import os

import psycopg
import pytest


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


@pytest.fixture(scope="session")
def db_url() -> str:
    return os.environ.get(
        "PCAD_TEST_DATABASE_URL",
        os.environ.get("DATABASE_URL", "postgresql://pcad:pcad@localhost:5432/pcad"),
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
        for table in APPLICATION_TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.execute("DROP TABLE IF EXISTS schema_migrations CASCADE")
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
