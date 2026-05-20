from __future__ import annotations

import mailbox
from dataclasses import dataclass
from datetime import datetime
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path


@dataclass(frozen=True)
class ParsedEmail:
    message_id: str
    subject: str
    from_addr: str
    to_addrs: list[str]
    cc_addrs: list[str]
    date: datetime | None
    in_reply_to: str | None
    references: list[str]
    body_text: str
    attachments: list[str]


def parse_mbox(path: Path) -> list[ParsedEmail]:
    """Parse an mbox file into plain-text email records."""
    emails: list[ParsedEmail] = []
    box = mailbox.mbox(path)
    for index, message in enumerate(box):
        message_id = _clean_message_id(message.get("Message-ID")) or f"{path.stem}-{index}"
        emails.append(
            ParsedEmail(
                message_id=message_id,
                subject=str(message.get("Subject", "")).strip(),
                from_addr=_first_address(message.get("From", "")),
                to_addrs=_addresses(message.get_all("To", [])),
                cc_addrs=_addresses(message.get_all("Cc", [])),
                date=_parse_date(message.get("Date")),
                in_reply_to=_clean_message_id(message.get("In-Reply-To")),
                references=[_clean_message_id(ref) for ref in str(message.get("References", "")).split() if ref],
                body_text=_plain_text(message).strip(),
                attachments=_attachments(message),
            )
        )
    return emails


def _plain_text(message: Message) -> str:
    if message.is_multipart():
        parts: list[str] = []
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            disposition = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disposition:
                continue
            if part.get_content_type() == "text/plain":
                parts.append(_decode_payload(part))
        return "\n\n".join(part for part in parts if part)
    return _decode_payload(message) if message.get_content_type() == "text/plain" else ""


def _decode_payload(message: Message) -> str:
    payload = message.get_payload(decode=True)
    if payload is None:
        raw = message.get_payload()
        return raw if isinstance(raw, str) else ""
    charset = message.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _attachments(message: Message) -> list[str]:
    names: list[str] = []
    for part in message.walk() if message.is_multipart() else []:
        disposition = (part.get("Content-Disposition") or "").lower()
        filename = part.get_filename()
        if "attachment" in disposition or filename:
            names.append(filename or "unnamed attachment")
    return names


def _addresses(values: list[str] | tuple[str, ...] | str) -> list[str]:
    raw_values = [values] if isinstance(values, str) else list(values)
    return [address for _, address in getaddresses(raw_values) if address]


def _first_address(value: str) -> str:
    addresses = _addresses(value)
    return addresses[0] if addresses else value


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def _clean_message_id(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().strip("<>")

