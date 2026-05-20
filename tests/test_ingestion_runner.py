from __future__ import annotations

import json
import mailbox
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import Jsonb

from company_ai.config import Settings
from company_ai.ingestion.runner import run_demo_ingestion
from company_ai.migrations import apply_migrations


def test_run_demo_ingestion_populates_expected_tables(empty_db: str, tmp_path: Path) -> None:
    settings = _settings(empty_db)
    apply_migrations(settings)
    synthetic_dir = _mini_corpus(tmp_path)

    report = run_demo_ingestion(settings, synthetic_dir=synthetic_dir, clean=True, skip_embeddings=True)

    assert report.accounts == 2
    assert report.raw_artifacts == 4
    assert report.rag_documents >= 3
    with psycopg.connect(empty_db) as conn:
        doc_types = {
            row[0]
            for row in conn.execute("SELECT DISTINCT doc_type FROM rag_documents").fetchall()
        }
        counts = dict(conn.execute(
            """
            SELECT 'raw_artifacts', count(*) FROM raw_artifacts
            UNION ALL SELECT 'rag_documents', count(*) FROM rag_documents
            UNION ALL SELECT 'source_citations', count(*) FROM source_citations
            """
        ).fetchall())
    assert doc_types == {"source_artifact_chunk"}
    assert counts["raw_artifacts"] == report.raw_artifacts
    assert counts["rag_documents"] == report.rag_documents
    assert counts["source_citations"] == report.source_citations


def test_run_demo_ingestion_clean_rerun_is_stable_and_unclean_fails(empty_db: str, tmp_path: Path) -> None:
    settings = _settings(empty_db)
    apply_migrations(settings)
    synthetic_dir = _mini_corpus(tmp_path)

    first = run_demo_ingestion(settings, synthetic_dir=synthetic_dir, clean=True, skip_embeddings=True)
    first_hashes = _document_hashes(empty_db)

    with pytest.raises(psycopg.errors.UniqueViolation):
        run_demo_ingestion(settings, synthetic_dir=synthetic_dir, clean=False, skip_embeddings=True)

    second = run_demo_ingestion(settings, synthetic_dir=synthetic_dir, clean=True, skip_embeddings=True)

    assert first.raw_artifacts == second.raw_artifacts
    assert first.rag_documents == second.rag_documents
    assert first_hashes == _document_hashes(empty_db)


def test_missing_rendered_page_count_detects_absent_pdf_images(migrated_db: str, tmp_path: Path) -> None:
    settings = _settings(migrated_db)
    root = tmp_path / "data" / "rendered"
    existing = root / "pdf_ACC_1_contract" / "page_1.png"
    missing = root / "pdf_ACC_1_contract" / "page_2.png"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"png")
    _seed_pdf_artifact(settings, [str(existing), str(missing)])

    assert _missing_rendered_page_count(settings, root) == 1


def test_missing_rendered_page_count_rejects_paths_outside_rendered_root(migrated_db: str, tmp_path: Path) -> None:
    settings = _settings(migrated_db)
    root = tmp_path / "data" / "rendered"
    outside = tmp_path / "elsewhere" / "page_1.png"
    outside.parent.mkdir(parents=True)
    outside.write_bytes(b"png")
    _seed_pdf_artifact(settings, [str(outside)])

    assert _missing_rendered_page_count(settings, root) == 1


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


def _mini_corpus(tmp_path: Path) -> Path:
    root = tmp_path / "mini_corpus"
    crm = root / "crm"
    account_dir = root / "accounts" / "northstar_robotics"
    internal_dir = root / "accounts" / "internal_company_knowledge"
    crm.mkdir(parents=True)
    account_dir.mkdir(parents=True)
    internal_dir.mkdir(parents=True)
    _write_csv(crm / "users.csv", ["user_id", "name"], [["SYN_USER_0001", "Avery Stone"]])
    _write_csv(
        crm / "accounts.csv",
        ["account_id", "account_name", "owner_id", "industry"],
        [
            ["SYN_ACC_0001", "Northstar Robotics", "SYN_USER_0001", "Manufacturing"],
            ["SYN_ACC_INTERNAL", "Internal company knowledge", "SYN_USER_0001", "Company operations"],
        ],
    )
    _write_mbox(account_dir / "emails.mbox")
    (account_dir / "meeting.md").write_text(
        """# Meeting: Northstar pilot review

**Date:** 2026-05-03
**Attendees:** Daniel Panea, Jordan Lee

---

**Daniel:** We reviewed the pilot scope and agreed on the next step.
**Jordan:** The main concern is security approval before procurement can sign.
""",
        encoding="utf-8",
    )
    (internal_dir / "decision.md").write_text(
        """# Meeting: Engineering decision record - Postgres and pgvector

**Date:** 2026-05-04
**Attendees:** Daniel Panea, Architecture reviewers

---

**Daniel:** We decided to use Postgres with pgvector because source artifacts, citations, and embeddings can stay in one auditable database.
**Reviewer:** The decision can be reopened if corpus size or isolation requirements exceed what a single database handles cleanly.
""",
        encoding="utf-8",
    )
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "reference_date": "2026-05-13",
                "accounts": [
                    {
                        "account_id": "SYN_ACC_0001",
                        "account_slug": "northstar_robotics",
                        "account_name": "Northstar Robotics",
                        "artifacts": [
                            {"path": "accounts/northstar_robotics/emails.mbox", "type": "email_thread", "format": "mbox"},
                            {"path": "accounts/northstar_robotics/meeting.md", "type": "meeting_transcript", "format": "markdown"},
                        ],
                    }
                ],
                "internal_knowledge": {
                    "account_id": "SYN_ACC_INTERNAL",
                    "account_slug": "internal_company_knowledge",
                    "account_name": "Internal company knowledge",
                    "artifacts": [
                        {
                            "path": "accounts/internal_company_knowledge/decision.md",
                            "type": "meeting_transcript",
                            "format": "markdown",
                        }
                    ],
                },
                "crm": {
                    "users": "crm/users.csv",
                    "accounts": "crm/accounts.csv",
                },
            }
        ),
        encoding="utf-8",
    )
    return root


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    lines = [",".join(header)]
    lines.extend(",".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_mbox(path: Path) -> None:
    box = mailbox.mbox(path)
    box.lock()
    try:
        root_id = "northstar-root@example.test"
        box.add(_message(root_id, "Security approval", "daniel@example.test", ["jordan@northstar.example"], "Can we resolve the security concern this week?"))
        box.add(_message("northstar-reply@example.test", "Re: Security approval", "jordan@northstar.example", ["daniel@example.test"], "Procurement is blocked until the security concern is answered.", in_reply_to=root_id, references=[root_id]))
        box.flush()
    finally:
        box.unlock()
        box.close()


def _message(
    message_id: str,
    subject: str,
    from_addr: str,
    to_addrs: list[str],
    body: str,
    *,
    in_reply_to: str | None = None,
    references: list[str] | None = None,
) -> EmailMessage:
    message = EmailMessage()
    message["Message-ID"] = f"<{message_id}>"
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = ", ".join(to_addrs)
    message["Date"] = format_datetime(datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc))
    if in_reply_to:
        message["In-Reply-To"] = f"<{in_reply_to}>"
    if references:
        message["References"] = " ".join(f"<{item}>" for item in references)
    message.set_content(body)
    return message


def _seed_pdf_artifact(settings: Settings, rendered_paths: list[str]) -> None:
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            """
            INSERT INTO users_or_owners (user_id, name, is_active)
            VALUES ('USR_PDF', 'PDF Owner', true)
            ON CONFLICT (user_id) DO NOTHING
            """
        )
        conn.execute(
            """
            INSERT INTO accounts (account_id, account_name, owner_id)
            VALUES ('ACC_PDF', 'PDF Account', 'USR_PDF')
            ON CONFLICT (account_id) DO NOTHING
            """
        )
        conn.execute(
            """
            INSERT INTO raw_artifacts (
                artifact_id, account_id, artifact_type, title, mime_type, source_path,
                rendered_path, extracted_text, metadata, extraction_method, created_at
            )
            VALUES (%s, 'ACC_PDF', 'pdf', 'Contract', 'application/pdf', 'synthetic/contract.pdf',
                %s, 'Extracted text', %s, 'plain_text', now())
            """,
            (
                "pdf:ACC_PDF:contract",
                rendered_paths[0] if rendered_paths else None,
                Jsonb({"rendered_image_paths": rendered_paths}),
            ),
        )
        conn.commit()


def _document_hashes(db_url: str) -> list[tuple[str, str]]:
    with psycopg.connect(db_url) as conn:
        return conn.execute("SELECT doc_id, source_hash FROM rag_documents ORDER BY doc_id").fetchall()
