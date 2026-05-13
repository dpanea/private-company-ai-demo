# Package 1 — Skeleton and core

**Purpose.** Lay down the project skeleton, Pydantic models, SQL schema, migration runner, settings, logging, and DB helpers. Everything else imports from here. Keep it small and focused — no business logic.

**Depends on:** nothing.

**Blocks:** packages 2, 3, 4, 5.

**Estimated size:** small (~500 LOC code + schema + tests).

## Outputs

```text
private-company-ai-demo/
├── pyproject.toml
├── docker-compose.yml          # Postgres only at this stage
├── .env.example
├── src/
│   └── pcad/                   # "private company ai demo" package
│       ├── __init__.py
│       ├── config.py
│       ├── logging_utils.py
│       ├── models.py
│       ├── db.py
│       └── migrations.py
├── sql/
│   ├── migrations/
│   │   ├── 0001_init.sql
│   │   ├── 0002_pgvector_pgtrgm.sql
│   │   ├── 0003_normalized_crm_tables.sql
│   │   ├── 0004_raw_artifacts.sql
│   │   ├── 0005_rag_documents.sql
│   │   ├── 0006_source_citations.sql
│   │   ├── 0007_conversation.sql
│   │   ├── 0008_fake_notes.sql
│   │   └── 0009_proactive_alerts.sql
│   └── README.md
└── tests/
    ├── conftest.py
    └── test_skeleton.py
```

The Python package is named `pcad` (short for "private company ai demo") to keep imports terse: `from pcad.models import Account`.

## pyproject.toml

Use `setuptools` build backend, the same shape as the Uniendo Nodos `pyproject.toml`. Required dependencies for this package only:

```toml
[project]
name = "private-company-ai-demo"
version = "0.1.0"
description = "Public demo and open-source reference architecture for a private company memory layer."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "Apache-2.0" }
dependencies = [
    "pydantic>=2.8.0",
    "psycopg[binary]>=3.2.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[project.scripts]
pcad = "pcad.cli:main"

[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

Note: a `pcad.cli` entry point is reserved here but its implementation lives in Package 3 (which adds the `ingest-demo` command) and Package 4 (which adds `serve`).

Other packages will add their own dependencies (fastapi, langgraph, pypdf, python-docx, pytesseract, etc.) by editing this file.

## .env.example

```env
# Database
DATABASE_URL=postgresql://pcad:pcad@localhost:5432/pcad

# OpenRouter (LLM and embeddings)
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=qwen/qwen-2.5-7b-instruct
LLM_REASONING_EFFORT=low
EMBEDDING_MODEL=qwen/qwen3-embedding-8b
EMBEDDING_DIMENSIONS=1536

# Sovereign deployment (vLLM) — optional, used by deploy/vllm/
# LLM_BASE_URL=http://vllm:8080/v1
# LLM_API_KEY=local

# Application
APP_TITLE=Private Company Memory Demo
HTTP_REFERER=https://demo.danielpanea.com
LOG_LEVEL=INFO
LOG_COLOR=false

# Session
SESSION_COOKIE_NAME=pcad_session
SESSION_TTL_DAYS=7
SESSION_SECRET=change-me-to-a-long-random-string

# Rate limiting (Package 4 enforces these)
RATE_LIMIT_PER_IP_PER_MINUTE=20
RATE_LIMIT_PER_SESSION_PER_HOUR=50
DAILY_TOKEN_BUDGET=1500000
```

## docker-compose.yml (Postgres only at this stage)

Package 6 expands this to include the app and (optionally) the vLLM service. For Package 1, ship only Postgres so the migration runner and tests work locally.

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: pcad
      POSTGRES_PASSWORD: pcad
      POSTGRES_DB: pcad
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pcad -d pcad"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

## src/pcad/config.py

Settings class that loads from environment with sane defaults. Mirror the Uniendo Nodos `core/config.py` pattern. The class must be `pydantic.BaseSettings` (via `pydantic-settings`) or, to avoid an extra dependency, a `dataclass` with a `from_env()` classmethod (the Uniendo Nodos style). Use the dataclass style for consistency with Uniendo Nodos.

Required fields:

- `database_url: str`
- `openrouter_api_key: str | None`
- `openrouter_base_url: str`
- `llm_model: str`
- `llm_reasoning_effort: str` (one of `"low"`, `"medium"`, `"high"`)
- `embedding_model: str`
- `embedding_dimensions: int`
- `app_title: str`
- `http_referer: str | None`
- `log_level: str`
- `log_color: bool`
- `session_cookie_name: str`
- `session_ttl_days: int`
- `session_secret: str`
- `rate_limit_per_ip_per_minute: int`
- `rate_limit_per_session_per_hour: int`
- `daily_token_budget: int`
- `context_token_budget: int` (default 6000, matches Uniendo Nodos)
- `agent_generation_max_attempts: int` (default 3)

Provide a `require_openrouter_key()` method that raises if the key is missing (mirror Uniendo Nodos).

## src/pcad/logging_utils.py

Copy [src/un_private_ai/core/logging_utils.py](../../uniendo-nodos-private-ai/src/un_private_ai/core/logging_utils.py) verbatim, renaming module imports. Same structured-log philosophy: `logger.info("<event.name> key=value ...")`.

## src/pcad/models.py

Pydantic models. Adapt from Uniendo Nodos [src/un_private_ai/core/models.py](../../uniendo-nodos-private-ai/src/un_private_ai/core/models.py) with these changes:

- All language-facing field comments/docstrings in English.
- Add new models documented below.

Required models:

### Existing CRM models (adapted from Uniendo Nodos)

- `UserOwner`
- `Account`
- `Contact`
- `Opportunity`
- `Contract`
- `Activity` — represents both Task and Event records via `source_object` discriminator
- `RagDocument`
- `SourceCitation`
- `SyntheticDataset` — convenience container

### New models for this demo

- `RawArtifact` — the raw company artifact a visitor sees in the left panel:
  - `artifact_id: str`
  - `account_id: str | None`
  - `artifact_type: Literal["email", "email_thread", "pdf", "docx", "meeting_transcript", "crm_record"]`
  - `title: str`
  - `mime_type: str`
  - `source_path: str` — path under `data/synthetic/` to the original file
  - `rendered_path: str | None` — path to a rendered image (for PDF pages); `None` for non-image types
  - `extracted_text: str` — the text that was extracted by the ingestion pipeline (post-OCR for scanned PDFs)
  - `metadata: dict[str, Any]` — format-specific metadata (sender/recipient/date for emails, page count for PDFs, etc.)
  - `extraction_method: Literal["plain_text", "ocr", "docx_xml", "mbox_parse", "csv_row"]`
  - `created_at: datetime`
  - `ingested_at: datetime`

- `ProactiveAlert`:
  - `alert_id: str`
  - `account_id: str`
  - `alert_type: Literal["unresolved_objection", "stalled_account", "approaching_close_date", "missing_followup", "champion_positive_signal", "data_inconsistency"]`
  - `severity: Literal["info", "warning", "critical"]`
  - `title: str`
  - `body_markdown: str`
  - `evidence_doc_ids: list[str]`
  - `evidence_artifact_ids: list[str]`
  - `created_at: datetime`

- `FakeNote`:
  - `note_id: str`
  - `session_id: str`
  - `account_id: str`
  - `note_type: Literal["meeting_summary", "email_summary", "task", "risk", "general"]`
  - `title: str`
  - `body: str`
  - `note_date: date`
  - `created_at: datetime`

- `ConversationThread`:
  - `thread_id: str`
  - `session_id: str`
  - `account_id: str | None`
  - `account_name: str | None`
  - `title: str`
  - `workflow_seed: str | None` — the workflow identifier that started this thread (`"call_briefing"`, `"what_changed"`, etc.), `None` for free-text threads
  - `created_at: datetime`
  - `updated_at: datetime`

- `ConversationMessage`:
  - `message_id: str`
  - `thread_id: str`
  - `role: Literal["user", "assistant"]`
  - `content: str`
  - `account_id: str | None`
  - `account_name: str | None`
  - `citations: list[dict[str, Any]]`
  - `metadata: dict[str, Any]`
  - `created_at: datetime`

- `Session`:
  - `session_id: str`
  - `created_at: datetime`
  - `last_seen_at: datetime`
  - `expires_at: datetime`

## sql/ schema

Split the schema into versioned migration files. The migration runner in `src/pcad/migrations.py` applies them in order and tracks which have been applied in a `schema_migrations` table.

Each file is a self-contained `CREATE TABLE` / `CREATE INDEX` / `CREATE EXTENSION` block. Adapt from Uniendo Nodos [sql/schema.sql](../../uniendo-nodos-private-ai/sql/schema.sql).

### Required changes vs. Uniendo Nodos

1. **English full-text search.** `to_tsvector('english', ...)` everywhere.
2. **Drop chat schema, replace with conversation schema.** Uniendo Nodos has `admin_sessions`, `chat_threads`, `chat_messages` for logged-in admin use. Replace with:
   - `sessions` (anonymous, cookie-based)
   - `conversation_threads`
   - `conversation_messages`
3. **Add `raw_artifacts` table** (new).
4. **Add `fake_notes` table** (new, with `session_id` for per-session scoping).
5. **Add `proactive_alerts` table** (new).
6. **Drop Salesforce-specific assumptions.** Field names like `raw_record_id`, `source_url` stay, but their values come from synthetic ingestion, not Salesforce.

### sql/migrations/0001_init.sql

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);
```

### sql/migrations/0002_pgvector_pgtrgm.sql

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### sql/migrations/0003_normalized_crm_tables.sql

Copy the `users_or_owners`, `accounts`, `contacts`, `opportunities`, `contracts`, `activities` tables verbatim from Uniendo Nodos schema. They are already English-named.

### sql/migrations/0004_raw_artifacts.sql

```sql
CREATE TABLE IF NOT EXISTS raw_artifacts (
    artifact_id text PRIMARY KEY,
    account_id text REFERENCES accounts(account_id) ON DELETE CASCADE,
    artifact_type text NOT NULL CHECK (artifact_type IN (
        'email', 'email_thread', 'pdf', 'docx', 'meeting_transcript', 'crm_record'
    )),
    title text NOT NULL,
    mime_type text NOT NULL,
    source_path text NOT NULL,
    rendered_path text,
    extracted_text text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    extraction_method text NOT NULL CHECK (extraction_method IN (
        'plain_text', 'ocr', 'docx_xml', 'mbox_parse', 'csv_row'
    )),
    created_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_artifacts_account ON raw_artifacts(account_id, artifact_type);
CREATE INDEX IF NOT EXISTS idx_raw_artifacts_metadata ON raw_artifacts USING gin(metadata);
```

### sql/migrations/0005_rag_documents.sql

Adapt from Uniendo Nodos schema. Key changes:

- `to_tsvector('english', ...)` instead of `'spanish'`.
- Add new `doc_type` values to the implicit set (no DB constraint, but documented): `email_thread_summary`, `meeting_summary`, `risk_summary`.
- Add `session_id text` column (nullable) for documents derived from session-scoped fake notes. Retrieval queries filter `WHERE session_id IS NULL OR session_id = current_session`.

```sql
CREATE TABLE IF NOT EXISTS rag_documents (
    doc_id text PRIMARY KEY,
    doc_type text NOT NULL,
    title text NOT NULL,
    content_markdown text NOT NULL,
    metadata_json jsonb NOT NULL,
    source_record_ids text[] NOT NULL DEFAULT '{}',
    source_record_hashes text[] NOT NULL DEFAULT '{}',
    account_id text REFERENCES accounts(account_id) ON DELETE CASCADE,
    opportunity_id text REFERENCES opportunities(opportunity_id) ON DELETE SET NULL,
    contract_id text REFERENCES contracts(contract_id) ON DELETE SET NULL,
    owner_id text REFERENCES users_or_owners(user_id),
    session_id text,
    last_source_updated_at timestamptz,
    generated_at timestamptz NOT NULL,
    source_hash text NOT NULL,
    embedding vector(1536),
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(content_markdown, '')), 'B')
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_rag_documents_account_type ON rag_documents(account_id, doc_type);
CREATE INDEX IF NOT EXISTS idx_rag_documents_opportunity_id ON rag_documents(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_rag_documents_contract_id ON rag_documents(contract_id);
CREATE INDEX IF NOT EXISTS idx_rag_documents_session ON rag_documents(session_id);
CREATE INDEX IF NOT EXISTS idx_rag_documents_metadata ON rag_documents USING gin(metadata_json);
CREATE INDEX IF NOT EXISTS idx_rag_documents_search ON rag_documents USING gin(search_vector);
CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding ON rag_documents USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_accounts_account_name_trgm ON accounts USING gin (account_name gin_trgm_ops);
```

### sql/migrations/0006_source_citations.sql

Copy from Uniendo Nodos verbatim.

### sql/migrations/0007_conversation.sql

```sql
CREATE TABLE IF NOT EXISTS sessions (
    session_id text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

CREATE TABLE IF NOT EXISTS conversation_threads (
    thread_id text PRIMARY KEY,
    session_id text NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    account_id text REFERENCES accounts(account_id) ON DELETE SET NULL,
    account_name text,
    title text NOT NULL,
    workflow_seed text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversation_threads_session_updated
    ON conversation_threads(session_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS conversation_messages (
    message_id text PRIMARY KEY,
    thread_id text NOT NULL REFERENCES conversation_threads(thread_id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('user', 'assistant')),
    content text NOT NULL,
    account_id text,
    account_name text,
    citations jsonb NOT NULL DEFAULT '[]'::jsonb,
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_thread_created
    ON conversation_messages(thread_id, created_at);
```

### sql/migrations/0008_fake_notes.sql

```sql
CREATE TABLE IF NOT EXISTS fake_notes (
    note_id text PRIMARY KEY,
    session_id text NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    account_id text NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
    note_type text NOT NULL CHECK (note_type IN (
        'meeting_summary', 'email_summary', 'task', 'risk', 'general'
    )),
    title text NOT NULL,
    body text NOT NULL,
    note_date date NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fake_notes_session_account
    ON fake_notes(session_id, account_id);
```

### sql/migrations/0009_proactive_alerts.sql

```sql
CREATE TABLE IF NOT EXISTS proactive_alerts (
    alert_id text PRIMARY KEY,
    account_id text NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
    session_id text,
    alert_type text NOT NULL CHECK (alert_type IN (
        'unresolved_objection', 'stalled_account', 'approaching_close_date',
        'missing_followup', 'champion_positive_signal', 'data_inconsistency'
    )),
    severity text NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    title text NOT NULL,
    body_markdown text NOT NULL,
    evidence_doc_ids text[] NOT NULL DEFAULT '{}',
    evidence_artifact_ids text[] NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_proactive_alerts_account
    ON proactive_alerts(account_id, session_id, severity);
```

## src/pcad/db.py

Thin connection helpers. Mirror the spirit of Uniendo Nodos [core/postgres.py](../../uniendo-nodos-private-ai/src/un_private_ai/core/postgres.py), but keep it focused on:

- `connect(settings: Settings) -> psycopg.Connection` (context manager friendly)
- `connect_dict(settings: Settings)` — returns a connection with `dict_row` row factory
- `ensure_extensions(conn)` — runs `CREATE EXTENSION IF NOT EXISTS` for `vector` and `pg_trgm` (idempotent helper for tests)

## src/pcad/migrations.py

A minimal forward-only migration runner.

```python
def apply_migrations(settings: Settings, migrations_dir: Path = Path("sql/migrations")) -> list[str]:
    """Apply any pending migrations in lexical order. Returns the list of versions applied."""
```

Logic:

1. Ensure `schema_migrations` exists (run `0001_init.sql` always; idempotent).
2. List all `*.sql` files in `migrations_dir` sorted.
3. For each file, compute the version (filename without `.sql`).
4. If `version` not in `schema_migrations`, execute the file's contents inside a transaction, then insert the version row.
5. Log each application: `logger.info("migration.apply.done version=%s", version)`.

Provide a CLI entry: `python -m pcad.migrations` (or `pcad migrate` once the CLI is wired in Package 3).

## Tests

`tests/conftest.py`:

- Provides a `db_url` fixture pointing at a local Postgres test database.
- Provides a `clean_db` fixture that truncates all application tables between tests.
- Skips DB tests gracefully when Postgres is unreachable.

`tests/test_skeleton.py`:

- Asserts `apply_migrations` runs to completion on an empty DB.
- Asserts running `apply_migrations` twice is idempotent.
- Asserts all expected tables exist after migration.
- Asserts the `pgvector` and `pg_trgm` extensions are present.
- Round-trips one of each Pydantic model through JSON.

## Acceptance criteria

The package is done when:

1. `uv sync` succeeds with no errors.
2. `docker compose up -d postgres` brings up Postgres with pgvector.
3. `python -m pcad.migrations` (or equivalent script) applies all 9 migrations cleanly on a fresh DB and is idempotent on rerun.
4. `uv run pytest` passes against a running local Postgres.
5. Every Pydantic model can be constructed, JSON-serialized, and reconstructed.
6. The codebase contains **no Spanish text**: `grep -ri "espanol\|espana\|spanish" src/ sql/` returns zero results.
7. The Python package imports as `from pcad.models import Account` from any test or downstream package.
