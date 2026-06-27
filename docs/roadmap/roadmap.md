# Seshat BI -- Roadmap

- **Status:** Delivered ledger + a partly-shipped companion tier. As of 2026-06-25 the
  entire originally-spec'd sequence (F005-F015, incl. F011A) is **SHIPPED** to
  `main`; **F016 (the Power BI execution adapter -- official Power BI MCP /
  connection; `pbi-cli` no longer preferred) remains the only parked feature of
  that original sequence** -- deliberately LAST, execution-only, and gated (hard
  rule #6). Separately, the **Companion Modules & Adapters tier (F024-F034)** is
  **PARTLY SHIPPED** (status corrected 2026-06-26): six of its features (F025-F030)
  shipped as docs-first skills under `.claude/skills/`; F024 + F031-F033 remain
  spec-only; and **F034's authoring slice shipped 2026-06-26** (its built-page
  worked example remains a human Power BI Desktop action -- see Tier 5) -- see Tier 5
  below for the verified per-feature status. Beyond that, the DAX-fortification
  follow-on (L4 value proxy) shipped 2026-06-26 (`retail value-check`); the
  `$$`-tokenizer fix and the F038 BPA spike shipped; the pbi-tools extract spike and
  the L3 new predicate ops were assessed and DEFERRED for want of a consumer/target
  (see `docs/superpowers/specs/`). Additionally, the **idea-bank execution sequence
  (A1/B2/B1/F7/F8) SHIPPED 2026-06-27** (PRs #62-#66) -- five gated items drawn from
  the exploratory idea bank; A1 + B1 take the static `retail check` gate to 33 rules
  (see the Idea-Bank section below). This doc records what was delivered, the one
  original feature still parked, and the companion tier's true state.
- **Product identity:** **Seshat BI** is the product (package alias `Seshat_BI`;
  previously developed under the internal name *Tower BI Agent Kit*). The
  **Readiness System** is the operating spine inside it.
- **Read first:** `docs/readiness/readiness-model.md` (the spine),
  `docs/architecture/readiness-pipeline.md` (how it sits on the existing kit).

## Autonomous roadmap run -- closure (2026-06-26)

The 2026-06-26 autonomous run is **closed**. Every prioritized item (the
ADR-0013 / autopilot DAX-fortification sequence #1-#5, plus the surfaced #6/#7)
is shipped or deferred for a stated cause -- verified by a closure audit
(8 independent adversarial checks; 8/8 outcomes accurate; zero new feature code
for any deferred/gated item).

| Item | Outcome | Where |
|------|---------|-------|
| `$$` dollar-quote tokenizer | **SHIPPED** | PR #37 (`31a508c`) |
| F038 Tabular Editor BPA spike | **SHIPPED** (six-gate PASS) | PR #38 (`9eccd43`) |
| pbi-tools extract spike | **DEFERRED** -- no `.pbix` target, no installed toolchain | PR #40 evidence; `docs/superpowers/specs/2026-06-26-pbi-tools-extract-spike-deferred.md` |
| L4 value proxy (`retail value-check`) | **SHIPPED** | PR #40 (`9e17dca`) |
| L3 new predicate operators | **DEFERRED** -- no consumer | PR #41; `docs/superpowers/specs/2026-06-26-l3-new-operators-deferred.md` |
| Tier-5 roadmap accuracy + L3 deferral record | **SHIPPED** (docs) | PR #41 (`90bf8de`) |
| F034 authoring slice | **SHIPPED** (built page = human Desktop action) | PR #43 (`a503448`) |

**Remaining work is human / gated only -- no agent-buildable item is left:**

- **F016 (Power BI execution adapter)** -- gated by hard rule #6 (not startable
  before Semantic Model Ready is `pass`); execution-only; deliberately last.
- **F034 built page** -- a human builds the approved design in Power BI Desktop and
  commits the PBIR; the agent's procedure + trace + review are ready, and the gate
  already permits the build.
- **F031-F033 (maintenance automation)** -- no consumer yet (the adapters they
  would maintain are docs-only skills); revisit when an adapter has a runtime.
- **pbi-tools / L3 new ops** -- revisit when a real `.pbix` workflow / installed
  toolchain (pbi-tools) or a real predicate consumer (L3) appears.

> The kit already ships an agent-first constitution, a source-mapping gate, the
> Spec-Kit foundation, the C086 worked example, a 33-rule static `retail check`
> (31 from the original sequence + A1/B1 from the idea-bank sequence),
> and a `retail validate` live surface. This roadmap reconciles that foundation
> (feature 001-004 + the orchestration/builder slices) with the readiness
> direction: every future feature advances one **readiness stage**.

## What the readiness spine answers

For every source / table / report, the spine must answer -- with **evidence and
blockers, never a hallucinated confidence score**:

| Question | Where it is answered |
|----------|----------------------|
| Where are we now? | `current_stage` in the readiness status |
| What artifacts exist? | `evidence[]` (committed files) |
| What checks passed? | stage `checks` + `retail check` / `retail validate` exit codes |
| What blockers remain? | `blocking_reasons[]` |
| Who must approve? | `approvals[]` (named owner) |
| What is the next allowed action? | `next_action` (one step) |

## Core readiness stages

The seven stages the spine tracks (detail per stage under `docs/readiness/`):

| # | Stage | Gate it enforces |
|---|-------|------------------|
| 1 | **Source Ready** | a profiled, understood source exists |
| 2 | **Mapping Ready** | grain/PK/PII/placement mapped + reviewed (the source-mapping gate) |
| 3 | **Silver Ready** | typed/cleaned silver built + statically clean |
| 4 | **Gold Ready** | Kimball star built + live-validated (PK/coverage/orphans/reconcile) |
| 5 | **Semantic Model Ready** | metric contracts + governed PBIP model |
| 6 | **Dashboard Ready** | report designed against approved metric contracts |
| 7 | **Publish Ready** | handoff pack complete; approved to publish |

No stage is entered before the prior stage is `pass`. The hard rules below make
the ordering non-negotiable.

## Six product layers

The kit's surfaces, top (what the user touches) to bottom (later adapter):

| Layer | Name | What it is | Status |
|-------|------|------------|--------|
| 1 | **Agent Experience** | the agent + skills are the interface; CLI is a gate it calls | shipped (conductor + verbs) |
| 2 | **Source Intelligence** | profile, business meaning, Arabic retail dictionary, drift detector | shipped (F006-F007, F014) |
| 3 | **Mapping Governance** | the source-mapping gate, grain confidence, mapping diff | shipped (gate + F008) |
| 4 | **Validation & Readiness** | `retail check` / `retail validate` + the readiness spine, QC room, ledger | shipped (checks + F005, F012, F015) |
| 5 | **Metrics & Semantic Model** | metric contracts, KPI packs, governed PBIP model | shipped (F009-F010) |
| 6 | **Dashboard & Delivery** | dashboard design, handoff pack; Power BI execution adapter | shipped (F011, F011A, F013); **F016 execution adapter remains (official Power BI MCP / connection; execution-only, gated, last)** |

## Feature sequence

Each feature advances a readiness stage. **The entire sequence below (F005-F015,
incl. F011A) is SHIPPED.** The single remaining feature is **F016 (the Power BI
execution adapter -- official Power BI MCP / connection; `pbi-cli` no longer preferred)**
-- the next executable slice, deliberately LAST, execution-only, and gated on
semantic-model readiness (hard rule #6). The tables below are kept as a delivered
ledger (catalog + commit refs); the original Now/Next/Then/Later tiers are retained
as the historical authoring order.

> **Numbering note (spec-dir vs roadmap F-number).** The roadmap F-number is the
> authoritative sequence id. Spec *directory* numbers under `specs/` are allocated
> from the next free on-disk slot when drafted, so they can differ from the F-number.
> The features F006-F015 were batch-drafted into `specs/007-016/` (which already held
> 001-006), giving a consistent **spec-dir = roadmap-F + 1** offset for that batch:
> 007=F006, 008=F007, 009=F008, 010=F009, 011=F010, 012=F011, 013=F012, 014=F013,
> 015=F014, 016=F015. F011A (Power BI Visual Foundation) was drafted later into the
> next free on-disk slot: spec-dir 017 = F011A. When a `specs/0NN-*` directory and a
> roadmap F-number disagree, the roadmap row wins; each spec's own header states both
> numbers.

### Tier 1 (authored first) -- SHIPPED

| Feature | Name | Layer | Advances stage | One-line scope | Shipped |
|---------|------|-------|----------------|----------------|---------|
| **005** | Retail Readiness Model | 4 | the spine itself (all stages) | the readiness state model + status template + per-stage docs (this slice's home) | yes (spine docs on `main`) |
| **006** | Table Onboarding Wizard | 1-2 | Source -> Mapping | an agent workflow that walks a new table through profile -> map -> gate | `f75159e` |
| **007** | Business Meaning Registry + Arabic Retail Dictionary | 2 | Source Ready | a generic registry of business terms + an Arabic<->English retail term dictionary (generic, not C086 values) | `7dfbcf5` |

### Tier 2 -- SHIPPED

| Feature | Name | Layer | Advances stage | One-line scope | Shipped |
|---------|------|-------|----------------|----------------|---------|
| **008** | Grain Confidence + Mapping Diff Reviewer | 3 | Mapping Ready | surface grain-uniqueness confidence + a reviewable diff between mapping versions | `2a3eeec` |
| **009** | Metric Contract Store + Retail KPI Packs | 5 | Semantic Model Ready | a store of metric definitions (name, grain, formula intent, owner) + generic retail KPI packs | `0a4347c` |
| **010** | Semantic Model Readiness | 5 | Semantic Model Ready | readiness checks for the PBIP model (relationships, date table, measures bind to contracts) | `8fa6bbf` |

### Tier 3 -- SHIPPED

| Feature | Name | Layer | Advances stage | One-line scope | Shipped |
|---------|------|-------|----------------|----------------|---------|
| **011** | Power BI Dashboard Design Skill | 6 | Dashboard Ready | an agent skill that designs a dashboard FROM approved metric contracts (no contracts -> no design) | `ecbb518` |
| **011A** | Power BI Visual Foundation | 6 | Dashboard Ready | the design FOUNDATION the F011 verb reasons with (four-surface router + generic templates/tokens/theme/blueprints; defines no new gate) | `53d43f1` |
| **012** | Data Quality Control Room | 4 | all stages | a consolidated view of data-quality findings + blockers across tables | `e9a3264` |
| **013** | BI Handoff Pack | 6 | Publish Ready | the documentation/evidence bundle handed to a BI consumer | `f00ff13` |

### Tier 4 -- SHIPPED (except F016)

| Feature | Name | Layer | Advances stage | One-line scope | Shipped |
|---------|------|-------|----------------|----------------|---------|
| **014** | Source Drift Detector | 2 | Source Ready | detect when a source's shape/semantics drift from its profile | `70914d4` |
| **015** | Reconciliation Ledger | 4 | Gold Ready | a durable ledger of cross-layer reconciliation results over time | `0eefe57` |
| **016** | Power BI Execution Adapter (official Power BI MCP / connection) | 6 | Dashboard/Publish | the deferred, EXECUTION-ONLY Power BI adapter -- materializes/publishes an already-approved model; cannot define metrics, mappings, semantic logic, or dashboard design. LAST, gated on semantic-model readiness. (`pbi-cli` is no longer the preferred path; the official Power BI MCP / connection is the preferred future adapter.) | **NOT BUILT -- the only remaining feature (gated, by design)** |

### Tier 5 -- Companion Modules & Adapters (F024-F034) -- PARTLY SHIPPED

Authored by the 2026-06-25 companion-modules audit
(`docs/superpowers/specs/2026-06-25-companion-modules-adapters-audit.md`). **Status
corrected 2026-06-26 (verified against the tree):** SIX of these shipped as
docs-first skills under `.claude/skills/` (per hard rule #8 -- a skill is a doc, not
runtime Python; no `src/retail/` change by design). The remaining four are genuinely
unbuilt -- see the Status column and the per-feature notes below; the earlier blanket
"PLANNED (specs drafted, not built)" header was stale once the skills landed. The
binding rule is unchanged: **Core Authority owns truth** -- a module/adapter may READ,
SUMMARIZE, VISUALIZE, write DERIVED evidence, or EXECUTE an approved step, but MUST NOT
create truth (no self-granted approval, no defining business meaning, no approving
metrics/mappings, no publishing Power BI, no moving a readiness stage to `pass` without
the required evidence + named human approval). F029 (dbt) and F030 (Dagster) are
OPTIONAL companion engines, not roadmap precursors to F016. F016 remains the
deliberately-last, bottom-of-stack execution-only adapter; nothing in this tier
sequences before it or assumes it exists.

| Feature | Name | F024 category | Spec dir | Status (verified 2026-06-26) |
|---------|------|---------------|----------|------------------------------|
| **F024** | Companion Tools Architecture | (defines the 5 categories) | `018` | spec-only (the DECISION ships as `docs/decisions/0008`; the six companions below already build against it -- only the spec doc itself is unwritten) |
| **F025** | PR Readiness Reviewer | Product Module (read-only) | `019` | **SHIPPED** -- `.claude/skills/pr-readiness-reviewer/` |
| **F026** | Readiness Viewer | Product Module (read-only) | `020` | **SHIPPED** -- `.claude/skills/readiness-viewer/` |
| **F027** | Approval Console | Product Module (artifact-writing) | `021` | **SHIPPED** -- `.claude/skills/approval-console/` |
| **F028** | Evidence Pack Generator | Product Module (artifact-writing) | `022` | **SHIPPED** -- `.claude/skills/evidence-pack-generator/` |
| **F029** | dbt Transformation Adapter | Execution Adapter (DB-connected) | `023` | **SHIPPED** -- `.claude/skills/dbt-transformation-adapter/` (+ ADR `0009`) |
| **F030** | Dagster Orchestration Adapter | Execution Adapter (orchestrator) | `024` | **SHIPPED** -- `.claude/skills/dagster-orchestration-adapter/` (+ ADR `0010`) |
| **F031** | Adapter Maintenance & Auto-Update Policy | Maintenance Automation | `025` | spec-only -- **no consumer yet** (the dbt/dagster adapters are docs-only skills + templates; there is no running runtime to maintain). Defer until an adapter has a runtime. ADR `0011` allotted. |
| **F032** | Adapter Compatibility Matrix | Maintenance Automation | `026` | spec-only -- same no-consumer reason as F031 |
| **F033** | Release & Maturity Management | Maintenance Automation / Skill | `027` | spec-only -- same no-consumer reason as F031 |
| **F034** | Visual Implementation MVP | Dashboard & Delivery (manual build, F016-independent) | `039` | **Authoring slice SHIPPED 2026-06-26** (spec `Finalized`) -- the three generic artifacts exist: the trace template (`templates/visual-implementation-trace.md`), the Dashboard Ready evidence-item edit (`docs/readiness/dashboard-ready.md`), and the review workflow (`.claude/skills/powerbi-dashboard-design/workflows/visual-implementation-review.md`). The **built page itself remains a human Power BI Desktop action** (US-1/SC-001/SC-007/FR-013 UNMET by design -- FR-008/FR-009 forbid agent-generated PBIR): `mappings/retail_store_sales/design/dashboard-layout.md` (approved design) + the committed PBIR report (`powerbi/RetailStoreSales.Report/`, page still empty) await a human's Desktop build, which the gate (`semantic_model_ready: pass` + design-review sign-off) already permits. |

> **Numbering (spec-dir vs F-number) for this tier.** Spec dirs were allocated
> from the next free on-disk slot, giving **spec-dir = F-number - 6** for F024-F033
> (018=F024 ... 027=F033). **F034** (Visual Implementation MVP) was drafted later
> into the next free slot **039** (the feature script numbers from the current max
> on-disk dir, not the first gap). When a `specs/0NN-*` dir and an F-number
> disagree, this roadmap row wins; each spec's own header states both. The
> **append-only ADR allotment** for the four new ADRs this tier authors is fixed
> here: 0008 (F024), 0009 (F029), 0010 (F030), 0011 (F031) -- shipped ADRs are
> 0001-0007 and are never reused.

## Idea-Bank execution sequence (A1/B2/B1/F7/F8) -- SHIPPED (2026-06-27)

A separate, gated five-PR sequence taken from the **idea bank**
(`docs/roadmap/idea-backlog.md`) via the approved plan
(`docs/planning/top-idea-bank-execution-plan.md`). The idea bank remains
exploratory; selection there was not a commitment -- each item still passed the
normal feature discipline (small PR, one family, review, CI green) before
shipping. All five are now **merged to `main`** (PRs #62-#66). Two add static
`retail check` rules (A1, B1); three are docs/CLI surface (B2, F7, F8). None
advances a readiness stage, grants an approval, or touches the gated F016
execution path.

| Idea | Name | Layer | What shipped | PR / commit |
|------|------|-------|--------------|-------------|
| **A1** | Route Registry Manifest | 1 (routing integrity) | `docs/routing/routes.yaml` (mirrors the knowledge-map routes 1-22) + static rule **A1** (`src/retail/rules/routes.py`): a `built` route target must resolve to a tracked file; a `planned` target must not yet exist (stale marker) -- honest both directions, read-only, lazy `yaml`. | #62 (`abbbd73`) |
| **B2** | Structured Findings Output | 4 (observability) | `retail check --format {text,json}`; default text output preserved **byte-for-byte** (proven by diff vs `main`); opt-in `run_json()` emits `{"findings":[...],"exit_code":N}`; `Finding.to_dict()` + `FindingDict`. No rule behavior changed. | #63 (`ca1431c`) |
| **B1** | Never-Execute Invariant Guard | 4 (invariant protection) | Static rule **B1** (`src/retail/rules/never_execute.py`): stdlib-`ast` scan of the static-core modules (cli/runner/core/registry/rules) for a **module-scope** DB/network import (psycopg2, requests, socket, http, urllib.request, ...). Lazy in-handler imports stay allowed; `urllib.parse` allowed; an unparseable module fails loud. Never opens a connection. | #64 (`9d12589`) |
| **F7** | KPI Decision-Question Index | 5 (KPI usability) | A "Decision questions this domain answers" section in all 11 `skills/retail-kpi-knowledge/domains/*.md`; each question routes to a real `contracts/*.md` (Seeded) or an honest `--`/Planned marker. Pure docs in the KPI meaning layer; no contract meaning changed. | #65 (`ae471aa`) |
| **F8** | KPI Coverage Scorecard | 5 (analytical coverage) | A per-table coverage scorecard template (`skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md`): coverage as explicit **status + named blocker** (Covered / Blocked -- missing field / Blocked -- needs business definition / Planned / Out of scope), **never a numeric score** (hard rule #9); Covered requires contract Seeded AND fields present; grants no readiness. | #66 (`9d782f8`) |

> **Effect on the static gate:** A1 and B1 take the registered `retail check`
> rule set from 31 to **33** (the wiring test `EXPECTED_RULE_IDS` is the guard; both
> emit zero findings on `main`). The DAX-governance L3 boundary is unchanged.

## Hard design rules (non-negotiable, gate the sequence)

These are the ordering constraints the roadmap encodes. They reinforce the
existing constitution (Principles I, IV, V, VIII), they do not replace it:

1. **Agent-first, not CLI-first.** The agent is the interface; `retail check` /
   `retail validate` are gates/helpers the agent calls.
2. **No source goes directly to silver.** Mapping Ready must `pass` first.
3. **No silver without** a source profile + source map + declared grain +
   reviewed/accepted unresolved questions.
4. **No gold to Power BI before validation.** Gold Ready requires the live checks.
5. **No dashboard design before metric contracts.** F011 is gated on F009/F010.
6. **No Power BI EXECUTION before semantic-model readiness.** The execution adapter
   (F016 -- preferably the official Power BI MCP / connection; `pbi-cli` no longer the
   preferred path) is LAST and gated. It is execution-only -- it materializes/publishes
   an already-approved model and CANNOT define metrics, mappings, semantic logic, or
   dashboard design. No current readiness stage depends on it.
7. **C086 is the first worked example, not the universal schema.** Generic
   templates carry no pharmacy specifics.
8. **Docs/templates/checklists first; automate only after artifacts prove
   useful.** A readiness stage is a doc + a status entry before it is code.
9. **No fake confidence.** Readiness is explicit `status` + `evidence` +
   `blocking_reasons`. Numeric scores are optional/deferred until scoring rules
   are defined (`docs/readiness/readiness-model.md`).

## What is intentionally out of scope (this roadmap slice)

- Still out of scope (unbuilt by design): the Power BI EXECUTION adapter (F016 --
  official Power BI MCP / connection preferred, `pbi-cli` no longer preferred;
  execution-only, gated + last), Fabric deployment, ML, forecasting, a universal
  ERP connector, and fully automated mapping approval.
- The shipped F005-F015 slices are docs/skills/templates (agent-first, hard rule
  #8); they added NO new `retail check` rule (the static gate was 27 rules at that
  slice; it grew to 31 after S8 + D9-D11 + G6, and then to **33** after the
  idea-bank A1 + B1 rules -- see the Idea-Bank execution sequence above) and
  NO new runtime validator beyond the already-shipped `retail check` / `retail
  validate`. Each shipped feature has its own spec under `specs/`.

## See also

- The spine: `docs/readiness/readiness-model.md`, `readiness-pipeline.md`,
  and the seven `docs/readiness/<stage>-ready.md` stage docs.
- Architecture: `docs/architecture/readiness-pipeline.md` (spine on the kit),
  `docs/architecture/tower-bi-agent-kit.md` (the kit).
- Foundation: `.specify/memory/constitution.md`, `specs/001-retail-bi-agent-kit/`,
  `docs/medallion-playbook.md`, `docs/worked-examples/c086-pharmacy.md`.
