from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


FIELDNAMES: dict[str, list[str]] = {
    "users": [
        "user_id",
        "name",
        "email",
        "is_active",
        "profile_or_role",
        "created_at",
        "updated_at",
    ],
    "accounts": [
        "account_id",
        "account_name",
        "account_type",
        "industry",
        "website",
        "phone",
        "billing_country",
        "billing_city",
        "owner_id",
        "parent_account_id",
        "created_at",
        "updated_at",
        "source_url",
        "raw_record_id",
        "raw_record_hash",
    ],
}


def write_crm_csvs(output_dir: Path, records: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_paths: dict[str, str] = {}
    for name in ("users", "accounts"):
        path = output_dir / f"{name}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES[name], extrasaction="raise")
            writer.writeheader()
            for row in records[name]:
                writer.writerow({field: _csv_value(row.get(field, "")) for field in FIELDNAMES[name]})
        manifest_paths[name] = f"crm/{name}.csv"
    return manifest_paths


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
