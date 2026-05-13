from __future__ import annotations

import json
from typing import Any

from .citations import allowed_citation_labels, citation_label


DEFAULT_CONTEXT_TOKEN_BUDGET = 6000
DEFAULT_GENERATION_MAX_ATTEMPTS = 3
RESPONSE_MAX_TOKENS = 700
APPROX_CHARS_PER_TOKEN = 4

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
        history_block = "Recent conversation history:\n" + json.dumps(history, indent=2, default=str) + "\n\n"
    prefix = (
        f"User request: {pack['user_request']}\n\n"
        f"Retrieval plan:\n{json.dumps(pack['retrieval_plan'], indent=2, default=str)}\n\n"
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
        if candidate_tokens > remaining and compact_docs:
            omitted.append(item["doc_id"])
            continue
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
