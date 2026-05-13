from __future__ import annotations

import logging
from pathlib import Path

from .config import Settings
from .db import connect
from .logging_utils import configure_logging


logger = logging.getLogger(__name__)
DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "sql" / "migrations"


def apply_migrations(settings: Settings, migrations_dir: Path = DEFAULT_MIGRATIONS_DIR) -> list[str]:
    """Apply pending migrations in lexical order and return applied versions."""
    migrations_path = Path(migrations_dir)
    init_path = migrations_path / "0001_init.sql"
    applied: list[str] = []

    with connect(settings) as conn:
        conn.execute(init_path.read_text(encoding="utf-8"))
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
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
            logger.info("migration.apply.done version=%s", version)
            applied.append(version)
    return applied


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level, color=str(settings.log_color).lower())
    applied = apply_migrations(settings)
    logger.info("migration.apply.complete applied=%s", len(applied))


if __name__ == "__main__":
    main()
