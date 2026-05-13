from __future__ import annotations

import argparse
import json
from pathlib import Path

from pcad.config import Settings
from pcad.ingestion.runner import run_demo_ingestion
from pcad.logging_utils import configure_logging
from pcad.migrations import apply_migrations


def main() -> None:
    parser = argparse.ArgumentParser(prog="pcad")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("migrate")

    ingest = subparsers.add_parser("ingest-demo")
    ingest.add_argument("--clean", action="store_true")
    ingest.add_argument("--skip-embeddings", action="store_true")
    ingest.add_argument("--synthetic-dir", type=Path, default=Path("data/synthetic"))

    args = parser.parse_args()
    settings = Settings.from_env()
    configure_logging(settings.log_level, color=str(settings.log_color).lower())

    if args.command == "migrate":
        applied = apply_migrations(settings)
        print(json.dumps({"applied": applied}, indent=2))
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
    parser.error(f"Unknown command {args.command}")

