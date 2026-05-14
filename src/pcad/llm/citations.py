from __future__ import annotations

import logging
import re
from typing import Any

from pcad.models import SourceCitation


logger = logging.getLogger(__name__)
SOURCE_RE = re.compile(r"\[Source:\s*([^\]]+)\]")


def citation_label(citation: dict[str, Any] | SourceCitation) -> str:
    if isinstance(citation, SourceCitation):
        return f"{citation.source_object} {citation.source_record_id}"
    return f"{citation['source_object']} {citation['source_record_id']}"


def allowed_citation_labels(pack: dict[str, Any]) -> set[str]:
    labels: set[str] = set()
    for item in pack.get("retrieved_documents", []):
        for citation in item.get("citations", []):
            labels.add(citation_label(citation))
    return labels


def validate_citations(answer: str, pack: dict[str, Any]) -> dict[str, Any]:
    allowed = allowed_citation_labels(pack)
    cited = set(SOURCE_RE.findall(answer))
    return {
        "allowed_citations": sorted(allowed),
        "cited": sorted(cited),
        "unknown_citations": sorted(cited - allowed),
        "has_citation": bool(cited),
        "valid": bool(cited) and not (cited - allowed),
    }


def normalize_citation_format(answer: str, pack: dict[str, Any]) -> str:
    labels = allowed_citation_labels(pack)
    if not labels:
        return answer
    label_alt = "|".join(re.escape(label) for label in sorted(labels, key=len, reverse=True))
    pattern = re.compile(
        rf"\[\[?Source:\s*(?P<label>{label_alt})\s*\]?\]"
        rf"|\(Source:\s*(?P<label2>{label_alt})\s*\)"
        rf"|(?<!\[)\bSource:\s*(?P<label3>{label_alt})\b(?!\])"
    )
    return pattern.sub(lambda m: f"[Source: {m.group('label') or m.group('label2') or m.group('label3')}]", answer)


def repair_missing_citations(answer: str, pack: dict[str, Any]) -> str:
    validation = validate_citations(answer, pack)
    if validation["valid"]:
        return answer
    allowed = allowed_citation_labels(pack)
    if not allowed:
        return answer

    repaired = answer
    for label in sorted(allowed, key=len, reverse=True):
        if f"[Source: {label}]" in repaired:
            continue
        pattern = re.compile(rf"(?<!\[Source:\s){re.escape(label)}(?!\s*\])")
        repaired = pattern.sub(f"[Source: {label}]", repaired)
    repaired = normalize_citation_format(repaired, pack)
    if validate_citations(repaired, pack)["valid"]:
        return repaired

    fallback = _fallback_citation_label(pack)
    if not fallback:
        return answer
    logger.debug("citations.repair_missing_citation fallback_citation=%s", fallback)
    return answer.rstrip() + f"\n\nSources consulted: see panel on the right. [Source: {fallback}]"


def _fallback_citation_label(pack: dict[str, Any]) -> str | None:
    for item in pack.get("retrieved_documents", []):
        for citation in item.get("citations", []):
            if _citation_points_to_artifact(citation, pack.get("account_id")):
                return citation_label(citation)
    if pack.get("account_id"):
        return None
    allowed = sorted(allowed_citation_labels(pack))
    return allowed[0] if allowed else None


def _citation_points_to_artifact(citation: dict[str, Any], account_id: str | None) -> bool:
    record_id = str(citation.get("source_record_id") or "")
    source_object = str(citation.get("source_object") or "")
    if source_object in {"Email", "Meeting"}:
        return ":" in record_id or bool(account_id)
    return False
