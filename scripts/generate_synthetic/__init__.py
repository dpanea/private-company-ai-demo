from __future__ import annotations

from .accounts import AccountSpec, build_accounts, build_crm_records
from .generator import generate_corpus

__all__ = [
    "AccountSpec",
    "build_accounts",
    "build_crm_records",
    "generate_corpus",
]
