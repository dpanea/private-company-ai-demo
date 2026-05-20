"""End-to-end tests for the ConversationService orchestration.

These tests exercise the real retriever, the real Postgres schema, and the
structured-answer path. The only component substituted is the LLM itself —
replaced with `DeterministicLlm` so we can assert behavior without paying
tokens. The LLM is the external dependency, not the orchestration.
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from company_ai.agent.conversation_service import ConversationService
from company_ai.api.rate_limit import BUDGET_MESSAGE
from company_ai.db import connect_dict
from company_ai.llm.client import TokenUsage
from company_ai.llm.deterministic import DeterministicLlm

from tests._seed import (
    make_settings,
    seed_account,
    seed_rag_document,
    seed_session,
    seed_user,
)


class ForbidLlm(DeterministicLlm):
    """LLM stub that raises on any call. Use for budget-gate tests."""

    def complete(self, *args: Any, **kwargs: Any) -> str:  # type: ignore[override]
        raise AssertionError("LLM.complete was called when it should not have been")

    def complete_stream(self, *args: Any, **kwargs: Any) -> Iterator[str]:  # type: ignore[override]
        raise AssertionError("LLM.complete_stream was called when it should not have been")
        yield ""  # pragma: no cover

    def embed(self, text: str) -> list[float]:  # type: ignore[override]
        raise AssertionError("LLM.embed was called when it should not have been")

    def embed_batch(self, texts: list[str]) -> list[list[float]]:  # type: ignore[override]
        raise AssertionError("LLM.embed_batch was called when it should not have been")


class FixedStructuredLlm(DeterministicLlm):
    """Streams a caller-supplied structured JSON answer (one whitespace token at a time)."""

    def __init__(self, payload: dict[str, Any], *, embedding_dim: int = 1536) -> None:
        super().__init__(embedding_dim=embedding_dim)
        self._payload = json.dumps(payload)
        self.stream_call_count = 0

    def complete_stream(  # type: ignore[override]
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 700,
        response_format: dict[str, Any] | None = None,
    ) -> Iterator[str]:
        self.stream_call_count += 1
        for token in self._payload.split(" "):
            yield token + " "


def _parse_sse(events: list[str]) -> list[tuple[str, dict[str, Any]]]:
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


def _seed_account_with_artifact_chunk(settings) -> str:
    owner_id = seed_user(settings, user_id="USR_TEST")
    seed_account(
        settings,
        account_id="ACC_BRANNFELD",
        account_name="Brannfeld Industrial",
        owner_id=owner_id,
    )
    seed_rag_document(
        settings,
        doc_id="source_artifact_chunk:email:ACC_BRANNFELD:msg_1:message",
        account_id="ACC_BRANNFELD",
        doc_type="source_artifact_chunk",
        title="Security review email",
        content=(
            "Operations is the champion. Security review is the open risk. "
            "Procurement has open questions on milestones."
        ),
        citations=[
            {
                "source_object": "Email",
                "source_record_id": "msg_1",
                "title": "Security review email",
            }
        ],
    )
    return "ACC_BRANNFELD"


def test_send_message_stream_end_to_end(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    account_id = _seed_account_with_artifact_chunk(settings)
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
                "What are the open risks for this account?",
            )
        )
    )

    event_types = [event for event, _ in events]
    assert event_types[0] == "user_message"
    status_values = [data.get("status") for event, data in events if event == "status"]
    assert "thinking" in status_values
    assert "generating" in status_values
    assert "token" in event_types
    assert "replace" in event_types
    assert event_types[-1] == "done"

    # Streamed visible text contains the block prose, never JSON braces or keys.
    streamed_text = "".join(data["content"] for event, data in events if event == "token")
    assert "{" not in streamed_text and "}" not in streamed_text
    assert '"text"' not in streamed_text and '"status"' not in streamed_text

    # The final replace event carries structured blocks (no inline markers).
    replace_event = next(data for event, data in events if event == "replace")
    assert "[Source:" not in replace_event["content"]
    assert any("Email msg_1" in block["citations"] for block in replace_event["blocks"])

    messages = service.get_messages(session_id, thread.thread_id)
    assert [m.role for m in messages] == ["user", "assistant"]
    assistant = messages[-1]
    assert "[Source:" not in assistant.content
    assert any("Email msg_1" in block["citations"] for block in assistant.metadata["blocks"])
    assert assistant.account_id == account_id
    assert assistant.metadata["response_type"] == "answer"
    assert assistant.metadata["citation_validation"]["valid"] is True
    assert any(c["source_record_id"] == "msg_1" for c in assistant.citations)

    with connect_dict(settings) as conn:
        row = conn.execute(
            "SELECT tokens_in, tokens_out FROM daily_budget_usage"
        ).fetchone()
    assert row is not None
    assert row["tokens_in"] >= 42 and row["tokens_out"] >= 17


def test_budget_gate_short_circuits_before_llm(migrated_db: str) -> None:
    settings = make_settings(migrated_db, daily_token_budget=0)
    account_id = _seed_account_with_artifact_chunk(settings)
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


def test_single_streaming_call_emits_one_complete_pair(migrated_db: str) -> None:
    """The structured answer is produced by a single streaming LLM call."""
    settings = make_settings(migrated_db)
    account_id = _seed_account_with_artifact_chunk(settings)
    session_id = seed_session(settings)

    payload = {
        "status": "answered",
        "account": {"account_id": account_id, "account_name": "Brannfeld Industrial"},
        "clarification": {"message": "", "candidates": []},
        "blocks": [
            {
                "type": "paragraph",
                "text": "Procurement remains blocked on milestones.",
                "citations": ["Email msg_1"],
            }
        ],
    }
    llm = FixedStructuredLlm(payload)
    service = ConversationService(settings, llm_client=llm)

    thread = service.create_thread(session_id, account_id=account_id, workflow_seed=None)
    list(service.send_message_stream(session_id, thread.thread_id, "What is the procurement blocker?"))

    assert llm.stream_call_count == 1


def test_insufficient_evidence_when_only_internal_context_available(migrated_db: str) -> None:
    """If the structured answer cannot cite visible artifacts, no source is invented."""
    settings = make_settings(migrated_db)
    owner_id = seed_user(settings, user_id="USR_NO_SOURCE")
    account_id = seed_account(
        settings,
        account_id="ACC_NO_SOURCE",
        account_name="No Source Account",
        owner_id=owner_id,
    )
    session_id = seed_session(settings)

    payload = {
        "status": "insufficient_evidence",
        "account": {"account_id": account_id, "account_name": "No Source Account"},
        "clarification": {"message": "", "candidates": []},
        "blocks": [],
    }
    llm = FixedStructuredLlm(payload)
    service = ConversationService(settings, llm_client=llm)

    thread = service.create_thread(session_id, account_id=account_id, workflow_seed=None)
    list(service.send_message_stream(session_id, thread.thread_id, "What are the open risks?"))

    assistant = service.get_messages(session_id, thread.thread_id)[-1]
    assert assistant.content == "I do not have enough evidence in the visible source artifacts to answer that."
    assert assistant.metadata["citation_validation"]["status"] == "insufficient_evidence"
    assert assistant.citations == []


def test_uncited_answer_falls_back_to_insufficient_evidence(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    account_id = _seed_account_with_artifact_chunk(settings)
    session_id = seed_session(settings)
    payload = {
        "status": "answered",
        "account": {"account_id": account_id, "account_name": "Brannfeld Industrial"},
        "clarification": {"message": "", "candidates": []},
        "blocks": [
            {
                "type": "paragraph",
                "text": "This answer names a fact but does not cite evidence.",
                "citations": [],
            }
        ],
    }
    service = ConversationService(settings, llm_client=FixedStructuredLlm(payload))

    thread = service.create_thread(session_id, account_id=account_id, workflow_seed=None)
    events = _parse_sse(list(service.send_message_stream(session_id, thread.thread_id, "What is the blocker?")))

    replace_event = next(data for event, data in events if event == "replace")
    assert replace_event["content"].startswith("I do not have enough evidence")
    assistant = service.get_messages(session_id, thread.thread_id)[-1]
    assert assistant.metadata["citation_validation"]["status"] == "insufficient_evidence"
    assert assistant.citations == []
