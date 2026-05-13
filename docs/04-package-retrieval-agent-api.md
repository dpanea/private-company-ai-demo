# Package 4 — Retrieval, agent, API

**Purpose.** The brain of the demo. Hybrid retrieval (BM25 + vector + reciprocal-rank fusion), the unified `ConversationService` that handles workflows + free-text in one path, proactive alert generation, FastAPI endpoints, SSE streaming, rate limiting, and budget protection.

**Depends on:** Package 1, Package 3.

**Blocks:** Package 6.

**Soft-depended-on-by:** Package 5 (frontend can develop against the documented API contract before this is implemented).

**Estimated size:** large (~3000 LOC including tests).

## Outputs

```text
src/pcad/
├── llm/
│   ├── __init__.py
│   ├── client.py               # OpenAI-compatible client (works with OpenRouter AND vLLM)
│   ├── prompts.py              # public prompt + citation helpers (extracted from Uniendo Nodos private functions)
│   ├── citations.py            # validation, normalization, repair
│   └── deterministic.py        # DeterministicLlm test double
├── retrieval/
│   ├── __init__.py
│   ├── retriever.py            # PostgresHybridRetriever, RRF, account resolution
│   ├── intent.py               # intent classifier (heuristic + LLM)
│   └── alerts.py               # ProactiveAlertGenerator
├── agent/
│   ├── __init__.py
│   └── conversation_service.py # the unified multi-turn ConversationService
├── api/
│   ├── __init__.py
│   ├── app.py                  # FastAPI application factory
│   ├── routes.py               # endpoint definitions
│   ├── sessions.py             # anonymous session middleware (cookie-based)
│   ├── rate_limit.py           # per-IP and per-session limiters + daily budget gate
│   └── schemas.py              # request/response Pydantic models
└── cli.py                      # add `serve` subcommand
```

## Dependencies to add to pyproject.toml

```toml
"fastapi>=0.115.0",
"uvicorn>=0.30.0",
"langgraph>=1.0.0",
"itsdangerous>=2.2.0",         # signed session cookies
```

Uniendo Nodos uses `urllib.request` directly to call OpenRouter. **Keep that pattern.** No `httpx` or `requests` — the urllib path is dependency-free and works for both streaming and non-streaming.

## src/pcad/llm/client.py

A single OpenAI-compatible client class that works against any base URL. Used identically for OpenRouter (default) and vLLM (sovereign deployment).

```python
class OpenAICompatibleClient:
    """OpenAI-compatible chat completions + embeddings client.

    Works with:
      - OpenRouter:  base_url=https://openrouter.ai/api/v1
      - vLLM:        base_url=http://vllm:8080/v1
      - Anything else exposing the OpenAI API shape.

    Switching providers is purely a config change (LLM_BASE_URL + LLM_API_KEY).
    """

    def __init__(self, settings: Settings) -> None: ...
    def embed(self, text: str) -> list[float]: ...
    def complete(self, messages, *, temperature=0.1, max_tokens=700, response_format=None) -> str: ...
    def complete_stream(self, messages, *, temperature=0.1, max_tokens=700) -> Iterator[str]: ...
```

Adapt from [core/openrouter.py](../../uniendo-nodos-private-ai/src/un_private_ai/core/openrouter.py). Rename the class from `OpenRouterClient` to `OpenAICompatibleClient`. The headers logic (`HTTP-Referer`, `X-Title`) is OpenRouter-specific but harmless when sent to vLLM, so keep it.

Also keep `DeterministicLlm` from Uniendo Nodos for tests (move to `src/pcad/llm/deterministic.py`).

## src/pcad/llm/prompts.py and src/pcad/llm/citations.py

**Refactor target.** In Uniendo Nodos, the chat service imports private helpers from `agent.py` (`_answer_messages`, `_render_context_prompt`, `_normalize_citation_format`, `_validate_citations`). For the new repo, these belong in public modules.

Move and rename:

- `src/pcad/llm/prompts.py`:
  - `build_answer_messages(context_prompt, *, attempt, previous_answer, previous_validation, system_prompt) -> list[dict]`
  - `render_context_prompt(pack, *, token_budget) -> str`
  - `compact_context_doc(item) -> dict`
  - `estimate_tokens(text) -> int`
  - Public English `DEFAULT_SYSTEM_PROMPT` constant. Adapt from Uniendo Nodos but in English. Key requirements:
    - Answer only from provided context.
    - Cite every substantive paragraph or bullet with `[Source: ObjectType RecordId]` using a label from the allowed list.
    - If unanswerable, say so explicitly.
    - Output plain text or basic markdown; no fancy link syntax.

- `src/pcad/llm/citations.py`:
  - `allowed_citation_labels(pack) -> set[str]`
  - `citation_label(citation) -> str`
  - `validate_citations(answer, pack) -> dict`
  - `normalize_citation_format(answer, pack) -> str`
  - `repair_missing_citations(answer, pack) -> str` ← **with the substring-overlap fix** documented in [bug-fixes-uniendo-nodos.md](bug-fixes-uniendo-nodos.md)

The citation label format is **English**: `[Source: Account SYN_ACC_0001]`, `[Source: Email msg-2026-04-15-abc]`, etc. Regex patterns must match `Source:` not `Fuente:`.

## src/pcad/retrieval/retriever.py

Adapt from [core/retrieval.py](../../uniendo-nodos-private-ai/src/un_private_ai/core/retrieval.py).

Key changes:

1. **English embedding instruction.** Replace the Spanish `_query_instruction` with:
   ```python
   def _query_instruction(query: str) -> str:
       return (
           "Instruction: retrieve company memory documents that answer this business question.\n"
           "Query: " + query
       )
   ```
2. **English tsvector.** All `websearch_to_tsquery('spanish', ...)` → `'english'`.
3. **Reciprocal Rank Fusion (RRF) instead of score-max + bonus.** Replace the `hybrid_search` merge logic with RRF (`k=60` is the standard constant):
   ```text
   score(doc) = sum_over_rankers( 1 / (k + rank_in_ranker(doc)) )
   ```
   where rankers are: `base_context` (rank 1 for all base-context docs), full-text, and vector. Document-type boosts (`DOC_TYPE_BOOSTS`) are *added* to the RRF score after fusion, not multiplied in.
   See [bug-fixes-uniendo-nodos.md](bug-fixes-uniendo-nodos.md) for the same RRF change applied upstream.
4. **Session-scoped retrieval.** Add a `session_id: str | None` to `RetrievalPlan` and all queries against `rag_documents`. The WHERE clause becomes:
   ```sql
   AND (session_id IS NULL OR session_id = %s)
   ```
   so per-session fake-note-derived documents are included for the right visitor, and global synthetic documents are visible to everyone.
5. **English account-resolution error messages.** The Spanish phrases like `"No pude resolver..."` become `"I couldn't determine which account you mean..."`.
6. **Drop the all-accounts-in-Python fetch in the exact-match path.** Replace with a single SQL that uses pg_trgm for both contained-name matching and fuzzy similarity in one query, with a `CASE` to label the match method. Document the rationale in a code comment.

The doc-type boost map should be updated for the new doc types:

```python
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
```

## src/pcad/retrieval/intent.py

Adapt from [core/intent.py](../../uniendo-nodos-private-ai/src/un_private_ai/core/intent.py). Changes:

- **English keywords.** Drop Spanish entries.
- **New intents:** `what_changed`, `open_risks`, `briefing`, `next_action`. Map them to `doc_types`:

```python
DOC_TYPES_BY_INTENT = {
    "account_question": ALL_DOC_TYPES,
    "briefing": ["account_memory", "recent_activity_timeline", "opportunity_snapshot",
                 "meeting_summary", "email_thread_summary", "stakeholder_map", "risk_summary"],
    "what_changed": ["recent_activity_timeline", "email_thread_summary", "meeting_summary", "account_memory"],
    "open_risks": ["risk_summary", "account_memory", "email_thread_summary", "meeting_summary"],
    "next_action": ["recent_activity_timeline", "risk_summary", "account_memory", "opportunity_snapshot"],
    "draft_follow_up": ["account_memory", "recent_activity_timeline", "opportunity_snapshot",
                        "email_thread_summary", "stakeholder_map"],
    "stakeholder_question": ["stakeholder_map", "account_memory", "opportunity_snapshot"],
    "contract_question": ["account_memory", "contract_snapshot", "recent_activity_timeline"],
}

ALL_DOC_TYPES = [
    "account_memory",
    "opportunity_snapshot",
    "recent_activity_timeline",
    "contract_snapshot",
    "stakeholder_map",
    "email_thread_summary",
    "meeting_summary",
    "risk_summary",
]
```

- The LLM intent-classifier JSON schema must also be updated to the new intent set.

## src/pcad/retrieval/alerts.py

**New code, no Uniendo Nodos counterpart.**

```python
class ProactiveAlertGenerator:
    """Generates proactive alerts for an account based on its raw_artifacts,
    rag_documents, activities, and any session-scoped fake_notes.
    """

    def __init__(self, settings: Settings) -> None: ...

    def generate_for_account(
        self,
        account_id: str,
        *,
        session_id: str | None = None,
    ) -> list[ProactiveAlert]:
        """Compute alerts. Existing alerts for this (account_id, session_id) are
        DELETEd and the new ones INSERTed. Returns the list inserted.
        """
```

Alert rules (v1 — deterministic, no LLM):

| Alert type | Rule |
|---|---|
| `approaching_close_date` | Open opportunity with `close_date` within 14 days. Severity `warning` if 0–7 days, `critical` if `close_date <= today AND is_closed = false`. |
| `stalled_account` | No `activities` row for this account in the last 14 days (using `reference_date` from manifest as "today"). Severity `warning`. |
| `unresolved_objection` | Any email_thread_summary or meeting_summary whose `content_markdown` contains keywords like "concern", "objection", "blocker", "issue with", "worried about" and where the *next* activity in chronological order does not contain "resolved", "addressed", "answered", "followed up". Severity `warning`. |
| `missing_followup` | Open `activities` row with `priority = 'High'` and `activity_date` older than 5 days. Severity `warning`. |
| `champion_positive_signal` | Email or meeting in the last 14 days containing strong positive phrases ("let's move forward", "ready to proceed", "looks great", "approved by", "we're on board"). Severity `info`. |
| `data_inconsistency` | Opportunity with `stage = 'Closed Won'` but no `contracts` row. Or `is_won = true` but `is_closed = false`. Severity `info`. |

Each alert records:

- `body_markdown` — short 2–4 sentence explanation citing the evidence.
- `evidence_doc_ids` — list of `rag_documents.doc_id` that support the alert.
- `evidence_artifact_ids` — list of `raw_artifacts.artifact_id` that support the alert.

Alerts are regenerated:

- Once at the end of `run_demo_ingestion` (per account, without `session_id`).
- On every `POST /api/sessions/{sid}/accounts/{aid}/fake-notes` call (per `session_id` + `account_id`).

## src/pcad/agent/conversation_service.py

**This is the unified multi-turn agent.** It replaces both `core/agent.py` and `web/chat_service.py` from Uniendo Nodos. The two are merged because in this demo, every request is multi-turn-capable: workflows just seed the first turn.

```python
class ConversationService:
    def __init__(
        self,
        settings: Settings,
        *,
        retriever: PostgresHybridRetriever | None = None,
        llm_client: OpenAICompatibleClient | None = None,
        alerts: ProactiveAlertGenerator | None = None,
    ) -> None: ...

    # Thread management
    def list_threads(self, session_id: str) -> list[ConversationThread]: ...
    def create_thread(self, session_id: str, *, account_id: str | None, workflow_seed: str | None) -> ConversationThread: ...
    def get_thread(self, session_id: str, thread_id: str) -> ConversationThread: ...
    def get_messages(self, session_id: str, thread_id: str) -> list[ConversationMessage]: ...

    # Streaming send
    def send_message_stream(
        self,
        session_id: str,
        thread_id: str,
        user_text: str,
    ) -> Generator[str, None, None]:
        """SSE event stream: user_message → status → token… → done.

        - Inserts the user message.
        - Resolves account (sticky from thread state when not overridden).
        - Builds retrieval plan with conversation history budget (last 6 messages).
        - Runs hybrid retrieval scoped to (account, session).
        - Streams LLM tokens.
        - Validates citations, normalizes format, and persists assistant message.
        """
```

Implementation notes:

- **Account stickiness** as in Uniendo Nodos: thread state holds `active_account_id` / `active_account_name`. Account hint from new intent only overrides if it points elsewhere clearly.
- **Account-clarification turn-handling** as in Uniendo Nodos: when account resolution is ambiguous, the assistant turn is a clarification message; the next user message can disambiguate.
- **Conversation history is included in retrieval and prompt.** Pass the last 6 messages (3 user + 3 assistant) as additional context in the LLM prompt before the new user message. The retrieval query is the current user message (not the full history) — keep retrieval focused.
- **Workflow seeds.** When a thread is created with `workflow_seed="call_briefing"`, the first user message is auto-generated by `_workflow_seed_to_prompt("call_briefing", account_name)`. The mapping:

  ```python
  WORKFLOW_SEEDS = {
      "call_briefing": "Brief me before a call with {account_name}. Cover recent activity, open opportunities, stakeholders, and any open risks.",
      "what_changed": "What changed for {account_name} in the last 14 days that I should know about before reaching out?",
      "open_risks": "What are the open risks, objections, or unresolved questions for {account_name}?",
      "follow_up_draft": "Draft a short follow-up email to the primary contact at {account_name}. Reference the most recent meaningful interaction.",
      "next_action": "What is the most important next action I should take on {account_name} this week?",
  }
  ```

  When the thread is created, the seed prompt is inserted as the first user message before retrieval runs.

- **Per-session retrieval scoping.** The `RetrievalPlan.session_id` carries through to all SQL queries, so per-session fake-note-derived documents are included.

Reuse from Uniendo Nodos:

- The SSE event structure (`user_message`, `status`, `token`, `done`, `error`) from [web/chat_service.py:97](../../uniendo-nodos-private-ai/src/un_private_ai/web/chat_service.py).
- The thread title auto-generation (`_title_from_message`).
- The citation-extraction-from-pack logic (`_citations_from_pack`).
- The LangGraph orchestration in [core/agent.py](../../uniendo-nodos-private-ai/src/un_private_ai/core/agent.py) is **optional** — it's overkill for a single retrieval+generate flow with a clarification side-branch. Recommendation: write `ConversationService.send_message_stream` as straight Python (clearer for this use case). Keep LangGraph available for future extensibility but don't introduce the dependency unless used.

  Decision lock: **do not use LangGraph in v1.** Drop the LangGraph dependency from pyproject.toml.

## src/pcad/api/sessions.py

Cookie-based anonymous session middleware.

```python
class SessionMiddleware:
    """On every request:
      - Read SESSION_COOKIE_NAME from the request cookies.
      - If valid and not expired: load Session from DB.
      - Otherwise: create a new Session row and set the cookie.
      - Attach Session to request.state.session.
    """
```

- Cookie is signed with `SESSION_SECRET` (use `itsdangerous`).
- Cookie attributes: `HttpOnly`, `SameSite=Lax`, `Secure` in production (controlled by an env flag).
- `Session.last_seen_at` is bumped on every request.
- Sessions older than `SESSION_TTL_DAYS` are deleted by a cleanup function called periodically (a simple "on each request, 1% chance" cleanup is acceptable for the demo).

## src/pcad/api/rate_limit.py

Three-layer protection:

1. **Per-IP rate limit.** Token-bucket in-process (acceptable for single-instance demo). Limit: `RATE_LIMIT_PER_IP_PER_MINUTE` requests per minute per source IP. Applied as middleware to `/api/*` routes.
2. **Per-session rate limit.** Token-bucket per `session_id`. Limit: `RATE_LIMIT_PER_SESSION_PER_HOUR` *messages* (only LLM-calling endpoints count). Applied inside `ConversationService.send_message_stream`.
3. **Daily global budget gate.** Persist daily token usage in a small table (`daily_budget_usage(date, tokens_in, tokens_out, cost_estimate_eur)`). Before each LLM call, sum today's usage and if it exceeds `DAILY_TOKEN_BUDGET`, return a degraded canned response without calling the LLM. After each LLM call, update the row with the actual usage from the OpenRouter response (`usage.prompt_tokens`, `usage.completion_tokens`).

When the budget gate trips, the assistant message says:

> The public demo has hit its daily budget for this account. The system is still here to demonstrate the architecture — try again tomorrow, or book a private walkthrough for live interaction.

## src/pcad/api/schemas.py

Request/response Pydantic models for the API. See the API contract below.

## src/pcad/api/routes.py

API surface (mounted under `/api`):

### Public endpoints

```text
GET    /api/health
GET    /api/accounts
GET    /api/accounts/{account_id}
GET    /api/accounts/{account_id}/artifacts
GET    /api/accounts/{account_id}/alerts
GET    /api/artifacts/{artifact_id}              # returns raw_artifact with extracted_text + rendered page urls
GET    /api/artifacts/{artifact_id}/page/{n}     # serves a rendered PNG (StaticFiles works too)
GET    /api/threads
POST   /api/threads                               # body: {account_id, workflow_seed}
GET    /api/threads/{thread_id}
GET    /api/threads/{thread_id}/messages
POST   /api/threads/{thread_id}/messages/stream   # body: {message}; returns SSE
POST   /api/accounts/{account_id}/fake-notes      # body: {note_type, title, body, note_date}; triggers re-build of per-session docs + alerts
GET    /api/accounts/{account_id}/fake-notes
DELETE /api/fake-notes/{note_id}
GET    /api/session                                # returns {session_id, created_at}; used by the frontend to verify the cookie
```

### Behaviors

- **Account, artifact, alerts list endpoints** scope reads by `session_id` for anything session-aware (alerts, fake-notes-derived rag_documents).
- **`POST /api/accounts/{account_id}/fake-notes`:** after INSERT, kick off a synchronous re-build:
  1. Build new `email_summary` / `meeting_summary` / `risk_summary` docs scoped to this session.
  2. Index their embeddings.
  3. Recompute alerts for this account scoped to this session.
  4. Return the new fake note + the new alerts.
- **`POST /api/threads/{thread_id}/messages/stream`:** delegates to `ConversationService.send_message_stream`. Returns `text/event-stream`.
- **`GET /api/artifacts/{artifact_id}`:** returns `RawArtifact` plus a list of page URLs (`/api/artifacts/{id}/page/0`, etc.) for PDFs.

## src/pcad/api/app.py

```python
def create_app(settings: Settings | None = None) -> FastAPI:
    """Compose the FastAPI app with session middleware, rate limit middleware,
    static files, and the routes module.
    """
```

Mount static files:

- `/static` → `src/pcad/api/static/` (frontend assets from Package 5).
- `/rendered` → `data/rendered/` (PDF page images).
- `/` → `static/index.html` (single-page demo).

## CLI

Add to `src/pcad/cli.py`:

```text
uv run pcad serve [--host 127.0.0.1] [--port 8000] [--reload]
```

## Reuse from Uniendo Nodos

| Source | Adapt to |
|---|---|
| `core/openrouter.py` | `pcad/llm/client.py` + `pcad/llm/deterministic.py` |
| `core/agent.py` (private helpers) | `pcad/llm/prompts.py` + `pcad/llm/citations.py` (made public) |
| `core/retrieval.py` | `pcad/retrieval/retriever.py` (with RRF, English) |
| `core/intent.py` | `pcad/retrieval/intent.py` (English, new intents) |
| `web/chat_service.py` | `pcad/agent/conversation_service.py` (English, drops separate `core/agent.py`, adds workflow seeds + session scoping) |
| `web/app.py` | `pcad/api/app.py` (no admin auth; anonymous sessions instead) |

## Tests

`tests/test_retrieval.py`:

- Account resolution: exact match wins, fuzzy match within ambiguity_delta returns multiple candidates, no match raises.
- RRF: given crafted full-text + vector + base-context inputs, the fused order matches the expected RRF ranking.
- Session scoping: a doc with `session_id = "A"` is not returned for `session_id = "B"`.

`tests/test_intent.py`:

- Each new intent fires on its keyword set.
- LLM fallback path uses the `DeterministicLlm` to confirm the JSON-schema response shape is parsed correctly.

`tests/test_alerts.py`:

- For each rule type, build a small fixture and assert the alert fires (or doesn't).
- Re-running for the same (account, session) replaces existing alerts.

`tests/test_conversation_service.py`:

- Workflow seed: creating a thread with `workflow_seed="call_briefing"` inserts a user message with the expected seed text.
- Account stickiness: a follow-up message on a thread reuses the previous turn's account.
- Account clarification: ambiguous resolution produces a clarification message; the next user message can pick a candidate.
- Per-session fake notes appear in retrieval for that session but not other sessions.

`tests/test_api.py`:

- Anonymous session cookie is set on first request and reused on second.
- Rate limit returns 429 when exceeded.
- Daily budget gate returns the canned message and increments a counter without calling the LLM (use `DeterministicLlm`).
- SSE endpoint emits `user_message`, `status`, `token`, `done` events in order.

## Acceptance criteria

1. `uv run pcad serve` starts on `127.0.0.1:8000`.
2. Every endpoint in the API surface works against a freshly ingested DB.
3. All tests pass with `uv run pytest`.
4. The codebase contains no Spanish text (`grep -ri "spanish\|espanol\|fuente" src/` returns zero).
5. Citation labels use the `[Source: ...]` format consistently.
6. RRF replaces the score-max+bonus hybrid merge.
7. The budget gate trips correctly under simulated heavy usage and the assistant message matches the canned text.
8. Per-session fake notes are invisible to other sessions.
9. The LangGraph dependency is **not** in pyproject.toml.
