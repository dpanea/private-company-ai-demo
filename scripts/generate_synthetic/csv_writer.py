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
    "contacts": [
        "contact_id",
        "account_id",
        "name",
        "first_name",
        "last_name",
        "email",
        "phone",
        "mobile_phone",
        "title",
        "role_or_department",
        "owner_id",
        "created_at",
        "updated_at",
        "source_url",
        "raw_record_id",
        "raw_record_hash",
    ],
    "opportunities": [
        "opportunity_id",
        "account_id",
        "primary_contact_id",
        "contract_id",
        "name",
        "stage",
        "amount",
        "currency",
        "probability",
        "close_date",
        "is_closed",
        "is_won",
        "owner_id",
        "record_type_id",
        "created_at",
        "updated_at",
        "source_url",
        "raw_record_id",
        "raw_record_hash",
    ],
    "contracts": [
        "contract_id",
        "account_id",
        "opportunity_id_if_available",
        "contract_number",
        "status",
        "start_date",
        "end_date",
        "activated_date",
        "customer_signed_contact_id",
        "owner_id",
        "created_at",
        "updated_at",
        "source_url",
        "raw_record_id",
        "raw_record_hash",
    ],
    "activities": [
        "activity_id",
        "source_object",
        "account_id",
        "opportunity_id",
        "contact_id",
        "lead_id",
        "contract_id",
        "who_id",
        "what_id",
        "owner_id",
        "subject",
        "activity_type",
        "subtype",
        "status",
        "priority",
        "activity_date",
        "start_datetime",
        "end_datetime",
        "description",
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
    for name in ("users", "accounts", "contacts", "opportunities", "contracts", "activities"):
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
