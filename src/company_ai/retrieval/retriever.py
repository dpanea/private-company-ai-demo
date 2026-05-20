from __future__ import annotations

import logging
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

from company_ai.config import Settings
from company_ai.db import connect_dict
from company_ai.llm.citations import citation_is_user_visible
from company_ai.llm.client import EmbeddingClient
from company_ai.retrieval.intent import IntentResult
from company_ai.util import vector_literal


logger = logging.getLogger(__name__)
ACCOUNT_FUZZY_MIN_SCORE = 0.42
ACCOUNT_AMBIGUITY_DELTA = 0.08
RRF_K = 60


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
    semantic_query: str
    keyword_query: str
    account_id: str | None
    account_name: str | None
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

        normalized_query = _normalize_for_match(query)
        with connect_dict(self.settings) as conn:
            rows = conn.execute(
                """
                WITH scored AS (
                    SELECT
                        account_id,
                        account_name,
                        CASE
                            WHEN %(query_norm)s <> '' AND %(query_norm)s LIKE '%%' || lower(account_name) || '%%' THEN 'name_in_query'
                            ELSE 'fuzzy_trigram'
                        END AS method,
                        CASE
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
                    "query_norm": normalized_query,
                    "search": query,
                    "threshold": ACCOUNT_FUZZY_MIN_SCORE,
                },
            ).fetchall()
        candidates = [
            AccountCandidate(row["account_id"], row["account_name"], float(row["score"]), row["method"])
            for row in rows
        ]
        try:
            selected = _select_account_candidate(candidates)
        except AccountResolutionError as exc:
            # If the query gave us no plausible matches, surface a few real accounts
            # so the user can pick one rather than getting a dead-end "I don't know".
            if not exc.candidates:
                exc.candidates = self._all_accounts(limit=5)
            raise
        return selected.account_id, selected.account_name

    def _all_accounts(self, *, limit: int = 5) -> list[AccountCandidate]:
        with connect_dict(self.settings) as conn:
            rows = conn.execute(
                "SELECT account_id, account_name FROM accounts ORDER BY account_name LIMIT %s",
                (limit,),
            ).fetchall()
        return [AccountCandidate(row["account_id"], row["account_name"], 0.0, "all_accounts") for row in rows]

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
            semantic_query=query,
            keyword_query=query,
            account_id=account_id,
            account_name=account_name,
            session_id=session_id,
        )

    def fetch_base_context(self, plan: RetrievalPlan) -> list[dict[str, Any]]:
        if not plan.account_id:
            return []
        with connect_dict(self.settings) as conn:
            return conn.execute(
                """
                SELECT doc_id, doc_type, title, content_markdown, metadata_json,
                       account_id, owner_id, generated_at,
                       0.0::float AS score, ARRAY['base_context']::text[] AS reasons
                FROM rag_documents
                WHERE account_id = %s
                  AND (session_id IS NULL OR session_id = %s)
                  AND doc_type = 'source_artifact_chunk'
                ORDER BY last_source_updated_at DESC NULLS LAST,
                         generated_at DESC
                LIMIT 6
                """,
                (plan.account_id, plan.session_id),
            ).fetchall()

    def full_text_search(self, plan: RetrievalPlan) -> list[dict[str, Any]]:
        with connect_dict(self.settings) as conn:
            return conn.execute(
                """
                SELECT doc_id, doc_type, title, content_markdown, metadata_json,
                       account_id, owner_id, generated_at,
                       ts_rank_cd(search_vector, websearch_to_tsquery('english', %s))::float AS score,
                       ARRAY['full_text']::text[] AS reasons
                FROM rag_documents
                WHERE (%s::text IS NULL OR account_id = %s)
                  AND (session_id IS NULL OR session_id = %s)
                  AND doc_type = 'source_artifact_chunk'
                  AND search_vector @@ websearch_to_tsquery('english', %s)
                ORDER BY score DESC
                LIMIT %s
                """,
                (plan.keyword_query, plan.account_id, plan.account_id, plan.session_id, plan.keyword_query, plan.limit),
            ).fetchall()

    def vector_search(self, plan: RetrievalPlan) -> list[dict[str, Any]]:
        if not self.embedding_client:
            return []
        query_embedding = self.embedding_client.embed(_query_instruction(plan.semantic_query))
        query_vector = vector_literal(query_embedding)
        with connect_dict(self.settings) as conn:
            return conn.execute(
                """
                SELECT doc_id, doc_type, title, content_markdown, metadata_json,
                       account_id, owner_id, generated_at,
                       (1.0 - (embedding <=> %s::vector))::float AS score,
                       ARRAY['vector']::text[] AS reasons
                FROM rag_documents
                WHERE embedding IS NOT NULL
                  AND (%s::text IS NULL OR account_id = %s)
                  AND (session_id IS NULL OR session_id = %s)
                  AND doc_type = 'source_artifact_chunk'
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_vector, plan.account_id, plan.account_id, plan.session_id, query_vector, plan.limit),
            ).fetchall()

    def hybrid_search(self, plan: RetrievalPlan, base_context: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        base = base_context or []
        fts = self.full_text_search(plan)
        vec = self.vector_search(plan)
        merged = _rrf_merge(base, fts, vec)
        results = sorted(merged.values(), key=lambda r: float(r["rrf_score"]), reverse=True)[: plan.limit]
        for row in results:
            row["score"] = row["rrf_score"]
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
                    "citations": [citation for citation in citations_by_doc.get(row["doc_id"], []) if citation_is_user_visible(citation)][:5],
                }
                for row in rows
            ],
            "instructions": {"must_cite_sources": True, "do_not_invent": True, "answer_only_from_context": True},
        }


def _query_instruction(query: str) -> str:
    return "Instruction: retrieve company memory documents that answer this business question.\nQuery: " + query


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
