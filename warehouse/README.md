# warehouse/ — tool-agnostic data layer

SQL that defines the DigitalOcean PostgreSQL analytics database. Any reporting
tool (Power BI today, others later) reads from here — nothing in this folder is
Power BI-specific.

## Schemas

| Schema  | Purpose |
|---------|---------|
| `raw`   | Landing zone. Manual loads now; a future automated feed targets the same tables. |
| `marts` | Reporting views/tables consumed by BI tools. |

## Folders

- `schema/` — DDL: `CREATE SCHEMA`, table definitions.
- `marts/` — reporting view/mart definitions (read by Power BI).
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

> No live DB or real SQL content exists yet — this is the structure the first
> mart and migration drop into.
