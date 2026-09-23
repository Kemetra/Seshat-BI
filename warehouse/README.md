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
- Migrations numbered and idempotent by **drop-and-rebuild in one transaction**
  (`DROP TABLE IF EXISTS` + `CREATE TABLE`), so a re-run replaces rather than
  duplicates — the latest build wins.

## Applying against DigitalOcean Postgres

Connection variables live in `.env` (see `.env.example`). DigitalOcean managed
Postgres requires TLS (`sslmode=require`). Apply migrations in numeric order, e.g.:

\`\`\`bash
psql "host=$ANALYTICS_DB_HOST port=$ANALYTICS_DB_PORT dbname=$ANALYTICS_DB_NAME \
  user=$ANALYTICS_DB_USER sslmode=$ANALYTICS_DB_SSLMODE" \
  -f warehouse/migrations/0003_create_silver_retail_store_sales.sql
\`\`\`

> The committed migration set, applied in numeric order against a database that
> already holds the bronze sources:
>
> - `0003`/`0004` -- `retail_store_sales` worked example (silver, gold Kimball star);
>   `0010` removes the blank padding from `gold.dim_date_rss` month/day labels.
> - `0005` -- `demo_sample_orders` silver (local demo harness); `0011` enforces its
>   declared primary key.
> - `0006`/`0007`/`0008` -- finance GL actuals + budget silver and their gold star;
>   `0009` hardens that star (natural-key-unique conformed dimensions, unpadded date
>   labels plus `iso_year`, and an `amount` that survives a blank zero side).
>
> An applied migration is never edited in place: a fix ships as a new numbered
> follow-up. Because `0004`-`0008` are full DROP+CREATE rebuilds, re-applying one
> means re-applying its follow-up afterwards.
