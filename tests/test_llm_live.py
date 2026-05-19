"""Live integration test against the configured OpenAI-compatible endpoint.

Opt-in to avoid silently spending tokens on routine `pytest` runs:

    PCAD_LIVE_LLM=1 uv run pytest -m live tests/test_llm_live.py -v

The test makes a real streaming call with `response_format` to verify that:

  - the request is accepted and the stream emits content,
  - only `blocks[].text` (or `clarification.message`) reaches the user,
  - the raw payload is valid JSON matching `ANSWER_RESPONSE_FORMAT`,
  - `render_structured_answer` validates citation labels and returns structured blocks.
"""
from __future__ import annotations

import os
from typing import Any

import pytest

from pcad.config import Settings
from pcad.llm.citations import render_structured_answer
from pcad.llm.client import OpenAICompatibleClient
from pcad.llm.prompts import (
    ANSWER_RESPONSE_FORMAT,
    build_answer_messages,
    render_context_prompt,
)
from pcad.llm.streaming import StructuredAnswerStreamer


pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("PCAD_LIVE_LLM") != "1",
        reason="set PCAD_LIVE_LLM=1 (and run with `-m live`) to opt into real LLM calls",
    ),
]


@pytest.fixture(scope="module")
def client() -> OpenAICompatibleClient:
    from dotenv import load_dotenv  # local import: only relevant when live tests run

    load_dotenv()
    return OpenAICompatibleClient(Settings.from_env())


def _pack(user_request: str, content: str) -> dict[str, Any]:
    return {
        "user_request": user_request,
        "account_name": "Brannfeld Industrial",
        "retrieval_plan": {"intent": "account_question"},
        "conversation_history": [],
        "retrieved_documents": [
            {
                "doc_id": "d1",
                "doc_type": "source_artifact_chunk",
                "title": "Mutual NDA (page 1)",
                "score": 1.0,
                "content_markdown": content,
                "metadata": {},
                "reasons": ["vector"],
                "citations": [
                    {
                        "source_object": "PDF",
                        "source_record_id": "mutual_nda",
                        "title": "Mutual NDA",
                    }
                ],
            }
        ],
    }


def _stream(client: OpenAICompatibleClient, pack: dict[str, Any]) -> tuple[str, StructuredAnswerStreamer]:
    messages = build_answer_messages(render_context_prompt(pack))
    streamer = StructuredAnswerStreamer()
    visible = []
    for token in client.complete_stream(
        messages, temperature=0.0, max_tokens=500, response_format=ANSWER_RESPONSE_FORMAT
    ):
        visible.append(streamer.feed(token))
    return "".join(visible), streamer


def test_live_llm_streams_structured_answer_with_citation(client: OpenAICompatibleClient) -> None:
    """The model returns `status=answered` JSON; only prose streams; citation is appended."""
    pack = _pack(
        "What does the mutual NDA say?",
        "The mutual NDA covers confidential information exchanged during the Brannfeld evaluation. "
        "Term: 2 years. Survives termination by 1 year.",
    )

    visible_text, streamer = _stream(client, pack)

    # The streamed visible text never leaks JSON syntax.
    assert "{" not in visible_text and "}" not in visible_text
    assert '"status"' not in visible_text and '"text"' not in visible_text

    # The raw response is valid JSON we can validate.
    answer, blocks, validation, payload = render_structured_answer(streamer.raw, pack)
    assert payload.get("status") in {"answered", "insufficient_evidence", "needs_account_clarification"}
    assert validation["valid"], f"validation failed: {validation} raw={streamer.raw[:300]!r}"
    assert "[Source:" not in answer

    if validation["status"] == "answered":
        assert validation["cited"], "answered status must cite at least one source"
        assert all(label in validation["allowed_citations"] for label in validation["cited"])
        assert any(block["citations"] for block in blocks), "answered status must attach citations to a block"


def test_live_llm_returns_insufficient_evidence_without_inventing_citations(
    client: OpenAICompatibleClient,
) -> None:
    """When the context cannot answer the question, no citation is invented."""
    pack = _pack(
        "What is the customer's annual procurement budget in EUR?",
        "The mutual NDA covers confidential information. No financial figures, budgets, or "
        "spend amounts are mentioned anywhere in this document.",
    )

    _visible, streamer = _stream(client, pack)
    answer, _blocks, validation, _ = render_structured_answer(streamer.raw, pack)

    assert validation["valid"]
    assert validation["status"] == "insufficient_evidence"
    assert validation["cited"] == []
    assert "[Source:" not in answer
