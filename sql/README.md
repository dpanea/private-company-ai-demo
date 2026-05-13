# SQL Migrations

Migrations are forward-only SQL files applied in lexical order by `pcad.migrations`.

Run them locally with:

```bash
python -m pcad.migrations
```

Schema changes should be added as new files under `sql/migrations/`; do not edit already-applied migrations in shared environments.
