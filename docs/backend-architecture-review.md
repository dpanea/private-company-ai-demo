# Backend architecture review — manual roadmap and red flags

Originally written 2026-05-14 against commit `71e1906`. Updated 2026-05-15 to
record the fixes that have landed since. The document keeps its original
two-half shape, plus a short status summary at the top so you can see at a
glance what changed.

1. **[Status of fixes since the original review](#0-status-of-fixes-since-the-original-review)** — short.
2. **[Architecture walkthrough](#1-architecture-walkthrough)** — what the backend does, layer by layer, in the order the code executes a request. Each section ends with concrete files/lines to open.
3. **[Red flags and resolution log](#2-red-flags-and-resolution-log)** — each item carries `[FIXED]`, `[KEPT]`, or `[DEFERRED]` with the rationale.

The frontend (`src/pcad/api/static/`) is intentionally not covered in depth.

---

## 0. Status of fixes since the original review

Landed on the same branch:

- **LLM client on httpx.** Replaced the `urllib.request` client with `httpx.Client` + retry-with-backoff on 408/425/429/5xx, `Retry-After` honoring, persistent connection, explicit `close()`. ([src/pcad/llm/client.py](src/pcad/llm/client.py))
- **Connection pool.** All `connect` / `connect_dict` calls now go through a per-URL `psycopg_pool.ConnectionPool` cached in [src/pcad/db.py](src/pcad/db.py); migrations and tests still use a raw connection via `raw_connect`.
- **Migrations are correct and serialized.** Single execution of `0001_init.sql` (no more double-apply); a `pg_advisory_lock(0x70636164)` brackets the whole runner so concurrent CLI + app starts cannot race. ([src/pcad/migrations.py](src/pcad/migrations.py))
- **Daily budget gate moved up.** `send_message_stream` now checks `check_daily_budget` *before* `_prepare_pipeline`, so an over-budget session never pays for intent classification. ([src/pcad/agent/conversation_service.py:144](src/pcad/agent/conversation_service.py:144))
- **Per-page PDF OCR.** [parse_pdf](src/pcad/ingestion/parsers/pdf.py) now decides page-by-page (40-char threshold) and OCRs only the image-only pages.
- **Dead code removed.** `fetch_documents_by_ids`, `account_candidates`, the `MeetingSummaryInput` rebuild, and the `account_id_if_available` fallback on contracts are gone.
- **Per-record `source_record_hashes`.** [ai_ready_documents.py](src/pcad/ingestion/ai_ready_documents.py) emits one hash per source ID instead of one hash of the joined list.
- **`resolve_account` rewritten as a CTE.** Same matching semantics, one set of parameters, far easier to read. ([src/pcad/retrieval/retriever.py:resolve_account](src/pcad/retrieval/retriever.py))
- **Citation repair now logs at WARNING** with the unknown vs. allowed sets when the regex fallback path fires. ([src/pcad/llm/citations.py:repair_missing_citations](src/pcad/llm/citations.py))
- **Prompt builder trimmed.** `retrieval_plan` is no longer JSON-dumped wholesale (just `intent` + account name), conversation history renders as plain `role: content` lines, and per-doc truncation runs when one doc would alone blow the token budget. ([src/pcad/llm/prompts.py](src/pcad/llm/prompts.py))
- **Lifespan + startup checks.** [src/pcad/api/app.py](src/pcad/api/app.py) gained a proper `lifespan` that asserts `EMBEDDING_DIMENSIONS` matches the live `rag_documents.embedding` column type, starts an asyncio cleanup task, and closes the LLM client + DB pool on shutdown.
- **`SessionMiddleware`** runs DB I/O through `run_in_threadpool` so the event loop never blocks on psycopg, and the 1%-sampled cleanup has been replaced with [periodic_session_cleanup](src/pcad/api/sessions.py).
- **Fake-note POST is non-blocking.** Embedding + alert regeneration run via `BackgroundTasks`; the request returns immediately. ([src/pcad/api/routes.py:create_fake_note](src/pcad/api/routes.py))
- **Standard tools.** Hand-rolled `load_dotenv` replaced with `python-dotenv`; `LOG_COLOR` is now a real `bool` end-to-end instead of stringified.
- **`record_token_usage` no longer pretends to track cost.** The always-zero `cost_estimate_eur` parameter is gone.
- **DATABASE_URL stitching.** [.env.example](.env.example) no longer duplicates the connection string; [src/pcad/config.py:_resolve_database_url](src/pcad/config.py) stitches `postgresql://USER:PASS@HOST:PORT/DB` from `POSTGRES_*` (URL-quoted) when `DATABASE_URL` is not set. [docker-compose.yml](docker-compose.yml) feeds `POSTGRES_HOST=postgres` instead of repeating the URL.
- **Artifact modal layout.** Title cluster is now reliably top-left, close button top-right. The broken `grid-template-columns: minmax(0, 1fr) auto` override is gone; `.modal-head` is `display: flex; justify-content: space-between` with a `.modal-head-text` wrapper for the icon + title. ([src/pcad/api/static/js/views/artifact_modal.js](src/pcad/api/static/js/views/artifact_modal.js), [src/pcad/api/static/css/styles.css](src/pcad/api/static/css/styles.css))
- **Synthetic PDFs are no longer mostly whitespace.** Per-section `PageBreak` is gone, `BodyPara` is justified at 10.5pt/15pt leading, and the proposal and NDA sections were expanded into multi-paragraph prose. A `proposal_2026_q2.pdf` that used to be 5 sparse pages is now 3 dense ones. ([scripts/generate_synthetic/pdfs.py](scripts/generate_synthetic/pdfs.py), [scripts/generate_synthetic/accounts.py](scripts/generate_synthetic/accounts.py))
- **Synthetic Word documents look like Word documents.** Real 28pt bold title, 13pt italic grey subtitle, a metadata line, then `Heading 1` sections (Situation / Working notes / Risks / Next steps / Demo boundary). Body text is Calibri 11pt with 1.25 line spacing. ([scripts/generate_synthetic/docx_writer.py](scripts/generate_synthetic/docx_writer.py))
- **CLI exits cleanly.** `pcad migrate` / `pcad ingest-demo` now call `close_pools()` on exit so you no longer get four 5-second psycopg-pool reaper warnings. ([src/pcad/cli.py](src/pcad/cli.py))

Explicitly deferred (still in §2 with rationale):

- **JSON-only citation contract.** Would replace the regex normalize/validate/repair stack but requires changing the streaming UX. Not worth doing inside this PR.
- **LLM-based risk and meeting extraction.** Bigger product change with its own eval needs.
- **`metadata_json` ↔ `metadata` schema unification.** The `SELECT metadata_json AS metadata` aliasing works and a column rename is a destructive migration for negligible benefit.

---

## 1. Architecture walkthrough

### 1.1 Stack at a glance

- **Web**: FastAPI + Uvicorn, SSE for streaming chat ([src/pcad/api/app.py](src/pcad/api/app.py), [src/pcad/cli.py:45](src/pcad/cli.py:45)).
- **DB**: PostgreSQL 16 + `pgvector` + `pg_trgm`. psycopg 3 with `dict_row` rows; `psycopg_pool.ConnectionPool` per database URL, cached in [src/pcad/db.py](src/pcad/db.py).
- **Models**: Pydantic v2 with `extra="forbid"` ([src/pcad/models.py](src/pcad/models.py)).
- **LLM**: `httpx.Client`-based OpenAI-compatible client with retry-with-backoff for chat completions, streaming, and embeddings ([src/pcad/llm/client.py](src/pcad/llm/client.py)).
- **Migrations**: lexical file scan + `schema_migrations` table, guarded by `pg_advisory_lock` ([src/pcad/migrations.py](src/pcad/migrations.py), [sql/migrations/](sql/migrations/)).
- **CLI**: `pcad migrate | serve | ingest-demo | bootstrap-demo` ([src/pcad/cli.py](src/pcad/cli.py)).

### 1.2 Configuration and DATABASE_URL

[src/pcad/config.py](src/pcad/config.py) loads `.env` via `python-dotenv` (existing env wins) and constructs a frozen `Settings` dataclass.

A few notes worth knowing:

- `DATABASE_URL` is optional. If absent, `_resolve_database_url` stitches `postgresql://USER:PASS@HOST:PORT/DB` from `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` / `POSTGRES_HOST` (default `localhost`) / `POSTGRES_PORT` (default `5432`). Username/password/db are URL-quoted, so passwords with `@`, `/`, `:` etc. don't break the URL.
- Docker Compose uses the stitching path too: it injects `POSTGRES_HOST=postgres` rather than repeating the connection string. ([docker-compose.yml](docker-compose.yml))
- New tunables since the first pass: `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES`, `CONVERSATION_HISTORY_TURNS`.

### 1.3 Data model and schema

Two parallel layers of data:

- **Normalized CRM** (mirrors a Salesforce-like shape): `accounts`, `contacts`, `opportunities`, `contracts`, `activities` (Task/Event), `users_or_owners`. Schema in [sql/migrations/0003_normalized_crm_tables.sql](sql/migrations/0003_normalized_crm_tables.sql); Pydantic in [src/pcad/models.py:13](src/pcad/models.py:13).
- **AI-ready documents and raw artifacts**:
  - `raw_artifacts` — extracted text + metadata per source file (PDF/DOCX/MBOX/MD) ([sql/migrations/0004_raw_artifacts.sql](sql/migrations/0004_raw_artifacts.sql)).
  - `rag_documents` — synthesized, retrievable "memory documents" with `embedding vector(1536)` and a `tsvector` generated column ([sql/migrations/0005_rag_documents.sql](sql/migrations/0005_rag_documents.sql)).
  - `source_citations` — per-doc list of upstream citation pointers ([sql/migrations/0006_source_citations.sql](sql/migrations/0006_source_citations.sql)).

Conversation/visitor data:

- `sessions` — anonymous, signed-cookie-backed ([sql/migrations/0007_conversation.sql](sql/migrations/0007_conversation.sql)).
- `conversation_threads` / `conversation_messages` — multi-turn threads scoped per session.
- `fake_notes` — visitor-added synthetic notes, session-scoped ([sql/migrations/0008_fake_notes.sql](sql/migrations/0008_fake_notes.sql); CHECK widened in [0011](sql/migrations/0011_fake_note_artifact_types.sql)).
- `proactive_alerts` — heuristic alerts cached per (account, session) ([sql/migrations/0009_proactive_alerts.sql](sql/migrations/0009_proactive_alerts.sql)).
- `daily_budget_usage` — per-day token counter for the global budget cap ([sql/migrations/0010_daily_budget_usage.sql](sql/migrations/0010_daily_budget_usage.sql)). `cost_estimate_eur` exists in the schema but is intentionally always written as `0`; cost computation belongs in an offline pricing job.

**Open files when reviewing**:

- [sql/migrations/0001_init.sql](sql/migrations/0001_init.sql) through [0011](sql/migrations/0011_fake_note_artifact_types.sql) in order.
- [src/pcad/models.py](src/pcad/models.py) end-to-end — compact, one BaseModel per table.
- [src/pcad/migrations.py](src/pcad/migrations.py) — bootstraps `schema_migrations`, then `pg_advisory_lock` + loop over `*.sql`.

### 1.4 Ingestion pipeline

Driven by `pcad ingest-demo` → [src/pcad/ingestion/runner.py:67 `run_demo_ingestion`](src/pcad/ingestion/runner.py:67).

The flow:

1. **Manifest** ([src/pcad/ingestion/manifest.py](src/pcad/ingestion/manifest.py)) — reads `data/synthetic/manifest.json` describing accounts, per-account artifacts, and CRM CSV paths.
2. **CRM parsing** ([src/pcad/ingestion/parsers/csv_crm.py](src/pcad/ingestion/parsers/csv_crm.py)) — `csv.DictReader` + Pydantic validation, including header-shape checks.
3. **Per-artifact parsing** ([src/pcad/ingestion/runner.py:156 `_parse_artifact`](src/pcad/ingestion/runner.py:156)) — routes by `format`:
   - `mbox` → [parsers/mbox.py](src/pcad/ingestion/parsers/mbox.py): `mailbox.mbox`, plain-text body extraction; produces `ParsedEmail[]`.
   - `pdf` → [parsers/pdf.py](src/pcad/ingestion/parsers/pdf.py): `pypdf` text-layer extraction. Pages with fewer than `PAGE_TEXT_MIN_CHARS = 40` chars are individually rasterized via `pdf2image` and OCR'd with Tesseract; the rest keep the text-layer output. `ocr_page_indices` carries the list. Rendered PNGs are saved under `data/rendered/<artifact_id>/page_N.png` for UI display.
   - `docx` → [parsers/docx.py](src/pcad/ingestion/parsers/docx.py): `python-docx`, heading style prefixes.
   - `markdown` → [parsers/meeting_md.py](src/pcad/ingestion/parsers/meeting_md.py): speaker-labeled transcript parser.
4. **Normalization** ([src/pcad/ingestion/normalize.py](src/pcad/ingestion/normalize.py)):
   - Emails → threads via `References[0]` or `In-Reply-To` ([normalize.py:42 `normalize_email_threads`](src/pcad/ingestion/normalize.py:42)).
   - Meetings → topic/action/risk bullets via casefold keyword matching ([normalize.py:63 `normalize_meeting_for_summary`](src/pcad/ingestion/normalize.py:63)), with `source_artifact_id` threaded through.
5. **AI-ready document construction** ([src/pcad/ingestion/ai_ready_documents.py `DocumentBuilder`](src/pcad/ingestion/ai_ready_documents.py:51)): for each account it builds typed markdown documents (`account_memory`, `recent_activity_timeline`, `stakeholder_map`, `risk_summary`, one `email_thread_summary` per thread, one `meeting_summary` per meeting; plus `opportunity_snapshot` per opp and `contract_snapshot` per contract). Each doc carries `SourceCitation` rows in `Object Id` shape, and `source_record_hashes` now contains one hash per record.
6. **Persistence** ([runner.py:108](src/pcad/ingestion/runner.py:108)) — one transaction: optional TRUNCATE, then `executemany` inserts into CRM tables → raw_artifacts → rag_documents → source_citations.
7. **Embeddings** ([src/pcad/ingestion/embeddings.py `index_pending_embeddings`](src/pcad/ingestion/embeddings.py:17)) — selects rows with `embedding IS NULL`, batches of 32, calls `/embeddings`. Transient HTTP failures are retried inside the httpx client.
8. **Proactive alerts** ([src/pcad/retrieval/alerts.py `ProactiveAlertGenerator`](src/pcad/retrieval/alerts.py:12)) — deterministic SQL queries per account; deletes and re-inserts the (account, session) row group every time.

**Synthetic corpus generator** ([scripts/generate_synthetic/](scripts/generate_synthetic/)):

- PDFs are dense, justified prose without forced section breaks ([pdfs.py](scripts/generate_synthetic/pdfs.py)).
- Word documents have a styled cover (28pt bold title + 13pt italic subtitle + small grey meta line) and `Heading 1`-styled sections ([docx_writer.py](scripts/generate_synthetic/docx_writer.py)).
- Section copy lives in [scripts/generate_synthetic/accounts.py](scripts/generate_synthetic/accounts.py).

**Open files when reviewing**:

- [src/pcad/ingestion/runner.py](src/pcad/ingestion/runner.py) — start here, follow `run_demo_ingestion` top to bottom.
- [src/pcad/ingestion/ai_ready_documents.py](src/pcad/ingestion/ai_ready_documents.py) — long but mechanical; pay attention to the citation-label format.
- [src/pcad/retrieval/alerts.py](src/pcad/retrieval/alerts.py) — all six alert types are pure SQL + dataclass mapping.

### 1.5 Retrieval

Entry point: [src/pcad/retrieval/retriever.py `PostgresHybridRetriever`](src/pcad/retrieval/retriever.py:64).

Flow when the agent needs context for a query:

1. **Intent resolution** ([src/pcad/retrieval/intent.py `IntentResolver.resolve`](src/pcad/retrieval/intent.py:123)):
   - First a heuristic over `INTENT_KEYWORDS` produces an `(intent, confidence)`.
   - If `confidence < 0.85` and an LLM is configured, calls `complete(...)` with a strict-JSON-schema `response_format` to refine. Falls back to heuristic on any failure.
   - Output: `IntentResult` with `intent`, `doc_types`, `account_hint`, and three booleans.
2. **Account resolution** ([retriever.py:resolve_account](src/pcad/retrieval/retriever.py)):
   - Single-CTE query that computes `method` (`intent_account_hint` / `name_in_query` / `fuzzy_trigram`) and `score` per row, then filters by method or threshold. Same matching semantics as before (`pg_trgm`'s `similarity` + `strict_word_similarity`, exact case-insensitive match, substring in query) but only one parameter set.
   - Picks the top-scoring candidate if it dominates by `> ACCOUNT_AMBIGUITY_DELTA (0.08)`, otherwise raises `AccountResolutionError` with structured candidates so the agent can ask a clarifying question.
3. **Retrieval plan** ([retriever.py:build_retrieval_plan](src/pcad/retrieval/retriever.py)) — packages query, account, doc_types, session, limit into a `RetrievalPlan` dataclass.
4. **Three rankers**:
   - **Base context** ([retriever.py:fetch_base_context](src/pcad/retrieval/retriever.py)) — always pulls up to 3 docs of type `account_memory` and `recent_activity_timeline`.
   - **Full-text** ([retriever.py:full_text_search](src/pcad/retrieval/retriever.py)) — `websearch_to_tsquery('english', …)` against the generated `search_vector` column, ranked by `ts_rank_cd`.
   - **Vector** ([retriever.py:vector_search](src/pcad/retrieval/retriever.py)) — pgvector cosine distance against an embedded `query_instruction(query)` string.
   Both apply account scope, session scope (visitor fake notes), and `doc_type = ANY(intent.doc_types)`.
5. **RRF merge + doc-type boost** ([retriever.py:`_rrf_merge`](src/pcad/retrieval/retriever.py) and [`_rank_hybrid_results`](src/pcad/retrieval/retriever.py)) — classic reciprocal-rank fusion `1/(60+rank)`, summed across rankers, plus a static `DOC_TYPE_BOOSTS` table.
6. **Context pack** ([retriever.py:build_context_pack](src/pcad/retrieval/retriever.py)) — assembles `user_request`, `retrieval_plan`, `conversation_history`, and `retrieved_documents` (each with up to 5 citations) into the dict the prompt builder consumes.

The dead `fetch_documents_by_ids` and `account_candidates` methods have been removed.

### 1.6 Agent / conversation service

[src/pcad/agent/conversation_service.py `ConversationService`](src/pcad/agent/conversation_service.py:53).

This is *not* a LangGraph agent — it's a single linear pipeline with citation-retry inside. The order of operations for a streaming user message:

1. Trim text, enforce per-session message-per-hour rate limit ([send_message_stream:122](src/pcad/agent/conversation_service.py:122)).
2. Load the thread; remember the previous account stickiness ([:135](src/pcad/agent/conversation_service.py:135)).
3. **Workflow seed expansion** — if the thread was created with a `workflow_seed` like `call_briefing` and this is the first user message, replace the visible label with the canned prompt from `WORKFLOW_SEEDS` ([:29](src/pcad/agent/conversation_service.py:29)).
4. Insert the user message; SSE `user_message`.
5. **Daily budget check** ([:148](src/pcad/agent/conversation_service.py:148)) — runs **before** any LLM call. If the daily budget is blown, the canned `BUDGET_MESSAGE` is streamed and the request stops. This is the only path that avoids spending tokens once over budget.
6. SSE `thinking`.
7. **Clarification continuation** — if the last assistant message was an `account_clarification`, treat this user message as the answer (match against stored candidates) and re-run the original request.
8. **Prepare pipeline** ([_prepare_pipeline:220](src/pcad/agent/conversation_service.py:220)) — intent → account resolution (with stickiness fallback) → retrieval plan → base context + hybrid search → context pack.
9. **Render context prompt + stream** — calls `llm_client.complete_stream`, yielding `token` SSE events.
10. **Citation finalization** ([_finalize_answer_text](src/pcad/agent/conversation_service.py)):
    - `normalize_citation_format` repairs `[[Source: …]]`, `(Source: …)`, `Source: …` shapes.
    - `validate_citations` checks the answer cites at least one label and only labels present in the pack.
    - If invalid, retries up to `AGENT_GENERATION_MAX_ATTEMPTS` (default 3) via *non-streaming* `complete`.
    - If still invalid, `repair_missing_citations` heuristically appends a `[Source: …]` tag to known labels appearing in the text. When the hard fallback fires (appending `"Sources consulted: see panel on the right. [Source: X]"`), the path is logged at `WARNING` with the allowed and unknown label sets.
11. Token usage from `client.last_usage` is added to `daily_budget_usage` ([:215](src/pcad/agent/conversation_service.py:215)).
12. Stream `replace` event with the finalized text (if it differs from the streamed text), persist the assistant message, update the thread title, emit `done`.

History context to the LLM is now `CONVERSATION_HISTORY_TURNS`-bounded plain text (not JSON), and the prompt passes only `intent` + `account_name` from the retrieval plan instead of the whole dataclass.

### 1.7 LLM client

[src/pcad/llm/client.py `OpenAICompatibleClient`](src/pcad/llm/client.py).

- `httpx.Client` with a configurable timeout and a persistent connection.
- `_post_json` retries on transport errors and on `{408, 425, 429, 500, 502, 503, 504}` with exponential backoff + jitter; honors `Retry-After` when sane.
- Streaming completions use `client.stream("POST", …)` and parse the OpenAI SSE wire format.
- `embed`, `embed_batch`, `complete` share the same retry path.
- `last_usage` is recorded on every chat response (and on streaming chunks that include `usage`).
- `close()` releases the underlying connection; the FastAPI lifespan calls it on shutdown.

Deterministic test double at [src/pcad/llm/deterministic.py](src/pcad/llm/deterministic.py).

### 1.8 API surface

[src/pcad/api/app.py `create_app`](src/pcad/api/app.py:23) wires:

- `lifespan`: asserts `EMBEDDING_DIMENSIONS` matches the live `rag_documents.embedding` column type, starts an asyncio `periodic_session_cleanup` task, and on shutdown cancels the task, closes the LLM client, and closes all DB pools.
- `SessionMiddleware` ([src/pcad/api/sessions.py](src/pcad/api/sessions.py)) — signed cookie via `itsdangerous`, server-side row in `sessions`. DB work runs through `run_in_threadpool` so the event loop never blocks.
- A custom `http` middleware for per-IP rate limiting on non-GET `/api/` calls ([app.py](src/pcad/api/app.py)).
- Static mounts for `/static` and `/rendered` (PDF page PNGs).

Routes ([src/pcad/api/routes.py](src/pcad/api/routes.py)):

| Endpoint | Notes |
|---|---|
| `GET /api/health` | trivial |
| `GET /api/session` | echoes current session |
| `GET /api/accounts` | list + per-session alert counts |
| `GET /api/accounts/{id}` | detail + contacts/opps/contracts |
| `GET /api/accounts/{id}/artifacts` | real + virtual fake-note artifacts |
| `GET /api/accounts/{id}/alerts` | session-scoped alerts |
| `GET /api/artifacts/{id}` | real or `crm:Object:id` virtual artifact |
| `GET /api/artifacts/{id}/page/{n}` | rendered PDF page PNG |
| `GET/POST /api/threads`, `GET /api/threads/{id}` | thread CRUD subset |
| `GET /api/threads/{id}/messages` | history |
| `POST /api/threads/{id}/messages/stream` | **SSE chat endpoint** |
| `POST/GET /api/accounts/{id}/fake-notes`, `DELETE /api/fake-notes/{id}` | session-scoped synthetic notes |

The fake-note `POST` inserts the row + the session-scoped `rag_documents` and `source_citations` rows synchronously, then dispatches `_finalize_fake_note` (embedding indexer + alert regeneration) to `BackgroundTasks` so the request returns promptly. The `alerts` field of the response is initially empty; the client refetches `/accounts/{id}/alerts` to see the updated set.

### 1.9 Rate limiting & budget

[src/pcad/api/rate_limit.py](src/pcad/api/rate_limit.py).

- **Per-IP** and **per-session** token-bucket limiters held in process memory (`threading.Lock` + dict). Single-worker only.
- Both buckets cap at `MAX_BUCKETS = 10_000` with stale-eviction at `4 * window_seconds`.
- **Daily budget**: `check_daily_budget` reads `daily_budget_usage`; `record_token_usage` upserts after each LLM call. The schema's `cost_estimate_eur` column is stable, but is always written as `0`.

### 1.10 What I'd open in what order

1. [src/pcad/models.py](src/pcad/models.py) — get the type vocabulary in your head.
2. [sql/migrations/0003](sql/migrations/0003_normalized_crm_tables.sql) through [0006](sql/migrations/0006_source_citations.sql), [0007](sql/migrations/0007_conversation.sql), [0009](sql/migrations/0009_proactive_alerts.sql) — the schema your queries run against.
3. [src/pcad/ingestion/runner.py](src/pcad/ingestion/runner.py) — top-down through one ingestion.
4. [src/pcad/ingestion/ai_ready_documents.py](src/pcad/ingestion/ai_ready_documents.py) — `build_all` and one of the builder methods.
5. [src/pcad/retrieval/intent.py](src/pcad/retrieval/intent.py).
6. [src/pcad/retrieval/retriever.py](src/pcad/retrieval/retriever.py).
7. [src/pcad/llm/prompts.py](src/pcad/llm/prompts.py), then [src/pcad/llm/citations.py](src/pcad/llm/citations.py).
8. [src/pcad/agent/conversation_service.py](src/pcad/agent/conversation_service.py) — `send_message_stream` reads cleanly when you already understand the layers below.
9. [src/pcad/api/app.py](src/pcad/api/app.py), then [src/pcad/api/routes.py](src/pcad/api/routes.py) — last, since by now it's all glue.

---

## 2. Red flags and resolution log

Each item carries one of three states:

- `[FIXED]` — landed on this branch, with the fix and the file it's in.
- `[KEPT]` — explicitly decided not to fix; the rationale follows.
- `[DEFERRED]` — worth doing but big enough to deserve its own PR; not part of this pass.

Severity tags from the original review (`[H]`, `[M]`, `[L]`) are preserved for context.

### 2.1 Reinventing standard tools

- **[M] [FIXED] `load_dotenv` is hand-rolled** — replaced with `python-dotenv` (`load_dotenv(..., override=False)`). Existing env vars still win. ([src/pcad/config.py](src/pcad/config.py))
- **[H] [FIXED] LLM client uses `urllib.request`** — rebuilt on `httpx.Client` with persistent connection, configurable timeout, retry-with-backoff on transport errors and 408/425/429/5xx, `Retry-After` honoring, and explicit `close()` called from the FastAPI lifespan. ([src/pcad/llm/client.py](src/pcad/llm/client.py))
- **[M] [KEPT] Custom token-bucket rate limiter.** Stays in process. The single-worker constraint is documented; moving to Redis or `slowapi` is overkill for the public demo. Worth revisiting if the deployment ever scales horizontally.
- **[M] [FIXED] No DB connection pool.** `psycopg_pool.ConnectionPool` is now cached per database URL inside [src/pcad/db.py](src/pcad/db.py); `connect` and `connect_dict` are context-manager wrappers around the pool. Migrations and tests still use a raw connection via `raw_connect` (the pool must not run before extensions exist).
- **[L] [KEPT] Manual SSE framing.** It works. `sse-starlette` would add a dependency for marginal gain.

### 2.2 Correctness bugs

- **[H] [FIXED] Daily budget check happens after the intent LLM call.** Budget gate moved to the top of `send_message_stream`, before `_prepare_pipeline` (which calls the intent classifier). An over-budget request now spends zero tokens. ([src/pcad/agent/conversation_service.py:144](src/pcad/agent/conversation_service.py:144))
- **[H] [FIXED] Migration runner double-executes `0001_init.sql`.** The bootstrap step now creates only `schema_migrations` (as a literal `CREATE TABLE IF NOT EXISTS`), and the migration loop applies every `*.sql` exactly once. ([src/pcad/migrations.py](src/pcad/migrations.py))
- **[H] [FIXED] No migration locking.** The runner wraps the whole pass in `pg_advisory_lock(0x70636164)` / `pg_advisory_unlock`. Concurrent CLI + app starts now serialize. ([src/pcad/migrations.py](src/pcad/migrations.py))
- **[H] [FIXED] `_virtual_crm_artifact` references a non-existent column.** The `account_id_if_available` fallback for contracts is gone. ([src/pcad/api/routes.py](src/pcad/api/routes.py))
- **[H] [FIXED] `parse_pdf` OCR threshold is whole-document.** Now per-page: each page below `PAGE_TEXT_MIN_CHARS = 40` is rasterized individually and OCR'd, the rest keep the text-layer extraction. `ParsedPdf.ocr_page_indices` exposes the list for downstream uses. ([src/pcad/ingestion/parsers/pdf.py](src/pcad/ingestion/parsers/pdf.py))
- **[H] [FIXED] `source_record_hashes` is a single hash of joined IDs.** Now one hash per source record, matching the field name. ([src/pcad/ingestion/ai_ready_documents.py](src/pcad/ingestion/ai_ready_documents.py))
- **[M] [KEPT] CHECK constraint mismatch on `fake_notes`.** Migration 0011 already widens the CHECK to include both name sets, and the runtime path is unambiguous; consolidating would require a destructive migration plus a coordinated frontend change for no user-visible win.
- **[M] [KEPT] Field name inconsistency `metadata_json` vs `metadata`.** The `SELECT metadata_json AS metadata` aliasing in conversation queries works and is local to a couple of SQL strings. A column rename would be a destructive migration touching both the schema and the frontend payloads. Net negative.
- **[M] [FIXED] Dead `MeetingSummaryInput` rebuild in `_parse_meeting_artifact`.** Removed. `normalize_meeting_for_summary` now takes `source_artifact_id` directly. ([src/pcad/ingestion/runner.py](src/pcad/ingestion/runner.py), [src/pcad/ingestion/normalize.py](src/pcad/ingestion/normalize.py))
- **[M] [FIXED] Dead `fetch_documents_by_ids` and `account_candidates`.** Removed. ([src/pcad/retrieval/retriever.py](src/pcad/retrieval/retriever.py))
- **[M] [FIXED] `cleanup_expired_sessions` runs at 1% of requests.** Replaced with `periodic_session_cleanup`, an asyncio task started from the FastAPI lifespan; it sleeps ~1 hour between cleanups and logs the deletion count. ([src/pcad/api/sessions.py](src/pcad/api/sessions.py), [src/pcad/api/app.py](src/pcad/api/app.py))
- **[L] [FIXED] `_serialize_artifact_row` mutates input.** Now returns a new dict. ([src/pcad/api/routes.py](src/pcad/api/routes.py))
- **[L] [FIXED] `embedding_dimensions=1536` hard-coded.** The lifespan startup hook queries `format_type(atttypid, atttypmod)` on `rag_documents.embedding` and raises `RuntimeError` if the column dimension and `EMBEDDING_DIMENSIONS` disagree. ([src/pcad/api/app.py:_assert_embedding_dimensions](src/pcad/api/app.py))

### 2.3 Things done too manually that have standard solutions

- **[H] [DEFERRED] Citation validation, normalization, and repair are bespoke regex.** Switching to a JSON output contract (`{text, citations}`) would replace the whole regex stack but would also kill token-by-token streaming UX. The trade-off is real enough to deserve its own PR with a frontend design review. Partial mitigation already landed: the hard-fallback path now logs at `WARNING` so silent degraded answers are visible in logs. ([src/pcad/llm/citations.py](src/pcad/llm/citations.py))
- **[M] [KEPT] Hybrid fusion with hardcoded RRF + doc-type boost.** The boosts are still magic numbers but they are explicit and small; introducing a re-ranker (cross-encoder or LLM-as-judge) was scoped out of this pass.
- **[M] [DEFERRED] Keyword/heuristic intent classifier.** Still in place. Acceptable for the demo because the strict-JSON LLM path catches the low-confidence cases; replacing the heuristic with a small eval-driven training set is out of scope here.
- **[M] [DEFERRED] Risk extraction is regex sentence-grep.** Real fix is an LLM extraction pass at ingestion time. Big enough to deserve its own evaluation; explicitly out of scope.
- **[M] [DEFERRED] Meeting topic/action/risk extraction is keyword-based.** Same story.
- **[L] [KEPT] Sentence split via `re.split(r"(?<=[.!?])\s+")`.** Demo-grade. Not worth pulling in `nltk` / `spaCy` for one regex.
- **[M] [FIXED] `resolve_account` SQL repeats the same clause four times.** Rewritten as a single CTE with one parameter set per match path. Same matching semantics. ([src/pcad/retrieval/retriever.py:resolve_account](src/pcad/retrieval/retriever.py))

### 2.4 Architectural concerns

- **[M] [FIXED] Sync psycopg from FastAPI.** `SessionMiddleware.dispatch` now runs `_load_or_create` through `run_in_threadpool`. Route handlers remain `def` so Starlette still threadpools them. ([src/pcad/api/sessions.py](src/pcad/api/sessions.py))
- **[M] [FIXED] `POST /api/accounts/{id}/fake-notes` does too much synchronously.** Embedding indexing + alert regeneration are dispatched to `BackgroundTasks`; the request returns immediately. Failures are logged. ([src/pcad/api/routes.py:create_fake_note](src/pcad/api/routes.py))
- **[M] [DEFERRED] `replace` SSE event after streaming.** Same JSON-output rework as the citation contract.
- **[M] [FIXED] `render_context_prompt` admits one oversized doc unconditionally.** Now per-doc truncation: if a doc alone exceeds the remaining budget, its `content` is trimmed (preserving label, score, citations) down to a per-doc minimum, with a `... [truncated]` marker. Docs below the per-doc minimum are dropped and listed under `Documents omitted because of token budget`. ([src/pcad/llm/prompts.py](src/pcad/llm/prompts.py))
- **[M] [FIXED] `retrieval_plan` is JSON-dumped into the prompt.** Replaced with a one-line `Retrieval focus: intent=…, account=…` hint. ([src/pcad/llm/prompts.py](src/pcad/llm/prompts.py))
- **[L] [FIXED] Conversation history sent as `json.dumps(history, indent=2)`.** Now rendered as plain `role: content` lines. ([src/pcad/llm/prompts.py](src/pcad/llm/prompts.py))
- **[L] [FIXED] `_recent_history` returns 6 raw rows.** Configurable via `CONVERSATION_HISTORY_TURNS` (default 6). ([src/pcad/agent/conversation_service.py](src/pcad/agent/conversation_service.py), [src/pcad/config.py](src/pcad/config.py))
- **[L] [KEPT] CRM and rag_documents inserts use positional `executemany`.** Refactoring to named placeholders is purely cosmetic and would touch a lot of lines. Left for a future cleanup.

### 2.5 Operational gaps

- **[M] [FIXED] No structured error logging on retry exhaustion.** `repair_missing_citations` now logs at `WARNING` with both the unknown labels and the allowed-label count when the hard fallback fires, and again when there is no fallback available. ([src/pcad/llm/citations.py](src/pcad/llm/citations.py))
- **[M] [FIXED] Embedding indexer doesn't retry on 429.** Inherits the httpx client's retry-with-backoff path automatically — no separate retry logic needed in the indexer. ([src/pcad/llm/client.py](src/pcad/llm/client.py))
- **[M] [FIXED] Cost tracking is tokens only.** `record_token_usage` no longer takes a `cost_estimate_eur` argument; the schema column stays for backward compatibility, written as `0`. A proper price-aware tracker belongs in an offline job. ([src/pcad/api/rate_limit.py](src/pcad/api/rate_limit.py))
- **[L] [FIXED] `LOG_COLOR` round-trips through a string.** `configure_logging` accepts `bool | str | None`; CLI and migrations pass the bool directly. ([src/pcad/logging_utils.py](src/pcad/logging_utils.py), [src/pcad/cli.py](src/pcad/cli.py), [src/pcad/migrations.py](src/pcad/migrations.py))

### 2.6 Frontend / synthetic-corpus follow-ups

These were flagged later and landed in the same pass:

- **[M] [FIXED] Artifact modal layout — title and X were on the wrong sides.** `.modal-head` is now `display: flex; justify-content: space-between` with a `.modal-head-text` wrapper for the icon + title cluster. The earlier broken `grid-template-columns: minmax(0, 1fr) auto` override is gone. ([src/pcad/api/static/js/views/artifact_modal.js](src/pcad/api/static/js/views/artifact_modal.js), [src/pcad/api/static/css/styles.css](src/pcad/api/static/css/styles.css))
- **[M] [FIXED] Synthetic PDFs were mostly whitespace.** Forced per-section page breaks removed; section prose expanded; body style is now justified at 10.5pt with 15pt leading; headings use `KeepTogether` with their first paragraph to avoid widow lines. Result: `proposal_2026_q2.pdf` went from 5 sparse pages to 3 dense ones. ([scripts/generate_synthetic/pdfs.py](scripts/generate_synthetic/pdfs.py), [scripts/generate_synthetic/accounts.py](scripts/generate_synthetic/accounts.py))
- **[M] [FIXED] Word documents looked unstyled.** The generator now writes a styled cover (28pt bold dark-navy title, 13pt italic grey subtitle, 10pt grey metadata line), then `Heading 1` sections (`Situation`, `Working notes` with `List Bullet`, `Risks and dependencies`, `Next steps`, `Demo boundary`). Body style retuned to Calibri 11pt with 1.25 line spacing. Parser still extracts the right markdown (`# Situation`, etc.). ([scripts/generate_synthetic/docx_writer.py](scripts/generate_synthetic/docx_writer.py))

### 2.7 Operational ergonomics added on top

Not in the original review but landed in the same pass for the same "demo should feel finished" reason:

- **`DATABASE_URL` stitching.** `.env.example` stops duplicating the connection string; the app builds it from `POSTGRES_*` when `DATABASE_URL` is unset. URL-quotes the user/password/db parts. Docker Compose feeds `POSTGRES_HOST=postgres` instead of repeating the URL. ([src/pcad/config.py:_resolve_database_url](src/pcad/config.py), [.env.example](.env.example), [docker-compose.yml](docker-compose.yml))
- **CLI exits cleanly.** `pcad migrate` and `pcad ingest-demo` wrap their work in `try/finally close_pools()` so the psycopg-pool reaper doesn't print four 5-second warnings on every CLI run. ([src/pcad/cli.py](src/pcad/cli.py))

---

## 3. What to look at next

If you want to keep landing improvements in priority order:

1. **Citation JSON contract.** The biggest open item. Replaces the regex normalize/validate/repair stack with `{text, citations}` JSON output and removes the streamed-then-replaced UX. Needs a coordinated frontend change.
2. **LLM-driven risk and meeting extraction at ingest time.** Highest-leverage on demo quality. Needs an eval harness so we can compare to the current keyword pass.
3. **Schema cleanups** — `metadata_json` rename, `cost_estimate_eur` drop, `fake_notes.note_type` CHECK consolidation. Bundle them into one destructive-migration PR with a release note.
4. **Replace the in-process rate limiter** if the demo ever runs more than one Uvicorn worker. Until then, the single-worker assumption is documented and fine.
