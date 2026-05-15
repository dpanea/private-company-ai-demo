from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row, tuple_row
from psycopg_pool import ConnectionPool

from .config import Settings


logger = logging.getLogger(__name__)

_pools: dict[str, ConnectionPool] = {}
_pools_lock = threading.Lock()


def _get_pool(settings: Settings) -> ConnectionPool:
    """Return a process-wide ConnectionPool keyed by database URL."""
    url = settings.database_url
    pool = _pools.get(url)
    if pool is not None:
        return pool
    with _pools_lock:
        pool = _pools.get(url)
        if pool is None:
            pool = ConnectionPool(
                conninfo=url,
                min_size=settings.db_pool_min_size,
                max_size=settings.db_pool_max_size,
                kwargs={"row_factory": tuple_row},
                open=True,
            )
            _pools[url] = pool
            logger.debug("db.pool.open url=%s min=%s max=%s", url, settings.db_pool_min_size, settings.db_pool_max_size)
        return pool


def close_pools() -> None:
    """Close every cached pool (FastAPI shutdown hook, test teardown)."""
    with _pools_lock:
        for pool in _pools.values():
            try:
                pool.close()
            except Exception:  # pragma: no cover - best-effort
                logger.exception("db.pool.close_failed")
        _pools.clear()


@contextmanager
def connect(settings: Settings) -> Iterator[Connection[Any]]:
    """Context-manager yielding a pooled connection with tuple rows."""
    with _get_pool(settings).connection() as conn:
        conn.row_factory = tuple_row
        yield conn


@contextmanager
def connect_dict(settings: Settings) -> Iterator[Connection[dict[str, Any]]]:
    """Context-manager yielding a pooled connection with dict rows."""
    with _get_pool(settings).connection() as conn:
        conn.row_factory = dict_row
        yield conn


def ensure_extensions(conn: Connection[Any]) -> None:
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


@contextmanager
def raw_connect(settings: Settings) -> Iterator[Connection[Any]]:
    """Open a non-pooled connection. Use only for migrations and tests."""
    with psycopg.connect(settings.database_url) as conn:
        yield conn
