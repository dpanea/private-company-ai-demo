# Architecture

The Company Knowledge AI is a public, anonymous demo of a private,
source-backed AI assistant over company knowledge. This document walks
through the layers from raw artifacts to streaming answers, and notes the
intentional limits of the demo.

```
synthetic artifacts ──► parsers ──► AI-ready documents ──► Postgres + pgvector
                                                              │
                                                              ▼
                              hybrid retrieval (BM25 + vector, RRF-merged)
                                                              │
                                                              ▼
                          conversation service (intent → context pack → LLM)
                                                              │
                                                              ▼
                              streaming structured JSON ──► UI (citations)
```

## Layers

### 1. Synthetic corpus (`scripts/generate_synthetic/`)

A self-contained generator that produces the input artifacts the demo
ingests: emails (mbox), PDFs (some text-layer, some scanned), Word docs,
meeting transcripts (Markdown), and a CRM-style CSV. The output is a
`data/synthetic/` tree plus a `manifest.json` describing what to ingest.

All content is fictional. There are no real customers, no real
correspondence, and no API keys.

### 2. Ingestion (`src/company_ai/ingestion/`)

Reads the manifest, dispatches to one of five format-specific parsers
(`mbox`, `pdf`, `docx`, `meeting_md`, `csv_crm`), and turns every artifact
into a `RawArtifact` row plus one or more `RagDocument` "source artifact
chunks" — Markdown-normalized excerpts annotated with the citation that
points back to the originating record.

Scanned PDFs without a text layer go through Tesseract OCR; everything
else extracts text directly. Embeddings are computed in batches against
the configured OpenAI-compatible endpoint and stored in pgvector.

### 3. Storage (`sql/init.sql`)

A single Postgres schema:

- `users_or_owners`, `accounts` — minimal CRM surface used by the demo UI.
- `raw_artifacts` — one row per ingested artifact, with the extracted text
  and per-format metadata.
- `rag_documents` — one row per retrievable chunk, with FTS vector
  (`tsvector`) and pgvector embedding.
- `source_citations` — every chunk's pointers back to its origin
  (`source_object`, `source_record_id`, excerpt, title, date).
- `sessions`, `conversation_threads`, `conversation_messages` — anonymous
  session state and chat history.
- `demo_notes` — visitor-added session-scoped notes (so the demo can show
  the system reacting to new information without persisting state across
  visitors).
- `daily_budget_usage` — token-spend ledger used by the budget gate.

### 4. Retrieval (`src/company_ai/retrieval/`)

`PostgresHybridRetriever` runs three rankers and merges them with
Reciprocal Rank Fusion:

- a small *base context* (most recently updated chunks for the active account),
- *full-text search* over `to_tsvector('english', …)`,
- *vector search* over pgvector cosine similarity.

`IntentResolver` classifies the user request into a small set of intents
(briefing, follow-up, decision lookup, etc.). When the intent requires an
account, the retriever resolves one — first against an explicit
`account_id`, then against fuzzy account-name matching with a confidence
threshold and ambiguity check. Unresolved or ambiguous matches surface a
clarification request rather than guessing.

### 5. Conversation (`src/company_ai/agent/`)

`ConversationService` orchestrates one streaming response:

1. Persist the user message and snapshot recent history.
2. Resolve intent and account (or branch to clarification).
3. Build a retrieval plan, fetch base + hybrid context, and pack it.
4. Render a context prompt fitted to a token budget.
5. Stream a structured-JSON answer from the LLM.
6. Parse the JSON, validate every cited label against the allowed
   citation list from the pack, and fall back to "insufficient evidence"
   if the model hallucinates.
7. Emit SSE events (`user_message`, `status`, `token`, `replace`, `done`,
   `error`) so the UI can show progress and final citations.

The streaming parser in `llm/streaming.py` extracts visible text out of
the JSON as it lands, so users see characters appear in real time while
the citation validator still runs against the final payload.

### 6. API (`src/company_ai/api/`)

A FastAPI app with anonymous signed-cookie sessions
(`SessionMiddleware`), an in-process token-bucket rate limiter, and a
daily token-budget gate. Routes:

- `GET /api/accounts`, `GET /api/accounts/{id}`, `GET /api/accounts/{id}/artifacts`
- `GET /api/artifacts/{id}`, `GET /api/artifacts/{id}/page/{n}`
- `GET/POST /api/threads`, `GET /api/threads/{id}/messages`
- `POST /api/threads/{id}/messages/stream` — SSE chat stream
- `GET/POST/DELETE /api/accounts/{id}/demo-notes` — visitor-added notes
- `GET /api/session`, `DELETE /api/session`

`/` serves the marketing landing page; `/demo` serves the demo SPA.

### 7. Frontend (`src/company_ai/api/static/`)

Vanilla HTML/CSS/JS. A tiny pub-sub store (`state.js`), a hash router, and
view modules that render markup from state and bind events. Streaming
responses are read off a `fetch` ReadableStream and dispatched as SSE
events to the conversation panel, which buffers tokens with
`requestAnimationFrame` so high-volume token streams don't trigger a
re-render per character.

The UI namespaces its DOM hooks with `data-app-*` so the internal
identifiers don't collide with anything else.

## Deployment

- Local: `docker compose up -d postgres`, then `uv run company-ai migrate`,
  `uv run company-ai ingest-demo --clean`, `uv run company-ai serve`.
- Public demo: a single Hetzner VPS with Docker Compose, Caddy in front
  for HTTPS and IP-level rate limiting (see [`deploy/caddy/`](../deploy/caddy/)).
- Sovereign option: a parallel compose under [`deploy/vllm/`](../deploy/vllm/)
  swaps the hosted LLM for a local vLLM container with the same
  OpenAI-compatible client.

## Demo scope vs. production scope

This repo deliberately leaves out everything that turns a demo into a
product:

- Production connectors and incremental sync.
- Per-user permissions, auth, multi-tenant isolation.
- Real OCR pipelines for arbitrary scanned documents.
- Email-thread reconstruction beyond `In-Reply-To` / `References`.
- Schema evolution against live data.
- Evaluation suites, gold-question sets, hallucination measurement.
- Audit logging, retention, dead-letter queues, backups, runbooks.

Those are real engagement concerns — this repo shows the *shape* of the
core system without pretending to be the whole thing.
