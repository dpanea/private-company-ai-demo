from __future__ import annotations


def safe_id(value: str) -> str:
    """Slugify a string into a stable, URL-safe artifact id fragment."""
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_") or "unknown"


def vector_literal(values: list[float]) -> str:
    """Format a float vector as a pgvector literal."""
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"
