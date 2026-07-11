<div align="center">

<img src="assets/brand/seshat-bi-hero.svg" alt="Seshat BI -- Retail BI Readiness System -- From messy retail data to trusted, governed BI." width="820" />

<br/>

An agent-first Retail BI readiness system: profile the source, map its meaning,
build the medallion warehouse, validate it, define metrics, prepare the semantic
model, design the dashboard -- and only then publish.

<br/>

[![status](https://img.shields.io/badge/status-active-0B9A9A?style=flat-square&labelColor=001E35)](#what-is-built-today)
[![warehouse](https://img.shields.io/badge/warehouse-PostgreSQL-0B9A9A?style=flat-square&logo=postgresql&logoColor=F7F1E7&labelColor=001E35)](#architecture)
[![BI](https://img.shields.io/badge/BI-Power%20BI%20PBIP-C69214?style=flat-square&logo=powerbi&logoColor=001E35&labelColor=001E35)](#power-bi-policy)
[![governance](https://img.shields.io/badge/gate-retail%20check-0B9A9A?style=flat-square&labelColor=001E35)](docs/glossary.md)
[![python](https://img.shields.io/badge/python-3.13-C69214?style=flat-square&logo=python&logoColor=F7F1E7&labelColor=001E35)](#quickstart)
[![license](https://img.shields.io/badge/license-Apache--2.0-0B9A9A?style=flat-square&labelColor=001E35)](LICENSE)

</div>

---

## Why Seshat

Seshat was the ancient Egyptian figure of writing, measurement, and record
keeping -- you mapped and documented the world before you built on it. This tool
takes the same stance toward retail data: **nothing advances without recorded
evidence and a passed gate.**

Seshat BI answers one question, safely:

> Is this retail source ready to become trusted Power BI analytics?

It is not a pile of SQL scripts and `.pbix` files. It is a disciplined operating
kit for an AI agent (or a BI developer) that refuses to skip a step. Readiness is
never a faked confidence score -- it is `status` + `evidence` + `blocking_reasons`.

> [!NOTE]
> **Naming.** The product is **Seshat BI** (CLI / package alias `Seshat_BI`).
> It was previously developed under the internal name *Tower BI Agent Kit*; the
> governance spine is still called the **Readiness System**. Same product, one brand.

---

## The seven-star readiness spine

The seven points of the Seshat star are the seven readiness stages. Each is a
gate: a stage is never entered before the prior one passes.

```mermaid
flowchart LR
    RAW([raw source]):::raw
    S1[1 - Source Ready<br/><sub>profiled and understood</sub>]:::stage
    S2[2 - Mapping Ready<br/><sub>grain / keys / PII / placement</sub>]:::stage
    S3[3 - Silver Ready<br/><sub>typed, cleaned, statically clean</sub>]:::stage
    S4[4 - Gold Ready<br/><sub>Kimball mart + live-validated</sub>]:::stage
    S5[5 - Semantic Model Ready<br/><sub>metric contracts + governed model</sub>]:::stage
    S6[6 - Dashboard Ready<br/><sub>designed from approved metrics</sub>]:::stage
    S7[7 - Publish Ready<br/><sub>handoff pack, approved to publish</sub>]:::stage

    RAW --> S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7

    classDef raw fill:#E8D8BD,stroke:#001E35,stroke-width:1px,color:#001E35;
    classDef stage fill:#001E35,stroke:#C69214,stroke-width:1.5px,color:#F7F1E7;
```

The ordering is non-negotiable, and the gates are the product:

> [!IMPORTANT]
> - No source goes directly to silver.
> - No gold reaches Power BI before validation.
> - No dashboard is designed before its metrics are defined.
> - No Power BI execution runs before semantic-model readiness.

---

## Quickstart

Seshat BI ships a Python package exposing two console commands -- `retail` (the
canonical dev name) and `seshat` (the product-brand alias); both dispatch the same
entry point, so every command below works under either name.

```bash
# clone
git clone https://github.com/ahmed-shaaban-94/Seshat_BI.git
cd Seshat_BI

# install (editable, with dev extras)
python -m venv .venv
. .venv/Scripts/activate          # Windows Git Bash / PowerShell: use the matching activate
pip install -e ".[dev]"

# run the static governance gate over the whole repo
retail check                       # exit 0 == the repo is governance-clean
seshat check                       # same command, product-brand alias
```

> New user starting a fresh project? `seshat init-project my-retail-bi` scaffolds an
> empty workspace. Install-path details: [`docs/install/user-install.md`](docs/install/user-install.md).

No console script? With the package installed, the checker also runs as a
module -- and from a bare uninstalled clone, prefix with `PYTHONPATH=src`:

```bash
python -m retail.cli check --repo .
PYTHONPATH=src python -m retail.cli check --repo .   # bare clone, no install
```

Tests:

```bash
pytest -m unit -q                  # fast unit suite
```

Live validation and the DAX/value surfaces run only when a database connection
is configured (the driver import is lazy, so the rest of the kit works with no
DB):

```bash
pip install -e ".[db]"
retail validate       --source-map mappings/<table>/source-map.yaml   # gold-layer live checks
retail semantic-check --repo .                                        # L3 contract<->DAX drift
retail value-check    --repo .                                        # L4 value proxy (approved value vs live aggregate)
```

> [!IMPORTANT]
> Secrets live only in `.env` (git-ignored). Never commit a real database host,
> DSN, password, or Power BI connection string. Copy `.env.example` to `.env` and
> fill local values; if no DSN is available, the agent stays useful by authoring
> artifact structure and marking live values as pending -- it never fakes a pass.

---

## What is built today

Everything below is on `main`, each with a written spec (under `specs/` or
`docs/superpowers/specs/`) and held by the `retail check` gate. (For what is
planned but not yet built, see the [Roadmap](#roadmap).)

| Capability | What it gives you |
|------------|-------------------|
| **Spec-Kit foundation + agent constitution** | The governance law every workflow obeys (`.specify/memory/constitution.md`). |
| **Source-mapping gate** | `source-map.yaml` must be reviewed before any silver SQL is written. |
| **`retail check` (static gate)** | A static gate over committed SQL, TMDL/PBIR, config, docs, and repo text (rule catalog: `docs/glossary.md`); the exit code is the authority. |
| **`retail validate` (live surface)** | PK uniqueness, date coverage, orphan FKs, reconciliation, source-map-driven checks. |
| **DAX governance L1-L2** | DAX best-practice rules `D1`-`D11` enforced statically inside `retail check` (single-quote handling, `ALL`-variants, dollar-quote tokenizer, and more). |
| **`retail semantic-check` (L3 contract drift)** | Detects when a committed measure's denominator drifts from its metric contract. |
| **`retail value-check` (L4 value proxy)** | Recomputes a measure's live aggregate and compares it to an owner-approved expected value within tolerance -- never fakes a pass. |
| **`retail generate` (DAX Generator)** | Generates a verified best-practice DAX measure from an approved metric contract, with a self-proving loop. |
| **`retail status` (agent-control surface)** | A read-only `--format json` projection of committed readiness state (per-table `current_stage`, `evidence`, `blocking_reasons`, `next_action`) for an agent/host to poll -- a projection of committed evidence, never a computed or fabricated score. |
| **`seshat` command + `init-project`** | `seshat` is the product-brand alias of `retail` (same entry point). `seshat init-project <name>` scaffolds a fresh, empty Retail-BI project workspace for a new user. |
| **PBIR authoring adapters** | Deterministic, local-file, reviewable writers for committed PBIR JSON: `pbir-apply-theme`, `pbir-format-visual`, `pbir-set-page-background`, `pbir-set-geometry` -- style/lay out existing bound visuals; never create/retype a visual or grant a stage. Publish/execution stays gated (F016). |
| **Readiness spine (F005-F015, incl. F011A)** | The full seven-stage model: source intelligence, grain confidence, metric contracts, semantic-model readiness, dashboard design + the four-surface Visual Foundation, QC control room, reconciliation ledger, drift detector. |
| **Companion Modules & Adapters (F025-F030)** | Six docs-first skills: PR readiness reviewer, readiness viewer, approval console, evidence-pack generator, and optional **dbt** / **Dagster** adapters (advisory only -- they never create truth). |
| **F034 authoring slice** | The trace template, Dashboard Ready evidence item, and the read-only visual-implementation-review workflow (the built page itself stays a human Power BI Desktop action). |
| **C086 pharmacy worked example** | A complete, filled run of the pipeline -- proof of the pattern, not the universal schema. |
| **retail_store_sales worked example** | The validated worked example -- traverses the full seven-stage spine (to Dashboard Ready, Publish Ready `warning`) -- proves the generic playbook (no returns; PII kept; English-only). |

A green static check is necessary but not sufficient: semantic correctness needs
the live validation boundary when a database is available.

---

## Architecture

```mermaid
flowchart LR
    SRC([raw source]):::raw
    B[bronze<br/><sub>landing</sub>]:::med
    S[silver<br/><sub>cleaned</sub>]:::med
    G[gold<br/><sub>Kimball mart</sub>]:::gold
    PBI[Power BI PBIP<br/><sub>reads gold only</sub>]:::pbi

    SRC -.->|manual load now, automated later| B
    B --> S --> G --> PBI

    subgraph DO [DigitalOcean PostgreSQL]
        B
        S
        G
    end

    classDef raw fill:#E8D8BD,stroke:#001E35,color:#001E35;
    classDef med fill:#001E35,stroke:#0B9A9A,stroke-width:1.5px,color:#F7F1E7;
    classDef gold fill:#001E35,stroke:#C69214,stroke-width:2px,color:#F2C14E;
    classDef pbi fill:#0B9A9A,stroke:#001E35,stroke-width:1.5px,color:#F7F1E7;
    style DO fill:#F7F1E7,stroke:#C69214,stroke-dasharray:4 3,color:#001E35;
```

Responsibilities stay separated; Power BI is the reporting target, never the
source of truth.

| Layer | Responsibility |
|-------|----------------|
| **Agent Experience** | Reads readiness state, performs only the next allowed action. |
| **Source Intelligence** | Profiles sources, detects grain, maps business meaning, tracks drift. |
| **Mapping Governance** | Makes `source-map.yaml` reviewable before any silver SQL. |
| **Validation & Readiness** | `retail check`, `retail validate`, QC control room, reconciliation ledger. |
| **Metrics & Semantic Model** | KPI packs, metric contracts, semantic-model readiness. |
| **Dashboard & Delivery** | Dashboard blueprints and handoff packs; execution adapter comes last. |

---

## Start here as an agent

**Agent Mode** -- the guarded loop (inspect -> `seshat status` -> `seshat next`
-> do only the next allowed action -> `seshat check` -> stop at the gate) is
documented in [`docs/agent-mode.md`](docs/agent-mode.md). `seshat next
--format agent` (or `--format json` for hosts) answers: current stage,
readiness state, evidence, blockers, next allowed action, forbidden scope,
validation commands, and the stop point.

Read in this order, then act on the target's readiness state -- and only the next
allowed action:

1. `AGENTS.md` -- the short operating contract: what the agent can and cannot do.
2. `.specify/memory/constitution.md` -- the full governance law.
3. `docs/readiness/readiness-model.md` -- the seven-stage spine.
4. `docs/architecture/readiness-pipeline.md` -- how readiness sits on the kit.
5. `docs/worked-examples/retail-store-sales.md` -- the filled worked example; the full spine to Dashboard Ready.
6. `docs/worked-examples/README.md` -- the worked-examples index (which to read when).

<details>
<summary><b>Typical agent flow</b></summary>

```text
read readiness status
  -> profile source
  -> draft source-map.yaml
  -> record assumptions / questions / issues
  -> STOP for review if mapping is blocked
  -> build silver only after Mapping Ready passes
  -> build gold only after silver is clean
  -> validate gold before Power BI
  -> define metric contracts before dashboard design
  -> create handoff pack before publish
```

</details>

---

## Repository layout

| Path | Purpose |
|------|---------|
| `AGENTS.md` | Operating contract for AI agents. Read first. |
| `.specify/` | Spec-Kit constitution and governance memory. |
| `src/retail/` | The `retail` CLI package: static + live governance surfaces. |
| `warehouse/` | Tool-agnostic medallion SQL: `bronze` / `silver` / `gold` + migrations. |
| `powerbi/` | Power BI PBIP artifacts. Power BI reads `gold` only. |
| `specs/` | Feature specs, plans, tasks, checklists (one directory per feature; see `specs/README.md`). |
| `mappings/` | Filled per-table source-mapping artifacts, one folder per table. |
| `templates/` | Generic blanks: profiles, maps, contracts, readiness, dashboards, handoff packs. |
| `reports/` | Dashboard / page / visual blueprints and delivery artifacts. |
| `pipelines/` | Ingestion area: manual now, automated feed later. |
| `docs/readiness/` | The seven-stage Readiness System spine. |
| `docs/roadmap/` | Delivered ledger + the planned companion tier. |
| `docs/brand/` | The **Seshat BI** visual identity and brand rules. |
| `assets/brand/` | Committed brand assets (logo, seven-point star). |

---

## Power BI policy

Power BI is the reporting target, not the source of truth.

- Reads from `gold` only.
- Every measure traces to a metric contract; blueprints invent no KPIs.
- PBIP artifacts stay source-control friendly (plain-text TMDL/PBIR).
- Publishing / execution automation is deferred until semantic-model readiness passes.

---

## Roadmap

The originally-specified sequence (**F005-F015, including F011A**) is fully
shipped to `main`. What remains is deliberately **human-gated** or **deferred for
want of a consumer** -- never blocked by missing effort:

> [!WARNING]
> The items below are **not current capabilities.** Do not treat a gated or
> deferred feature as if it were shipped.

| Remaining item | State | Why it waits |
|----------------|-------|--------------|
| **F016 -- Power BI execution adapter** | gated, by design | Execution-only (materializes/publishes an already-approved model; cannot define metrics, mappings, semantic logic, or dashboard design). Deliberately last; not startable before `semantic_model_ready` is `pass`. |
| **F034 built page** | human action | The agent ships the trace template + review workflow; a person builds the approved design in Power BI Desktop and commits the PBIR. |
| **F024 + F031-F033** | spec-only | Companion architecture doc + maintenance automation -- no runtime consumer yet (the adapters they would maintain are docs-only skills). |
| **pbi-tools extract / L3 new operators** | deferred | Revisit when a real `.pbix` + installed toolchain (pbi-tools) or a real predicate consumer (L3) appears. |

> [!NOTE]
> The **Companion Modules & Adapters** that *did* ship (F025-F030 -- PR readiness
> reviewer, readiness viewer, approval console, evidence-pack generator, and the
> optional **dbt** / **Dagster** adapters) are listed under
> [What is built today](#what-is-built-today). dbt and Dagster are *optional
> companion engines* and advisory only -- they never create truth.

Guiding rules: any new feature must improve exactly one readiness stage, and
docs / templates / checklists come before automation. Full ledger:
[`docs/roadmap/roadmap.md`](docs/roadmap/roadmap.md).

---

## What this is not

Seshat BI is a small, governed Retail BI factory -- agent-led, evidence-based, and
blocked by real BI gates before delivery. It is deliberately **not**:

- a one-click automatic dashboard generator,
- a Fabric deployment platform,
- an ML / forecasting system,
- a universal ERP connector,
- a fully automated mapping-approval engine,
- a Power BI execution-first tool.

---

## Brand

The public identity is **Seshat BI**: a seven-point gold star (canonical truth and
the seven readiness gates), a teal data network (lineage and the BI model), and the
seated Seshat figure with a stylus (mapping and documentation before transformation).
The star is always seven-pointed.

<div align="center">
<img src="assets/brand/seshat-bi-brand-board.png" alt="Seshat BI brand board: logo system and palette" width="640" />
</div>

Full guide: [`docs/brand/visual-identity.md`](docs/brand/visual-identity.md) --
reusable mark: [`assets/brand/seshat-seven-star.svg`](assets/brand/seshat-seven-star.svg).

Palette: `deep_navy #001E35` | `rich_gold #C69214` | `teal #0B9A9A` | `ivory #F7F1E7`.

---

## Contributing

- Commit subjects follow `<type>: <description>` (`feat` / `fix` / `refactor` /
  `docs` / `chore` / `build` / `ci` / `perf` / `test` / `style` / `revert` / `brand`),
  **scope-free** -- no `docs(018):` parentheses (governance rule P2). An automated
  `[bot] ...` subject prefix is exempt.
- Conventions: [`docs/conventions.md`](docs/conventions.md).
- Glossary (terms, abbreviations, rule ids): [`docs/glossary.md`](docs/glossary.md).
- Contributing (setup, local checks, PR flow): [`CONTRIBUTING.md`](CONTRIBUTING.md).
- FAQ (common questions, with sources): [`docs/faq.md`](docs/faq.md).
- Release notes: [`RELEASE_NOTES.md`](RELEASE_NOTES.md) -- and the v0.1 snapshot [`docs/releases/v0.1.md`](docs/releases/v0.1.md).
- Local verification (mirrors CI intent): [`docs/quality/local-verification.md`](docs/quality/local-verification.md).
- Guided demo (worked example): [`docs/demo/retail-store-sales-demo.md`](docs/demo/retail-store-sales-demo.md).
- Capability snapshot: [`docs/quality/post-idea-bank-capability-state.md`](docs/quality/post-idea-bank-capability-state.md) -- what works now / planned / forbidden / needs-ruling / needs-data, by layer.
- Net Sales end-to-end trace (paper proof of one KPI path): [`docs/demo/net-sales-end-to-end-readiness-trace.md`](docs/demo/net-sales-end-to-end-readiness-trace.md).
- Big Data strategy (scale is a condition, not a tool): [`docs/big-data/big-data-capability-report.md`](docs/big-data/big-data-capability-report.md) + the assessment templates [`docs/big-data/data-volume-assessment.md`](docs/big-data/data-volume-assessment.md).
- Integration smoke test for the idea-bank features: [`docs/quality/top-idea-bank-integration-smoke-test.md`](docs/quality/top-idea-bank-integration-smoke-test.md).
- Before a PR, `retail check` must pass and committed text must be ASCII / UTF-8
  without BOM.
- License: Apache-2.0 (see [LICENSE](LICENSE)).

<div align="center">
<br/>
<sub>Seshat BI -- governed knowledge, measured structure, trusted BI.</sub>
</div>
