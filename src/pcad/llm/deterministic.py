from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from pcad.llm.client import TokenUsage


class DeterministicLlm:
    """In-process LLM test double.

    - `embed`/`embed_batch` produce deterministic vectors.
    - `complete` and `complete_stream` return a structured `company_memory_answer`
      JSON document that cites the first allowed label parsed from the prompt's
      `Allowed citations:` block, so the citation validator passes in tests.
      `complete_stream` yields the same JSON one whitespace-separated token at a
      time so callers exercising streaming see realistic SSE-shaped events.
    """

    def __init__(self, response: str | None = None, *, embedding_dim: int = 1536) -> None:
        if embedding_dim <= 0:
            raise ValueError("embedding_dim must be positive")
        self.response = response
        self.embedding_dim = embedding_dim
        self.calls: list[list[dict[str, str]]] = []
        self.last_usage = TokenUsage()

    def embed(self, text: str) -> list[float]:
        seed = sum(ord(ch) for ch in text) or 1
        return [float((seed + index) % 997) / 997.0 for index in range(self.embedding_dim)]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]

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
        return _structured_demo_answer(messages)

    def complete_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 700,
        response_format: dict[str, Any] | None = None,
    ) -> Iterator[str]:
        answer = self.complete(messages, temperature=temperature, max_tokens=max_tokens, response_format=response_format)
        for token in answer.split(" "):
            yield token + " "

    def close(self) -> None:  # parity with OpenAICompatibleClient.close
        return None


def _structured_demo_answer(messages: list[dict[str, str]]) -> str:
    user_content = messages[-1]["content"] if messages else ""
    citation = "Email msg_1"
    marker = "Allowed citations:"
    if marker in user_content:
        for line in user_content.split(marker, 1)[1].strip().splitlines():
            label = line.strip("- ").strip()
            if label:
                citation = label
                break
    return json.dumps(
        {
            "status": "answered",
            "account": {"account_id": None, "account_name": None},
            "clarification": {"message": "", "candidates": []},
            "blocks": [
                {
                    "type": "paragraph",
                    "text": "Deterministic answer generated without calling an external LLM. The retrieved evidence is available in the context.",
                    "citations": [citation],
                }
            ],
        }
    )
