# Implementation Plan: dbt Transformation Adapter

**Branch**: `023-dbt-transformation-adapter` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

**Roadmap feature**: F029 (spec-dir 023; the roadmap F-number is authoritative. F024-F033
are a forward batch not yet recorded in the committed roadmap, which documents through
F016. This plan edits no roadmap.)

**Input**: Feature specification from `specs/023-dbt-transformation-adapter/spec.md`

## Summary

Define how dbt enters as a TRANSFORMATION ADAPTER (build engine) for Silver/Gold without
becoming the brain. dbt may build staging/silver/gold models ONLY after Mapping Ready =
`pass`; every model cites the approved `source-map.yaml`; dbt tests produce EVIDENCE while
Tower readiness + a named human DECIDE the stage. dbt is positioned as an OPTIONAL
ALTERNATIVE engine: `warehouse/migrations` stays the DEFAULT until a reconciliation parity
test proves the dbt mart reproduces the existing gold tables (`gold.fct_sales_rss` and its
dims), at which point a named human may approve the build-path switch. This slice is
PLANNING-ONLY: it writes the five spec-kit files and ENUMERATES the future dbt project
shape + docs/decision/templates/skill as planned outputs. It creates NO dbt files and NO
runtime code.

## Technical Context

**Language/Version**: None this slice -- docs/planning only (Markdown spec-kit artifacts).
The FEATURE when built targets dbt-core + dbt-postgres (pinned together) over the existing
DigitalOcean Postgres; the build slice (not this one) introduces that.

**Primary Dependencies**: None at runtime this slice. The feature when built depends on
dbt-core + dbt-postgres and on the approved `source-map.yaml` + `readiness-status.yaml`
per table.

**Storage**: This slice -- five committed text files under
`specs/023-dbt-transformation-adapter/`. The feature when built adds a `dbt/` project tree,
two `templates/dbt-*-contract.md`, one `docs/decisions/0007-*.md`, one
`docs/integrations/dbt-adapter.md`, and one `.claude/skills/dbt-transformation-adapter/
SKILL.md` -- all ENUMERATED below, NONE created now.

**Testing**: No code this slice, so no unit tests. Verification is: (1) the five files are
ASCII + UTF-8 no BOM, (2) zero dbt files / runtime code added (diff check), (3) zero
`retail_store_sales`/C086 specifics leak into any generic artifact this slice plans,
(4) the gating + evidence-not-approval + parity rules are stated unambiguously.

**Target Platform**: Repo text artifacts consumed by the agent + reviewed by a human.

**Project Type**: Execution Adapter (DB-connected, not publish-capable) -- but this SLICE is
a documentation/planning slice (no source tree change).

**Performance Goals**: N/A (static text this slice).

**Constraints**: ASCII + UTF-8 no BOM; generic (no `retail_store_sales`/C086 values in
generic templates); Windows path budget (keep names short); no secrets/DSN/credentials in
any tracked file; no dbt files this slice; dbt never self-approves a stage.

**Scale/Scope**: 5 spec-kit files this slice. The enumerated future build = ~1 dbt project
+ 2 contract templates + 1 ADR + 1 integration doc + 1 skill (FUTURE, not now).

## Constitution Check

*GATE: must pass before and after design. Constitution at `.specify/memory/constitution.md`.*

| Principle | How this feature complies |
|-----------|---------------------------|
| I. Agent-First, Gate-Enforced | The agent invokes dbt; `retail check` / readiness stay the gates. dbt is a build engine the agent calls behind a cleared gate, not a gate or an authority. dbt self-grants nothing. |
| II. Depend, Never Fork | dbt is depended on as an OPTIONAL external engine (dbt-core + dbt-postgres), not forked. Tower BI adds the gate + the parity contract around it; it does not reimplement dbt. |
| III. Medallion, Gold-Only | dbt builds bronze->silver->gold and STOPS at gold; Power BI reads gold only. dbt is DB-connected, not publish-capable (FR-009). |
| IV. Source Mapping Before Silver | THE central line: dbt may not run any silver/gold model until Mapping Ready = `pass` and the model cites the approved map (FR-001, FR-002). This is Principle IV made operational for a build engine. |
| V. Agent Stops at Judgment Calls | Grain ambiguity, sentinel-vs-null, PII publish-safety, business rollup/segment are stop-and-ask (FR-003); dbt never auto-resolves one, never silently changes grain. The agent recommends; a named human decides. |
| VI. Defaults Then Deviations | Migrations remain the DEFAULT build path; dbt is the deviation, allowed only after a passing parity test + a recorded human approval (FR-006). The switch is explicit, never silent. |
| VII. C086 Is An Example | `retail_store_sales` is the CITED filled first-MVP instance; the generic adapter/model contracts + ADR + skill carry no `retail_store_sales`/C086 values (FR-012, SC-004). |
| VIII. Static-First, Live Deferred | This SLICE ships only the five planning docs -- NO dbt files, NO runtime code (FR-011, SC-005). The FEATURE when built is execution-only, gated on Mapping Ready=`pass`, and self-approves nothing; dbt test results are evidence, not a gate. (This is a DB-connected execution adapter being PLANNED, not a static-only feature -- the slice is planning-only, the feature is gated execution.) |
| IX. Secrets & Reproducibility | No secrets: only `profiles.example.yml` (placeholders) is planned for commit; `profiles.yml` is git-ignored; no DSN/credential/host in any tracked file (FR-008, SC-006). ASCII + UTF-8 no BOM; short paths; pinned dbt-core+dbt-postgres for reproducibility (FR-010). |

**Result**: PASS. No violations; Complexity Tracking left empty.

### Authority gate (feature-specific, load-bearing)

This is the batch's FIRST DB-connected adapter, so the authority line is heavier than a
pure-docs feature's. The plan holds it explicitly:

- dbt READS truth (the approved map), EXECUTES approved steps (builds + tests behind the
  gate), and WRITES DERIVED evidence (run/test/parity results). It CREATES no truth.
- A green `dbt test` is evidence, NEVER an approval. Only Tower readiness + a named human
  move a stage to `pass`, citing that evidence + the approval.
- dbt never defines source mapping / metric contracts / business meaning, never resolves a
  Principle V call, never publishes Power BI, never flips the build-path default on its own.

## Project Structure

### Documentation (this feature -- the five files this slice WRITES)

```text
specs/023-dbt-transformation-adapter/
|- spec.md                 # feature spec (this slice)
|- plan.md                 # this file
|- tasks.md                # planning task list
|- checklists/
   |- acceptance.md        # specification quality checklist
   |- governance.md        # Core-Authority / Principle-V governance gate
```

No `research.md` / `data-model.md` / `contracts/` dir is generated: there is no code to
research this slice, and the "contracts" this feature will later produce are the
`templates/dbt-*-contract.md` files (planned future outputs, not speckit `contracts/`).

### Repository artifacts this feature PLANS (not created this slice)

These are FUTURE outputs the build slice will create. This slice only ENUMERATES them;
it writes NONE of them. NO dbt files are created now.

```text
dbt/                                         # PLANNED (not created this slice)
|- dbt_project.yml                           #   project config
|- profiles.example.yml                      #   EXAMPLE profile, NO secrets (real profiles.yml git-ignored)
|- models/
|  |- sources/                               #   sources -> bronze/silver (cite the approved map)
|  |- staging/                               #   staging models (one retail_store_sales staging model = first MVP)
|  |- intermediate/                          #   intermediate transforms (if needed)
|  |- marts/                                 #   marts reproducing the gold star (one mart model = first MVP)
|- tests/                                    #   schema + data tests + the reconciliation parity test
|- macros/                                   #   shared macros

templates/
|- dbt-adapter-contract.md                   # PLANNED -- generic adapter contract (gate, evidence-not-approval, parity, no-secrets, auto-update)
|- dbt-model-contract.md                     # PLANNED -- generic per-model contract (source-map citations, grain, tests)

docs/integrations/
|- dbt-adapter.md                            # PLANNED -- how dbt plugs in as an optional engine behind the gate

docs/decisions/
|- 0007-dbt-is-transformation-adapter.md     # PLANNED -- ADR: dbt is an optional alternative engine; migrations default until parity

.claude/skills/dbt-transformation-adapter/
|- SKILL.md                                  # PLANNED -- agent skill: run dbt ONLY behind Mapping Ready=pass; record derived evidence
```

**Structure Decision**: planning/documentation slice -- no `src/`, no `dbt/`, no template
or skill files this slice. The dbt project lives in a top-level `dbt/` dir (its own home,
parallel to `warehouse/`) so the two build paths stay clearly separate. Generic contracts
live in the existing `templates/` dir; the ADR in `docs/decisions/`; the integration doc in
a new `docs/integrations/`; the skill under `.claude/skills/`. All FUTURE.

## Phase 0 -- Research (no external research needed)

No unknowns requiring external research. The reconciliation target is already in-repo and
exact: `warehouse/migrations/0004_create_gold_retail_store_sales_star.sql` defines
`gold.fct_sales_rss` (transaction grain, `transaction_id` degenerate dim, four entity dims
with a -1 unknown member, `dim_date_rss` a contiguous `generate_series` calendar, additive
measures `price_per_unit` / `quantity` / `total_spent`). The dbt mart must reproduce the
gold tables AS COMMITTED. NOTE a pre-existing repo tension the dbt parity target inherits:
migration 0004 (line ~89) currently INSERTS a -1 member into `dim_date_rss`, which
`retail check` rule S8 flags (a marked date table should carry no sentinel key member).
F029 does NOT resolve that tension -- it reproduces the committed gold as-is; if S8 is later
fixed by dropping the date -1 member, the dbt mart follows the migration. (This is the
16110d8 docs-vs-SQL split-brain: the mapping artifacts were reconciled but migration 0004
was not changed.)
The adapter taxonomy/category is owned by F024 (referenced by roadmap identity, not
restated). The one decision (dbt = optional alternative, migrations default until parity) is
resolved with a recommended posture, not deferred research.

## Phase 1 -- Design (the artifact shapes this feature PLANS)

**dbt project (`dbt/`, planned)**: `sources` point at the already-built bronze/silver;
`staging` models clean/type per the approved map; `marts` reproduce the gold star. First
MVP = one `retail_store_sales` staging model + one mart model. Tests: `unique(
transaction_id)`, `not_null(transaction_id)`, `relationships` from the fact FKs to each
dimension, and the reconciliation parity test against `gold.fct_sales_rss`.

**dbt-adapter-contract.md (generic, planned)**: states the entry gate (Mapping Ready =
`pass`), the evidence-not-approval rule (dbt test = evidence; Tower readiness + a named
human decide), the parity requirement + tolerance, the no-secrets rule (only
`profiles.example.yml`), and the auto-update policy (pin dbt-core + dbt-postgres together;
patch/minor -> PR; major -> human review; no automerge for minor/major until compatibility
tests exist). No `retail_store_sales` values.

**dbt-model-contract.md (generic, planned)**: per-model citation of the approved
`source-map.yaml` (path + git ref + rows for grain/PK/columns), the grain it builds, and the
tests it carries. A column with no citation is a defect.

**0007-dbt-is-transformation-adapter.md (ADR, planned)**: records the OPTIONAL-ALTERNATIVE
posture -- migrations stay the default; dbt becomes a table's build path only after the
parity test passes and a named human approves; both paths never feed the same gold tables
silently.

**dbt-transformation-adapter/SKILL.md (planned)**: the agent skill that runs dbt ONLY
behind Mapping Ready=`pass`, records run/test/parity results as derived evidence into
`readiness-status.yaml`, and STOPS at every Principle V judgment call and at every stage
transition for a named human.

## Phase 1 -- Constitution re-check

Re-checked after design: still PASS. The design keeps dbt behind the Mapping Ready gate
(IV), keeps dbt test results as evidence not approval (I / authority gate), keeps migrations
the default until parity (VI), stops at gold (III), commits no secrets (IX), and adds no dbt
files this slice (VIII). The authority gate holds: dbt creates no truth.

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.
