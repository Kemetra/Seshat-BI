# warehouse/ — tool-agnostic data layer

SQL that defines the DigitalOcean PostgreSQL analytics database. Any reporting
tool (Power BI today, others later) reads from here — nothing in this folder is
Power BI-specific.

## Schemas (medallion: bronze → silver → gold)

| Schema   | Role | Purpose |
|----------|------|---------|
| `bronze` | landing | Raw source data, faithful, all columns as TEXT + lineage (`_source_file`, `_loaded_at`). No cleaning. Loaded by `pipelines/`. |
| `silver` | refined | Typed, deduplicated, standardized (e.g. quantities → numeric, dates parsed, trimmed text). Built from `bronze`. |
| `gold`   | reporting | Curated marts (facts/dims, aggregates) consumed by BI tools. Built from `silver`. **Power BI reads `gold`.** |

> Earlier drafts of this repo used `raw`/`marts` (a 2-layer model). The deployed
> database uses the 3-layer medallion above: `bronze` = the old `raw` (landing),
> `gold` = the old `marts` (reporting), with `silver` added for cleaning/typing.

## Folders

- `schema/` — DDL: `CREATE SCHEMA`, table definitions.
- `gold/` — reporting view/mart definitions for the `gold` schema (read by Power BI).
- `migrations/` — ordered, idempotent change scripts (`NNNN_description.sql`).

## Conventions

- `snake_case` everywhere.
- Views prefixed `vw_`, fact tables `fct_`, dimension tables `dim_`.
- Migrations numbered and idempotent (`CREATE ... IF NOT EXISTS`, guarded `ALTER`).

## Applying against DigitalOcean Postgres

Connection variables live in `.env` (see `.env.example`). DigitalOcean managed
Postgres requires TLS (`sslmode=require`). Apply migrations in numeric order, e.g.:

\`\`\`bash
psql "host=$ANALYTICS_DB_HOST port=$ANALYTICS_DB_PORT dbname=$ANALYTICS_DB_NAME \
  user=$ANALYTICS_DB_USER sslmode=$ANALYTICS_DB_SSLMODE" -f warehouse/migrations/0001_init.sql
\`\`\`

> `bronze` is populated (C086 sales, see `pipelines/`). `silver` and `gold` schemas
> exist but are not yet built out — that's the next step.
