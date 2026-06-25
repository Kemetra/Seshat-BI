# Retail Tower Analytics

Standalone analytics service for the Retail Tower ecosystem. Power BI is the
primary reporting tool; the layout leaves room for other tools later. Data is
served from a dedicated **PostgreSQL database on DigitalOcean**.

Building a new retail mart? Copy the pattern in `docs/worked-examples/c086-pharmacy.md`.

## Layout

| Folder | Purpose |
|--------|---------|
| `warehouse/` | Tool-agnostic SQL: medallion `bronze` (landing) -> `silver` (typed/cleaned) -> `gold` (reporting), plus migrations. |
| `powerbi/` | Power BI projects in **PBIP** (plain-text) format -- the only tool-specific folder. Reads `gold` only. |
| `pipelines/` | Data ingestion: manual now, automated feed later (same `bronze` landing contract). |
| `templates/` | Generic source-mapping-gate blanks (profile, map, assumptions, questions, reconciliation). |
| `mappings/` | Per-table **filled** mapping artifacts, one folder per table (`mappings/<table>/`). See [ADR 0003](docs/decisions/0003-mapping-artifact-location.md). |
| `docs/` | Design specs, conventions, data dictionary, decisions (ADRs), worked examples. |
| `docs/readiness/` | The **Tower BI Readiness System** -- the stage/state spine (model, pipeline, 7 stage docs). |
| `docs/roadmap/` | The product roadmap (identity, six layers; F005-F015 shipped, F016 the one gated feature remaining). |

## Architecture

```
DigitalOcean PostgreSQL
  bronze (landing)  ->  silver (typed/cleaned)  ->  gold (reporting)  ->  Power BI (PBIP, gold only)
        ^
   manual loads now ; automated feed later
```

## Getting started

1. Copy `.env.example` to `.env` and fill in the DigitalOcean Postgres connection
   values. `.env` is git-ignored -- never commit it.
2. **For Power BI:** enable **Power BI Project (.pbip)** in Power BI Desktop
   Preview features (it's in preview as of 2025-12), then save projects under
   `powerbi/`. See `powerbi/README.md`.
3. **For SQL:** add schema/gold/migrations under `warehouse/` (medallion
   bronze/silver/gold). See `warehouse/README.md`.

## Product direction (Tower BI Readiness System)

The product is the **Tower BI Agent Kit** (agent-first); its operating spine is the
**Tower BI Readiness System** -- seven readiness stages (Source -> Mapping -> Silver
-> Gold -> Semantic Model -> Dashboard -> Publish), each tracked with explicit
`status + evidence + blockers` (never a fake confidence score). The agent reads
readiness state to decide the one next allowed action; `retail check` /
`retail validate` are gates it calls, not the product.

- Roadmap (F005-F015 shipped; F016 gated, remaining): [`docs/roadmap/roadmap.md`](docs/roadmap/roadmap.md)
- The spine: [`docs/readiness/readiness-model.md`](docs/readiness/readiness-model.md)
- How it sits on the kit: [`docs/architecture/readiness-pipeline.md`](docs/architecture/readiness-pipeline.md)
- Agent operating rules: [`AGENTS.md`](AGENTS.md)

## Conventions

See [`docs/conventions.md`](docs/conventions.md). Design rationale lives in
[`docs/superpowers/specs/`](docs/superpowers/specs/).

## Notes for Windows

PBIP enforces a 260-char path limit; this repo intentionally sits at a short root
path. Line endings are handled by `.gitattributes` + `core.autocrlf=true`.
