"""End-to-end tests for the ConversationService orchestration.

These tests exercise the real retriever, the real Postgres schema, the real
citation validation/repair logic, and the real persistence path. The only
component substituted is the LLM itself — replaced with `DeterministicLlm` (or
a small subclass) so we can assert behavior without paying tokens. That is the
correct boundary for a test double: the LLM is the *external* dependency, not
the orchestration we are trying to validate.
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest

from pcad.agent.conversation_service import ConversationService
from pcad.api.rate_limit import BUDGET_MESSAGE
from pcad.db import connect_dict
from pcad.llm.client import TokenUsage
from pcad.llm.deterministic import DeterministicLlm
from pcad.retrieval.retriever import _query_instruction

from tests._seed import (
    make_settings,
    seed_account,
    seed_rag_document,
    seed_session,
    seed_user,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class ForbidLlm(DeterministicLlm):
    """An LLM stub that raises if any path is called. Use for budget tests."""

    def complete(self, *args: Any, **kwargs: Any) -> str:  # type: ignore[override]
        raise AssertionError("LLM.complete was called when it should not have been")

    def complete_stream(self, *args: Any, **kwargs: Any) -> Iterator[str]:  # type: ignore[override]
        raise AssertionError("LLM.complete_stream was called when it should not have been")
        yield ""  # pragma: no cover

    def embed(self, text: str) -> list[float]:  # type: ignore[override]
        raise AssertionError("LLM.embed was called when it should not have been")

    def embed_batch(self, texts: list[str]) -> list[list[float]]:  # type: ignore[override]
        raise AssertionError("LLM.embed_batch was called when it should not have been")


class SequencedLlm(DeterministicLlm):
    """Returns each response in sequence; sticks on the last for over-runs.

    Used to drive multi-attempt scenarios such as the citation retry loop.
    Embeddings and JSON-schema (intent) calls continue to use the deterministic
    parent implementation so an unexpected intent LLM call doesn't poison the
    sequence we care about.
    """

    def __init__(self, responses: list[str], *, embedding_dim: int = 1536) -> None:
        super().__init__(embedding_dim=embedding_dim)
        self._responses = list(responses)
        self.complete_call_count = 0

    def complete(  # type: ignore[override]
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 700,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        if response_format is not None:
            # Intent classification path: delegate to the deterministic JSON stub.
            return super().complete(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
        self.calls.append(messages)
        index = min(self.complete_call_count, len(self._responses) - 1)
        self.complete_call_count += 1
        return self._responses[index]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_sse(events: list[str]) -> list[tuple[str, dict[str, Any]]]:
    """Parse raw SSE frames produced by send_message_stream into (event, data)."""
    parsed: list[tuple[str, dict[str, Any]]] = []
    for frame in events:
        event = None
        data: dict[str, Any] | None = None
        for line in frame.splitlines():
            if line.startswith("event: "):
                event = line[len("event: ") :].strip()
            elif line.startswith("data: "):
                data = json.loads(line[len("data: ") :])
        if event is not None and data is not None:
            parsed.append((event, data))
    return parsed


def _seed_account_with_memory(settings) -> str:
    """Seed one account plus an account_memory rag_document and an Account citation."""
    owner_id = seed_user(settings, user_id="USR_TEST")
    seed_account(
        settings,
        account_id="ACC_BRANNFELD",
        account_name="Brannfeld Industrial",
        owner_id=owner_id,
    )
    seed_rag_document(
        settings,
        doc_id="account_memory:ACC_BRANNFELD",
        account_id="ACC_BRANNFELD",
        doc_type="account_memory",
        title="Account memory: Brannfeld Industrial",
        content=(
            "Operations is the champion. Security review is the open risk. "
            "Procurement has open questions on milestones."
        ),
        citations=[
            {
                "source_object": "Account",
                "source_record_id": "ACC_BRANNFELD",
                "title": "Brannfeld Industrial",
            }
        ],
    )
    return "ACC_BRANNFELD"


# ---------------------------------------------------------------------------
# 1. End-to-end agent test with DeterministicLlm
# ---------------------------------------------------------------------------


def test_send_message_stream_end_to_end(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    account_id = _seed_account_with_memory(settings)
    session_id = seed_session(settings)
    llm = DeterministicLlm()
    llm.last_usage = TokenUsage(prompt_tokens=42, completion_tokens=17)
    service = ConversationService(settings, llm_client=llm)

    thread = service.create_thread(session_id, account_id=account_id, workflow_seed=None)
    events = _parse_sse(
        list(
            service.send_message_stream(
                session_id,
                thread.thread_id,
                "Brief me before a call about the open risks for this account",
            )
        )
    )

    event_types = [event for event, _ in events]
    # Order matters: user message first, status updates, tokens, then done.
    assert event_types[0] == "user_message"
    status_values = [data.get("status") for event, data in events if event == "status"]
    assert "thinking" in status_values
    assert "generating" in status_values
    assert "token" in event_types
    assert event_types[-1] == "done"

    streamed_text = "".join(data["content"] for event, data in events if event == "token")
    assert "[Source: Account ACC_BRANNFELD]" in streamed_text

    # Assistant message persisted, citations attached, thread title updated.
    messages = service.get_messages(session_id, thread.thread_id)
    assert [m.role for m in messages] == ["user", "assistant"]
    assistant = messages[-1]
    assert "[Source: Account ACC_BRANNFELD]" in assistant.content
    assert assistant.account_id == account_id
    assert assistant.metadata["response_type"] == "answer"
    assert assistant.metadata["citation_validation"]["valid"] is True
    assert any(c["source_record_id"] == "ACC_BRANNFELD" for c in assistant.citations)

    thread_after = service.get_thread(session_id, thread.thread_id)
    assert thread_after.title != "New conversation"

    # Token usage was recorded.
    with connect_dict(settings) as conn:
        row = conn.execute(
            "SELECT tokens_in, tokens_out FROM daily_budget_usage"
        ).fetchone()
    assert row is not None
    assert row["tokens_in"] >= 42 and row["tokens_out"] >= 17


# ---------------------------------------------------------------------------
# 2. Budget gate runs before any LLM call
# ---------------------------------------------------------------------------


def test_budget_gate_short_circuits_before_llm(migrated_db: str) -> None:
    settings = make_settings(migrated_db, daily_token_budget=0)
    account_id = _seed_account_with_memory(settings)
    session_id = seed_session(settings)
    llm = ForbidLlm()
    service = ConversationService(settings, llm_client=llm)

    thread = service.create_thread(session_id, account_id=account_id, workflow_seed=None)
    events = _parse_sse(
        list(service.send_message_stream(session_id, thread.thread_id, "anything goes here"))
    )

    event_types = [event for event, _ in events]
    assert event_types == ["user_message", "token", "done"]
    streamed = next(data["content"] for event, data in events if event == "token")
    assert streamed == BUDGET_MESSAGE

    messages = service.get_messages(session_id, thread.thread_id)
    assert messages[-1].role == "assistant"
    assert messages[-1].metadata["response_type"] == "budget_exceeded"
    assert messages[-1].content == BUDGET_MESSAGE


# ---------------------------------------------------------------------------
# 7. Citation retry loop
# ---------------------------------------------------------------------------


def test_citation_retry_loop_succeeds_on_second_attempt(migrated_db: str) -> None:
    settings = make_settings(migrated_db, agent_generation_max_attempts=3)
    account_id = _seed_account_with_memory(settings)
    session_id = seed_session(settings)

    valid_answer = "Final answer with citation [Source: Account ACC_BRANNFELD]."
    llm = SequencedLlm(
        responses=[
            "First attempt has no citation at all.",  # streamed: invalid
            valid_answer,                              # retry 1: valid
            "Should never be returned.",               # retry 2: not reached
        ]
    )
    service = ConversationService(settings, llm_client=llm)
    thread = service.create_thread(session_id, account_id=account_id, workflow_seed=None)

    events = _parse_sse(
        list(
            service.send_message_stream(
                session_id,
                thread.thread_id,
                "What are the open risks and the procurement blocker for this account?",
            )
        )
    )

    # We used 2 chat completions (the streamed first attempt + 1 retry).
    assert llm.complete_call_count == 2

    # The final assistant content is the valid answer (after replace),
    # not the first invalid attempt.
    messages = service.get_messages(session_id, thread.thread_id)
    assistant = messages[-1]
    assert assistant.content.strip().endswith("[Source: Account ACC_BRANNFELD].")
    assert assistant.metadata["citation_validation"]["valid"] is True

    # And a `replace` SSE was emitted because the streamed and final answers differ.
    event_types = [event for event, _ in events]
    assert "replace" in event_types


def test_citation_repair_no_fallback_path_logs_warning(
    migrated_db: str, caplog: pytest.LogCaptureFixture
) -> None:
    """If every attempt is uncitable AND no Email/Meeting fallback exists, the
    answer comes through unchanged and a WARNING fires."""
    settings = make_settings(migrated_db, agent_generation_max_attempts=2)
    account_id = _seed_account_with_memory(settings)
    session_id = seed_session(settings)

    llm = SequencedLlm(
        responses=[
            "No citation in the streamed answer.",
            "Still no citation in the retry either.",
        ]
    )
    service = ConversationService(settings, llm_client=llm)
    thread = service.create_thread(session_id, account_id=account_id, workflow_seed=None)

    with caplog.at_level("WARNING", logger="pcad.llm.citations"):
        list(
            service.send_message_stream(
                session_id,
                thread.thread_id,
                "What are the open risks and the procurement blocker for this account?",
            )
        )

    assistant = service.get_messages(session_id, thread.thread_id)[-1]
    # Pack only had an Account citation, no Email/Meeting → fallback returns None.
    # The answer is left as the LLM produced it, and the validator stays invalid.
    assert assistant.content == "Still no citation in the retry either."
    assert assistant.metadata["citation_validation"]["valid"] is False
    # complete() is called twice: once by complete_stream (streamed attempt),
    # once for the single retry allowed by agent_generation_max_attempts=2.
    assert llm.complete_call_count == 2

    assert any(
        "citations.repair_missing_citation.no_fallback" in record.getMessage()
        for record in caplog.records
    ), [record.getMessage() for record in caplog.records]


def test_citation_repair_fallback_appends_when_email_citation_available(
    migrated_db: str, caplog: pytest.LogCaptureFixture
) -> None:
    """With an Email citation in the pack, the hard fallback appends a Sources line."""
    settings = make_settings(migrated_db, agent_generation_max_attempts=2)
    owner_id = seed_user(settings, user_id="USR_FB")
    seed_account(
        settings,
        account_id="ACC_FB",
        account_name="Fallback Account",
        owner_id=owner_id,
    )
    user_query = "What are the open risks and the procurement blocker for this account?"
    llm = SequencedLlm(
        responses=[
            "First attempt has no citation.",
            "Retry attempt also has none.",
        ]
    )
    # Seed the doc's embedding to exactly match the LLM-side embedding of the
    # retrieval query, so vector_search returns this doc unconditionally
    # regardless of whether FTS hits.
    target_embedding = llm.embed(_query_instruction(user_query))
    seed_rag_document(
        settings,
        doc_id="email_thread_summary:ACC_FB:t1",
        account_id="ACC_FB",
        doc_type="email_thread_summary",
        title="Email thread summary: Procurement",
        content="A procurement blocker remains unresolved.",
        embedding=target_embedding,
        citations=[
            {
                "source_object": "Email",
                "source_record_id": "msg-1",
                "title": "Procurement blocker",
            }
        ],
    )
    session_id = seed_session(settings)
    service = ConversationService(settings, llm_client=llm)
    thread = service.create_thread(session_id, account_id="ACC_FB", workflow_seed=None)

    with caplog.at_level("WARNING", logger="pcad.llm.citations"):
        list(service.send_message_stream(session_id, thread.thread_id, user_query))

    assistant = service.get_messages(session_id, thread.thread_id)[-1]
    assert "Sources consulted" in assistant.content
    assert "[Source: Email msg-1]" in assistant.content
    assert assistant.metadata["citation_validation"]["valid"] is True

    assert any(
        "citations.repair_missing_citation.fallback_used" in record.getMessage()
        for record in caplog.records
    ), [record.getMessage() for record in caplog.records]
