from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any


class DeterministicLlm:
    """Small deterministic LLM test double used by package-4 tests."""

    def __init__(self, response: str | None = None) -> None:
        self.response = response
        self.calls: list[list[dict[str, str]]] = []

    def embed(self, text: str) -> list[float]:
        seed = sum(ord(ch) for ch in text) or 1
        return [float((seed + index) % 997) / 997.0 for index in range(8)]

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 700,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        self.calls.append(messages)
        if self.response is not None:
            return self.response
        if response_format:
            return json.dumps(
                {
                    "intent": "account_question",
                    "confidence": 0.9,
                    "doc_types": ["account_memory"],
                    "account_hint": None,
                    "needs_recent_activity": False,
                    "needs_contracts": False,
                    "wants_draft": False,
                }
            )
        user_content = messages[-1]["content"] if messages else ""
        citation = "Account SYN_ACC_0001"
        marker = "Allowed citations:"
        if marker in user_content:
            tail = user_content.split(marker, 1)[1].strip().splitlines()
            if tail:
                citation = tail[0].strip("- ").strip()
        return (
            "Deterministic answer generated without calling an external LLM. "
            "The retrieved evidence is available in the context. "
            f"[Source: {citation}]"
        )

    def complete_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 700,
    ) -> Iterator[str]:
        answer = self.complete(messages, temperature=temperature, max_tokens=max_tokens)
        for token in answer.split(" "):
            yield token + " "
