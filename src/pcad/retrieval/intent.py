from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from typing import Any

from pcad.llm.client import LlmClient


logger = logging.getLogger(__name__)

ALL_DOC_TYPES = [
    "account_memory",
    "opportunity_snapshot",
    "recent_activity_timeline",
    "contract_snapshot",
    "stakeholder_map",
    "email_thread_summary",
    "meeting_summary",
    "risk_summary",
]

INTENTS = [
    "account_question",
    "briefing",
    "what_changed",
    "open_risks",
    "next_action",
    "draft_follow_up",
    "stakeholder_question",
    "contract_question",
]

DOC_TYPES_BY_INTENT = {
    "account_question": ALL_DOC_TYPES,
    "briefing": [
        "account_memory",
        "recent_activity_timeline",
        "opportunity_snapshot",
        "meeting_summary",
        "email_thread_summary",
        "stakeholder_map",
        "risk_summary",
    ],
    "what_changed": ["recent_activity_timeline", "email_thread_summary", "meeting_summary", "account_memory"],
    "open_risks": ["risk_summary", "account_memory", "email_thread_summary", "meeting_summary"],
    "next_action": ["recent_activity_timeline", "risk_summary", "account_memory", "opportunity_snapshot"],
    "draft_follow_up": [
        "account_memory",
        "recent_activity_timeline",
        "opportunity_snapshot",
        "email_thread_summary",
        "stakeholder_map",
    ],
    "stakeholder_question": ["stakeholder_map", "account_memory", "opportunity_snapshot"],
    "contract_question": ["account_memory", "contract_snapshot", "recent_activity_timeline"],
}

INTENT_KEYWORDS = {
    "briefing": ("brief", "briefing", "before a call", "call prep", "prepare me"),
    "what_changed": ("what changed", "changed", "new", "recent", "last 14 days", "since", "updates"),
    "open_risks": ("risk", "risks", "objection", "concern", "blocker", "blocked", "unresolved", "worried"),
    "next_action": ("next action", "next step", "what should i do", "this week", "priority"),
    "draft_follow_up": ("follow-up", "follow up", "draft", "email", "reply", "send"),
    "stakeholder_question": ("stakeholder", "contact", "champion", "decision maker", "who is"),
    "contract_question": ("contract", "renewal", "agreement", "signed", "terms"),
}

LLM_CONFIDENCE_THRESHOLD = 0.85
INTENT_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "company_memory_intent_classification",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "enum": sorted(INTENTS)},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "doc_types": {"type": "array", "items": {"type": "string", "enum": ALL_DOC_TYPES}},
                "account_hint": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "needs_recent_activity": {"type": "boolean"},
                "needs_contracts": {"type": "boolean"},
                "wants_draft": {"type": "boolean"},
            },
            "required": [
                "intent",
                "confidence",
                "doc_types",
                "account_hint",
                "needs_recent_activity",
                "needs_contracts",
                "wants_draft",
            ],
            "additionalProperties": False,
        },
    },
}


@dataclass(frozen=True)
class IntentResult:
    raw_query: str
    intent: str
    confidence: float
    source: str
    doc_types: list[str]
    account_hint: str | None = None
    needs_recent_activity: bool = False
    needs_contracts: bool = False
    wants_draft: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class IntentResolver:
    def __init__(self, llm_client: LlmClient | None = None) -> None:
        self.llm_client = llm_client

    def resolve(self, query: str) -> IntentResult:
        heuristic = self._heuristic(query)
        if heuristic.confidence >= LLM_CONFIDENCE_THRESHOLD or not self.llm_client:
            return heuristic
        try:
            return self._from_llm(query, heuristic)
        except Exception as exc:
            logger.warning("intent.llm_failed fallback=%s error=%s", heuristic.intent, exc)
            return heuristic

    def _heuristic(self, query: str) -> IntentResult:
        lowered = query.lower()
        matches: list[tuple[str, int]] = []
        for intent, terms in INTENT_KEYWORDS.items():
            count = sum(1 for term in terms if _term_matches(lowered, term))
            if count:
                matches.append((intent, count))
        if not matches:
            return _intent_result(query, "account_question", confidence=0.2, source="heuristic")
        matches.sort(key=lambda item: item[1], reverse=True)
        top_intent, top_count = matches[0]
        confidence = min(0.95, 0.65 + (0.15 * top_count))
        if len(matches) > 1 and matches[1][1] == top_count:
            confidence = 0.55
        return _intent_result(query, top_intent, confidence=confidence, source="heuristic")

    def _from_llm(self, query: str, heuristic: IntentResult) -> IntentResult:
        messages = [
            {
                "role": "system",
                "content": (
                    "Classify a question for a private company-memory copilot. "
                    "Return JSON that exactly matches the requested schema. "
                    f"Allowed intents: {', '.join(INTENTS)}. "
                    f"doc_types can only contain: {', '.join(ALL_DOC_TYPES)}."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "query": query,
                        "heuristic": heuristic.as_dict(),
                        "expected_schema": {
                            "intent": "account_question",
                            "confidence": 0.0,
                            "doc_types": ALL_DOC_TYPES,
                            "account_hint": None,
                            "needs_recent_activity": False,
                            "needs_contracts": False,
                            "wants_draft": False,
                        },
                    }
                ),
            },
        ]
        raw = self.llm_client.complete(messages, temperature=0.0, max_tokens=220, response_format=INTENT_RESPONSE_FORMAT)
        payload = _extract_json_object(raw)
        return _intent_result(
            query,
            _parse_intent(payload.get("intent"), heuristic.intent),
            confidence=_clamp_float(payload.get("confidence"), fallback=heuristic.confidence),
            source="llm",
            doc_types=_valid_doc_types(payload.get("doc_types")) or heuristic.doc_types,
            account_hint=_optional_str(payload.get("account_hint")),
            needs_recent_activity=bool(payload.get("needs_recent_activity", heuristic.needs_recent_activity)),
            needs_contracts=bool(payload.get("needs_contracts", heuristic.needs_contracts)),
            wants_draft=bool(payload.get("wants_draft", heuristic.wants_draft)),
        )


def _intent_result(
    query: str,
    intent: str,
    *,
    confidence: float,
    source: str,
    doc_types: list[str] | None = None,
    account_hint: str | None = None,
    needs_recent_activity: bool | None = None,
    needs_contracts: bool | None = None,
    wants_draft: bool | None = None,
) -> IntentResult:
    safe_intent = _parse_intent(intent, "account_question")
    safe_doc_types = _valid_doc_types(doc_types) or DOC_TYPES_BY_INTENT[safe_intent]
    return IntentResult(
        raw_query=query,
        intent=safe_intent,
        confidence=max(0.0, min(float(confidence), 1.0)),
        source=source,
        doc_types=safe_doc_types,
        account_hint=account_hint,
        needs_recent_activity=needs_recent_activity if needs_recent_activity is not None else safe_intent in {"briefing", "what_changed", "next_action"},
        needs_contracts=needs_contracts if needs_contracts is not None else safe_intent == "contract_question",
        wants_draft=wants_draft if wants_draft is not None else safe_intent == "draft_follow_up",
    )


def _parse_intent(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value in INTENTS:
        return value
    return fallback if fallback in INTENTS else "account_question"


def _term_matches(lowered_query: str, term: str) -> bool:
    lowered_term = term.lower()
    if " " in lowered_term or "-" in lowered_term:
        return lowered_term in lowered_query
    return re.search(rf"\b{re.escape(lowered_term)}\b", lowered_query) is not None


def _valid_doc_types(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    allowed = set(ALL_DOC_TYPES)
    return list(dict.fromkeys(item for item in value if isinstance(item, str) and item in allowed))


def _optional_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _clamp_float(value: Any, *, fallback: float) -> float:
    try:
        return max(0.0, min(float(value), 1.0))
    except (TypeError, ValueError):
        return fallback


def _extract_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        raise ValueError("intent classifier response did not contain a valid JSON object")
    if not isinstance(parsed, dict):
        raise ValueError("intent classifier did not return a JSON object")
    return parsed
