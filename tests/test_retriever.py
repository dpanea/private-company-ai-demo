"""Integration tests for PostgresHybridRetriever.

`resolve_account` and `hybrid_search` are exercised against a real Postgres so
the SQL — including the pg_trgm thresholds, the CTE branches, the FTS / vector
ranking, and the RRF merge — is what's actually validated. No mocking of the
DB; the LLM substitute is only there to feed `vector_search` a deterministic
query embedding.
"""
from __future__ import annotations

import pytest

from pcad.llm.deterministic import DeterministicLlm
from pcad.retrieval.intent import IntentResult
from pcad.retrieval.retriever import (
    AccountResolutionError,
    PostgresHybridRetriever,
    _query_instruction,
)

from tests._seed import make_settings, seed_account, seed_rag_document, seed_user


# ---------------------------------------------------------------------------
# resolve_account
# ---------------------------------------------------------------------------


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


def test_resolve_account_exact_lowercase_match_wins_over_fuzzy_siblings(
    migrated_db: str,
) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_GMBH", account_name="Brannfeld Industrial GmbH")
    seed_account(settings, account_id="ACC_AG", account_name="Brannfeld Industrial AG")
    retriever = PostgresHybridRetriever(settings)

    # The case-insensitive substring-of-query rule pins to ACC_GMBH; ACC_AG only
    # matches via fuzzy trigram, which scores below 1.0 and loses by more than
    # ACCOUNT_AMBIGUITY_DELTA, so the resolver picks ACC_GMBH unambiguously.
    account_id, name = retriever.resolve_account("brannfeld industrial gmbh")
    assert account_id == "ACC_GMBH"
    assert name == "Brannfeld Industrial GmbH"


def test_resolve_account_ambiguous_when_one_name_is_a_prefix_of_another(
    migrated_db: str,
) -> None:
    """If two account names both substring-match the query, the resolver
    refuses rather than guessing."""
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_GMBH", account_name="Brannfeld Industrial GmbH")
    seed_account(settings, account_id="ACC_BARE", account_name="Brannfeld Industrial")
    retriever = PostgresHybridRetriever(settings)

    with pytest.raises(AccountResolutionError) as exc_info:
        retriever.resolve_account("brannfeld industrial gmbh")
    assert exc_info.value.code == "account_ambiguous"


def test_resolve_account_uses_account_hint_for_exact_match(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_RYNVOSS", account_name="Rynvoss Logistics BV")
    seed_account(settings, account_id="ACC_BRANN", account_name="Brannfeld Industrial")
    retriever = PostgresHybridRetriever(settings)

    # Query references neither account by name; the hint disambiguates.
    account_id, _ = retriever.resolve_account(
        "what changed lately?", account_hint="Rynvoss Logistics BV"
    )
    assert account_id == "ACC_RYNVOSS"


def test_resolve_account_substring_in_query_wins(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_ALPHA", account_name="Alpha Robotics")
    seed_account(settings, account_id="ACC_BETA", account_name="Beta Logistics")
    retriever = PostgresHybridRetriever(settings)

    account_id, _ = retriever.resolve_account(
        "Tell me about alpha robotics open risks"
    )
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
    # Two accounts whose names are equally close to "northstar" so the
    # ACCOUNT_AMBIGUITY_DELTA tie-break fires.
    seed_account(settings, account_id="ACC_NORTH_A", account_name="Northstar Alpha")
    seed_account(settings, account_id="ACC_NORTH_B", account_name="Northstar Beta")
    retriever = PostgresHybridRetriever(settings)

    with pytest.raises(AccountResolutionError) as exc_info:
        retriever.resolve_account("northstar")
    assert exc_info.value.code == "account_ambiguous"
    assert {c.account_id for c in exc_info.value.candidates} >= {
        "ACC_NORTH_A",
        "ACC_NORTH_B",
    }


# ---------------------------------------------------------------------------
# hybrid_search and RRF
# ---------------------------------------------------------------------------


def test_hybrid_search_combines_full_text_vector_and_base_context(migrated_db: str) -> None:
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_HYBRID", account_name="Hybrid Test Account")

    query = "security review approved for the pilot"
    llm = DeterministicLlm()
    target_embedding = llm.embed(_query_instruction(query))
    other_embedding = [1.0 - value for value in target_embedding]

    # account_memory: matches base_context AND has the FTS terms.
    seed_rag_document(
        settings,
        doc_id="account_memory:ACC_HYBRID",
        account_id="ACC_HYBRID",
        doc_type="account_memory",
        title="Account memory: Hybrid Test Account",
        content="Security review approved for the pilot rollout.",
        embedding=target_embedding,
        citations=[
            {"source_object": "Account", "source_record_id": "ACC_HYBRID"}
        ],
    )
    # risk_summary: doesn't match FTS, deliberately distant embedding.
    seed_rag_document(
        settings,
        doc_id="risk_summary:ACC_HYBRID",
        account_id="ACC_HYBRID",
        doc_type="risk_summary",
        title="Risk summary: Hybrid Test Account",
        content="No notable risks were recorded for this account.",
        embedding=other_embedding,
        citations=[
            {"source_object": "Account", "source_record_id": "ACC_HYBRID"}
        ],
    )

    retriever = PostgresHybridRetriever(settings, embedding_client=llm)
    intent = IntentResult(
        raw_query=query,
        intent="account_question",
        confidence=1.0,
        source="test",
        doc_types=["account_memory", "risk_summary"],
    )
    plan = retriever.build_retrieval_plan(query, "ACC_HYBRID", "Hybrid Test Account", intent)

    base = retriever.fetch_base_context(plan)
    fts = retriever.full_text_search(plan)
    vec = retriever.vector_search(plan)
    merged = retriever.hybrid_search(plan, base)

    # All three rankers found *something* and the merged result is non-empty.
    assert any(row["doc_id"] == "account_memory:ACC_HYBRID" for row in base)
    assert any(row["doc_id"] == "account_memory:ACC_HYBRID" for row in fts)
    assert vec[0]["doc_id"] == "account_memory:ACC_HYBRID"

    # account_memory wins on combined signal + doc-type boost.
    assert merged[0]["doc_id"] == "account_memory:ACC_HYBRID"
    # And the reasons are the union of every ranker that found it.
    assert {"base_context", "full_text", "vector"} <= set(merged[0]["reasons"])


def test_hybrid_search_scopes_to_account_and_session(migrated_db: str) -> None:
    """A doc belonging to another account, or to a different session, must not surface."""
    settings = make_settings(migrated_db)
    seed_user(settings)
    seed_account(settings, account_id="ACC_OURS", account_name="Ours")
    seed_account(settings, account_id="ACC_THEIRS", account_name="Theirs")

    seed_rag_document(
        settings,
        doc_id="account_memory:ACC_OURS",
        account_id="ACC_OURS",
        doc_type="account_memory",
        title="Account memory: Ours",
        content="Security review approved for the pilot.",
        citations=[{"source_object": "Account", "source_record_id": "ACC_OURS"}],
    )
    # Wrong account
    seed_rag_document(
        settings,
        doc_id="account_memory:ACC_THEIRS",
        account_id="ACC_THEIRS",
        doc_type="account_memory",
        title="Account memory: Theirs",
        content="Security review approved for the pilot.",
        citations=[{"source_object": "Account", "source_record_id": "ACC_THEIRS"}],
    )
    # Right account, wrong session
    seed_rag_document(
        settings,
        doc_id="fake_note:ours:other_session",
        account_id="ACC_OURS",
        doc_type="account_memory",
        title="Visitor note from another session",
        content="Security review approved for the pilot.",
        session_id="some_other_session",
        citations=[{"source_object": "Account", "source_record_id": "ACC_OURS"}],
    )

    retriever = PostgresHybridRetriever(settings)
    intent = IntentResult(
        raw_query="security review",
        intent="account_question",
        confidence=1.0,
        source="test",
        doc_types=["account_memory"],
    )
    plan = retriever.build_retrieval_plan(
        "security review", "ACC_OURS", "Ours", intent, session_id="my_session"
    )
    base = retriever.fetch_base_context(plan)
    fts = retriever.full_text_search(plan)

    ids_in_base = {row["doc_id"] for row in base}
    ids_in_fts = {row["doc_id"] for row in fts}
    assert "account_memory:ACC_OURS" in (ids_in_base | ids_in_fts)
    assert "account_memory:ACC_THEIRS" not in (ids_in_base | ids_in_fts)
    assert "fake_note:ours:other_session" not in (ids_in_base | ids_in_fts)
