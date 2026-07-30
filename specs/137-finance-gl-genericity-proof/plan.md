# Implementation Plan: Finance GL Budget-vs-Actual Genericity Proof

**Branch**: `137-finance-gl-genericity-proof` | **Date**: 2026-07-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/137-finance-gl-genericity-proof/spec.md`

## Summary

Drive one NEW, non-retail subject area (`finance_gl`) through the EXISTING readiness spine
to Dashboard Ready, using only existing templates, verbs, rules, and formats -- and record
every retail-shaped obstruction in a genericity ledger. The feature adds a deterministic
synthetic source generator, the per-table mapping/warehouse/contract artifacts the spine
already defines, thirteen isolated defect variants (six of them registered as scenarios in
the existing benchmark format), one committed report page, and the ledger.

The technical approach is deliberately **additive and evidence-first**: no kit module is
modified as a design choice. If a kit change turns out to be unavoidable, it is a *finding*
recorded in the ledger and raised for owner decision -- not a silent edit. The ledger, not
this plan, decides whether a domain-profile abstraction is ever justified (spec FR-032).

## Technical Context

**Language/Version**: Python 3.13 (repo interpreter), stdlib only for the generator

**Primary Dependencies**: NONE added. The generator uses the standard library only
(`random.Random(seed)`, `csv`, `datetime`, `decimal`). The offline static core is
stdlib-only by Constitution Principle VIII and this feature must not weaken that.

**Storage**: CSV source files on disk (offline). No database connection anywhere in this
feature; every live leg is recorded `[PENDING LIVE PROFILE]`.

**Testing**: pytest with the repo's existing `unit` / `integration` markers; the existing
static gate (`seshat check`) for governance; the existing benchmark scenario format for
refusal behaviour.

**Target Platform**: Windows-first local development (repo default), CI on Linux. Offline
in both.

**Project Type**: Documentation-and-fixture feature over an existing Python package plus a
Power BI PBIP project. It is NOT a new runtime component.

**Performance Goals**: Not applicable as a product goal. One practical bound: fixture
generation must complete fast enough to run inside a normal unit-test invocation
(target: under a second for the clean set).

**Constraints**:
- Offline, deterministic, byte-identical regeneration from seed `20260730`.
- No new dependency, no new rule, no new CLI verb, no new skill, no new registry.
- No numeric confidence/health/maturity/readiness/genericity score anywhere.
- No self-granted approval anywhere.
- UTF-8 without BOM; ASCII-only in manifest-style YAML; Windows path-length limit applies
  to any new PBIP report/page directory name.

**Scale/Scope**: ~2 fiscal years, 30 accounts, 6 departments, 4-8 cost centers, ~5,000
journal lines, quarterly budgets, >= 2 budget versions, 5 clean source files, 13 defect
variants, 7 metric contracts, 1 report page, 1 ledger.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate for this feature | Verdict |
|-----------|----------------------|---------|
| **I. Agent-First, Gate-Enforced** | No new command surface; the agent calls existing verbs, and `seshat check` stays the gate. | **PASS** -- spec FR-031 forbids new verbs/aliases. |
| **II. Depend, Never Fork** | No dependency added; no template forked; the metric-contract template is FILLED, not copied. | **PASS** -- spec FR-013. |
| **III. Medallion, Postgres-First, Gold-Only** | bronze -> silver -> gold with Power BI reading gold only; two facts + conformed dims. | **PASS** -- spec FR-009. |
| **IV. Source Mapping Before Silver** | No `silver.*` SQL is authored until each finance table's mapping gate is cleared by a named human. | **PASS** -- enforced by task ordering (Slice C precedes Slice D) and by OD-4. |
| **V. Agent Stops at Judgment Calls** | Revenue sign, baseline meaning, allocation policy, gate approvals all stay open and blocking. | **PASS** -- spec FR-016/017/018, OD-1..OD-5. |
| **VI. Defaults Then Deviations** | Every deviation from the ratified cleaning defaults is recorded with the triggering data fact. | **PASS** -- planned in Slice C artifacts. |
| **VII. C086 Is An Example, Not The Schema** | This feature is the SECOND example and must not bake finance answers into generic templates. | **PASS** -- and it is the direct test of this principle. |
| **VIII. Static-First Governance, Live Deferred** | Entirely offline; no live DB; live legs `[PENDING LIVE PROFILE]`. | **PASS**. |
| **IX. Secrets and Reproducibility** | Synthetic data only; no secrets, no real records, no local absolute paths; byte-identical regeneration. | **PASS** -- spec FR-002/FR-004. |

**Post-Phase-1 re-check**: unchanged. The Phase 1 design adds no module to `src/`, no rule,
and no dependency; the only executable code introduced is a stdlib-only fixture generator
placed under an existing test/fixture location (see Structure Decision).

**No Complexity Tracking entries** -- there are no constitution violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/137-finance-gl-genericity-proof/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output -- decisions with evidence
├── data-model.md        # Phase 1 output -- entities, grains, validation rules
├── quickstart.md        # Phase 1 output -- how an author walks this example
├── contracts/
│   ├── generator-contract.md    # generator inputs/outputs/determinism contract
│   └── fixture-schema.md        # per-file column schema + defect variant catalog
├── checklists/
│   └── requirements.md  # spec quality checklist (already written)
├── ledger-baseline.md   # implementation-time output (task T003): pre-flight repo state
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
tests/fixtures/finance_gl/            # NEW -- generator + committed clean EXCERPTS only
├── generate.py                       #   stdlib-only, seed 20260730, no network/clock
└── excerpts/                         #   tiny committed samples for doc citation
    ├── finance_gl_actuals.head.csv
    └── finance_gl_budget.head.csv

mappings/finance_gl_actuals/          # NEW -- per-table spine artifacts (existing shapes)
├── source-profile.md
├── source-map.yaml
├── assumptions.md
├── unresolved-questions.md
├── readiness-status.yaml
└── approval-request-mapping-gate.md  #   + the named human's approval-decision artifact
mappings/finance_gl_budget/           # NEW -- same shapes, its OWN grain and PK
└── (same artifacts)

warehouse/migrations/                 # NEW files only; existing numbering continues
├── 0006_create_silver_finance_gl_actuals.sql
├── 0007_create_silver_finance_gl_budget.sql
└── 0008_create_gold_finance_gl_star.sql

benchmark/scenarios/
└── finance-gl-judgment.yaml          # NEW -- 6 business-judgment scenarios, existing format

docs/worked-examples/
├── finance-gl-budget-vs-actual.md    # NEW -- the worked example narrative
├── finance-gl-genericity-ledger.md   # NEW -- the ledger (the decisive artifact)
└── README.md                         # MODIFIED -- one index row only

powerbi/                              # NEW report + model artifacts (short names)
└── FinanceGL.Report / FinanceGL.SemanticModel
```

**Structure Decision**: the feature adds **new sibling directories beside existing ones**
and modifies almost nothing. The only edits to existing files are the worked-example index
row and whatever declaration surfaces their own completeness contracts require (FR-030).
`src/seshat/`, `src/retail/`, the rule modules, and every template stay byte-unchanged; a
diff proving that is itself an acceptance artifact (spec SC-007).

## Design decisions mapped to requirements

| Decision | Serves | Evidence / rationale |
|---|---|---|
| Generator is stdlib-only, seeded `random.Random(20260730)`, no clock/UUID | FR-001, FR-002 | Constitution VIII keeps the offline core stdlib-only; a seeded PRNG plus fixed base dates is sufficient and keeps regeneration byte-identical. |
| **Full CSVs are NOT committed**; only tiny excerpts are, and the full set is generated into a git-ignored path at verification time | FR-004, FR-005, spec Assumptions | **Measured**: the largest committed fixture in the repo today is `tests/fixtures/demo/demo_sample_orders.csv` at **1,801 bytes**; `benchmark/scenarios/fixtures/synthetic-orders.csv` is 343 bytes and `distribution/synthetic-retail/source.csv` is 447 bytes. A ~5,000-line journal file is two orders of magnitude larger than anything the repo has ever committed, so committing it would set a new precedent for bulk data in-tree. The generator + excerpts preserve reviewability without that precedent. |
| Two mapping directories, one per source table, each with its OWN grain/PK | FR-007, FR-008, SC-004 | Mirrors the observed per-table artifact layout under `mappings/retail_store_sales/`; a single shared directory would force a merged grain, which the spec forbids. |
| Actuals aggregate UP to quarter for comparison; budget is never spread DOWN | FR-010 | Downward allocation invents numbers. The established budget-vs-actual guidance is separate facts at native grains joined through conformed dimensions; the allocation direction is a policy decision (OD-3). |
| Variance % defined as a post-aggregation ratio in the contract intent | FR-014 | `docs/patterns/target-budget-fact.md` Section 3 already states this as a resolved default ("aggregate actuals and targets SEPARATELY at the comparison grain, then recompute the percentage. Never average two already-computed percentages."). This feature cites that rule rather than re-deriving it. |
| Missing-budget is a first-class flag metric, not a zero | FR-015 | Zero budget is a decision ("we planned nothing"); missing budget is an absence. Collapsing them silently misstates variance. |
| Six judgment cases become scenarios in `benchmark/scenarios/*.yaml` | FR-022 | The vocabulary they need already exists: `src/seshat/benchmark/model.py` defines `BEHAVIORS = ("proceed", "refuse", "block_for_evidence", "request_human_decision")` and grades categorically (`match` / `over_refusal` / `mismatch`) with an explicit "never aggregated into a score" comment. Reusing it costs no new format and makes refusal observable and repeatable. |
| Over-refusal counted as failure | FR-023, SC-003 | Already modelled by the existing `over_refusal` comparison outcome -- a gate that blocks a legitimate finance case is not "safe". |
| All eight visuals are authored by a human first | FR-027 | **Measured from `docs/integrations/pbir-adapter.md`**: the adapter ships per-visual formatting (increment B) and geometry (increment D) over an EXISTING `visual.json`, explicitly performs "No data bindings / measures / DAX / relationships / semantic-model edits", and "does not populate an empty page or author visuals". Data-bound visual CREATION is therefore outside the adapter today. |
| Ledger classification is categorical, conservative on ties | FR-029, edge cases | A numeric leak count would invite a threshold, and thresholds invite scores (hard rule #9). Ties resolve to `semantic_leak` so Phase-2 scoping cannot under-count. |

### PBIR authoring boundary -- per-visual classification (required by FR-027)

| # | Visual | Bound measure(s) | Creation | Adapter may then |
|---|---|---|---|---|
| 1 | Actual Amount card | Actual Amount | `human_only` | format, position |
| 2 | Budget Amount card | Budget Amount | `human_only` | format, position |
| 3 | Variance Amount card | Variance Amount | `human_only` | format, position |
| 4 | Variance % card | Variance % | `human_only` | format, position |
| 5 | Actual vs Budget trend | Actual Amount, Budget Amount | `human_only` | format, position |
| 6 | Variance by department | Variance Amount | `human_only` | format, position |
| 7 | Account hierarchy matrix | Actual Amount, Budget Amount, Variance Amount | `human_only` | format, position |
| 8 | Missing-budget exceptions table | Missing Budget Flag | `human_only` | format, position |

Every row is `human_only` for CREATION and BINDING, per the adapter's own documented
boundary. The agent authors the page blueprint, the binding map, and the design review; a
named human performs the Power BI Desktop authoring action (OD-5) and commits the PBIR.
Theme, formatting, geometry, and binding VALIDATION remain agent work. Power BI Service
publishing and Power BI MCP mutation are out of scope (ADR-0018 is `Proposed -- NOT
ratified`).

## Existing sources of truth this feature reads (and must not duplicate)

| Concern | Authority |
|---|---|
| Constitution / principles | `.specify/memory/constitution.md` |
| Cleaning defaults + deviations (RC ids) | `docs/decisions/0002-retail-cleaning-defaults.md` |
| Worked-example process + completeness tiers | `specs/084-worked-example-factory/` |
| Target/budget modelling pattern | `docs/patterns/target-budget-fact.md` |
| Variance contract SHAPE | `templates/metric-contract-shape.variance-vs-target.yaml` |
| Metric contract field set | `templates/metric-contract.yaml` |
| Refusal vocabulary + grading | `src/seshat/benchmark/model.py` |
| PBIR authoring boundary | `docs/integrations/pbir-adapter.md` |
| Doc-anchored claims | `docs/quality/status-claims.yaml` |
| Capability classification | `docs/capabilities/capabilities.yaml` |
| Per-table readiness record shape | `mappings/retail_store_sales/readiness-status.yaml` |

## Fixture generation and storage

1. `tests/fixtures/finance_gl/generate.py` exposes one entry point taking an output
   directory and an optional variant name; default variant is `clean`.
2. Determinism: a single `random.Random(20260730)` instance; all dates derived from a
   hard-coded base date; amounts as `Decimal` quantized to 2 places and formatted with a
   fixed format string; rows emitted in a declared sort order; `\n` line endings written
   explicitly; no `datetime.now()`, no `uuid4()`.
3. Verification: generate twice into two temp directories and compare bytes (and a SHA-256
   per file) -- equality is the test, not an assertion about the code.
4. Storage: full outputs go to a git-ignored directory; only the `excerpts/*.head.csv`
   files (tens of rows, comparable in size to existing committed fixtures) are tracked, for
   doc citation and review.
5. Each defect variant is produced by the SAME generator with a named variant flag, so a
   variant differs from clean by exactly one intended perturbation.

## Validation commands (to be confirmed against the repo before use, then run verbatim)

| Purpose | Command |
|---|---|
| Static governance gate | `python -m seshat.cli check` |
| Unit tests (fast subset) | `python -m pytest -m unit -q` |
| Generator determinism | the new unit test that generates twice and compares bytes + hashes |
| Kit lint / manifest consistency | `python -m seshat.cli kit-lint` (resolved from the CLI dispatch table on 2026-07-30) |
| Bundle regeneration | `python scripts/export_agent_bundles.py --repo .` -- **only if** `skills/**` or `.claude/skills/**` change; this feature must not change them, so the expected state is "not required" |
| PBIR binding validation | `python -m seshat.cli pbir-validate-bindings` (backed by `src/seshat/pbir_validate_bindings.py`) |
| Secret / raw-data safeguards | the gate's existing secret-scan and raw-data rules, via `check` |

Planning tasks run only the validations relevant to planning artifacts. No command's result
may be reported unless it was actually run.

## Risks and rollback

| Risk | Mitigation |
|---|---|
| The example quietly becomes a capability claim | Spec's explicit non-claim section + SC-007 diff check + FR-030 forbids declaring a capability that does not exist. |
| A forced kit edit gets made silently to keep the walk moving | Any kit edit is a ledger row AND an owner decision; the walk continues with the obstruction recorded rather than resolved unilaterally. |
| Fixture bloat sets a bulk-data precedent | Measured decision above: generator + tiny excerpts; full CSVs git-ignored. |
| Defect variants drift from the clean fixture over time | Variants are generated by the same seeded generator, never hand-edited copies. |
| The ledger over-claims (e.g. "semi-additive proven") | Spec boundary section explicitly scopes semi-additive to spec 091 and forbids that claim. |
| The human authoring step never happens, stranding US3 | US1+US2 are independently complete and deliver the genericity verdict without US3; US3 is P2 and its blocker is recorded honestly. |
| Registry omission turns the PR red late | FR-030 makes registry registration an explicit task in Slice F, checked before review. |

**Rollback**: every artifact is additive and lives under new paths, except the
worked-example index row and any required registry entries. Reverting the branch removes
the example wholesale with no migration to undo and no kit surface to restore (nothing was
executed against a database).

## Phase status

- **Phase 0 (research)**: see `research.md` -- decisions with evidence; zero unresolved
  NEEDS CLARIFICATION (business judgments are deliberately OPEN owner decisions, tracked as
  OD-1..OD-5 in the spec, which is a different thing from an unresolved technical unknown).
- **Phase 1 (design)**: see `data-model.md`, `contracts/`, `quickstart.md`.
- **Phase 2 (tasks)**: `/speckit-tasks` output in `tasks.md`. Implementation does not start
  until the owner ratifies this package.
