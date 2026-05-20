from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserOwner(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    name: str
    email: str | None = None
    is_active: bool = True
    profile_or_role: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Account(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    account_name: str
    account_type: str | None = None
    industry: str | None = None
    website: str | None = None
    phone: str | None = None
    billing_country: str | None = None
    billing_city: str | None = None
    owner_id: str | None = None
    parent_account_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    source_url: str | None = None
    raw_record_id: str | None = None
    raw_record_hash: str | None = None


class SourceCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citation_id: str
    doc_id: str
    source_system: str = "synthetic"
    source_object: str
    source_record_id: str
    source_url: str | None = None
    title: str | None = None
    source_date: date | None = None
    owner_id: str | None = None
    excerpt: str | None = None


class RagDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str
    doc_type: Literal["source_artifact_chunk"]
    title: str
    content_markdown: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    source_record_ids: list[str] = Field(default_factory=list)
    source_record_hashes: list[str] = Field(default_factory=list)
    account_id: str | None = None
    owner_id: str | None = None
    session_id: str | None = None
    last_source_updated_at: datetime | None = None
    generated_at: datetime = Field(default_factory=utc_now)
    source_hash: str
    citations: list[SourceCitation] = Field(default_factory=list)


class RawArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    account_id: str | None
    artifact_type: Literal["email", "pdf", "docx", "meeting_transcript"]
    title: str
    mime_type: str
    source_path: str
    rendered_path: str | None = None
    extracted_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    extraction_method: Literal["plain_text", "ocr", "docx_xml", "mbox_parse"]
    created_at: datetime
    ingested_at: datetime


class DemoNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_id: str
    session_id: str
    account_id: str
    note_type: Literal["meeting_transcript", "docx", "pdf", "email"]
    title: str
    body: str
    note_date: date
    created_at: datetime


class ConversationThread(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    session_id: str
    account_id: str | None
    account_name: str | None
    title: str
    workflow_seed: str | None
    created_at: datetime
    updated_at: datetime


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str
    thread_id: str
    role: Literal["user", "assistant"]
    content: str
    account_id: str | None
    account_name: str | None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class Session(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime


class SyntheticDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    users: list[UserOwner] = Field(default_factory=list)
    accounts: list[Account] = Field(default_factory=list)
    raw_artifacts: list[RawArtifact] = Field(default_factory=list)
    rag_documents: list[RagDocument] = Field(default_factory=list)
    source_citations: list[SourceCitation] = Field(default_factory=list)
