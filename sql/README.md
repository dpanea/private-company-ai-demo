# SQL schema

The schema lives in a single idempotent file, [`init.sql`](init.sql).
`company-ai migrate` applies it; every statement uses `IF NOT EXISTS`, so the
command is safe to re-run.

Run it locally with:

```bash
uv run company-ai migrate
```

For a clean wipe and reset (synthetic data only — never on production):

```bash
docker compose down -v postgres
docker compose up -d postgres
uv run company-ai migrate
uv run company-ai ingest-demo --clean
```
