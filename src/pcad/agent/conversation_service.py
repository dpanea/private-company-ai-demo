from __future__ import annotations

import json
import logging
import textwrap
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb

from pcad.api.rate_limit import BUDGET_MESSAGE, check_daily_budget, record_token_usage, session_message_limiter
from pcad.config import Settings
from pcad.db import connect_dict
from pcad.llm.citations import citation_label, normalize_citation_format, repair_missing_citations, validate_citations
from pcad.llm.client import LlmClient, OpenAICompatibleClient
from pcad.llm.prompts import DEFAULT_CONTEXT_TOKEN_BUDGET, DEFAULT_GENERATION_MAX_ATTEMPTS, RESPONSE_MAX_TOKENS, build_answer_messages, render_context_prompt
from pcad.models import ConversationMessage, ConversationThread
from pcad.retrieval.alerts import ProactiveAlertGenerator
from pcad.retrieval.intent import IntentResolver, IntentResult
from pcad.retrieval.retriever import AccountResolutionError, PostgresHybridRetriever
from pcad.util import safe_id


logger = logging.getLogger(__name__)

WORKFLOW_SEEDS = {
    "call_briefing": "Brief me before a call with {account_name}. Cover recent activity, open opportunities, stakeholders, and any open risks.",
    "what_changed": "What changed for {account_name} in the last 14 days that I should know about before reaching out?",
    "open_risks": "What are the open risks, objections, or unresolved questions for {account_name}?",
    "follow_up_draft": "Draft a short follow-up email to the primary contact at {account_name}. Reference the most recent meaningful interaction.",
    "next_action": "What is the most important next action I should take on {account_name} this week?",
}


@dataclass
class PreparedPipeline:
    intent: IntentResult
    account_id: str
    account_name: str
    pack: dict[str, Any]
    new_doc_ids: list[str]


@dataclass
class ClarificationResult:
    answer: str
    error: AccountResolutionError


class ConversationService:
    def __init__(
        self,
        settings: Settings,
        *,
        retriever: PostgresHybridRetriever | None = None,
        llm_client: LlmClient | None = None,
        alerts: ProactiveAlertGenerator | None = None,
    ) -> None:
        self.settings = settings
        self.llm_client = llm_client or OpenAICompatibleClient(settings)
        self.retriever = retriever or PostgresHybridRetriever(settings, embedding_client=self.llm_client)
        self.intent_resolver = IntentResolver(self.llm_client)
        self.alerts = alerts or ProactiveAlertGenerator(settings)

    def list_threads(self, session_id: str) -> list[ConversationThread]:
        with connect_dict(self.settings) as conn:
            rows = conn.execute(
                "SELECT * FROM conversation_threads WHERE session_id = %s ORDER BY updated_at DESC",
                (session_id,),
            ).fetchall()
        return [ConversationThread.model_validate(dict(row)) for row in rows]

    def create_thread(self, session_id: str, *, account_id: str | None, workflow_seed: str | None) -> ConversationThread:
        account_name = self._account_name(account_id) if account_id else None
        thread_id = str(uuid4())
        title = "New conversation"
        with connect_dict(self.settings) as conn:
            row = conn.execute(
                """
                INSERT INTO conversation_threads (thread_id, session_id, account_id, account_name, title, workflow_seed)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (thread_id, session_id, account_id, account_name, title, workflow_seed),
            ).fetchone()
            if workflow_seed:
                title = _title_from_message(_workflow_seed_to_prompt(workflow_seed, account_name or "this account"))
                row = conn.execute(
                    "UPDATE conversation_threads SET title = %s, updated_at = now() WHERE thread_id = %s RETURNING *",
                    (title, thread_id),
                ).fetchone()
            conn.commit()
        return ConversationThread.model_validate(dict(row))

    def get_thread(self, session_id: str, thread_id: str) -> ConversationThread:
        with connect_dict(self.settings) as conn:
            row = conn.execute(
                "SELECT * FROM conversation_threads WHERE session_id = %s AND thread_id = %s",
                (session_id, thread_id),
            ).fetchone()
        if not row:
            raise PermissionError("Thread not found")
        return ConversationThread.model_validate(dict(row))

    def get_messages(self, session_id: str, thread_id: str) -> list[ConversationMessage]:
        self.get_thread(session_id, thread_id)
        with connect_dict(self.settings) as conn:
            rows = conn.execute(
                """
                SELECT message_id, thread_id, role, content, account_id, account_name, citations, metadata_json AS metadata, created_at
                FROM conversation_messages
                WHERE thread_id = %s
                ORDER BY created_at, message_id
                """,
                (thread_id,),
            ).fetchall()
        return [ConversationMessage.model_validate(dict(row)) for row in rows]

    def send_message_stream(self, session_id: str, thread_id: str, user_text: str) -> Generator[str, None, None]:
        clean = " ".join(user_text.split())
        if not clean:
            yield _sse("error", {"detail": "Empty message"})
            return
        if not session_message_limiter.allow(
            f"session:{session_id}",
            limit=self.settings.rate_limit_per_session_per_hour,
            window_seconds=3600,
        ):
            yield _sse("error", {"detail": "Message rate limit exceeded"})
            return

        thread = self.get_thread(session_id, thread_id)
        prev_account_id = thread.account_id
        prev_account_name = thread.account_name
        # When the first message on a workflow-seeded thread arrives, expand the visible
        # label (e.g. "Brief me before a call") into the full retrieval prompt. We detect
        # "first message" by counting existing user messages before inserting this one.
        pipeline_clean = clean
        if thread.workflow_seed in WORKFLOW_SEEDS and self._user_message_count(thread_id) == 0:
            pipeline_clean = _workflow_seed_to_prompt(thread.workflow_seed, prev_account_name or "this account")
        user_message = self._insert_message(thread_id, "user", clean, account_id=prev_account_id, account_name=prev_account_name)
        yield _sse("user_message", _model_dump(user_message))

        # Cheapest possible budget short-circuit: refuse before the pipeline (which itself
        # can call the LLM for intent classification). This is the only path that avoids
        # spending tokens once we are over budget for the day.
        if not check_daily_budget(self.settings):
            assistant = self._insert_message(
                thread_id,
                "assistant",
                BUDGET_MESSAGE,
                account_id=prev_account_id,
                account_name=prev_account_name,
                metadata={"response_type": "budget_exceeded"},
            )
            self._update_thread_after_message(thread_id, clean, prev_account_id, prev_account_name)
            yield _sse("token", {"content": BUDGET_MESSAGE})
            yield _sse("done", {"assistant_message": _model_dump(assistant), "thread": _model_dump(self.get_thread(session_id, thread_id))})
            return

        yield _sse("status", {"status": "thinking"})

        last_assistant = self._last_assistant_message(thread_id)
        pending_meta = last_assistant.metadata if last_assistant else {}
        if pending_meta.get("response_type") == "account_clarification":
            original_request = pending_meta.get("original_request") or clean
            explicit_id = _candidate_id_from_text(clean, pending_meta.get("account_candidates", []))
            pipeline_request = original_request
            pipeline_explicit_id = explicit_id
            pipeline_prev_account_id = None
            pipeline_prev_account_name = None
        else:
            pipeline_request = pipeline_clean
            pipeline_explicit_id = None
            pipeline_prev_account_id = prev_account_id
            pipeline_prev_account_name = prev_account_name

        prepared = self._prepare_pipeline(
            session_id,
            pipeline_request,
            explicit_account_id=pipeline_explicit_id,
            previous_account_id=pipeline_prev_account_id,
            previous_account_name=pipeline_prev_account_name,
            history=self._recent_history(thread_id),
        )
        if isinstance(prepared, ClarificationResult):
            yield from self._finalize_clarification(thread_id, clean, prepared, original_request=pipeline_request)
            return

        yield _sse("status", {"status": "generating"})
        early_citations = _citations_from_pack(prepared.pack, {})
        if early_citations:
            yield _sse("citations", {"citations": early_citations})
        budget = self.settings.context_token_budget or DEFAULT_CONTEXT_TOKEN_BUDGET
        context_prompt = render_context_prompt(prepared.pack, token_budget=budget)
        messages = build_answer_messages(context_prompt, attempt=1, previous_answer="", previous_validation={})
        accumulated: list[str] = []
        stream_fn = getattr(self.llm_client, "complete_stream", None)
        if callable(stream_fn):
            try:
                for token in stream_fn(messages, max_tokens=RESPONSE_MAX_TOKENS):
                    accumulated.append(token)
                    yield _sse("token", {"content": token})
            except RuntimeError as exc:
                logger.error("conversation.stream.llm_failed error=%s", exc)
                yield _sse("error", {"detail": "The model failed while generating the answer."})
                return
            raw_answer = "".join(accumulated)
        else:
            raw_answer = self.llm_client.complete(messages, max_tokens=RESPONSE_MAX_TOKENS)
            yield _sse("token", {"content": raw_answer})

        answer, validation = self._finalize_answer_text(prepared, raw_answer, context_prompt)
        if answer != raw_answer:
            yield _sse("replace", {"content": answer})
        usage = getattr(self.llm_client, "last_usage", None)
        if usage and (usage.prompt_tokens or usage.completion_tokens):
            record_token_usage(self.settings, tokens_in=usage.prompt_tokens, tokens_out=usage.completion_tokens)
        yield from self._finalize_answer(thread_id, clean, prepared, answer, validation, session_id)

    def _prepare_pipeline(
        self,
        session_id: str,
        user_request: str,
        *,
        explicit_account_id: str | None = None,
        previous_account_id: str | None = None,
        previous_account_name: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> PreparedPipeline | ClarificationResult:
        intent = self.intent_resolver.resolve(user_request)
        if previous_account_id and not intent.account_hint and not explicit_account_id:
            account_id, account_name = previous_account_id, previous_account_name or ""
        else:
            try:
                account_id, account_name = self.retriever.resolve_account(
                    user_request,
                    explicit_account_id=explicit_account_id,
                    account_hint=intent.account_hint,
                )
            except AccountResolutionError as exc:
                return ClarificationResult(answer=_account_resolution_error_answer(exc), error=exc)

        plan = self.retriever.build_retrieval_plan(user_request, account_id, account_name, intent, session_id=session_id)
        base_context = self.retriever.fetch_base_context(plan)
        fresh = self.retriever.hybrid_search(plan, base_context)
        pack = self.retriever.build_context_pack(user_request, plan, fresh, conversation_history=history or [])
        return PreparedPipeline(intent=intent, account_id=account_id, account_name=account_name, pack=pack, new_doc_ids=[item["doc_id"] for item in pack["retrieved_documents"]])

    def _finalize_answer_text(
        self,
        prepared: PreparedPipeline,
        raw_answer: str,
        context_prompt: str,
    ) -> tuple[str, dict[str, Any]]:
        answer = normalize_citation_format(raw_answer, prepared.pack)
        validation = validate_citations(answer, prepared.pack)
        attempts = max(1, self.settings.agent_generation_max_attempts or DEFAULT_GENERATION_MAX_ATTEMPTS)
        for attempt in range(2, attempts + 1):
            if validation["valid"]:
                break
            messages = build_answer_messages(context_prompt, attempt=attempt, previous_answer=answer, previous_validation=validation)
            answer = normalize_citation_format(self.llm_client.complete(messages, max_tokens=RESPONSE_MAX_TOKENS), prepared.pack)
            validation = validate_citations(answer, prepared.pack)
        if not validation["valid"]:
            answer = repair_missing_citations(answer, prepared.pack)
            validation = validate_citations(answer, prepared.pack)
        return answer, validation

    def _finalize_answer(
        self,
        thread_id: str,
        user_message: str,
        prepared: PreparedPipeline,
        answer: str,
        validation: dict[str, Any],
        session_id: str,
    ) -> Generator[str, None, None]:
        citations = _citations_from_pack(prepared.pack, validation)
        assistant = self._insert_message(
            thread_id,
            "assistant",
            answer,
            account_id=prepared.account_id,
            account_name=prepared.account_name,
            citations=citations,
            metadata={"response_type": "answer", "citation_validation": validation},
        )
        thread = self._update_thread_after_message(thread_id, user_message, prepared.account_id, prepared.account_name)
        yield _sse("done", {"assistant_message": _model_dump(assistant), "thread": _serialize_row(thread)})

    def _finalize_clarification(
        self,
        thread_id: str,
        user_message: str,
        clarification: ClarificationResult,
        *,
        original_request: str,
    ) -> Generator[str, None, None]:
        candidates = [as_candidate(c) for c in clarification.error.candidates[:5]]
        assistant = self._insert_message(
            thread_id,
            "assistant",
            clarification.answer,
            metadata={"response_type": "account_clarification", "account_candidates": candidates, "original_request": original_request},
        )
        thread = self._update_thread_after_message(thread_id, user_message, None, None)
        yield _sse("done", {"assistant_message": _model_dump(assistant), "thread": _serialize_row(thread)})

    def _account_name(self, account_id: str | None) -> str | None:
        if not account_id:
            return None
        with connect_dict(self.settings) as conn:
            row = conn.execute("SELECT account_name FROM accounts WHERE account_id = %s", (account_id,)).fetchone()
        return row["account_name"] if row else None

    def _insert_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        *,
        account_id: str | None = None,
        account_name: str | None = None,
        citations: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMessage:
        with connect_dict(self.settings) as conn:
            row = conn.execute(
                """
                INSERT INTO conversation_messages (message_id, thread_id, role, content, account_id, account_name, citations, metadata_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING message_id, thread_id, role, content, account_id, account_name, citations, metadata_json AS metadata, created_at
                """,
                (str(uuid4()), thread_id, role, content, account_id, account_name, Jsonb(citations or []), Jsonb(metadata or {})),
            ).fetchone()
            conn.commit()
        return ConversationMessage.model_validate(dict(row))

    def _update_thread_after_message(self, thread_id: str, user_message: str, account_id: str | None, account_name: str | None) -> dict[str, Any]:
        with connect_dict(self.settings) as conn:
            existing = conn.execute("SELECT title FROM conversation_threads WHERE thread_id = %s", (thread_id,)).fetchone()
            next_title = _title_from_message(user_message) if existing and existing["title"] == "New conversation" else existing["title"]
            row = conn.execute(
                """
                UPDATE conversation_threads
                SET title = %s, account_id = %s, account_name = %s, updated_at = now()
                WHERE thread_id = %s
                RETURNING *
                """,
                (next_title, account_id, account_name, thread_id),
            ).fetchone()
            conn.commit()
        return dict(row)

    def _user_message_count(self, thread_id: str) -> int:
        with connect_dict(self.settings) as conn:
            row = conn.execute(
                "SELECT count(*)::int AS n FROM conversation_messages WHERE thread_id = %s AND role = 'user'",
                (thread_id,),
            ).fetchone()
        return int(row["n"]) if row else 0

    def _last_assistant_message(self, thread_id: str) -> ConversationMessage | None:
        with connect_dict(self.settings) as conn:
            row = conn.execute(
                """
                SELECT message_id, thread_id, role, content, account_id, account_name, citations, metadata_json AS metadata, created_at
                FROM conversation_messages
                WHERE thread_id = %s AND role = 'assistant'
                ORDER BY created_at DESC, message_id DESC
                LIMIT 1
                """,
                (thread_id,),
            ).fetchone()
        return ConversationMessage.model_validate(dict(row)) if row else None

    def _recent_history(self, thread_id: str) -> list[dict[str, str]]:
        limit = max(0, int(self.settings.conversation_history_turns))
        with connect_dict(self.settings) as conn:
            rows = conn.execute(
                """
                SELECT role, content FROM conversation_messages
                WHERE thread_id = %s
                ORDER BY created_at DESC, message_id DESC
                LIMIT %s
                """,
                (thread_id, limit),
            ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def _workflow_seed_to_prompt(seed: str, account_name: str) -> str:
    if seed not in WORKFLOW_SEEDS:
        raise ValueError(f"Unknown workflow_seed {seed!r}")
    return WORKFLOW_SEEDS[seed].format(account_name=account_name)


def _account_resolution_error_answer(error: AccountResolutionError) -> str:
    if error.code == "account_ambiguous":
        candidates = "; ".join(f"{c.account_name} ({c.account_id})" for c in error.candidates[:5])
        return f"I couldn't choose a single account safely. Possible candidates: {candidates}. Please reply with the exact account name or account_id."
    return "I couldn't determine which account you mean. Please include the exact account name or account_id."


def _citations_from_pack(pack: dict[str, Any], validation: dict[str, Any]) -> list[dict[str, Any]]:
    cited = set(validation.get("cited") or [])
    citations = _collect_citations_from_pack(pack, cited)
    if not citations and cited:
        citations = _collect_citations_from_pack(pack, set())
    return citations[:8]


def _collect_citations_from_pack(pack: dict[str, Any], cited: set[str]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    citations: list[dict[str, Any]] = []
    for item in pack.get("retrieved_documents", []):
        for citation in item.get("citations", []):
            label = citation_label(citation)
            if cited and label not in cited:
                continue
            if label in seen:
                continue
            artifact_id = _artifact_id_for_citation(citation, pack.get("account_id"))
            if artifact_id is None:
                continue
            seen.add(label)
            citations.append(
                {
                    "label": _sidebar_citation_label(citation, artifact_id),
                    "source_label": label,
                    "source_object": citation["source_object"],
                    "source_record_id": citation["source_record_id"],
                    "artifact_id": artifact_id,
                    "title": citation.get("title"),
                    "source_url": citation.get("source_url"),
                    "source_date": str(citation.get("source_date")) if citation.get("source_date") else None,
                    "excerpt": citation.get("excerpt"),
                }
            )
    return citations


def _artifact_id_for_citation(citation: dict[str, Any], account_id: str | None) -> str | None:
    record_id = str(citation.get("source_record_id") or "")
    source_object = str(citation.get("source_object") or "")
    if ":" in record_id:
        return record_id
    if source_object == "Email" and account_id:
        return f"email:{account_id}:{safe_id(record_id)}"
    if source_object in {"Account", "Contact", "Opportunity", "Contract", "Task", "Event", "FakeNote"}:
        return f"crm:{source_object}:{record_id}"
    return None


_ARTIFACT_PREFIX_LABELS = {
    "email": "Email",
    "pdf": "PDF",
    "docx": "Word document",
    "meeting": "Meeting",
}


def _sidebar_citation_label(citation: dict[str, Any], artifact_id: str) -> str:
    source_object = str(citation.get("source_object") or "")
    record_id = str(citation.get("source_record_id") or "")
    if source_object == "RiskEvidence":
        prefix, _, suffix = artifact_id.partition(":")
        label = _ARTIFACT_PREFIX_LABELS.get(prefix)
        if label:
            return f"{label} {suffix.rsplit(':', 1)[-1]}"
    if source_object == "Email" and record_id:
        return f"Email {record_id}"
    if artifact_id.startswith("crm:") and source_object and record_id:
        return f"{source_object} {record_id}"
    return citation_label(citation)


def _candidate_id_from_text(text: str, candidates: list[dict[str, Any]]) -> str | None:
    normalized = text.strip().casefold()
    for candidate in candidates:
        account_id = str(candidate.get("account_id", ""))
        account_name = str(candidate.get("account_name", ""))
        if normalized == account_id.casefold() or normalized == account_name.casefold():
            return account_id
    return None


def as_candidate(candidate: Any) -> dict[str, Any]:
    return {"account_id": candidate.account_id, "account_name": candidate.account_name, "score": candidate.score, "method": candidate.method}


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _title_from_message(message: str) -> str:
    return textwrap.shorten(message, width=60, placeholder="...")


def _model_dump(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json")


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    for key, value in list(data.items()):
        if isinstance(value, datetime):
            data[key] = value.isoformat()
    return data
