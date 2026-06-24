# Retail Tower Analytics

Standalone analytics service for the Retail Tower ecosystem. Power BI is the
primary reporting tool; the layout leaves room for other tools later. Data is
served from a dedicated **PostgreSQL database on DigitalOcean**.

Building a new retail mart? Copy the pattern in `docs/worked-examples/c086-pharmacy.md`.

## Layout

| Folder | Purpose |
|--------|---------|
| `warehouse/` | Tool-agnostic SQL: `raw` landing schema → `marts` reporting schema, plus migrations. |
| `powerbi/` | Power BI projects in **PBIP** (plain-text) format — the only tool-specific folder. |
| `pipelines/` | Data ingestion: manual now, automated feed later (same `raw` contract). |
| `templates/` | Generic source-mapping-gate blanks (profile, map, assumptions, questions, reconciliation). |
| `mappings/` | Per-table **filled** mapping artifacts, one folder per table (`mappings/<table>/`). See [ADR 0003](docs/decisions/0003-mapping-artifact-location.md). |
| `docs/` | Design specs, conventions, data dictionary, decisions (ADRs), worked examples. |

## Architecture

```
DigitalOcean PostgreSQL
  raw (landing)  →  marts (reporting)  →  Power BI (PBIP)
        ▲
   manual loads now · automated feed later
```

## Getting started

1. Copy `.env.example` to `.env` and fill in the DigitalOcean Postgres connection
   values. `.env` is git-ignored — never commit it.
2. **For Power BI:** enable **Power BI Project (.pbip)** in Power BI Desktop
   Preview features (it's in preview as of 2025-12), then save projects under
   `powerbi/`. See `powerbi/README.md`.
3. **For SQL:** add schema/marts/migrations under `warehouse/`. See
   `warehouse/README.md`.

## Conventions

See [`docs/conventions.md`](docs/conventions.md). Design rationale lives in
[`docs/superpowers/specs/`](docs/superpowers/specs/).

## Notes for Windows

PBIP enforces a 260-char path limit; this repo intentionally sits at a short root
path. Line endings are handled by `.gitattributes` + `core.autocrlf=true`.
