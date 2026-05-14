from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ThreadCreateIn(BaseModel):
    account_id: str | None = None
    workflow_seed: str | None = None


class SendMessageIn(BaseModel):
    message: str


class FakeNoteCreateIn(BaseModel):
    note_type: Literal["meeting_transcript", "docx", "pdf", "email"]
    title: str
    body: str
    note_date: date


class SessionOut(BaseModel):
    session_id: str
    created_at: datetime


class AccountOut(BaseModel):
    account_id: str
    account_name: str
    account_type: str | None = None
    industry: str | None = None
    website: str | None = None
    owner_id: str | None = None
    billing_country: str | None = None
    billing_city: str | None = None
    artifact_count: int | None = None
    alert_count: int | None = None
    days_since_activity: int | None = None


class ArtifactOut(BaseModel):
    artifact_id: str
    account_id: str | None
    artifact_type: str
    title: str
    mime_type: str
    source_path: str
    rendered_path: str | None = None
    extracted_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    page_urls: list[str] = Field(default_factory=list)


class AlertOut(BaseModel):
    alert_id: str
    account_id: str
    alert_type: str
    severity: str
    title: str
    body_markdown: str
    evidence_doc_ids: list[str] = Field(default_factory=list)
    evidence_artifact_ids: list[str] = Field(default_factory=list)
    created_at: datetime


class FakeNoteOut(BaseModel):
    note_id: str
    session_id: str
    account_id: str
    note_type: str
    title: str
    body: str
    note_date: date
    created_at: datetime


class FakeNoteCreateOut(BaseModel):
    note: FakeNoteOut
    alerts: list[AlertOut]
