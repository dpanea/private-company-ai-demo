from __future__ import annotations

from typing import Any

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from .config import Settings


def connect(settings: Settings) -> Connection[Any]:
    return psycopg.connect(settings.database_url)


def connect_dict(settings: Settings) -> Connection[dict[str, Any]]:
    return psycopg.connect(settings.database_url, row_factory=dict_row)


def ensure_extensions(conn: Connection[Any]) -> None:
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
