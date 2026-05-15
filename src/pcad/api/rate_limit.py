from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import date

from pcad.config import Settings
from pcad.db import connect_dict


BUDGET_MESSAGE = (
    "The public demo has hit its daily budget for this account. The system is still here to demonstrate the architecture — "
    "try again tomorrow, or book a private walkthrough for live interaction."
)

# Evict bucket entries whose `updated_at` is older than `EVICTION_FACTOR * window_seconds`.
# Bounds memory when many unique IPs / sessions hit the limiter and never return.
EVICTION_FACTOR = 4
MAX_BUCKETS = 10_000


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
                self._evict_stale(window_seconds)
                bucket = TokenBucket(limit, window_seconds, float(limit), time.monotonic())
                self._buckets[key] = bucket
            bucket.capacity = limit
            bucket.refill_seconds = window_seconds
            return bucket.allow()

    def _evict_stale(self, window_seconds: float) -> None:
        if len(self._buckets) < MAX_BUCKETS:
            return
        cutoff = time.monotonic() - EVICTION_FACTOR * window_seconds
        for key in [k for k, b in self._buckets.items() if b.updated_at < cutoff]:
            del self._buckets[key]


ip_rate_limiter = InMemoryRateLimiter()
session_message_limiter = InMemoryRateLimiter()


def check_daily_budget(settings: Settings) -> bool:
    with connect_dict(settings) as conn:
        row = conn.execute(
            "SELECT coalesce(tokens_in, 0) + coalesce(tokens_out, 0) AS total FROM daily_budget_usage WHERE usage_date = %s",
            (date.today(),),
        ).fetchone()
    total = int(row["total"]) if row and row["total"] is not None else 0
    return total < settings.daily_token_budget


def record_token_usage(settings: Settings, *, tokens_in: int = 0, tokens_out: int = 0) -> None:
    """Accumulate per-day token counts. Cost (EUR) is not tracked here — it varies
    by model and is best computed offline against an OpenRouter pricing table."""
    with connect_dict(settings) as conn:
        conn.execute(
            """
            INSERT INTO daily_budget_usage (usage_date, tokens_in, tokens_out, cost_estimate_eur)
            VALUES (%s, %s, %s, 0)
            ON CONFLICT (usage_date) DO UPDATE
            SET tokens_in = daily_budget_usage.tokens_in + EXCLUDED.tokens_in,
                tokens_out = daily_budget_usage.tokens_out + EXCLUDED.tokens_out
            """,
            (date.today(), tokens_in, tokens_out),
        )
        conn.commit()
