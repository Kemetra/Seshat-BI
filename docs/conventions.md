# Conventions

## SQL (warehouse/)

- `snake_case` for all identifiers.
- Schemas (medallion): `bronze` (raw landing), `silver` (typed/cleaned),
  `gold` (reporting marts; Power BI reads `gold`). See `warehouse/README.md`.
- Object prefixes: views `vw_`, fact tables `fct_`, dimension tables `dim_`.
- Migrations: numbered `NNNN_description.sql`, applied in order, idempotent
  (`IF NOT EXISTS`, guarded `ALTER`).

## Power BI / PBIP (powerbi/)

- Save as PBIP (preview feature must be enabled in Power BI Desktop).
- One semantic model per subject area; reports reference the model relatively.
- Connect via parameters; read from `marts` only.

## DAX

- Measures in `PascalCase`, organized into display folders.
- One measure per business concept; avoid duplicating logic across measures.

## Git

- Commit messages: `<type>: <description>` where type ∈
  `{feat, fix, refactor, docs, chore}`.
- `core.autocrlf=true`; line endings governed by `.gitattributes`.
