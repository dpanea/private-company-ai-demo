from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from pcad.ingestion.parsers.mbox import ParsedEmail
from pcad.ingestion.parsers.meeting_md import ParsedMeeting


KEYWORD_RE = re.compile(
    r"\b(next step|action|risk|decision|concern|approval|blocked|security|compliance|procurement|follow up)\b",
    re.IGNORECASE,
)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class EmailThread:
    account_id: str | None
    thread_id: str
    subject: str
    participants: list[str]
    emails: list[ParsedEmail]
    artifact_ids: list[str]
    extracted_text: str


@dataclass(frozen=True)
class MeetingSummaryInput:
    account_id: str | None
    meeting_id: str
    meeting_title: str
    meeting_date: str | None
    attendees: list[str]
    key_topics: list[str]
    action_items: list[str]
    risks: list[str]
    source_artifact_id: str | None = None


def normalize_email_threads(
    parsed: list[ParsedEmail], *, artifact_prefix: str = "email", account_id: str | None = None
) -> list[EmailThread]:
    """Group emails into threads via Message-ID, References, and In-Reply-To."""
    by_key: dict[str, list[ParsedEmail]] = {}
    for email in parsed:
        key = _thread_key(email)
        by_key.setdefault(key, []).append(email)
    threads: list[EmailThread] = []
    for key, emails in sorted(by_key.items()):
        ordered = sorted(emails, key=lambda item: item.date or datetime.min)
        participants = sorted(
            {address for email in ordered for address in [email.from_addr, *email.to_addrs, *email.cc_addrs] if address}
        )
        artifact_ids = [f"{artifact_prefix}:{_safe_id(email.message_id)}" for email in ordered]
        text = "\n\n---\n\n".join(_email_text(email) for email in ordered)
        subject = ordered[0].subject if ordered else key
        threads.append(EmailThread(account_id, _safe_id(key), subject, participants, ordered, artifact_ids, text))
    return threads


def normalize_meeting_for_summary(
    parsed: ParsedMeeting,
    *,
    meeting_id: str | None = None,
    account_id: str | None = None,
    source_artifact_id: str | None = None,
) -> MeetingSummaryInput:
    """Extract deterministic meeting-summary bullets from a transcript."""
    key_topics: list[str] = []
    action_items: list[str] = []
    risks: list[str] = []
    for speaker, text in parsed.turns:
        sentences = _sentences(text)
        for sentence in sentences[:1]:
            key_topics.append(f"{speaker}: {sentence}")
        for sentence in sentences:
            lower = sentence.casefold()
            bullet = f"{speaker}: {sentence}"
            if any(token in lower for token in ("next step", "action", "follow up", "send", "will ")):
                action_items.append(bullet)
            if any(token in lower for token in ("risk", "concern", "blocked", "security", "compliance", "procurement")):
                risks.append(bullet)
            elif KEYWORD_RE.search(sentence) and bullet not in key_topics:
                key_topics.append(bullet)
    return MeetingSummaryInput(
        account_id=account_id,
        meeting_id=meeting_id or _safe_id(parsed.meeting_title),
        meeting_title=parsed.meeting_title,
        meeting_date=parsed.meeting_date.isoformat() if parsed.meeting_date else None,
        attendees=parsed.attendees,
        key_topics=_dedupe(key_topics)[:12],
        action_items=_dedupe(action_items)[:8],
        risks=_dedupe(risks)[:8],
        source_artifact_id=source_artifact_id,
    )


def _thread_key(email: ParsedEmail) -> str:
    if email.references:
        return email.references[0]
    return email.in_reply_to or email.message_id


def _email_text(email: ParsedEmail) -> str:
    return (
        f"From: {email.from_addr}\n"
        f"To: {', '.join(email.to_addrs)}\n"
        f"Date: {email.date.isoformat() if email.date else 'Unknown'}\n"
        f"Subject: {email.subject}\n\n"
        f"{email.body_text}"
    )


def _sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in SENTENCE_RE.split(text.strip()) if sentence.strip()]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _safe_id(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_") or "unknown"
