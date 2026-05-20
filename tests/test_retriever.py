"""Integration tests for PostgresHybridRetriever.

`resolve_account` and `hybrid_search` are exercised against a real Postgres so
the SQL — including the pg_trgm thresholds, the CTE branches, the FTS / vector
ranking, and the RRF merge — is what's actually validated. No mocking of the
DB; the LLM substitute is only there to feed `vector_search` a deterministic
query embedding.
"""
from __future__ import annotations

import pytest

from company_ai.llm.deterministic import DeterministicLlm
from company_ai.retrieval.intent import IntentResult
from company_ai.retrieval.retriever import (
    AccountResolutionError,
    PostgresHybridRetriever,
    _query_instruction,
)

from tests._seed import make_settings, seed_account, seed_rag_document, seed_user


def _intent(query: str) -> IntentResult:
    return IntentResult("account_question")


def test_resolve_account_explicit_id_returns_account(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_X", account_name="Some Account")
    retriever = PostgresHybridRetriever(settings)

    account_id, name = retriever.resolve_account(
        "completely unrelated query", explicit_account_id="ACC_X"
    )
    assert account_id == "ACC_X"
    assert name == "Some Account"


def test_resolve_account_explicit_id_not_found_raises(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    retriever = PostgresHybridRetriever(settings)

    with pytest.raises(AccountResolutionError) as exc_info:
        retriever.resolve_account("query", explicit_account_id="DOES_NOT_EXIST")
    assert exc_info.value.code == "account_not_found"


def test_resolve_account_exact_lowercase_match_wins_over_fuzzy_siblings(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_GMBH", account_name="Brannfeld Industrial GmbH")
    seed_account(settings, account_id="ACC_AG", account_name="Brannfeld Industrial AG")
    retriever = PostgresHybridRetriever(settings)

    account_id, name = retriever.resolve_account("brannfeld industrial gmbh")
    assert account_id == "ACC_GMBH"
    assert name == "Brannfeld Industrial GmbH"


def test_resolve_account_ambiguous_when_one_name_is_a_prefix_of_another(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_GMBH", account_name="Brannfeld Industrial GmbH")
    seed_account(settings, account_id="ACC_BARE", account_name="Brannfeld Industrial")
    retriever = PostgresHybridRetriever(settings)

    with pytest.raises(AccountResolutionError) as exc_info:
        retriever.resolve_account("brannfeld industrial gmbh")
    assert exc_info.value.code == "account_ambiguous"


def test_resolve_account_substring_in_query_wins(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_ALPHA", account_name="Alpha Robotics")
    seed_account(settings, account_id="ACC_BETA", account_name="Beta Logistics")
    retriever = PostgresHybridRetriever(settings)

    account_id, _ = retriever.resolve_account("Tell me about alpha robotics open risks")
    assert account_id == "ACC_ALPHA"


def test_resolve_account_below_threshold_raises_unresolved(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_BRANN", account_name="Brannfeld Industrial")
    retriever = PostgresHybridRetriever(settings)

    with pytest.raises(AccountResolutionError) as exc_info:
        retriever.resolve_account("completely unrelated noise question xyz")
    assert exc_info.value.code == "account_unresolved"


def test_resolve_account_ambiguous_when_two_fuzzy_matches_tie(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_NORTH_A", account_name="Northstar Alpha")
    seed_account(settings, account_id="ACC_NORTH_B", account_name="Northstar Beta")
    retriever = PostgresHybridRetriever(settings)

    with pytest.raises(AccountResolutionError) as exc_info:
        retriever.resolve_account("northstar")
    assert exc_info.value.code == "account_ambiguous"
    assert {c.account_id for c in exc_info.value.candidates} >= {"ACC_NORTH_A", "ACC_NORTH_B"}


def test_hybrid_search_combines_full_text_vector_and_base_context(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_HYBRID", account_name="Hybrid Test Account")

    query = "security review approved for the pilot"
    llm = DeterministicLlm()
    target_embedding = llm.embed(_query_instruction(query))
    other_embedding = [1.0 - value for value in target_embedding]

    seed_rag_document(
        settings,
        doc_id="source_artifact_chunk:email:ACC_HYBRID:msg_1:message",
        account_id="ACC_HYBRID",
        doc_type="source_artifact_chunk",
        title="Security review email",
        content="Security review approved for the pilot rollout.",
        embedding=target_embedding,
        citations=[{"source_object": "Email", "source_record_id": "msg_1"}],
    )
    seed_rag_document(
        settings,
        doc_id="source_artifact_chunk:email:ACC_HYBRID:msg_2:message",
        account_id="ACC_HYBRID",
        doc_type="source_artifact_chunk",
        title="Unrelated note",
        content="No notable risks were recorded for this account.",
        embedding=other_embedding,
        citations=[{"source_object": "Email", "source_record_id": "msg_2"}],
    )

    retriever = PostgresHybridRetriever(settings, embedding_client=llm)
    plan = retriever.build_retrieval_plan(query, "ACC_HYBRID", "Hybrid Test Account", _intent(query))

    base = retriever.fetch_base_context(plan)
    fts = retriever.full_text_search(plan)
    vec = retriever.vector_search(plan)
    merged = retriever.hybrid_search(plan, base)

    target_id = "source_artifact_chunk:email:ACC_HYBRID:msg_1:message"
    assert any(row["doc_id"] == target_id for row in base)
    assert any(row["doc_id"] == target_id for row in fts)
    assert vec[0]["doc_id"] == target_id

    assert merged[0]["doc_id"] == target_id
    assert {"base_context", "full_text", "vector"} <= set(merged[0]["reasons"])


def test_hybrid_search_scopes_to_account_and_session(migrated_db: str) -> None:
    """A doc belonging to another account, or to a different session, must not surface."""
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_OURS", account_name="Ours")
    seed_account(settings, account_id="ACC_THEIRS", account_name="Theirs")

    seed_rag_document(
        settings,
        doc_id="source_artifact_chunk:email:ACC_OURS:msg_1:message",
        account_id="ACC_OURS",
        doc_type="source_artifact_chunk",
        title="Ours email",
        content="Security review approved for the pilot.",
        citations=[{"source_object": "Email", "source_record_id": "ours_msg_1"}],
    )
    seed_rag_document(
        settings,
        doc_id="source_artifact_chunk:email:ACC_THEIRS:msg_1:message",
        account_id="ACC_THEIRS",
        doc_type="source_artifact_chunk",
        title="Theirs email",
        content="Security review approved for the pilot.",
        citations=[{"source_object": "Email", "source_record_id": "theirs_msg_1"}],
    )
    seed_rag_document(
        settings,
        doc_id="demo_note:ours:other_session",
        account_id="ACC_OURS",
        doc_type="source_artifact_chunk",
        title="Visitor note from another session",
        content="Security review approved for the pilot.",
        session_id="some_other_session",
        citations=[{"source_object": "DemoNote", "source_record_id": "other_note"}],
    )

    retriever = PostgresHybridRetriever(settings)
    plan = retriever.build_retrieval_plan(
        "security review", "ACC_OURS", "Ours", _intent("security review"), session_id="my_session"
    )
    base = retriever.fetch_base_context(plan)
    fts = retriever.full_text_search(plan)

    ids = {row["doc_id"] for row in base} | {row["doc_id"] for row in fts}
    assert "source_artifact_chunk:email:ACC_OURS:msg_1:message" in ids
    assert "source_artifact_chunk:email:ACC_THEIRS:msg_1:message" not in ids
    assert "demo_note:ours:other_session" not in ids


@pytest.mark.parametrize(
    ("query", "doc_id", "title", "content", "citation"),
    [
        (
            "What does the mutual NDA say for Rynvoss?",
            "source_artifact_chunk:pdf:ACC_RYNVOSS:mutual_nda:page_1",
            "Mutual NDA (page 1)",
            "The mutual NDA covers confidential information exchanged during the Rynvoss evaluation.",
            {"source_object": "PDF", "source_record_id": "mutual_nda", "title": "Mutual NDA"},
        ),
        (
            "What is in the proposal for production-line workflow automation?",
            "source_artifact_chunk:pdf:ACC_RYNVOSS:proposal:page_1",
            "Proposal (page 1)",
            "The proposal describes production-line workflow automation scope, pricing, and pilot timeline.",
            {"source_object": "PDF", "source_record_id": "proposal", "title": "Proposal"},
        ),
        (
            "What next step is listed in the Word account plan?",
            "source_artifact_chunk:docx:ACC_RYNVOSS:account_plan:next_steps",
            "Account plan (Next steps)",
            "The Word account plan says the next step is to send the audit posture note.",
            {"source_object": "WordDocument", "source_record_id": "account_plan", "title": "Account plan"},
        ),
    ],
)
def test_source_artifact_questions_retrieve_pdf_and_word_chunks(
    migrated_db: str,
    query: str,
    doc_id: str,
    title: str,
    content: str,
    citation: dict[str, str],
) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_RYNVOSS", account_name="Rynvoss Logistics BV")
    seed_rag_document(
        settings,
        doc_id=doc_id,
        account_id="ACC_RYNVOSS",
        doc_type="source_artifact_chunk",
        title=title,
        content=content,
        citations=[citation],
    )
    retriever = PostgresHybridRetriever(settings)
    plan = retriever.build_retrieval_plan(query, "ACC_RYNVOSS", "Rynvoss Logistics BV", _intent(query))

    rows = retriever.hybrid_search(plan)
    pack = retriever.build_context_pack(query, plan, rows)

    assert rows[0]["doc_id"] == doc_id
    assert pack["retrieved_documents"][0]["citations"][0]["source_object"] == citation["source_object"]
