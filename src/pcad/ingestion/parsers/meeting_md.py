from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


TURN_RE = re.compile(r"^\*\*(?P<speaker>[^:*]+):\*\*\s*(?P<text>.*)$")


@dataclass(frozen=True)
class ParsedMeeting:
    meeting_title: str
    meeting_date: date | None
    attendees: list[str]
    turns: list[tuple[str, str]]
    full_text: str


def parse_meeting_md(path: Path) -> ParsedMeeting:
    """Parse a speaker-labeled markdown transcript."""
    full_text = path.read_text(encoding="utf-8")
    header_text, _, body = full_text.partition("---")
    header_lines = [line.strip() for line in header_text.splitlines() if line.strip()]
    title = _parse_title(header_lines)
    meeting_date = _parse_date_field(header_lines)
    attendees = _parse_attendees(header_lines)
    turns: list[tuple[str, str]] = []
    current_speaker: str | None = None
    current_text: list[str] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = TURN_RE.match(line)
        if match:
            if current_speaker:
                turns.append((current_speaker, " ".join(current_text).strip()))
            current_speaker = match.group("speaker").strip()
            current_text = [match.group("text").strip()]
        elif current_speaker:
            current_text.append(line)
    if current_speaker:
        turns.append((current_speaker, " ".join(current_text).strip()))
    return ParsedMeeting(title, meeting_date, attendees, turns, full_text)


def _parse_title(lines: list[str]) -> str:
    for line in lines:
        if line.startswith("#"):
            return line.lstrip("#").strip()
        if line.casefold().startswith("meeting:"):
            return line.split(":", 1)[1].strip()
    return "Untitled meeting"


def _parse_date_field(lines: list[str]) -> date | None:
    for line in lines:
        cleaned = _clean_header_line(line)
        if cleaned.casefold().startswith("date:"):
            try:
                return date.fromisoformat(cleaned.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def _parse_attendees(lines: list[str]) -> list[str]:
    for line in lines:
        cleaned = _clean_header_line(line)
        if cleaned.casefold().startswith("attendees:"):
            return [part.strip() for part in cleaned.split(":", 1)[1].split(",") if part.strip()]
    return []


def _clean_header_line(line: str) -> str:
    return line.replace("**", "").strip()
