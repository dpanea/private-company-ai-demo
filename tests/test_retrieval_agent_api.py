from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pcad.api.routes import _fake_note_artifact
from pcad.agent.conversation_service import _citations_from_pack
from pcad.llm.citations import allowed_citation_labels, render_structured_answer
from pcad.retrieval.intent import IntentResolver
from pcad.retrieval.retriever import _rank_hybrid_results, _rrf_merge


def test_intent_resolver_new_workflow_intents() -> None:
    resolver = IntentResolver()

    assert resolver.resolve("Brief me before a call with Northstar").intent == "briefing"
    assert resolver.resolve("What changed in the last 14 days?").intent == "what_changed"
    assert resolver.resolve("What open risks or blockers remain?").intent == "open_risks"
    assert resolver.resolve("What is the next action this week?").intent == "next_action"


def test_allowed_citation_labels_only_user_visible_objects() -> None:
    pack = {
        "retrieved_documents": [
            {
                "citations": [
                    {"source_object": "Account", "source_record_id": "SYN_ACC_0001"},
                    {"source_object": "PDF", "source_record_id": "mutual_nda"},
                    {"source_object": "Email", "source_record_id": "msg-1"},
                ]
            }
        ]
    }

    assert allowed_citation_labels(pack) == {"PDF mutual_nda", "Email msg-1"}


@pytest.mark.parametrize("fence", ["```json\n", "```JSON\n", "```\n", "  ```json  \n"])
def test_render_structured_answer_handles_markdown_fenced_json(fence: str) -> None:
    pack = {
        "retrieved_documents": [
            {"citations": [{"source_object": "PDF", "source_record_id": "mutual_nda"}]}
        ]
    }
    payload = (
        '{"status": "answered", "account": {"account_id": null, "account_name": null}, '
        '"clarification": {"message": "", "candidates": []}, '
        '"blocks": [{"type": "paragraph", "text": "Body.", "citations": ["PDF mutual_nda"]}]}'
    )
    raw = f"{fence}{payload}\n```"

    rendered, blocks, validation, _ = render_structured_answer(raw, pack)

    assert rendered == "Body."
    assert blocks == [{"text": "Body.", "citations": ["PDF mutual_nda"]}]
    assert validation["valid"]


def test_render_structured_answer_returns_blocks_without_inline_markers() -> None:
    pack = {
        "retrieved_documents": [
            {"citations": [{"source_object": "PDF", "source_record_id": "mutual_nda"}]}
        ]
    }
    raw = (
        '{"status": "answered", "account": {"account_id": null, "account_name": null}, '
        '"clarification": {"message": "", "candidates": []}, '
        '"blocks": [{"type": "paragraph", "text": "The NDA is mutual.", "citations": ["PDF mutual_nda"]}]}'
    )

    rendered, blocks, validation, _ = render_structured_answer(raw, pack)

    assert rendered == "The NDA is mutual."
    assert blocks == [{"text": "The NDA is mutual.", "citations": ["PDF mutual_nda"]}]
    assert "[Source:" not in rendered
    assert validation["valid"]
    assert validation["cited"] == ["PDF mutual_nda"]


def test_render_structured_answer_drops_unknown_citation_labels_from_blocks() -> None:
    pack = {
        "retrieved_documents": [
            {"citations": [{"source_object": "PDF", "source_record_id": "mutual_nda"}]}
        ]
    }
    raw = (
        '{"status": "answered", "account": {"account_id": null, "account_name": null}, '
        '"clarification": {"message": "", "candidates": []}, '
        '"blocks": [{"type": "paragraph", "text": "Body.", '
        '"citations": ["PDF mutual_nda", "PDF made_up"]}]}'
    )

    _, blocks, validation, _ = render_structured_answer(raw, pack)

    assert blocks == [{"text": "Body.", "citations": ["PDF mutual_nda"]}]
    assert validation["unknown_citations"] == ["PDF made_up"]
    assert not validation["valid"]


def test_insufficient_evidence_does_not_invent_citations() -> None:
    pack = {"retrieved_documents": []}
    raw = (
        '{"status": "insufficient_evidence", "account": {"account_id": null, "account_name": null}, '
        '"clarification": {"message": "", "candidates": []}, "blocks": []}'
    )

    rendered, blocks, validation, _ = render_structured_answer(raw, pack)

    assert rendered.startswith("I do not have enough evidence")
    assert blocks == [{"text": rendered, "citations": []}]
    assert validation["cited"] == []
    assert validation["status"] == "insufficient_evidence"


def test_account_clarification_state_uses_clarification_message() -> None:
    pack = {"retrieved_documents": []}
    raw = (
        '{"status": "needs_account_clarification", "account": {"account_id": null, "account_name": null}, '
        '"clarification": {"message": "Which client do you mean?", "candidates": []}, "blocks": []}'
    )

    rendered, blocks, validation, payload = render_structured_answer(raw, pack)

    assert rendered == "Which client do you mean?"
    assert blocks == [{"text": "Which client do you mean?", "citations": []}]
    assert validation["status"] == "needs_account_clarification"
    assert payload["status"] == "needs_account_clarification"


def test_source_artifact_citations_are_openable_artifacts() -> None:
    pack = {
        "account_id": "SYN_ACC_0001",
        "retrieved_documents": [
            {
                "citations": [
                    {
                        "source_object": "PDF",
                        "source_record_id": "mutual_nda",
                        "title": "Mutual NDA",
                    }
                ]
            }
        ],
    }

    citations = _citations_from_pack(pack, {"cited": {"PDF mutual_nda"}})

    assert citations == [
        {
            "label": "PDF Mutual NDA",
            "source_label": "PDF mutual_nda",
            "source_object": "PDF",
            "source_record_id": "mutual_nda",
            "artifact_id": "pdf:SYN_ACC_0001:mutual_nda",
            "title": "Mutual NDA",
            "source_url": None,
            "source_date": None,
            "excerpt": None,
        }
    ]


def test_rrf_merge_aggregates_reasons_and_picks_top_rank_doc() -> None:
    """All chunks share the same doc_type boost now, so the merged order is
    decided by RRF alone. Doc `a` wins because it appears at rank 1 in two
    rankers (base_context and full_text), whereas `b` only ever shows at rank 2."""
    base = [{"doc_id": "a", "doc_type": "source_artifact_chunk", "reasons": ["base_context"]}]
    full_text = [
        {"doc_id": "a", "doc_type": "source_artifact_chunk", "reasons": ["full_text"]},
        {"doc_id": "b", "doc_type": "source_artifact_chunk", "reasons": ["full_text"]},
    ]
    vector = [
        {"doc_id": "a", "doc_type": "source_artifact_chunk", "reasons": ["vector"]},
        {"doc_id": "b", "doc_type": "source_artifact_chunk", "reasons": ["vector"]},
    ]

    merged = _rrf_merge(base, full_text, vector)
    ranked = _rank_hybrid_results(merged.values(), limit=2)

    assert ranked[0]["doc_id"] == "a"
    assert {"base_context", "full_text", "vector"} <= set(ranked[0]["reasons"])
    assert ranked[1]["doc_id"] == "b"
    assert {"full_text", "vector"} <= set(ranked[1]["reasons"])


def test_fake_note_surfaces_as_source_artifact() -> None:
    created_at = datetime.now(timezone.utc)
    artifact = _fake_note_artifact(
        {
            "note_id": "note-1",
            "session_id": "session-1",
            "account_id": "SYN_ACC_0001",
            "note_type": "pdf",
            "title": "Procurement update",
            "body": "EU hosting is required.",
            "note_date": created_at.date(),
            "created_at": created_at,
        }
    )

    assert artifact["artifact_id"] == "test-note:note-1"
    assert artifact["artifact_type"] == "pdf"
    assert artifact["mime_type"] == "application/pdf"
    assert artifact["metadata"]["source_object"] == "TestNote"
    assert "EU hosting is required." in artifact["extracted_text"]
