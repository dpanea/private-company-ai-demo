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


class Contact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_id: str
    account_id: str
    name: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    mobile_phone: str | None = None
    title: str | None = None
    role_or_department: str | None = None
    owner_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    source_url: str | None = None
    raw_record_id: str | None = None
    raw_record_hash: str | None = None


class Opportunity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opportunity_id: str
    account_id: str
    primary_contact_id: str | None = None
    contract_id: str | None = None
    name: str
    stage: str | None = None
    amount: float | None = None
    currency: str | None = "EUR"
    probability: float | None = None
    close_date: date | None = None
    is_closed: bool | None = None
    is_won: bool | None = None
    owner_id: str | None = None
    record_type_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    source_url: str | None = None
    raw_record_id: str | None = None
    raw_record_hash: str | None = None


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_id: str
    account_id: str
    opportunity_id_if_available: str | None = None
    contract_number: str
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    activated_date: date | None = None
    customer_signed_contact_id: str | None = None
    owner_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    source_url: str | None = None
    raw_record_id: str | None = None
    raw_record_hash: str | None = None


class Activity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: str
    source_object: Literal["Task", "Event"]
    account_id: str | None = None
    opportunity_id: str | None = None
    contact_id: str | None = None
    lead_id: str | None = None
    contract_id: str | None = None
    who_id: str | None = None
    what_id: str | None = None
    owner_id: str | None = None
    subject: str | None = None
    activity_type: str | None = None
    subtype: str | None = None
    status: str | None = None
    priority: str | None = None
    activity_date: date | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    description: str | None = None
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
    doc_type: Literal[
        "account_memory",
        "opportunity_snapshot",
        "recent_activity_timeline",
        "contract_snapshot",
        "stakeholder_map",
        "email_thread_summary",
        "meeting_summary",
        "risk_summary",
    ]
    title: str
    content_markdown: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    source_record_ids: list[str] = Field(default_factory=list)
    source_record_hashes: list[str] = Field(default_factory=list)
    account_id: str | None = None
    opportunity_id: str | None = None
    contract_id: str | None = None
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
    artifact_type: Literal["email", "email_thread", "pdf", "docx", "meeting_transcript", "crm_record"]
    title: str
    mime_type: str
    source_path: str
    rendered_path: str | None = None
    extracted_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    extraction_method: Literal["plain_text", "ocr", "docx_xml", "mbox_parse", "csv_row"]
    created_at: datetime
    ingested_at: datetime


class ProactiveAlert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_id: str
    account_id: str
    alert_type: Literal[
        "unresolved_objection",
        "stalled_account",
        "approaching_close_date",
        "missing_followup",
        "champion_positive_signal",
        "data_inconsistency",
    ]
    severity: Literal["info", "warning", "critical"]
    title: str
    body_markdown: str
    evidence_doc_ids: list[str] = Field(default_factory=list)
    evidence_artifact_ids: list[str] = Field(default_factory=list)
    created_at: datetime


class FakeNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_id: str
    session_id: str
    account_id: str
    note_type: Literal["meeting_summary", "email_summary", "task", "risk", "general"]
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
    contacts: list[Contact] = Field(default_factory=list)
    opportunities: list[Opportunity] = Field(default_factory=list)
    contracts: list[Contract] = Field(default_factory=list)
    activities: list[Activity] = Field(default_factory=list)
    raw_artifacts: list[RawArtifact] = Field(default_factory=list)
    rag_documents: list[RagDocument] = Field(default_factory=list)
    source_citations: list[SourceCitation] = Field(default_factory=list)
    sessions: list[Session] = Field(default_factory=list)
    fake_notes: list[FakeNote] = Field(default_factory=list)
    conversation_threads: list[ConversationThread] = Field(default_factory=list)
    conversation_messages: list[ConversationMessage] = Field(default_factory=list)
    proactive_alerts: list[ProactiveAlert] = Field(default_factory=list)
