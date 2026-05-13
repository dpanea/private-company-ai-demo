# Bug fixes, improvements, and refactor — Uniendo Nodos backport

**Scope.** This document specifies three changes to the upstream repository `~/projects/uniendo-nodos-private-ai`. They are independent of the new demo repo and can be implemented by a separate coding agent in parallel.

1. Substring-overlap bug in `_repair_missing_citations`.
2. Reciprocal Rank Fusion replaces the score-max+bonus hybrid merge.
3. Unify the multi-turn conversation handling — fold `core/agent.py` and `web/chat_service.py` into a single `ConversationService` with public prompt and citation helpers.

The first two are correctness fixes; the third is a structural refactor that aligns the upstream codebase with the architecture used in `private-company-ai-demo` and removes duplicate state-flow logic. All three should land in a single coordinated PR.

**Repo:** `~/projects/uniendo-nodos-private-ai`

**Branch suggestion:** `refactor/unify-conversation-and-fixes`

## 1. Fix the substring-overlap bug in `_repair_missing_citations`

**File:** [src/un_private_ai/core/agent.py](../../uniendo-nodos-private-ai/src/un_private_ai/core/agent.py)

**Symptom.** When the LLM produces an answer that contains an allowed citation label but not wrapped in `[Fuente: ...]`, the repair function does:

```python
labels_in_answer = [label for label in sorted(allowed, key=len, reverse=True) if label in answer]
if labels_in_answer:
    repaired = answer
    for label in labels_in_answer:
        repaired = repaired.replace(label, f"[Fuente: {label}]")
    return _normalize_citation_format(repaired, pack)
```

The `labels_in_answer` list is correctly sorted by length descending, but `str.replace` is a global replace. If a long label and a short label *both* appear, the short label may be wrapped *inside* the already-wrapped long label, producing nested `[Fuente: [Fuente: ...]]`.

Example:

- Allowed: `Task 00TSYN000000001`, `Task 00TSYN0000000`
- Answer: `Lorem ipsum Task 00TSYN000000001 dolor.`
- After replace pass 1 (long first): `Lorem ipsum [Fuente: Task 00TSYN000000001] dolor.`
- After replace pass 2 (short next): `Lorem ipsum [Fuente: [Fuente: Task 00TSYN0000000]00001] dolor.`

This is rare in practice because most record IDs in Uniendo Nodos data have unique suffixes, but it is a correctness bug and worth fixing.

**Fix.** After wrapping a label, do not re-scan that wrapped substring on subsequent passes. Two acceptable approaches:

**Approach A** (preferred — explicit guard):

```python
def _repair_missing_citations(answer: str, pack: dict) -> str:
    validation = _validate_citations(answer, pack)
    if validation["valid"]:
        return answer
    allowed = _allowed_citation_labels(pack)
    if not allowed:
        return answer

    labels_sorted = sorted(allowed, key=len, reverse=True)
    repaired = answer
    for label in labels_sorted:
        pattern = rf"(?<!\[Fuente:\s){re.escape(label)}(?!\s*\])"
        repaired = re.sub(pattern, f"[Fuente: {label}]", repaired)

    if _validate_citations(repaired, pack)["valid"]:
        return _normalize_citation_format(repaired, pack)

    fallback = _fallback_citation_label(pack)
    if not fallback:
        return answer
    logger.warning("agent.postgres.node.generate_answer.repair_missing_citation fallback_citation=%s", fallback)
    return answer.rstrip() + f"\n\nFuentes consultadas: [Fuente: {fallback}]"
```

The look-behind `(?<!\[Fuente:\s)` and look-ahead `(?!\s*\])` prevent wrapping an already-wrapped label.

**Approach B** (alternative — process token by token): split the answer into tokens, wrap on whole-token matches only. More invasive, not recommended.

**Test.** Add a test in `tests/` that reproduces the substring-overlap case and asserts the repaired answer contains exactly one `[Fuente: <long-label>]` and no nested wrappers.

## 2. Replace score-max+bonus hybrid merge with Reciprocal Rank Fusion

**File:** [src/un_private_ai/core/retrieval.py](../../uniendo-nodos-private-ai/src/un_private_ai/core/retrieval.py)

**Current behavior.** `hybrid_search` merges full-text + vector + base-context results by:

```python
existing["score"] = max(float(existing["score"]), float(row["score"])) + HYBRID_MULTI_MATCH_BONUS
```

The scores being maxed come from different scales:

- `BASE_CONTEXT_SCORE = 1.0` (constant)
- `ts_rank_cd(...)` from full-text — typically `0.0` to `~10.0`, not normalized.
- `1.0 - (embedding <=> query)` from vector — `0.0` to `1.0`.

Mixing them via max happens to work for Uniendo Nodos because the `DOC_TYPE_BOOSTS` and the `HYBRID_MULTI_MATCH_BONUS` dominate the actual ranking, but it's brittle and not principled.

**Fix.** Replace with Reciprocal Rank Fusion. RRF is the standard hybrid retrieval merge:

```text
score(doc) = sum over rankers of  1 / (k + rank_in_ranker(doc))
```

where `k = 60` is the conventional constant. Then add `DOC_TYPE_BOOSTS` *after* fusion, so document-type preferences still tilt results but don't interact with the score-merging step.

**Implementation:**

```python
RRF_K = 60

def _rrf_merge(
    *rankers: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Each ranker is an already-ranked list of rows (best first).
    Returns a dict keyed by doc_id with merged 'rrf_score' and union of 'reasons'.
    """
    merged: dict[str, dict[str, Any]] = {}
    for ranker_rows in rankers:
        for rank_index, row in enumerate(ranker_rows):
            doc_id = row["doc_id"]
            contribution = 1.0 / (RRF_K + rank_index + 1)
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
```

And `hybrid_search` becomes:

```python
def hybrid_search(self, plan: RetrievalPlan, base_context: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    logger.info("retrieval.postgres.hybrid.start base_context_count=%s", len(base_context or []))
    base = base_context or []
    fts = self.full_text_search(plan)
    vec = self.vector_search(plan)

    merged = _rrf_merge(base, fts, vec)

    ranked = sorted(
        merged.values(),
        key=lambda row: row["rrf_score"] + _doc_type_boost(row["doc_type"]),
        reverse=True,
    )
    results = ranked[: plan.limit]
    logger.info(
        "retrieval.postgres.hybrid.done raw_count=%s deduped_count=%s returned_count=%s",
        len(base) + len(fts) + len(vec),
        len(merged),
        len(results),
    )
    return results
```

Drop the `BASE_CONTEXT_SCORE = 1.0` constant and `HYBRID_MULTI_MATCH_BONUS = 0.15` constant — neither is needed under RRF.

Update the `score` field on each result row to the new `rrf_score` value (or add the new field and leave `score` for backward compatibility — recommend the rename for clarity).

**Tests.**

Add `tests/test_rrf.py`:

- Hand-construct three rankers with known orderings. Assert that the fused order is what RRF predicts mathematically.
- Assert a document appearing high in two rankers beats one appearing higher in only one.
- Assert that swapping the ranker order does not change the fused result (RRF is order-independent).
- Assert that doc-type boosts can still tip a tie within the RRF tier.

Update existing `tests/test_retrieval.py` (or wherever hybrid is tested) to use the new score field.

## 3. Unify multi-turn conversation: fold `core/agent.py` and `web/chat_service.py` into a single `ConversationService`

**Files affected.**

- `src/un_private_ai/core/agent.py` — to be deleted (or reduced to thin re-exports for one release).
- `src/un_private_ai/web/chat_service.py` — to be deleted.
- `src/un_private_ai/core/prompts.py` — **new**.
- `src/un_private_ai/core/citations.py` — **new**.
- `src/un_private_ai/core/conversation.py` — **new** (the unified service).
- `src/un_private_ai/cli.py` — update `ask-postgres` to call the new service.
- `src/un_private_ai/web/app.py` — update to instantiate the new service.
- `pyproject.toml` — drop `langgraph` and `langgraph-checkpoint-postgres` (see note below).
- Existing tests under `tests/` — update imports.

### Motivation

The current split has three problems:

1. **Private-helpers-imported-publicly smell.** [web/chat_service.py:15-21](../../uniendo-nodos-private-ai/src/un_private_ai/web/chat_service.py) imports `_answer_messages`, `_normalize_citation_format`, `_render_context_prompt`, `_validate_citations` from `core/agent.py`. These are marked as private by convention (underscore prefix) but used by another module — a contract violation that makes the codebase fragile to refactoring.
2. **Two execution paths for the same logic.** [core/agent.py](../../uniendo-nodos-private-ai/src/un_private_ai/core/agent.py) is a LangGraph state machine used by the CLI; [web/chat_service.py:97](../../uniendo-nodos-private-ai/src/un_private_ai/web/chat_service.py) is a hand-rolled streaming pipeline used by the web. They reimplement the same flow (resolve intent → resolve account → retrieve → generate) with slightly different orchestrations and slightly different error handling. A bug fixed in one is not necessarily fixed in the other.
3. **LangGraph adds complexity without delivering value.** The current graph has a single linear path plus one conditional edge for account-resolution errors. The same shape is expressed more directly as Python without LangGraph. The `langgraph-checkpoint-postgres` dependency in `pyproject.toml` is not even used (checkpointing happens via the application's own `chat_threads` / `chat_messages` tables).

### Target shape

```text
core/
├── prompts.py          # public: prompt building + context rendering
├── citations.py        # public: validation, normalization, repair
├── conversation.py     # public: ConversationService — the only conversation entry point
├── retrieval.py        # unchanged (other than RRF from section 2)
├── intent.py           # unchanged
├── openrouter.py       # unchanged
├── models.py           # unchanged
├── postgres.py         # unchanged
├── config.py           # unchanged
└── synthetic.py        # unchanged
```

### Step 3.1 — Extract public prompt and citation modules

**Move the following from `core/agent.py` to `core/prompts.py`**, renaming to drop the underscore prefix:

- `_answer_messages` → `build_answer_messages`
- `_render_context_prompt` → `render_context_prompt`
- `_compact_context_doc` → `compact_context_doc`
- `_estimate_tokens` → `estimate_tokens`

Add a public constant `DEFAULT_SYSTEM_PROMPT` set to the current Spanish system prompt string from [agent.py:203-211](../../uniendo-nodos-private-ai/src/un_private_ai/core/agent.py) — unchanged content, just public.

Also move the `RESPONSE_MAX_TOKENS`, `DEFAULT_CONTEXT_TOKEN_BUDGET`, `DEFAULT_GENERATION_MAX_ATTEMPTS`, `APPROX_CHARS_PER_TOKEN` constants to `prompts.py`.

**Move the following from `core/agent.py` to `core/citations.py`**, dropping the underscore prefix:

- `_allowed_citation_labels` → `allowed_citation_labels`
- `_citation_label` → `citation_label`
- `_validate_citations` → `validate_citations`
- `_normalize_citation_format` → `normalize_citation_format`
- `_repair_missing_citations` → `repair_missing_citations` (with the section-1 fix applied)
- `_fallback_citation_label` → `fallback_citation_label`
- `_account_resolution_error_answer` → `account_resolution_error_answer`

These all keep their Spanish strings.

### Step 3.2 — Create `core/conversation.py`

The new `ConversationService` is the single conversational entry point. It supports both **stateful multi-turn** (replacing `web/chat_service.py`) and **stateless single-shot** (replacing `core/agent.py` for CLI use).

```python
from __future__ import annotations

import logging
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .citations import (
    allowed_citation_labels,
    normalize_citation_format,
    repair_missing_citations,
    validate_citations,
)
from .config import Settings
from .intent import IntentResolver
from .openrouter import LlmClient, OpenRouterClient
from .prompts import (
    DEFAULT_SYSTEM_PROMPT,
    RESPONSE_MAX_TOKENS,
    build_answer_messages,
    render_context_prompt,
)
from .retrieval import AccountResolutionError, PostgresHybridRetriever


logger = logging.getLogger(__name__)


@dataclass
class ConversationResult:
    answer: str
    response_type: str               # 'answer' | 'account_clarification' | 'error'
    active_account_id: str | None
    active_account_name: str | None
    citations: list[dict[str, Any]]
    citation_validation: dict[str, Any]
    metadata: dict[str, Any]
    generation_attempts: int


class ConversationService:
    """Unified conversation entry point.

    - run_single_shot(): for CLI / scripts. Stateless. Returns a ConversationResult.
    - send_message_stream(): for web. Stateful (chat_threads / chat_messages).
                             Yields SSE-formatted events.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        retriever: PostgresHybridRetriever | None = None,
        llm_client: LlmClient | None = None,
        intent_resolver: IntentResolver | None = None,
    ) -> None:
        self.settings = settings
        self.llm_client = llm_client or OpenRouterClient(settings)
        self.retriever = retriever or PostgresHybridRetriever(
            settings.database_url,
            embedding_client=self.llm_client,
        )
        self.intent_resolver = intent_resolver or IntentResolver(self.llm_client)

    # ----- Stateless single-shot path (CLI) -----

    def run_single_shot(
        self,
        user_request: str,
        *,
        explicit_account_id: str | None = None,
    ) -> ConversationResult:
        """Resolve account, retrieve, generate. No persistence, no streaming."""
        intent = self.intent_resolver.resolve(user_request)
        try:
            account_id, account_name = self.retriever.resolve_account(
                user_request,
                explicit_account_id=explicit_account_id,
                account_hint=intent.account_hint,
            )
        except AccountResolutionError as exc:
            return self._clarification_result(exc, user_request)

        plan = self.retriever.build_retrieval_plan(user_request, account_id, account_name, intent)
        base_context = self.retriever.fetch_base_context(plan)
        search_results = self.retriever.hybrid_search(plan, base_context)
        pack = self.retriever.build_context_pack(user_request, plan, search_results)
        return self._generate_with_retries(pack, account_id, account_name)

    # ----- Stateful streaming path (web) -----

    def list_chats(self, username: str) -> list[dict[str, Any]]: ...
    def create_chat(self, username: str) -> dict[str, Any]: ...
    def get_messages(self, username: str, chat_id: str) -> list[dict[str, Any]]: ...

    def send_message_stream(
        self,
        username: str,
        chat_id: str,
        message: str,
    ) -> Generator[str, None, None]:
        """SSE-formatted event stream: user_message → status → token… → done | error.

        Identical event protocol to the current web/chat_service.py.
        """
        ...

    # ----- Shared helpers (private) -----

    def _generate_with_retries(self, pack, account_id, account_name) -> ConversationResult:
        """Generate an answer with citation validation + retry + repair.
        Used by both run_single_shot and send_message_stream's non-streaming fallback.
        """
        ...

    def _clarification_result(self, error: AccountResolutionError, user_request: str) -> ConversationResult:
        """Build a ConversationResult for an unresolvable / ambiguous account."""
        ...
```

The streaming path internally:

1. Inserts the user message (same as current `chat_service.py`).
2. Resolves account with stickiness (same).
3. Builds retrieval plan, runs hybrid search, builds context pack (same).
4. Calls `llm_client.complete_stream(...)` and yields `token` events as they arrive.
5. After streaming finishes, normalizes citations, validates, and persists the assistant message.

The retry+repair logic (currently in `core/agent.py`'s `generate_answer_from_context_pack`) is encapsulated in `_generate_with_retries` and called by `run_single_shot` and by the *non-streaming* fallback in `send_message_stream` (when the LLM client lacks `complete_stream`). Streaming itself does not retry — if streaming fails citation validation, the assistant message is still saved but with `citation_validation.valid = false`, mirroring current behavior.

### Step 3.3 — Update the CLI

`src/un_private_ai/cli.py` currently exposes `ask-postgres` and related commands that call `build_postgres_agent(...).invoke({...})`.

Replace those call sites with:

```python
result = ConversationService(settings).run_single_shot(
    user_request,
    explicit_account_id=args.account_id,
)
print(result.answer)
```

The CLI output shape (Spanish error messages on ambiguity, citation validation diagnostics, etc.) must be preserved.

### Step 3.4 — Update the web app

`src/un_private_ai/web/app.py` instantiates `ChatService` in `create_app`. Replace with:

```python
chat_service = chat_service or ConversationService(settings)
```

The route handlers stay the same — they call `chat_service.list_chats(...)`, `chat_service.send_message_stream(...)`, etc. The new `ConversationService` exposes the same method signatures so the web layer is unchanged in shape.

Rename the local variable `chat_service` to `conversation_service` for clarity if desired; or keep the name to minimize churn.

### Step 3.5 — Delete the old files

- Delete `src/un_private_ai/core/agent.py`.
- Delete `src/un_private_ai/web/chat_service.py`.
- Update any test imports accordingly.

### Step 3.6 — Drop LangGraph dependencies

LangGraph was overkill for the current conversation shape — a single linear flow with one conditional branch for account-resolution errors is clearer as straight Python than as a compiled state graph. After removing `core/agent.py`, `langgraph` and `langgraph-checkpoint-postgres` are no longer imported anywhere in the repo.

**Action:**

1. Remove both dependencies from `pyproject.toml`:
   - `langgraph>=1.0.0`
   - `langgraph-checkpoint-postgres>=2.0.0`
2. Run `uv sync` to update the venv.
3. Run `uv lock` to regenerate the lockfile.
4. `grep -r "from langgraph" src/ tests/` must return zero results.

The `langgraph-checkpoint-postgres` dependency in particular was never used — the application persists conversation state via its own `chat_threads` / `chat_messages` tables, not via LangGraph checkpointers. Dropping it is purely cleanup.

If a real multi-step agent emerges later (multiple tool calls, conditional branching beyond the current shape, planning loops), LangGraph can be reintroduced at that point. It is not needed for v1.

### Step 3.7 — Tests

Existing test changes:

- Any test importing `_answer_messages`, `_render_context_prompt`, `_validate_citations`, `_normalize_citation_format`, or other previously private helpers from `core.agent` must update its imports to `core.prompts` / `core.citations`.
- Tests for `build_postgres_agent` and `generate_answer_from_context_pack` are replaced by tests for `ConversationService.run_single_shot`.
- Tests for `ChatService` are renamed to test the streaming branch of `ConversationService`. The SSE event protocol is identical, so most assertions transfer directly.

New tests under `tests/test_conversation_service.py`:

- `run_single_shot` happy path produces an answer with citations.
- `run_single_shot` with ambiguous account name returns a `response_type='account_clarification'` result with candidates.
- `run_single_shot` with `explicit_account_id` bypasses fuzzy matching.
- Streaming path emits `user_message`, `status`, `token`, `done` events in order.
- Account stickiness preserved across two streaming calls in the same chat.
- Account clarification flow: ambiguous turn returns candidates; next user message picks one.

### Step 3.8 — Documentation updates inside Uniendo Nodos

- Update [README.md](../../uniendo-nodos-private-ai/README.md): replace mentions of `core/agent.py` and the LangGraph graph with the new single-service description.
- Update [AGENTS.md](../../uniendo-nodos-private-ai/AGENTS.md) if it references the agent.py module by name.
- Add a short `docs/architecture.md` (if one does not exist) describing the conversation flow as it now is.

## Process and PR shape

- All three changes in a single PR titled `refactor: unify conversation service + citation repair + RRF`.
- Commit order for review clarity:
  1. `fix(agent): avoid nested citation wrapping in _repair_missing_citations`
  2. `refactor(retrieval): replace score-max hybrid merge with reciprocal rank fusion`
  3. `refactor(core): extract public prompts.py and citations.py from agent.py`
  4. `feat(core): add ConversationService unifying single-shot and streaming paths`
  5. `refactor(cli, web): use ConversationService and remove agent.py / chat_service.py`
  6. `chore: drop langgraph and langgraph-checkpoint-postgres dependencies`
  7. `docs: update README and AGENTS for new structure`
- No DB schema changes.
- API surface (web endpoints, CLI commands, request/response shapes) unchanged.
- Run the full `uv run pytest` suite before opening the PR.

## Acceptance criteria

1. The substring-overlap test fails on `main` and passes after the fix.
2. The new RRF tests pass.
3. All existing tests continue to pass (with import updates where helpers moved).
4. `src/un_private_ai/core/agent.py` and `src/un_private_ai/web/chat_service.py` no longer exist.
5. `core/prompts.py` and `core/citations.py` exist and contain no leading-underscore "private" public functions used by other modules.
6. The CLI's `ask-postgres` command behaves identically to before (same stdout, same exit codes).
7. The web app's chat behavior is identical from the frontend's point of view (same SSE events, same responses, same account stickiness).
8. `pyproject.toml` no longer lists `langgraph` or `langgraph-checkpoint-postgres`, and `grep -r "from langgraph" src/ tests/` returns zero results.
9. Manual spot-check: at least one realistic CLI query and one realistic web chat session both produce sensible answers with valid citations.
