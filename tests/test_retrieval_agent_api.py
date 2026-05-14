from __future__ import annotations

from datetime import datetime, timezone

from pcad.api.routes import _fake_note_artifact
from pcad.agent.conversation_service import _citations_from_pack
from pcad.llm.citations import normalize_citation_format, repair_missing_citations, validate_citations
from pcad.models import ProactiveAlert
from pcad.retrieval.alerts import _dedupe_alerts, _scope_session_alert_ids
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


def test_crm_citations_are_openable_virtual_artifacts() -> None:
    pack = {
        "account_id": "SYN_ACC_0001",
        "retrieved_documents": [
            {
                "citations": [
                    {
                        "source_object": "Opportunity",
                        "source_record_id": "SYN_OPP_0001",
                        "title": "Production-line workflow automation",
                    }
                ]
            }
        ],
    }

    citations = _citations_from_pack(pack, {"cited": {"Opportunity SYN_OPP_0001"}})

    assert citations == [
        {
            "label": "Opportunity SYN_OPP_0001",
            "source_label": "Opportunity SYN_OPP_0001",
            "source_object": "Opportunity",
            "source_record_id": "SYN_OPP_0001",
            "artifact_id": "crm:Opportunity:SYN_OPP_0001",
            "title": "Production-line workflow automation",
            "source_url": None,
            "source_date": None,
            "excerpt": None,
        }
    ]


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


def test_session_alert_ids_are_scoped_and_deduped() -> None:
    alert = ProactiveAlert(
        alert_id="alert:base",
        account_id="SYN_ACC_0001",
        alert_type="unresolved_objection",
        severity="warning",
        title="Unresolved objection detected",
        body_markdown="A blocker exists.",
        created_at=datetime.now(timezone.utc),
    )

    global_alert = _scope_session_alert_ids([alert], None)[0]
    session_alerts = _scope_session_alert_ids([alert, alert], "session-123")

    assert global_alert.alert_id == "alert:base"
    assert session_alerts[0].alert_id.startswith("alert:base:session:")
    assert session_alerts[0].alert_id != alert.alert_id
    assert len(_dedupe_alerts(session_alerts)) == 1


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

    assert artifact["artifact_id"] == "crm:FakeNote:note-1"
    assert artifact["artifact_type"] == "pdf"
    assert artifact["mime_type"] == "application/pdf"
    assert artifact["metadata"]["source_object"] == "FakeNote"
    assert "EU hosting is required." in artifact["extracted_text"]
