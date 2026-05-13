# AGENTS.md — private-company-ai-demo

## Purpose

This is the technical workspace for the **Private Company Memory Layer** public demo and open-source reference architecture. Coding agents working in this repository should follow the per-package specifications in [`docs/`](docs/) and the conventions in this file.

Commercial context, GTM, and positioning live in the Obsidian vault under:

- `/home/daniel/Notes/04 Professional Projects/Company Memory Demo/`

## Project shape

A public web demo at `demo.danielpanea.com` (or equivalent subdomain) that:

- ingests synthetic messy multi-format company artifacts (emails, PDFs, Word docs, meeting transcripts, CRM CSV exports)
- normalizes them into AI-ready documents stored in Postgres + pgvector
- answers user questions via hybrid retrieval + a LangGraph agent, with source citations
- exposes guided workflows (call briefing, what changed, follow-up draft) and a free-text question box
- supports multi-turn conversation with account stickiness
- lets visitors add synthetic notes and see the system react

Backed by an open-source repository under Apache-2.0, with documented "production scope" boundaries that signal where paid client engagements pick up.

## Package structure and dependencies

The implementation is broken into six packages:

| # | Package | Documents |
|---|---|---|
| 1 | Project skeleton & core | [docs/01-package-skeleton-and-core.md](docs/01-package-skeleton-and-core.md) |
| 2 | Synthetic corpus generation | [docs/02-package-synthetic-corpus.md](docs/02-package-synthetic-corpus.md) |
| 3 | Ingestion pipeline | [docs/03-package-ingestion.md](docs/03-package-ingestion.md) |
| 4 | Retrieval, agent, API | [docs/04-package-retrieval-agent-api.md](docs/04-package-retrieval-agent-api.md) |
| 5 | Frontend | [docs/05-package-frontend.md](docs/05-package-frontend.md) |
| 6 | Deployment & landing | [docs/06-package-deployment-landing.md](docs/06-package-deployment-landing.md) |

Dependency map and parallelization strategy in [docs/00-overview.md](docs/00-overview.md).

Two backports to the related Uniendo Nodos repo are documented in [docs/bug-fixes-uniendo-nodos.md](docs/bug-fixes-uniendo-nodos.md).

## Related upstream repository

This project reuses substantial code patterns from `~/projects/uniendo-nodos-private-ai`. That repo is the Spanish-language Salesforce-specific pilot for a client (Uniendo Nodos). The new repo:

- adapts the same architecture to English
- generalizes beyond Salesforce to multi-format messy sources
- adds an open-source reference architecture frame
- uses entirely synthetic data with no client information

See each package spec for explicit "reuse from Uniendo Nodos" notes.

## Conventions

### Language

- All UI text, prompts, system messages, error messages, synthetic data content, and embedding instructions are in **English**.
- The codebase uses American English in identifiers and docstrings.
- Localization (DE, ES) is explicitly out of scope for v1.

### Python

- Python 3.11+.
- Package manager: `uv` (never pip).
- Style: PEP 8, 4-space indent, `snake_case` for functions/variables, `PascalCase` for classes.
- Type hints required on all public functions and class methods.
- Use `from __future__ import annotations` at the top of every module.
- Test framework: `pytest`.

### Database

- PostgreSQL 16 + `pgvector` + `pg_trgm` extensions.
- Spanish-language full-text search from Uniendo Nodos (`to_tsvector('spanish', ...)`) must be replaced with **English** (`to_tsvector('english', ...)`).
- Schema changes go through versioned migration files in `sql/migrations/`, not direct `schema.sql` edits.

### Frontend

- Vanilla **HTML / CSS / JS**. No build step. No React, Next.js, Vue, or Svelte.
- Served as static files by FastAPI under `/static/` and `/`.
- The visual design comes from Claude Design exports — the coding agent's job is to wire up the markup, not redesign it.
- JavaScript uses native ES modules and the Fetch API. No bundler.

### Secrets

- All secrets in `.env` (gitignored).
- `.env.example` ships with placeholder names only.
- Never log secret values.
- Never commit any `.env` with real values.

### Frontend ↔ API contract

- JSON over HTTP for non-streaming endpoints.
- Server-Sent Events (SSE) for streaming chat responses.
- All API endpoints under `/api/`.
- Static assets under `/static/`.

### Logging

- Structured single-line logs with `key=value` fields, matching the Uniendo Nodos pattern.
- Format: `logger.info("<dotted.event.name> field=value field2=value2", ...)`.
- Never log full prompt content or LLM responses at INFO level — those go to DEBUG only.

### Commit style

- Short imperative subject lines.
- Optional prefixes: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- Keep commits focused.

## Daniel's role

Daniel is the architect and owner. Coding agents implement against the specs in `docs/`. When a spec is ambiguous or appears inconsistent with another spec, **ask Daniel before inventing**. Do not silently fill gaps with assumptions.

## What never to do

- Do not introduce a frontend framework or build step.
- Do not localize to Spanish or German in v1.
- Do not add user accounts, authentication, or multi-tenant features. The public demo is anonymous and session-scoped.
- Do not commit real OpenRouter API keys, even to `.env.example`.
- Do not skip the citation validation path in the agent.
- Do not hardcode Spanish text or `to_tsvector('spanish', ...)` anywhere.
- Do not add features that would compete with paid client work (production-grade ingestion, multi-tenant SaaS, billing, admin dashboards). These belong outside this repo.

## Hardware and deployment notes

- Public demo runs on a Hetzner VPS owned by Daniel. CPU-only. OpenRouter for LLM and embeddings.
- Reverse proxy: Caddy.
- Network exposure: HTTP/HTTPS only. Tailscale for admin access.
- The sovereign deployment path (vLLM with self-hosted open weights) is documented and ships as a working `docker-compose.yml`, but is not used by the public demo. Daniel will test it once on real hardware before publishing.
