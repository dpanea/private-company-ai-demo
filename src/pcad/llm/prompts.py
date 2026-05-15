from __future__ import annotations

import json
from typing import Any

from .citations import allowed_citation_labels, citation_label


DEFAULT_CONTEXT_TOKEN_BUDGET = 6000
DEFAULT_GENERATION_MAX_ATTEMPTS = 3
RESPONSE_MAX_TOKENS = 700
APPROX_CHARS_PER_TOKEN = 4
DOC_MIN_TOKENS = 80  # do not truncate a doc below this; drop it instead

DEFAULT_SYSTEM_PROMPT = (
    "You are a private company memory copilot for a public demo. "
    "Answer only from the provided context. If the answer is not present, say that explicitly. "
    "Cite every substantive paragraph or bullet with an exact allowed source label. "
    "Use citation format [Source: ObjectType RecordId]. "
    "Return plain text or basic markdown only; do not use links, footnotes, or invented sources."
)


def build_answer_messages(
    context_prompt: str,
    *,
    attempt: int,
    previous_answer: str,
    previous_validation: dict[str, Any],
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> list[dict[str, str]]:
    user = context_prompt
    if attempt > 1:
        user += (
            "\n\nThe previous answer failed citation validation. "
            "Rewrite it using only allowed citations and preserve the exact [Source: ObjectType RecordId] format.\n"
            f"Previous validation: {json.dumps(previous_validation, ensure_ascii=False, default=str)}\n"
            f"Previous answer: {previous_answer}"
        )
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user}]


def render_context_prompt(pack: dict[str, Any], *, token_budget: int = DEFAULT_CONTEXT_TOKEN_BUDGET) -> str:
    allowed = sorted(allowed_citation_labels(pack))
    history = pack.get("conversation_history") or []
    history_block = ""
    if history:
        history_block = "Recent conversation history:\n" + _render_history(history) + "\n\n"
    plan = pack.get("retrieval_plan") or {}
    plan_block = _render_plan_summary(plan, pack.get("account_name"))
    prefix = (
        f"User request: {pack['user_request']}\n\n"
        f"{plan_block}"
        f"{history_block}"
        "Allowed citations:\n"
        + "\n".join(f"- {label}" for label in allowed)
        + "\n\nRetrieved context:\n"
    )
    remaining = max(0, token_budget - estimate_tokens(prefix))
    compact_docs = []
    omitted = []
    for item in pack["retrieved_documents"]:
        candidate = compact_context_doc(item)
        candidate_tokens = estimate_tokens(json.dumps(candidate, ensure_ascii=False, default=str))
        if candidate_tokens > remaining:
            truncated = _truncate_doc_to_budget(candidate, remaining)
            if truncated is None:
                omitted.append(item["doc_id"])
                continue
            candidate = truncated
            candidate_tokens = estimate_tokens(json.dumps(candidate, ensure_ascii=False, default=str))
        compact_docs.append(candidate)
        remaining -= candidate_tokens
    prompt = prefix + json.dumps(compact_docs, indent=2, ensure_ascii=False, default=str)
    if omitted:
        prompt += "\n\nDocuments omitted because of token budget:\n" + "\n".join(f"- {doc_id}" for doc_id in omitted)
    return prompt


def compact_context_doc(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "doc_id": item["doc_id"],
        "doc_type": item["doc_type"],
        "title": item["title"],
        "score": item["score"],
        "content": item["content_markdown"],
        "citations": [
            {
                "label": citation_label(citation),
                "title": citation.get("title"),
                "date": str(citation.get("source_date")) if citation.get("source_date") else None,
                "excerpt": citation.get("excerpt"),
            }
            for citation in item["citations"]
        ],
    }


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + APPROX_CHARS_PER_TOKEN - 1) // APPROX_CHARS_PER_TOKEN)


def _render_plan_summary(plan: dict[str, Any], account_name: str | None) -> str:
    """Minimal retrieval-plan hint for the model — intent + account only."""
    intent = plan.get("intent")
    if not intent and not account_name:
        return ""
    parts: list[str] = []
    if intent:
        parts.append(f"intent={intent}")
    if account_name:
        parts.append(f"account={account_name}")
    return f"Retrieval focus: {', '.join(parts)}\n\n"


def _render_history(history: list[dict[str, str]]) -> str:
    lines = []
    for turn in history:
        role = str(turn.get("role", "")).strip() or "user"
        content = str(turn.get("content", "")).strip()
        if not content:
            continue
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _truncate_doc_to_budget(doc: dict[str, Any], remaining_tokens: int) -> dict[str, Any] | None:
    """Trim `content` so the doc fits within `remaining_tokens`. Drop if too small."""
    if remaining_tokens < DOC_MIN_TOKENS:
        return None
    overhead = estimate_tokens(json.dumps({**doc, "content": ""}, ensure_ascii=False, default=str))
    budget_for_content = remaining_tokens - overhead
    if budget_for_content < DOC_MIN_TOKENS:
        return None
    char_budget = max(DOC_MIN_TOKENS * APPROX_CHARS_PER_TOKEN, budget_for_content * APPROX_CHARS_PER_TOKEN)
    content = doc["content"]
    if len(content) <= char_budget:
        return doc
    truncated_content = content[: char_budget - 20].rstrip() + "\n... [truncated]"
    return {**doc, "content": truncated_content}
