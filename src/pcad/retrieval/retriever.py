from __future__ import annotations

import logging
import unicodedata
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

from pcad.config import Settings
from pcad.db import connect_dict
from pcad.llm.client import EmbeddingClient
from pcad.retrieval.intent import IntentResult


logger = logging.getLogger(__name__)
ACCOUNT_FUZZY_MIN_SCORE = 0.42
ACCOUNT_AMBIGUITY_DELTA = 0.08
RRF_K = 60
DOC_TYPE_BOOSTS = {
    "account_memory": 0.30,
    "recent_activity_timeline": 0.20,
    "opportunity_snapshot": 0.15,
    "risk_summary": 0.15,
    "email_thread_summary": 0.12,
    "meeting_summary": 0.12,
    "contract_snapshot": 0.10,
    "stakeholder_map": 0.05,
}


@dataclass(frozen=True)
class AccountCandidate:
    account_id: str
    account_name: str
    score: float
    method: str


class AccountResolutionError(RuntimeError):
    def __init__(self, code: str, message: str, candidates: list[AccountCandidate] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.candidates = candidates or []

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "candidates": [asdict(c) for c in self.candidates]}


@dataclass(frozen=True)
class RetrievalPlan:
    intent: str
    intent_confidence: float
    intent_source: str
    semantic_query: str
    keyword_query: str
    account_id: str | None
    account_name: str | None
    account_hint: str | None
    doc_types: list[str]
    session_id: str | None = None
    limit: int = 8


class PostgresHybridRetriever:
    def __init__(self, settings: Settings, embedding_client: EmbeddingClient | None = None) -> None:
        self.settings = settings
        self.embedding_client = embedding_client

    def resolve_account(
        self,
        query: str,
        explicit_account_id: str | None = None,
        account_hint: str | None = None,
    ) -> tuple[str, str]:
        if explicit_account_id:
            with connect_dict(self.settings) as conn:
                row = conn.execute(
                    "SELECT account_id, account_name FROM accounts WHERE account_id = %s",
                    (explicit_account_id,),
                ).fetchone()
            if row:
                return row["account_id"], row["account_name"]
            raise AccountResolutionError("account_not_found", f"No account exists with id {explicit_account_id}.")

        search_text = account_hint or query
        normalized_query = _normalize_for_match(query)
        normalized_hint = _normalize_for_match(account_hint or "")
        # One CTE that computes score+method per row, then a single WHERE-by-method filter.
        # Trigram index on accounts.account_name covers the fuzzy path; the exact/substring
        # paths are linear but bounded by row count (3 demo accounts).
        with connect_dict(self.settings) as conn:
            rows = conn.execute(
                """
                WITH scored AS (
                    SELECT
                        account_id,
                        account_name,
                        CASE
                            WHEN %(hint)s <> '' AND lower(account_name) = lower(%(hint_raw)s) THEN 'intent_account_hint'
                            WHEN %(query_norm)s <> '' AND %(query_norm)s LIKE '%%' || lower(account_name) || '%%' THEN 'name_in_query'
                            ELSE 'fuzzy_trigram'
                        END AS method,
                        CASE
                            WHEN %(hint)s <> '' AND lower(account_name) = lower(%(hint_raw)s) THEN 1.0
                            WHEN %(query_norm)s <> '' AND %(query_norm)s LIKE '%%' || lower(account_name) || '%%' THEN 1.0
                            ELSE GREATEST(similarity(account_name, %(search)s), strict_word_similarity(account_name, %(search)s))
                        END::float AS score
                    FROM accounts
                )
                SELECT account_id, account_name, score, method
                FROM scored
                WHERE method <> 'fuzzy_trigram' OR score >= %(threshold)s
                ORDER BY score DESC, account_name
                LIMIT 5
                """,
                {
                    "hint": normalized_hint,
                    "hint_raw": account_hint or "",
                    "query_norm": normalized_query,
                    "search": search_text,
                    "threshold": ACCOUNT_FUZZY_MIN_SCORE,
                },
            ).fetchall()
        candidates = [
            AccountCandidate(row["account_id"], row["account_name"], float(row["score"]), row["method"])
            for row in rows
        ]
        selected = _select_account_candidate(candidates)
        return selected.account_id, selected.account_name

    def build_retrieval_plan(
        self,
        query: str,
        account_id: str | None,
        account_name: str | None,
        intent: IntentResult,
        *,
        session_id: str | None = None,
    ) -> RetrievalPlan:
        return RetrievalPlan(
            intent=intent.intent,
            intent_confidence=intent.confidence,
            intent_source=intent.source,
            semantic_query=query,
            keyword_query=query,
            account_id=account_id,
            account_name=account_name,
            account_hint=intent.account_hint,
            doc_types=intent.doc_types,
            session_id=session_id,
        )

    def fetch_base_context(self, plan: RetrievalPlan) -> list[dict[str, Any]]:
        if not plan.account_id:
            return []
        with connect_dict(self.settings) as conn:
            return conn.execute(
                """
                SELECT doc_id, doc_type, title, content_markdown, metadata_json,
                       account_id, opportunity_id, contract_id, owner_id, generated_at,
                       0.0::float AS score, ARRAY['base_context']::text[] AS reasons
                FROM rag_documents
                WHERE account_id = %s
                  AND (session_id IS NULL OR session_id = %s)
                  AND doc_type IN ('account_memory', 'recent_activity_timeline')
                ORDER BY CASE doc_type WHEN 'account_memory' THEN 1 WHEN 'recent_activity_timeline' THEN 2 ELSE 3 END
                LIMIT 3
                """,
                (plan.account_id, plan.session_id),
            ).fetchall()

    def full_text_search(self, plan: RetrievalPlan) -> list[dict[str, Any]]:
        with connect_dict(self.settings) as conn:
            return conn.execute(
                """
                SELECT doc_id, doc_type, title, content_markdown, metadata_json,
                       account_id, opportunity_id, contract_id, owner_id, generated_at,
                       ts_rank_cd(search_vector, websearch_to_tsquery('english', %s))::float AS score,
                       ARRAY['full_text']::text[] AS reasons
                FROM rag_documents
                WHERE (%s::text IS NULL OR account_id = %s)
                  AND (session_id IS NULL OR session_id = %s)
                  AND doc_type = ANY(%s)
                  AND search_vector @@ websearch_to_tsquery('english', %s)
                ORDER BY score DESC
                LIMIT %s
                """,
                (plan.keyword_query, plan.account_id, plan.account_id, plan.session_id, plan.doc_types, plan.keyword_query, plan.limit),
            ).fetchall()

    def vector_search(self, plan: RetrievalPlan) -> list[dict[str, Any]]:
        if not self.embedding_client:
            return []
        query_embedding = self.embedding_client.embed(_query_instruction(plan.semantic_query))
        vector_literal = _vector_literal(query_embedding)
        with connect_dict(self.settings) as conn:
            return conn.execute(
                """
                SELECT doc_id, doc_type, title, content_markdown, metadata_json,
                       account_id, opportunity_id, contract_id, owner_id, generated_at,
                       (1.0 - (embedding <=> %s::vector))::float AS score,
                       ARRAY['vector']::text[] AS reasons
                FROM rag_documents
                WHERE embedding IS NOT NULL
                  AND (%s::text IS NULL OR account_id = %s)
                  AND (session_id IS NULL OR session_id = %s)
                  AND doc_type = ANY(%s)
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (vector_literal, plan.account_id, plan.account_id, plan.session_id, plan.doc_types, vector_literal, plan.limit),
            ).fetchall()

    def hybrid_search(self, plan: RetrievalPlan, base_context: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        base = base_context or []
        fts = self.full_text_search(plan)
        vec = self.vector_search(plan)
        merged = _rrf_merge(base, fts, vec)
        results = _rank_hybrid_results(merged.values(), limit=plan.limit)
        logger.info("retrieval.hybrid raw=%s deduped=%s returned=%s", len(base) + len(fts) + len(vec), len(merged), len(results))
        return results

    def citations_for(self, doc_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        if not doc_ids:
            return {}
        with connect_dict(self.settings) as conn:
            rows = conn.execute(
                """
                SELECT * FROM source_citations
                WHERE doc_id = ANY(%s)
                ORDER BY doc_id, source_date DESC NULLS LAST, citation_id
                """,
                (doc_ids,),
            ).fetchall()
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            grouped.setdefault(row["doc_id"], []).append(dict(row))
        return grouped

    def build_context_pack(
        self,
        query: str,
        plan: RetrievalPlan,
        rows: list[dict[str, Any]],
        *,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        citations_by_doc = self.citations_for([row["doc_id"] for row in rows])
        return {
            "user_request": query,
            "retrieval_plan": asdict(plan),
            "account_id": plan.account_id,
            "account_name": plan.account_name,
            "conversation_history": conversation_history or [],
            "retrieved_documents": [
                {
                    "doc_id": row["doc_id"],
                    "doc_type": row["doc_type"],
                    "title": row["title"],
                    "content_markdown": row["content_markdown"],
                    "metadata": row["metadata_json"],
                    "score": row["score"],
                    "reasons": row["reasons"],
                    "citations": citations_by_doc.get(row["doc_id"], [])[:5],
                }
                for row in rows
            ],
            "instructions": {"must_cite_sources": True, "do_not_invent": True, "answer_only_from_context": True},
        }


def _query_instruction(query: str) -> str:
    return "Instruction: retrieve company memory documents that answer this business question.\nQuery: " + query


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def _rrf_merge(*rankers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for ranker_rows in rankers:
        for rank_index, row in enumerate(ranker_rows, start=1):
            doc_id = row["doc_id"]
            contribution = 1.0 / (RRF_K + rank_index)
            if doc_id not in merged:
                entry = dict(row)
                entry["rrf_score"] = 0.0
                entry["reasons"] = list(row.get("reasons") or [])
                merged[doc_id] = entry
            entry = merged[doc_id]
            entry["rrf_score"] += contribution
            for reason in row.get("reasons") or []:
                if reason not in entry["reasons"]:
                    entry["reasons"].append(reason)
    return merged


def _rank_hybrid_results(rows: Iterable[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    ranked = []
    for row in rows:
        row["score"] = row["rrf_score"] + DOC_TYPE_BOOSTS.get(row["doc_type"], 0.0)
        ranked.append(row)
    return sorted(ranked, key=lambda r: (float(r["score"]), float(r["rrf_score"])), reverse=True)[:limit]


def _select_account_candidate(candidates: list[AccountCandidate]) -> AccountCandidate:
    if not candidates:
        raise AccountResolutionError("account_unresolved", "I couldn't determine which account you mean from the question.")
    ranked = sorted(candidates, key=lambda c: c.score, reverse=True)
    plausible = [c for c in ranked if c.score >= ACCOUNT_FUZZY_MIN_SCORE or c.score == 1.0]
    if not plausible:
        raise AccountResolutionError("account_unresolved", "I couldn't determine which account you mean from the question.", ranked[:3])
    if len(plausible) > 1 and plausible[0].score - plausible[1].score <= ACCOUNT_AMBIGUITY_DELTA:
        raise AccountResolutionError("account_ambiguous", "The question matches several possible accounts.", plausible[:5])
    return plausible[0]


def _normalize_for_match(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in normalized if not unicodedata.combining(c))
    return " ".join(without_accents.casefold().split())
