from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

from pcad.config import Settings
from pcad.db import connect_dict


BUDGET_MESSAGE = (
    "The public demo has hit its daily budget for this account. The system is still here to demonstrate the architecture — "
    "try again tomorrow, or book a private walkthrough for live interaction."
)


@dataclass
class TokenBucket:
    capacity: int
    refill_seconds: float
    tokens: float
    updated_at: float

    def allow(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.updated_at
        self.tokens = min(float(self.capacity), self.tokens + elapsed * (self.capacity / self.refill_seconds))
        self.updated_at = now
        if self.tokens < 1.0:
            return False
        self.tokens -= 1.0
        return True


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, *, limit: int, window_seconds: float) -> bool:
        if limit <= 0:
            return False
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = TokenBucket(limit, window_seconds, float(limit), time.monotonic())
                self._buckets[key] = bucket
            bucket.capacity = limit
            bucket.refill_seconds = window_seconds
            return bucket.allow()


ip_rate_limiter = InMemoryRateLimiter()
session_message_limiter = InMemoryRateLimiter()


def check_daily_budget(settings: Settings) -> bool:
    with connect_dict(settings) as conn:
        _ensure_budget_table(conn)
        row = conn.execute(
            "SELECT coalesce(tokens_in, 0) + coalesce(tokens_out, 0) AS total FROM daily_budget_usage WHERE usage_date = %s",
            (date.today(),),
        ).fetchone()
    total = int(row["total"]) if row and row["total"] is not None else 0
    return total < settings.daily_token_budget


def record_token_usage(settings: Settings, *, tokens_in: int = 0, tokens_out: int = 0, cost_estimate_eur: float = 0.0) -> None:
    with connect_dict(settings) as conn:
        _ensure_budget_table(conn)
        conn.execute(
            """
            INSERT INTO daily_budget_usage (usage_date, tokens_in, tokens_out, cost_estimate_eur)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (usage_date) DO UPDATE
            SET tokens_in = daily_budget_usage.tokens_in + EXCLUDED.tokens_in,
                tokens_out = daily_budget_usage.tokens_out + EXCLUDED.tokens_out,
                cost_estimate_eur = daily_budget_usage.cost_estimate_eur + EXCLUDED.cost_estimate_eur
            """,
            (date.today(), tokens_in, tokens_out, cost_estimate_eur),
        )
        conn.commit()


def _ensure_budget_table(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_budget_usage (
            usage_date date PRIMARY KEY,
            tokens_in integer NOT NULL DEFAULT 0,
            tokens_out integer NOT NULL DEFAULT 0,
            cost_estimate_eur numeric NOT NULL DEFAULT 0,
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
