# AGENTS.md

Notes for coding agents (and humans) working in this repository. For a
deeper explanation of the system, read [docs/architecture.md](docs/architecture.md).

## Project shape

A public, anonymous web demo of a source-backed AI assistant over synthetic
company knowledge. The system ingests messy multi-format artifacts (emails,
PDFs, Word docs, meeting transcripts, CRM CSVs), normalizes them into
AI-ready documents in Postgres + pgvector, and answers questions through
guided workflows with citations.

This is a *reference architecture*, not a turnkey product. Things like
auth, multi-tenant isolation, evaluation harnesses, and production
connectors are deliberately out of scope — see
[docs/architecture.md](docs/architecture.md) for the boundary.

## Conventions

### Language
- All UI text, prompts, system messages, and synthetic data are in **English**.

### Python
- Python 3.11+.
- Package manager: `uv` (not pip).
- PEP 8, 4-space indent, `snake_case` for functions/variables, `PascalCase` for classes.
- Type hints on public functions and class methods.
- `from __future__ import annotations` at the top of every module.
- Tests use `pytest`.

### Database
- PostgreSQL 16 with `pgvector` and `pg_trgm`.
- Schema lives in a single `sql/init.sql`. The `migrate` command applies it
  idempotently — there is no migration history beyond the initial install.

### Frontend
- Vanilla HTML / CSS / JS. No build step, no framework, no bundler.
- Served as static files by FastAPI under `/static/` and `/`.
- JavaScript uses native ES modules and `fetch`.

### Secrets
- Never commit a `.env` with real values; `.env.example` ships placeholders only.
- Never log secret values.

### Frontend ↔ API contract
- JSON over HTTP for non-streaming endpoints, all under `/api/`.
- Server-Sent Events (SSE) for streaming chat responses.

### Logging
- Structured single-line logs with `key=value` fields.
- Format: `logger.info("<dotted.event.name> field=value field2=value2", ...)`.
- Never log full prompt content or LLM responses at INFO level — DEBUG only.

### Commits
- Short imperative subject lines.
- Optional prefixes: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.

## What never to do
- Do not introduce a frontend framework or build step.
- Do not add user accounts, authentication, or multi-tenant features.
- Do not commit real LLM API keys, even to `.env.example`.
- Do not skip citation validation in the conversation service.
- Do not hardcode language-specific full-text-search configurations (e.g. a
  Spanish `to_tsvector`); the demo is English-only.

## Local agent context

If a file named `AGENTS.local.md` exists alongside this one, read it as well.
That file is gitignored and is meant for private, machine-local context
(e.g. workstation paths, related private repos) that should not appear in
the public history.
