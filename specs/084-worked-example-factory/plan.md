# Implementation Plan: Worked-Example Factory

**Branch**: `spec/worked-example-factory` | **Date**: 2026-07-03 | **Spec**: `specs/084-worked-example-factory/spec.md`

**Input**: Feature specification from `specs/084-worked-example-factory/spec.md`

**Note**: This plan is docs-only, per the task's absolute boundaries. It plans
the *documentation deliverable* (a process + a completeness contract), not a
runtime feature. There is no code to design.

## Summary

The primary requirement is a repeatable, generic **process document** for
producing a future worked example (any domain, illustratively inventory or
customer loyalty), plus an **acceptance-criteria contract** for judging a
candidate example "complete," calibrated against the existing
`retail_store_sales` example. The technical approach (research.md) is: cite and
compose the artifacts and gates that already exist (the five mapping-gate
templates, the readiness spine, the maturity ladder, the medallion playbook) -- add no new template, no new rule, no new runtime surface. The one new
first-class idea this feature contributes is the explicit two-tier
completeness split (repo-only vs. human/live-gated) and the load-bearing
maturity-vs-capability distinction, both derived from already-shipped postures
(Principle VIII's static-first/live-deferred split; AGENTS.md's graceful
deferred mode) rather than invented from scratch.

## Technical Context

**Language/Version**: N/A -- documentation only (no code produced or modified).

**Primary Dependencies**: None new. Cites existing repo artifacts:
`templates/*` (five mapping-gate templates + `metric-contract.yaml` +
`readiness-status.yaml` + `maturity-report.md` + `handoff/`),
`docs/readiness/readiness-model.md`, `docs/medallion-playbook.md`,
`docs/decisions/0002-retail-cleaning-defaults.md`,
`docs/worked-examples/retail-store-sales.md`, `.specify/memory/
constitution.md`.

**Storage**: N/A. No database, no migration, no live connection produced by
this feature. (A *future* worked example built under this process would use
the existing DigitalOcean Postgres medallion -- unchanged, out of scope here.)

**Testing**: N/A for this feature's own deliverable (it is prose + a
checklist). The *validation* of this spec chain is the checklist self-review
(`checklists/requirements.md`) plus the end-of-chain `analyze` step
(STEP 4) plus a read-only `retail check --repo .` dry run reported with its
exact exit code (no mutation, no live DB).

**Target Platform**: N/A -- Markdown/YAML documentation, consumed by a future
human or agent author.

**Project Type**: Documentation / process-definition (Spec-Kit "docs-first"
slice, matching the precedent of the 2026-07-03 design-governance wave, which
also shipped as docs+static-rules with "Readiness stages affected: None").

**Performance Goals**: N/A.

**Constraints**: Must not create, scaffold, or partially fill any concrete
worked example. Must not touch `src/**`, add a rule ID, or change CI. Must not
fabricate a metric, contract, or approval. Must not reference or resurrect
C086. Must stay ASCII / UTF-8 without BOM (repo convention; `retail check`
enforceable rules may flag violations even in docs-only PRs).

**Scale/Scope**: One feature's worth of documentation (spec, plan, research,
data-model, quickstart, one contract file, tasks, analysis) inside
`specs/084-worked-example-factory/`. No other directory is touched.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Check | Result |
|-----------|-------|--------|
| I. Agent-First, Gate-Enforced | Does this feature add or weaken a gate? | No new gate; no gate weakened. This feature documents how existing gates (source-mapping gate, `retail check`, `retail validate`) apply to a future example. PASS. |
| II. Depend, Never Fork | Does this feature touch the Power BI execution adapter? | No. Not referenced beyond citing existing policy (gold-only, parameterized connections). PASS. |
| III. Medallion, Postgres-First, Gold-Only | Does this feature propose a new storage substrate? | No. A future example built under this process would use the existing Postgres medallion; this feature adds no storage decision. PASS. |
| IV. Source Mapping Before Silver | Does this feature let silver be written before mapping? | No -- the quickstart explicitly sequences profile -> map -> gate -> silver, and stops before silver if mapping is not cleared. PASS. |
| V. Agent Stops at Judgment Calls | Does this feature let an agent self-decide a judgment call, or self-grant an approval? | No -- the completeness contract's Tier 2 explicitly forbids the factory process from filling any `approvals[]` entry; the quickstart explicitly stops at judgment calls. This is the feature's central discipline (FR-006, Non-Goals). PASS. |
| VI. Defaults Then Deviations | Does this feature bypass the RC-defaults-then-deviations discipline? | No -- reinforced: contract item C-C2 requires the same adopted/deviated integrity invariant `assumptions.md` already states. PASS. |
| VII. C086 Is An Example, Not The Schema | Does this feature reference or resurrect C086 specifics? | No -- explicitly forbidden (FR-007, Non-Goals, multiple edge cases); verified absent from every produced file (SC-004). PASS. |
| VIII. Static-First Governance, Live Deferred | Does this feature claim a live-validation result it did not run, or blur static vs. live? | No -- the two-tier completeness split is built specifically to keep this distinction explicit (research.md Sec 5); no live claim is made anywhere in this spec chain. PASS. |
| IX. Secrets and Reproducibility | Does this feature commit a secret or a real connection string? | No -- none referenced; the quickstart repeats the "never a baked-in host" rule. PASS. |
| Readiness System (spine) | Which readiness stage does this feature advance? | **None.** This is a meta/process feature orthogonal to the seven-stage per-table spine, exactly as the roadmap's "improve exactly one readiness stage" guiding rule anticipates a possible exception for -- precedented by the 2026-07-03 design-governance wave, which recorded "Readiness stages affected: None" for the same reason (a cross-cutting governance/process addition, not a per-table stage). This feature instead advances the **maturity-ladder precondition**: it defines what evidence a future example must produce to be counted toward L2/L3, without itself producing that evidence. Documented here as a justified, precedented deviation from the per-stage guiding rule, not a violation of it. |

**Overall**: PASS. No violation requires a Complexity Tracking entry (see
below -- table intentionally near-empty).

## Project Structure

### Documentation (this feature)

```text
specs/084-worked-example-factory/
|-- spec.md                                  # Feature spec (done)
|-- checklists/
|   `-- requirements.md                      # Self-validation (done)
|-- plan.md                                  # This file
|-- research.md                              # Phase 0 output (done)
|-- data-model.md                            # Phase 1 output (done)
|-- quickstart.md                            # Phase 1 output (done)
|-- contracts/
|   `-- worked-example-completeness.md       # Phase 1 output (done) -- the acceptance-criteria contract
|-- tasks.md                                 # Phase 2 output (STEP 3, next)
`-- analysis/
    `-- analyze-report.md                    # STEP 4 output (or speckit-analyze, if it runs cleanly)
```

### Source code (repository root)

**Structure Decision**: No source code is added or modified by this feature.
This is a documentation-only slice; there is no `src/`, `backend/`,
`frontend/`, or `tests/` change. The only future consumer of this feature's
output is a *separate*, later effort that would actually build a second worked
example -- that effort would touch `mappings/<new-table>/`, `warehouse/
migrations/`, `powerbi/<Table>.SemanticModel/`, and `docs/worked-examples/
<new-table>.md`, none of which exist yet and none of which this feature
creates (spec.md FR-011, Non-Goals).

## Likely files/dirs a FUTURE worked-example-building effort would touch

(Identified for planning clarity only -- per the task's boundaries, none of
these are created or scaffolded by this feature.)

- `mappings/<new-table>/` (source-profile.md, source-map.yaml, assumptions.md,
  unresolved-questions.md, reconciliation-report.md, metrics/, design/,
  handoff/, readiness-status.yaml)
- `warehouse/migrations/NNNN_create_silver_<new-table>.sql` and
  `..._gold_<new-table>_star.sql`
- `powerbi/<NewTable>.SemanticModel/` (TMDL)
- `docs/worked-examples/<new-table>.md`
- `docs/worked-examples/README.md` (one new row added to the index table)
- Possibly `docs/releases/<Fxxx>/maturity-report.md` (a future maturity
  reassessment citing the new example as L2 evidence -- owned by the
  `release-notes-generator` skill, not this feature)

## Tests and validation for THIS feature's own deliverable

- **Checklist self-review**: `checklists/requirements.md`, already completed
  (Phase 0).
- **Calibration check**: `contracts/worked-example-completeness.md`'s own
  "Calibration check (SC-002)" section, applying the contract to
  retail_store_sales and confirming it verdicts "complete" -- done in Phase 1
  by direct file citation (no script; a documentation cross-check, not a
  runtime test).
- **Cross-artifact consistency**: STEP 4 (`analyze`), see below.
- **Repo-hygiene dry check**: a read-only `retail check --repo .` run at the
  end of the chain, reported with its exact exit code (this validates that the
  new Markdown/YAML files under `specs/084-worked-example-factory/` do not
  trip any static rule -- e.g. ASCII-only, no committed secret pattern -- not
  that a worked example was built).

## Operational risks

- **Risk: the completeness contract drifts from the templates it cites** if a
  template changes later (e.g. a sixth mapping-gate artifact is added).
  Mitigation: the contract cites template files by path, not by inlined copy,
  so a template change is visible as a stale citation, not a silent
  contradiction; a future amendment would need to re-walk the contract against
  the changed template (recorded here as a known maintenance cost, not fixed
  by this feature).
- **Risk: a future author reads this factory as license to skip a human
  approval** because Tier 1 looks "complete." Mitigation: FR-004, the Human-
  Approval Boundaries section, and contract Tier 2's explicit list are all
  designed to make this misreading hard to make by accident; the quickstart
  repeats it a third time at the point of use.
- **Risk: "maturity advanced" gets reported as "capability gained"** in a
  future PR description or release note, despite this feature's guidance.
  Mitigation: FR-005 and User Story 3 give a reviewer a named, quotable rule
  to cite ("zero `src/retail` change, zero new CLI verb, zero new rule") -- this feature cannot force compliance in a future PR, only make the violation
  easy to name.

## Backwards compatibility

Fully additive. No existing file is modified by this feature (verified at
validation time via `git status --short`). No existing template's shape
changes. No existing worked example's artifacts are touched.

## Repo-only vs. live-DB split (recap)

Already the spine of `research.md` Sec 5 and `data-model.md`'s Completeness Tier
entity: this feature's own production needs neither a live DB nor a human
approval (Assumption A-004). A *future* worked example built under this
process will need both, at the points enumerated in `quickstart.md` steps 3,
5-7's approval callouts and step 4's live-validate callout.

## Forbidden scope (restated from spec.md for plan-level visibility)

- No concrete worked example authored, scaffolded, or partially filled.
- No `src/**` change, no new/changed rule ID, no CI change, no new dependency.
- No C086 reference or resurrection.
- No fabricated metric, contract, expected value, or approval.
- No numeric maturity score (rungs stay binary per `templates/maturity-
  report.md`).
- No commit, push, PR, merge, or self-approval performed while producing this
  spec chain.

## Complexity Tracking

*No entries.* The Constitution Check above found no violation requiring
justification -- this feature adds zero new templates, zero new rules, zero new
runtime surfaces, and reuses the existing five-artifact mapping-gate pattern
and the existing maturity ladder verbatim.
