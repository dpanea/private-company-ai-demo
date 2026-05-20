from __future__ import annotations

import json

from company_ai.llm.streaming import StructuredAnswerStreamer


def _stream(streamer: StructuredAnswerStreamer, payload: dict) -> str:
    raw = json.dumps(payload)
    visible = []
    for char in raw:
        visible.append(streamer.feed(char))
    return "".join(visible)


def test_streamer_emits_only_block_text_for_answered_status() -> None:
    streamer = StructuredAnswerStreamer()
    visible = _stream(
        streamer,
        {
            "status": "answered",
            "account": {"account_id": "acc_1", "account_name": "Acc"},
            "clarification": {"message": "ignored", "candidates": []},
            "blocks": [
                {"type": "paragraph", "text": "First paragraph.", "citations": ["Email msg_1"]},
                {"type": "paragraph", "text": "Second paragraph.", "citations": []},
            ],
        },
    )

    assert visible == "First paragraph.\n\nSecond paragraph."
    # No JSON syntax leaks through.
    assert "{" not in visible and "}" not in visible
    assert '"text"' not in visible and '"status"' not in visible
    assert "msg_1" not in visible  # citation labels are not part of the stream
    assert streamer.status == "answered"


def test_streamer_emits_clarification_message_when_clarifying() -> None:
    streamer = StructuredAnswerStreamer()
    visible = _stream(
        streamer,
        {
            "status": "needs_account_clarification",
            "account": {"account_id": None, "account_name": None},
            "clarification": {"message": "Which client do you mean?", "candidates": []},
            "blocks": [],
        },
    )

    assert visible == "Which client do you mean?"


def test_streamer_emits_block_text_for_insufficient_evidence() -> None:
    streamer = StructuredAnswerStreamer()
    visible = _stream(
        streamer,
        {
            "status": "insufficient_evidence",
            "account": {"account_id": None, "account_name": None},
            "clarification": {"message": "ignored", "candidates": []},
            "blocks": [
                {"type": "paragraph", "text": "I cannot find that.", "citations": []},
            ],
        },
    )

    assert visible == "I cannot find that."


def test_streamer_decodes_escape_sequences_and_unicode() -> None:
    streamer = StructuredAnswerStreamer()
    visible = _stream(
        streamer,
        {
            "status": "answered",
            "account": {"account_id": None, "account_name": None},
            "clarification": {"message": "", "candidates": []},
            "blocks": [
                {"type": "paragraph", "text": "Line 1\nLine 2 — \"quoted\".", "citations": []},
            ],
        },
    )

    assert visible == 'Line 1\nLine 2 — "quoted".'


def test_streamer_preserves_raw_input_for_post_validation() -> None:
    streamer = StructuredAnswerStreamer()
    payload = {
        "status": "answered",
        "account": {"account_id": "x", "account_name": "X"},
        "clarification": {"message": "", "candidates": []},
        "blocks": [{"type": "paragraph", "text": "Body.", "citations": ["Email m"]}],
    }
    raw = json.dumps(payload)
    for char in raw:
        streamer.feed(char)
    assert json.loads(streamer.raw) == payload
