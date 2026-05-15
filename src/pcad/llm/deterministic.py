from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from pcad.llm.client import TokenUsage


class DeterministicLlm:
    """In-process LLM test double.

    - `embed` / `embed_batch` produce vectors of `embedding_dim` floats, seeded
      from the text content so they are deterministic across runs. The default
      dim (1536) matches the demo's `rag_documents.embedding` column so the
      stub can drive `vector_search` without dimension mismatches.
    - `complete` returns whatever was passed via `response`. If `response` is
      `None` it parses the prompt's `Allowed citations:` block and constructs an
      answer that cites the first allowed label, which is enough to satisfy the
      agent's citation validator in tests.
    - `complete_stream` tokenizes that answer on whitespace and yields each
      piece, so callers exercising streaming see realistic SSE-shaped events.
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

    def close(self) -> None:  # parity with OpenAICompatibleClient.close
        return None
