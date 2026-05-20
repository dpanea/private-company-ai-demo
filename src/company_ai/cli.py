from __future__ import annotations

import argparse
import json
from pathlib import Path

import uvicorn

from company_ai.config import Settings
from company_ai.db import close_pools, connect
from company_ai.ingestion.runner import run_demo_ingestion
from company_ai.logging_utils import configure_logging
from company_ai.migrations import apply_migrations


def main() -> None:
    try:
        _main()
    finally:
        # Release pooled connections so the CLI exits cleanly instead of
        # waiting for psycopg-pool's reaper to time out.
        close_pools()


def _main() -> None:
    parser = argparse.ArgumentParser(prog="company_ai")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("migrate")

    serve = subparsers.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")

    ingest = subparsers.add_parser("ingest-demo")
    ingest.add_argument("--clean", action="store_true")
    ingest.add_argument("--skip-embeddings", action="store_true")
    ingest.add_argument("--synthetic-dir", type=Path, default=Path("data/synthetic"))

    bootstrap = subparsers.add_parser("bootstrap-demo")
    bootstrap.add_argument("--skip-embeddings", action="store_true")
    bootstrap.add_argument("--synthetic-dir", type=Path, default=Path("data/synthetic"))

    args = parser.parse_args()
    settings = Settings.from_env()
    configure_logging(settings.log_level, color=settings.log_color)

    if args.command == "migrate":
        applied = apply_migrations(settings)
        print(json.dumps({"applied": applied}, indent=2))
        return
    if args.command == "serve":
        uvicorn.run("company_ai.api.app:create_app", host=args.host, port=args.port, reload=args.reload, factory=True)
        return
    if args.command == "ingest-demo":
        report = run_demo_ingestion(
            settings,
            synthetic_dir=args.synthetic_dir,
            clean=args.clean,
            skip_embeddings=args.skip_embeddings,
        )
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return
    if args.command == "bootstrap-demo":
        document_count = _rag_document_count(settings)
        if document_count > 0:
            print(json.dumps({"ingested": False, "rag_documents": document_count}, indent=2, sort_keys=True))
            return
        report = run_demo_ingestion(
            settings,
            synthetic_dir=args.synthetic_dir,
            clean=True,
            skip_embeddings=args.skip_embeddings,
        )
        print(json.dumps({"ingested": True, "report": report.as_dict()}, indent=2, sort_keys=True))
        return
    parser.error(f"Unknown command {args.command}")


def _rag_document_count(settings: Settings) -> int:
    with connect(settings) as conn:
        row = conn.execute("SELECT count(*) FROM rag_documents").fetchone()
    if row is None:
        return 0
    return int(row[0])
