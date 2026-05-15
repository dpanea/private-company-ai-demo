from __future__ import annotations

import json
import re
from typing import Any

from pcad.models import SourceCitation


USER_VISIBLE_SOURCE_OBJECTS = {"Email", "PDF", "WordDocument", "Meeting", "TestNote"}


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


def render_structured_answer(raw: str, pack: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Validate the structured JSON answer and render the final user-facing text.

    Returns a tuple `(rendered_text, validation, payload)` where `rendered_text`
    contains the answer with inline `[Source: ...]` citation labels appended
    after each block (or the clarification message / insufficiency notice).
    """
    payload = _extract_json_object(raw)
    status = _answer_status(payload.get("status"))
    allowed = allowed_citation_labels(pack)
    blocks = payload.get("blocks") if isinstance(payload.get("blocks"), list) else []
    cited: list[str] = []
    rendered_blocks: list[str] = []
    unknown: set[str] = set()

    for block in blocks:
        if not isinstance(block, dict):
            continue
        text = str(block.get("text") or "").strip()
        if not text:
            continue
        labels = [str(label).strip() for label in block.get("citations") or [] if str(label).strip()]
        labels = list(dict.fromkeys(labels))
        for label in labels:
            if label not in allowed:
                unknown.add(label)
            else:
                cited.append(label)
        if labels and status == "answered":
            text = text.rstrip() + " " + " ".join(f"[Source: {label}]" for label in labels if label in allowed)
        rendered_blocks.append(text)

    if status == "insufficient_evidence":
        rendered = "\n\n".join(rendered_blocks).strip() or "I do not have enough evidence in the visible source artifacts to answer that."
        cited = []
        unknown = set()
        valid = True
    elif status == "needs_account_clarification":
        clarification = payload.get("clarification") if isinstance(payload.get("clarification"), dict) else {}
        rendered = str(clarification.get("message") or "").strip() or "Which client do you mean?"
        cited = []
        unknown = set()
        valid = True
    else:
        rendered = "\n\n".join(rendered_blocks).strip()
        valid = bool(rendered and cited) and not unknown
        if not rendered:
            rendered = "I do not have enough evidence in the visible source artifacts to answer that."
            status = "insufficient_evidence"
            valid = True

    validation = {
        "allowed_citations": sorted(allowed),
        "cited": sorted(set(cited)),
        "unknown_citations": sorted(unknown),
        "has_citation": bool(cited),
        "status": status,
        "valid": valid,
    }
    return rendered, validation, payload


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
        decoder = json.JSONDecoder()
        for index, char in enumerate(cleaned):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(cleaned[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        snippet = cleaned[:200].replace("\n", " ")
        raise ValueError(f"structured answer did not contain a valid JSON object (got: {snippet!r})")
    if not isinstance(parsed, dict):
        raise ValueError(f"structured answer was not a JSON object (got: {type(parsed).__name__})")
    return parsed
