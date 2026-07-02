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
- Migrations are numbered and idempotent by **drop-and-rebuild in one
  transaction** — each script `DROP TABLE IF EXISTS ...` then `CREATE TABLE` (not
  additive `CREATE ... IF NOT EXISTS`). Re-running a migration is safe and the
  **latest build wins**; it fully replaces the table it owns.

## Applying against DigitalOcean Postgres

Connection variables live in `.env` (see `.env.example`). DigitalOcean managed
Postgres requires TLS (`sslmode=require`). Apply the migrations in numeric order.
Run with `ON_ERROR_STOP=on` so a failing script (e.g. a superseded guard) aborts
instead of continuing. Example (one migration):

\`\`\`bash
psql -v ON_ERROR_STOP=on \
  "host=$ANALYTICS_DB_HOST port=$ANALYTICS_DB_PORT dbname=$ANALYTICS_DB_NAME \
   user=$ANALYTICS_DB_USER sslmode=$ANALYTICS_DB_SSLMODE" \
  -f warehouse/migrations/0003_create_silver_retail_store_sales.sql
\`\`\`

### Migration set (current state)

Both `silver` and `gold` are **fully built** — not "the next step":

| # | Builds | Layer |
|---|--------|-------|
| `0003_create_silver_retail_store_sales.sql` | `silver.retail_store_sales` | silver |
| `0004_create_gold_retail_store_sales_star.sql` | gold star over retail_store_sales | gold |
| `0005_create_silver_sales_c086.sql` | `silver.sales_c086` (authoritative) | silver |
| `0006_create_gold_sales_c086_star.sql` | gold star over `sales_c086` | gold |

### Supersession (⚠ do not run 0001 / 0002)

Two early migrations were replaced by a later rebuild with a different schema.
They are retained for history but each opens with a `-- *** SUPERSEDED ***`
header and a PL/pgSQL guard (`RAISE EXCEPTION` right after `BEGIN`) that aborts
the transaction **before** its destructive `DROP TABLE` — so running one cannot
silently revert the authoritative build.

| Superseded | Replaced by | Reason |
|------------|-------------|--------|
| `0001_create_silver_sales_c086.sql` | `0005_create_silver_sales_c086.sql` | old silver shape; its DROP would revert the current silver |
| `0002_create_gold_star.sql` | `0006_create_gold_sales_c086_star.sql` | selects silver columns that no longer exist; errors against the current schema |

So "apply in numeric order" now means the **live set: 0003, 0004, 0005, 0006**.
0001 and 0002 will refuse to run.

> `bronze` is populated (C086 sales, see `pipelines/`). `silver` and `gold` are
> both built by the migrations above (retail_store_sales via 0003/0004,
> `sales_c086` via 0005/0006).
