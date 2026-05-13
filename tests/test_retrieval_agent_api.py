from __future__ import annotations

from pcad.llm.citations import normalize_citation_format, repair_missing_citations, validate_citations
from pcad.retrieval.intent import IntentResolver
from pcad.retrieval.retriever import _rank_hybrid_results, _rrf_merge


def test_intent_resolver_new_workflow_intents() -> None:
    resolver = IntentResolver()

    assert resolver.resolve("Brief me before a call with Northstar").intent == "briefing"
    assert resolver.resolve("What changed in the last 14 days?").intent == "what_changed"
    assert resolver.resolve("What open risks or blockers remain?").intent == "open_risks"
    assert resolver.resolve("What is the next action this week?").intent == "next_action"


def test_source_citation_validation_and_repair() -> None:
    pack = {
        "retrieved_documents": [
            {
                "citations": [
                    {"source_object": "Account", "source_record_id": "SYN_ACC_0001"},
                    {"source_object": "Email", "source_record_id": "msg-1"},
                ]
            }
        ]
    }

    normalized = normalize_citation_format("Context says Source: Account SYN_ACC_0001", pack)
    assert normalized == "Context says [Source: Account SYN_ACC_0001]"
    assert validate_citations(normalized, pack)["valid"]

    repaired = repair_missing_citations("The account is engaged. Account SYN_ACC_0001", pack)
    assert "[Source: Account SYN_ACC_0001]" in repaired
    assert validate_citations(repaired, pack)["valid"]


def test_rrf_merge_uses_rank_and_additive_doc_type_boosts() -> None:
    base = [{"doc_id": "a", "doc_type": "account_memory", "reasons": ["base_context"]}]
    full_text = [
        {"doc_id": "b", "doc_type": "risk_summary", "reasons": ["full_text"]},
        {"doc_id": "a", "doc_type": "account_memory", "reasons": ["full_text"]},
    ]
    vector = [{"doc_id": "b", "doc_type": "risk_summary", "reasons": ["vector"]}]

    merged = _rrf_merge(base, full_text, vector)
    ranked = _rank_hybrid_results(merged.values(), limit=2)

    assert ranked[0]["doc_id"] == "a"
    assert "base_context" in ranked[0]["reasons"]
    assert ranked[1]["doc_id"] == "b"
    assert set(ranked[1]["reasons"]) == {"full_text", "vector"}
