# Tower BI Agent Kit

**Agent-first Retail BI readiness system for turning messy retail sources into governed Power BI-ready analytics.**

This repository is not just a collection of SQL scripts or Power BI files. It is a disciplined operating kit for an AI agent: profile the source, map the business meaning, build medallion tables, validate the result, define metrics, prepare the semantic model, design the dashboard, and only then publish.

> Product: **Tower BI Agent Kit**  
> Operating spine: **Tower BI Readiness System**  
> Substrate: **DigitalOcean PostgreSQL** medallion warehouse  
> BI target: **Power BI PBIP** reading from `gold` only

---

## What this repo does

Tower BI Agent Kit helps an agent or BI developer answer one question safely:

> Is this retail source ready to become trusted Power BI analytics?

The repo enforces a staged path:

```text
raw source
  -> source profile
  -> source map
  -> bronze landing
  -> silver typed/cleaned tables
  -> gold reporting mart
  -> metric contracts
  -> semantic model contract
  -> dashboard blueprint
  -> BI handoff / publish readiness
```

The key rule is simple:

```text
No source goes directly to silver.
No gold goes to Power BI before validation.
No dashboard is designed before metrics are defined.
No Power BI execution adapter runs before semantic-model readiness.
```

---

## Current status

Most of the readiness system is already on `main`.

| Area | Status |
|------|--------|
| Spec-Kit foundation | Shipped |
| Agent operating rules | Shipped |
| Source-mapping gate | Shipped |
| C086 pharmacy worked example | Shipped |
| `retail check` static governance gate | Shipped |
| `retail validate` live validation surface | Shipped |
| Readiness stages F005-F015 | Shipped |
| Power BI execution adapter F016 | Not built yet; deliberately gated and last |

F016 is execution-only. It must not define source mappings, metrics, semantic logic, or dashboard design.

---

## The seven readiness stages

Every source, table, model, or report should have an explicit readiness state: `status`, `evidence`, `blocking_reasons`, approvals, and the next allowed action.

| # | Stage | Gate enforced |
|---|-------|---------------|
| 1 | **Source Ready** | The source is profiled and understood. |
| 2 | **Mapping Ready** | Grain, keys, PII, and target placement are mapped and reviewed. |
| 3 | **Silver Ready** | Typed and cleaned silver tables exist and pass static checks. |
| 4 | **Gold Ready** | Reporting mart exists and live validation passes. |
| 5 | **Semantic Model Ready** | Metric contracts and governed Power BI model expectations exist. |
| 6 | **Dashboard Ready** | Report design consumes approved metrics only. |
| 7 | **Publish Ready** | Handoff pack is complete and publishing is approved. |

Readiness is never a fake numeric confidence score. It is evidence plus blockers.

---

## Architecture

```text
DigitalOcean PostgreSQL

  bronze  ->  silver  ->  gold  ->  Power BI PBIP
 landing     cleaned     mart       gold only

      ^
      |
manual load now; automated ingestion later
```

The repo separates responsibilities clearly:

| Layer | Responsibility |
|-------|----------------|
| Agent Experience | The agent reads readiness state and performs only the next allowed workflow. |
| Source Intelligence | Profiles sources, detects grain, maps business meaning, tracks drift. |
| Mapping Governance | Makes `source-map.yaml` reviewable before any silver SQL. |
| Validation & Readiness | Uses `retail check`, `retail validate`, quality control room, and reconciliation ledger. |
| Metrics & Semantic Model | Defines KPI packs, metric contracts, and semantic-model readiness. |
| Dashboard & Delivery | Produces dashboard blueprints and handoff packs; execution adapter comes last. |

---

## Repository layout

| Path | Purpose |
|------|---------|
| `AGENTS.md` | Short operating contract for AI agents. Read this first. |
| `.specify/` | Spec-Kit constitution and governance memory. |
| `specs/` | Feature specs, plans, tasks, and checklists. |
| `src/retail/` | The `retail` CLI package: static and live governance surfaces. |
| `warehouse/` | Tool-agnostic medallion SQL: `bronze`, `silver`, `gold`, migrations. |
| `powerbi/` | Power BI PBIP artifacts. Power BI reads `gold` only. |
| `pipelines/` | Ingestion area: manual now, automated feed later. |
| `templates/` | Generic blanks for profiles, maps, contracts, readiness, dashboard specs, handoff packs. |
| `mappings/` | Filled per-table source-mapping artifacts. One folder per table. |
| `metrics/` | Metric contracts and KPI packs. |
| `registries/` | Business meaning registry and Arabic/English retail dictionary. |
| `reports/` | Dashboard/page/visual blueprints and delivery artifacts. |
| `docs/readiness/` | The Tower BI Readiness System spine. |
| `docs/roadmap/` | Delivered roadmap and the remaining gated feature. |
| `docs/worked-examples/` | Worked examples, especially C086 pharmacy. |

---

## Start here as an agent

Read in this order:

1. `AGENTS.md` — what the agent can and cannot do.
2. `.specify/memory/constitution.md` — the full governance law.
3. `docs/readiness/readiness-model.md` — the seven-stage readiness spine.
4. `docs/architecture/readiness-pipeline.md` — how readiness sits on the kit.
5. `docs/worked-examples/c086-pharmacy.md` — the first filled example, not the schema.

Then inspect the target table/source readiness state and perform only the next allowed action.

Typical agent flow:

```text
read readiness status
  -> profile source
  -> draft source-map.yaml
  -> record assumptions/questions/issues
  -> stop for review if mapping is blocked
  -> build silver only after Mapping Ready passes
  -> build gold only after silver is clean
  -> validate gold before Power BI
  -> define metric contracts before dashboard design
  -> create handoff pack before publish
```

---

## Local development

This repo provides a Python package named `retail`.

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows Git Bash / PowerShell users may use the matching activate script
pip install -e .[dev]
pytest
```

Run the static governance gate:

```bash
retail check
```

Run live validation only when a database connection is configured:

```bash
pip install -e .[db]
retail validate --source-map mappings/<table>/source-map.yaml
```

Secrets must stay in `.env`, which is git-ignored. Never commit a real database host, DSN, password, or Power BI connection string.

---

## Environment

Copy the example env file and fill local values only:

```bash
cp .env.example .env
```

Expected live DB values may be provided through `DATABASE_URL` or the `ANALYTICS_DB_*` variables documented in the repo. If no DSN is available, agents must stay useful by authoring artifact structure, marking live values as pending, and never faking a validation pass.

---

## C086 worked example

C086 is the first serious worked example. It proves the workflow; it does not define the universal schema.

Use it to understand the pattern:

```text
docs/worked-examples/c086-pharmacy.md
mappings/<c086-table>/source-profile.md
mappings/<c086-table>/source-map.yaml
mappings/<c086-table>/assumptions.md
mappings/<c086-table>/unresolved-questions.md
mappings/<c086-table>/reconciliation-report.md
```

Generic templates must stay generic. Pharmacy-specific codes, segment rollups, and PII decisions belong only inside the C086 filled artifacts.

---

## Quality gates

The kit relies on two kinds of checks:

| Gate | Scope |
|------|-------|
| `retail check` | Static checks over committed SQL, TMDL/PBIR, config, docs, and repo text. |
| `retail validate` | Live checks against the database: PK uniqueness, date coverage, orphan FKs, reconciliation, and source-map-driven validation. |

A green static check is necessary but not sufficient. Semantic correctness requires the live validation boundary when a database is available.

---

## Power BI policy

Power BI is the reporting target, not the source of truth.

Rules:

- Power BI reads from `gold` only.
- Measures must trace to metric contracts.
- Dashboard blueprints must not invent KPIs.
- PBIP artifacts must stay source-control friendly.
- Publishing/execution automation is deferred until semantic-model readiness passes.

F016 is the future Power BI execution adapter. It is intentionally last.

---

## Roadmap

The roadmap is now a delivered ledger:

- F005-F015 are shipped to `main`.
- F016 remains unbuilt by design.
- Any new feature must improve exactly one readiness stage.
- Docs, templates, and checklists come before automation.

Read the full roadmap here:

```text
docs/roadmap/roadmap.md
```

---

## Non-goals right now

This repo is not currently trying to be:

- a full automatic dashboard generator,
- a Fabric deployment platform,
- an ML forecasting system,
- a universal ERP connector,
- a fully automated mapping approval engine,
- a Power BI execution-first tool.

The product is a small governed Retail BI factory: agent-led, evidence-based, and blocked by real BI gates before business delivery.
