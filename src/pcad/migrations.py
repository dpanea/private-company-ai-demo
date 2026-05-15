from __future__ import annotations

import logging
from pathlib import Path

from .config import Settings
from .db import raw_connect
from .logging_utils import configure_logging


logger = logging.getLogger(__name__)
DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "sql" / "migrations"

# A stable 64-bit identifier so concurrent runners (CLI + app) serialize on the
# same advisory lock. Generated once with `crc32('pcad_migrations')`.
MIGRATION_ADVISORY_LOCK_KEY = 0x70636164


def apply_migrations(settings: Settings, migrations_dir: Path = DEFAULT_MIGRATIONS_DIR) -> list[str]:
    """Apply pending migrations in lexical order and return applied versions."""
    migrations_path = Path(migrations_dir)
    applied: list[str] = []

    with raw_connect(settings) as conn:
        # Bootstrap the ledger so the advisory lock and seen-version query can run.
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "    version text PRIMARY KEY,"
            "    applied_at timestamptz NOT NULL DEFAULT now()"
            ")"
        )
        conn.commit()

        # Serialize against other processes (CLI / second app instance / tests).
        conn.execute("SELECT pg_advisory_lock(%s)", (MIGRATION_ADVISORY_LOCK_KEY,))
        try:
            seen_versions = {
                row[0]
                for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
            }
            for migration_path in sorted(migrations_path.glob("*.sql")):
                version = migration_path.stem
                if version in seen_versions:
                    continue
                sql = migration_path.read_text(encoding="utf-8")
                with conn.transaction():
                    conn.execute(sql)
                    conn.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s)",
                        (version,),
                    )
                logger.info("migration.apply.done version=%s", version)
                applied.append(version)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_ADVISORY_LOCK_KEY,))
            conn.commit()
    return applied


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level, color=settings.log_color)
    applied = apply_migrations(settings)
    logger.info("migration.apply.complete applied=%s", len(applied))


if __name__ == "__main__":
    main()
