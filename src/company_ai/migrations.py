from __future__ import annotations

import logging
from pathlib import Path

from .config import Settings
from .db import raw_connect
from .logging_utils import configure_logging


logger = logging.getLogger(__name__)
DEFAULT_INIT_SQL = Path(__file__).resolve().parents[2] / "sql" / "init.sql"

# Stable 64-bit identifier so concurrent runners (CLI + app) serialize on the
# same Postgres advisory lock.
MIGRATION_ADVISORY_LOCK_KEY = 0x636B6169


def apply_migrations(settings: Settings, init_sql: Path = DEFAULT_INIT_SQL) -> bool:
    """Apply the single init schema if it has not been applied yet.

    Returns True if the schema was applied during this call, False if it was
    already in place. The file is idempotent (every statement uses IF NOT
    EXISTS), so a second call is a cheap no-op.
    """
    sql = Path(init_sql).read_text(encoding="utf-8")
    with raw_connect(settings) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (MIGRATION_ADVISORY_LOCK_KEY,))
        try:
            with conn.transaction():
                conn.execute(sql)
            logger.info("migration.apply.done file=%s", init_sql.name)
            return True
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_ADVISORY_LOCK_KEY,))
            conn.commit()


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level, color=settings.log_color)
    apply_migrations(settings)


if __name__ == "__main__":
    main()
