from __future__ import annotations

import json
import re
from typing import Any

from company_ai.models import SourceCitation


USER_VISIBLE_SOURCE_OBJECTS = {"Email", "PDF", "WordDocument", "Meeting", "DemoNote"}


def citation_label(citation: dict[str, Any] | SourceCitation) -> str:
    if isinstance(citation, SourceCitation):
        return f"{citation.source_object} {citation.source_record_id}"
    return f"{citation['source_object']} {citation['source_record_id']}"


def citation_is_user_visible(citation: dict[str, Any] | SourceCitation) -> bool:
    if isinstance(citation, SourceCitation):
        return citation.source_object in USER_VISIBLE_SOURCE_OBJECTS
    return str(citation.get("source_object") or "") in USER_VISIBLE_SOURCE_OBJECTS


def allowed_citation_labels(pack: dict[str, Any]) -> set[str]:
    labels: set[str] = set()
    for item in pack.get("retrieved_documents", []):
        for citation in item.get("citations", []):
            if citation_is_user_visible(citation):
                labels.add(citation_label(citation))
    return labels


def insufficient_evidence_validation(pack: dict[str, Any]) -> dict[str, Any]:
    """Validation dict used when we fall back to an insufficient-evidence answer."""
    return {
        "allowed_citations": sorted(allowed_citation_labels(pack)),
        "cited": [],
        "unknown_citations": [],
        "has_citation": False,
        "status": "insufficient_evidence",
        "valid": True,
    }


_INSUFFICIENT_EVIDENCE_TEXT = "I do not have enough evidence in the visible source artifacts to answer that."


def render_structured_answer(
    raw: str, pack: dict[str, Any]
) -> tuple[str, list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Validate the structured JSON answer and project it for the UI.

    Returns `(rendered_text, blocks, validation, payload)`:

    - `rendered_text`: plain text of all block bodies joined with blank lines
      (no `[Source: ...]` markers). Used as the SQL `content` column and for
      the streaming-bubble fallback.
    - `blocks`: validated, ordered list of `{"text": str, "citations": list[str]}`.
      Citation labels are guaranteed to be in the Allowed citations set. This is
      the structured payload the frontend renders into text + clickable chips.
    - `validation`: status / cited / unknown_citations / valid metadata.
    - `payload`: the raw parsed JSON object (for debug logging).
    """
    payload = _extract_json_object(raw)
    status = _answer_status(payload.get("status"))
    allowed = allowed_citation_labels(pack)
    raw_blocks = payload.get("blocks") if isinstance(payload.get("blocks"), list) else []
    cited: list[str] = []
    unknown: set[str] = set()
    rendered_blocks: list[dict[str, Any]] = []

    for block in raw_blocks:
        if not isinstance(block, dict):
            continue
        text = str(block.get("text") or "").strip()
        if not text:
            continue
        labels = list(dict.fromkeys(
            str(label).strip() for label in block.get("citations") or [] if str(label).strip()
        ))
        valid_labels: list[str] = []
        for label in labels:
            if label in allowed:
                valid_labels.append(label)
                cited.append(label)
            else:
                unknown.add(label)
        rendered_blocks.append({"text": text, "citations": valid_labels})

    if status == "insufficient_evidence":
        blocks = [{"text": _INSUFFICIENT_EVIDENCE_TEXT, "citations": []}]
        cited = []
        unknown = set()
        valid = True
    elif status == "needs_account_clarification":
        clarification = payload.get("clarification") if isinstance(payload.get("clarification"), dict) else {}
        message = str(clarification.get("message") or "").strip() or "Which client do you mean?"
        blocks = [{"text": message, "citations": []}]
        cited = []
        unknown = set()
        valid = True
    else:
        if not rendered_blocks:
            blocks = [{"text": _INSUFFICIENT_EVIDENCE_TEXT, "citations": []}]
            status = "insufficient_evidence"
            valid = True
            cited = []
            unknown = set()
        else:
            blocks = rendered_blocks
            valid = bool(cited) and not unknown

    rendered = "\n\n".join(block["text"] for block in blocks).strip()

    validation = {
        "allowed_citations": sorted(allowed),
        "cited": sorted(set(cited)),
        "unknown_citations": sorted(unknown),
        "has_citation": bool(cited),
        "status": status,
        "valid": valid,
    }
    return rendered, blocks, validation, payload


def _answer_status(value: Any) -> str:
    if value in {"answered", "insufficient_evidence", "needs_account_clarification"}:
        return str(value)
    return "answered"


_CODE_FENCE_RE = re.compile(r"^\s*```(?:json|JSON)?\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)


def _extract_json_object(text: str) -> dict[str, Any]:
    if not text or not text.strip():
        raise ValueError("structured answer was empty")
    cleaned = text.strip()
    fence = _CODE_FENCE_RE.match(cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Recover from a single leading-prose prefix by scanning to the first `{`.
        first_brace = cleaned.find("{")
        if first_brace >= 0:
            try:
                parsed, _ = json.JSONDecoder().raw_decode(cleaned[first_brace:])
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                return parsed
        snippet = cleaned[:200].replace("\n", " ")
        raise ValueError(f"structured answer did not contain a valid JSON object (got: {snippet!r})")
    if not isinstance(parsed, dict):
        raise ValueError(f"structured answer was not a JSON object (got: {type(parsed).__name__})")
    return parsed
