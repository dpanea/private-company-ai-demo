from __future__ import annotations

import re
from dataclasses import dataclass


INTENT_KEYWORDS = {
    "topic_catchup": ("catch me up", "catch up", "overview", "summary", "status", "where are we"),
    "decision_archaeology": ("what did we decide", "decision", "decided", "why did we pick", "why we picked", "reopen"),
    "briefing": ("brief", "briefing", "before a call", "call prep", "prepare me"),
    "what_changed": ("what changed", "changed", "new", "recent", "last 14 days", "since", "updates"),
    "open_risks": ("risk", "risks", "objection", "concern", "blocker", "blocked", "unresolved", "worried"),
    "next_action": ("next action", "next step", "what should i do", "this week", "priority"),
    "draft_follow_up": ("follow-up", "follow up", "draft", "email", "reply", "send"),
    "stakeholder_question": ("stakeholder", "contact", "champion", "decision maker", "who is"),
    "contract_question": ("contract", "renewal", "agreement", "signed", "terms"),
}


@dataclass(frozen=True)
class IntentResult:
    intent: str


class IntentResolver:
    """Heuristic intent classifier. Used as a small hint in the retrieval prompt."""

    def resolve(self, query: str) -> IntentResult:
        lowered = query.lower()
        matches: list[tuple[str, int]] = []
        for intent, terms in INTENT_KEYWORDS.items():
            count = sum(1 for term in terms if _term_matches(lowered, term))
            if count:
                matches.append((intent, count))
        if not matches:
            return IntentResult("account_question")
        matches.sort(key=lambda item: item[1], reverse=True)
        return IntentResult(matches[0][0])


def _term_matches(lowered_query: str, term: str) -> bool:
    lowered_term = term.lower()
    if " " in lowered_term or "-" in lowered_term:
        return lowered_term in lowered_query
    return re.search(rf"\b{re.escape(lowered_term)}\b", lowered_query) is not None
