from __future__ import annotations


def safe_id(value: str) -> str:
    """Slugify a string into a stable, URL-safe artifact id fragment."""
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_") or "unknown"
