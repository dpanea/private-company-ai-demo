# 00 — Implementation overview and orchestration

This document is the **management view** of the implementation effort. It defines the package dependency graph, what can run in parallel, what must block, and what each package owns end-to-end. Read this before assigning work to coding agents.

The detailed per-package specs are in:

- [01-package-skeleton-and-core.md](01-package-skeleton-and-core.md)
- [02-package-synthetic-corpus.md](02-package-synthetic-corpus.md)
- [03-package-ingestion.md](03-package-ingestion.md)
- [04-package-retrieval-agent-api.md](04-package-retrieval-agent-api.md)
- [05-package-frontend.md](05-package-frontend.md)
- [06-package-deployment-landing.md](06-package-deployment-landing.md)
- [bug-fixes-uniendo-nodos.md](bug-fixes-uniendo-nodos.md) — separate backport task to the related repo

## Goal in one paragraph

Ship a public web demo at `demo.danielpanea.com` (or equivalent subdomain on `danielpanea.com`) that takes messy synthetic company artifacts (emails, PDFs, meeting transcripts, Word docs, CRM CSVs), runs them through a documented ingestion + retrieval + LLM pipeline, and answers user questions through guided workflows and a free-text box with citations and proactive alerts. The repository is fully open-source under Apache-2.0, with documented "production scope" boundaries. Backend code reuses ~80% of the patterns from `~/projects/uniendo-nodos-private-ai`.

## Package dependency graph

```text
                              ┌────────────────────────────────┐
                              │  1. Skeleton & core            │
                              │  pyproject, src/, schema, models│
                              │  settings, logging, db helpers │
                              └───────────┬────────────────────┘
                                          │
                ┌─────────────────────────┼─────────────────────────┐
                │                         │                         │
                ▼                         ▼                         ▼
   ┌────────────────────┐   ┌─────────────────────┐   ┌──────────────────────┐
   │ 2. Synthetic corpus│   │ 3. Ingestion        │   │ 5. Frontend          │
   │ Generate messy raw │   │ Parsers, AI-ready   │   │ Vanilla HTML/CSS/JS  │
   │ artifacts in       │   │ doc builder,        │   │ wired to mock API    │
   │ data/synthetic/    │   │ embedding indexer   │   │ then real API        │
   └─────────┬──────────┘   └──────────┬──────────┘   └──────────┬───────────┘
             │                         │                         │
             └──────────┬──────────────┘                         │
                        ▼                                        │
            ┌───────────────────────────┐                        │
            │ 4. Retrieval, agent, API  │                        │
            │ Hybrid retrieval, RRF,    │                        │
            │ ConversationService,      │                        │
            │ alerts, FastAPI endpoints,│                        │
            │ rate limiting             │                        │
            └─────────────┬─────────────┘                        │
                          │                                      │
                          └──────────────┬───────────────────────┘
                                         ▼
                              ┌─────────────────────┐
                              │ 6. Deployment &     │
                              │    landing          │
                              │ docker-compose,     │
                              │ vLLM compose,       │
                              │ Caddy, landing page │
                              └─────────────────────┘
```

## What blocks what

| Package | Hard dependencies (must finish first) | Soft dependencies (can run in parallel with mock) |
|---------|---------------------------------------|---------------------------------------------------|
| 1 Skeleton & core | — | — |
| 2 Synthetic corpus | 1 (for Pydantic models) | — |
| 3 Ingestion | 1, 2 | — |
| 4 Retrieval, agent, API | 1, 3 | 2 (only needs the corpus to be loadable, which 3 handles) |
| 5 Frontend | 1 (for API contract definitions) | 4 (frontend can be built against a JSON mock first) |
| 6 Deployment & landing | 4, 5 | — |
| Uniendo Nodos backport | Independent — different repo | — |

## Recommended scheduling (single agent, sequential)

If you run one agent at a time, do them in numerical order. Package 4 is the largest; budget the most time there.

## Recommended scheduling (multiple agents in parallel)

This is the parallel plan that matches what Daniel typically does — multiple coding agents working concurrently.

### Wave 0 — independent immediately

These have no dependencies on this repo's other packages:

- **Uniendo Nodos backport** ([bug-fixes-uniendo-nodos.md](bug-fixes-uniendo-nodos.md)) — runs in `~/projects/uniendo-nodos-private-ai`, completely independent.

### Wave 1 — must run first

- **Package 1 — Skeleton & core** runs alone. It produces the Pydantic models, SQL schema, and project layout that every other package imports. Nothing else can start in this repo until this is merged. Target: small package, fast.

### Wave 2 — parallel after Package 1

Once Package 1 is merged, the following can run in parallel with each other:

- **Package 2 — Synthetic corpus** (produces files on disk, no API surface).
- **Package 3 — Ingestion** (can begin against the Package-1 models; will integrate with Package 2's output when ready). Ingestion can be developed using a tiny inline test fixture and switched to the Package-2 corpus once it lands.
- **Package 5 — Frontend** (can be developed against a JSON mock of the Package-4 API contract documented in [04-package-retrieval-agent-api.md](04-package-retrieval-agent-api.md). The API contract is stable from the start, so the frontend agent does not need to wait for backend implementation).

### Wave 3 — after 2 and 3

- **Package 4 — Retrieval, agent, API** depends on Package 1 (schema, models) and Package 3 (so there's a populated DB to retrieve from). Can also import Package 2 output during integration testing.

### Wave 4 — final integration

- **Package 6 — Deployment & landing** depends on having a working app (Packages 4 and 5 integrated). Includes docker-compose for the demo stack, the parallel sovereign `deploy/vllm/docker-compose.yml`, Caddy config, landing page, and final README polish.

## Critical path

`1 → 3 → 4 → 6` is the critical path. Optimize for getting Package 1 small and Package 3 unblocked quickly. Package 5 (frontend) is *not* on the critical path because it can develop against the documented API contract.

## Shared decisions across all packages

These are locked decisions every coding agent must honor. They appear once here rather than being repeated in every spec.

### Language

English everywhere. No Spanish, no German. No `to_tsvector('spanish', ...)`. All prompts, instructions, error messages, synthetic data, comments, and identifiers are English. Localization is explicitly out of scope for v1.

### Python and packaging

- Python 3.11+.
- `uv` is the package manager. `pyproject.toml` is the single source of truth for dependencies.
- All modules start with `from __future__ import annotations`.
- Public functions and methods carry type hints.

### Database

- PostgreSQL 16 with `pgvector` and `pg_trgm` extensions.
- English full-text search via `to_tsvector('english', ...)`.
- Schema versioned under `sql/migrations/` (one file per migration, applied via the migration runner described in Package 1).

### Conversation model

The system supports **multi-turn conversation throughout**. There is one unified `ConversationService` (Package 4). Workflows are implemented as seeded first messages: clicking "Brief me before a call" starts a new conversation thread with a pre-written user prompt; the visitor can then ask follow-ups in the same thread. Account stickiness across turns is preserved (the active account is stored on the thread).

### Sessions and fake notes

The public demo is anonymous. Each visitor gets an anonymous session id stored in an HTTP cookie. Fake notes added by a visitor are scoped to their session id; they never bleed into other visitors' demos. Conversation threads are also session-scoped.

There is no login, no user accounts, no admin UI.

### LLM and embeddings

- Default backend: OpenRouter, configured via `OPENROUTER_API_KEY` env var.
- LLM model: configurable via env. Default to a balanced open-weights model on OpenRouter (e.g. `google/gemma-2-9b-it` or `qwen/qwen-2.5-7b-instruct`; Package 6 picks the final default after a quick quality check).
- Embedding model: configurable via env. Default to a hosted embedding model with 1536 dimensions (e.g. `qwen/qwen3-embedding-8b`, matching Uniendo Nodos).
- Sovereign alternative: vLLM exposing an OpenAI-compatible API. Documented and shipped as `deploy/vllm/docker-compose.yml`. The same `OpenAICompatibleClient` is used either way; only `LLM_BASE_URL` changes.

### Rate limiting

The public demo must protect Daniel's OpenRouter credits. Package 4 implements:

- Per-IP rate limit (e.g. 20 requests / minute).
- Per-session rate limit (e.g. 50 messages / hour).
- A daily global budget cap (e.g. €10 / day equivalent in tokens). When exceeded, the demo returns a friendly degraded response without calling the LLM.
- Optional captcha challenge on the free-text question box if abuse is detected — out of scope for v1, but the hook should be present.

### Reuse from Uniendo Nodos

`~/projects/uniendo-nodos-private-ai` is the upstream reference. Each package spec lists exactly which files to copy/adapt. The general rule:

- Backend patterns (retrieval, agent, intent, openrouter client, models, postgres helpers, schema, document builder): copy and adapt.
- Spanish text: rewrite to English.
- Frontend / chat UI: do **not** copy — vanilla HTML/CSS/JS exported from Claude Design is the source of truth.
- Tests: copy and adapt to English where applicable.

### Frontend

Vanilla HTML/CSS/JS, no build step. Static files served by FastAPI. The visual design comes from Claude Design as HTML/CSS exports; the frontend agent's job is to wire it up to the API, not to redesign. See Package 5 for the full API contract and event-flow specification.

### License and openness

Apache-2.0. One repository, fully public, including the demo UI. No secrets in commits.

## Acceptance criteria for the project as a whole

The demo is "done" when:

1. A visitor lands on the demo URL, sees three synthetic accounts in a selector, and can pick one.
2. The visitor sees a left panel listing the messy source artifacts (emails, PDFs, meeting notes, etc.) for that account, with visible artifact-type indicators.
3. The visitor can click "Brief me before a call" and receive a streaming, source-cited briefing within ~15 seconds.
4. The visitor can ask a follow-up question in the same thread and receive a streaming, source-cited answer.
5. The visitor can click an artifact in the left panel to view its extracted content.
6. At least one PDF in the corpus is visibly scanned/skewed and was ingested through OCR.
7. The right panel shows the specific source artifacts cited in the current answer.
8. The proactive alerts panel shows at least 4 alerts for the current account.
9. The visitor can add a synthetic note via the fake-note form; after adding it, clicking "What changed?" shows the new note's impact.
10. Fake notes from one visitor never appear in another visitor's demo.
11. The repo has a working `docker compose up -d` for the demo stack on a fresh Hetzner CPU instance.
12. The repo has a working `deploy/vllm/docker-compose.yml` that has been tested at least once on real GPU hardware.
13. The README has a clear "Demo scope vs. production scope" section.
14. A daily OpenRouter budget cap is enforced and tested.
15. No Spanish text remains anywhere in the codebase or UI.

## Out of scope for v1 (do not build)

- Real Salesforce / HubSpot integration.
- User accounts, login, auth.
- File upload by end users.
- Multi-tenant SaaS.
- Admin dashboard.
- Billing.
- DE/ES localization.
- Production-grade ingestion (incremental sync, OCR pipeline for arbitrary docs, deduplication, audit logging).
- Conversation export / shareable links.
- A standalone landing page CMS — the landing page in Package 6 is a single static HTML file.
