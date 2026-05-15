from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ManifestArtifact(BaseModel):
    model_config = ConfigDict(extra="allow")

    path: str
    type: Literal["email_thread", "pdf", "docx", "meeting_transcript", "csv_crm"]
    format: str
    has_text_layer: bool | None = None
    requires_ocr: bool = False


class ManifestAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    account_slug: str
    account_name: str
    artifacts: list[ManifestArtifact] = Field(default_factory=list)


class ManifestCrm(BaseModel):
    model_config = ConfigDict(extra="ignore")

    users: str
    accounts: str


class SyntheticManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_date: date
    accounts: list[ManifestAccount]
    crm: ManifestCrm


def load_manifest(synthetic_dir: Path) -> SyntheticManifest:
    """Load and validate a Package-2 manifest.json file."""
    path = synthetic_dir / "manifest.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Synthetic manifest not found: {path}") from exc
    return SyntheticManifest.model_validate(payload)

