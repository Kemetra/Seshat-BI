# Implementation Plan: Adapter Maintenance and Auto-Update Policy

**Branch**: `025-adapter-maintenance-policy` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

**Roadmap feature**: F031 (spec directory 025). The roadmap F-number is the
authoritative feature identity; the directory number is the next free on-disk slot.
When they disagree, the roadmap F-number wins. F031 is in a planning batch ahead of
the committed roadmap ledger (F005-F016) -- this plan does not imply F031 is already
in that ledger.

**Input**: Feature specification from `specs/025-adapter-maintenance-policy/spec.md`

## Summary

Plan the maintenance discipline that makes Constitution Principle II ("Depend, Never
Fork") safe in practice: a written, lane-based update policy plus the required checks
every update PR must pass, plus one ADR recording the automerge decision. Updates are
PR-based; **Lane A** (dev tools, GitHub Actions patch/minor, docs tooling) may
automerge ONLY on green CI; **Lane B** (`dbt-core`, `dbt-postgres`, `dagster`,
`dagster-dbt`, `psycopg2`, Postgres-driver, Power BI modeling utilities) requires a
named human review; **Lane C** (the Power BI execution adapter, anything
publish-capable, major DB-driver changes, anything touching credentials/auth or
semantic-model behavior) never automerges. The load-bearing invariant: **no update in
any lane may bypass a readiness gate or move a stage to `pass`** -- automerge lives
entirely below the readiness spine. This slice is **docs/planning only**: it writes
the five Spec-Kit files and ENUMERATES the future deliverables; it creates no policy
doc, no ADR, no CI/bot config, and no runtime code.

## Technical Context

**Language/Version**: None (docs/planning only this slice -- Markdown planning
artifacts). The future deliverables are Markdown policy docs + one Markdown ADR +
OPTIONAL YAML bot config; no Python.

**Primary Dependencies**: None at runtime. The policy's required-check runtime is the
EXISTING CI (`.github/workflows/ci.yml`: ruff format check, ruff lint, `pytest -m
unit`, `retail check`) plus a human reviewer. Authoring style borrows from the ops/
ADR conventions already in `docs/decisions/000N-*.md`.

**Storage**: Committed text. This slice: the five files under
`specs/025-adapter-maintenance-policy/`. Future (planned, not created): two docs under
a new `docs/operations/` home, one ADR under `docs/decisions/`, and OPTIONAL config
under `.github/`.

**Testing**: No code, so no unit tests. Verification is: (1) `retail check` exit 0
with no new rule added (this feature adds no rule), (2) the five planning files
are ASCII + UTF-8 no BOM, (3) the lane table is total (every FR-001 example class maps
to exactly one lane) and the required-checks list is exact, (4) no C086 /
`retail_store_sales` specifics leak.

**Target Platform**: Repo text artifacts consumed by an agent + a human reviewer; the
update PR runtime is GitHub CI + branch protection.

**Project Type**: Documentation/planning feature (no source tree change this slice).

**Performance Goals**: N/A (static text).

**Constraints**: ASCII + UTF-8 no BOM; generic (no C086/pharmacy values); no numeric
confidence/maturity score anywhere; no new `retail check` rule, validator, or CLI; no
policy doc / ADR / CI config created in this slice; Windows path budget (keep names
short).

**Scale/Scope**: Five Spec-Kit files now. Four future deliverables enumerated (two
docs + one ADR + one optional config), authored in a later slice.

## Constitution Check

*GATE: must pass before and after design. Constitution at `.specify/memory/constitution.md`.*

| Principle | How this feature complies |
|-----------|---------------------------|
| I. Agent-First, Gate-Enforced | Adds no gate and grants the policy/automerge no authority over pass/fail. Lane A automerge is a dependency/CI-plane action; the readiness gates stay the authority. The agent may classify a lane and run checks; it does not approve truth. |
| II. Depend, Never Fork | THE centerpiece. This feature is how "depend, never fork" is operationalized: it keeps the borrowed engines (dbt, Dagster, the Power BI execution adapter, the Postgres driver, the toolchain) current and upgradeable with no fork tax and no stranding on a snapshot. Lanes B/C route adapter upgrades through human review; no update vendors or re-implements an adapter. |
| III. Medallion, Postgres-First, Gold-Only | Not directly triggered -- the policy builds no SQL and reads no data. It GOVERNS updates to the medallion adapters (dbt/Dagster, Lane B) and requires any update that could regress the gold-only read surface to re-pass its gate; it changes no medallion behavior. |
| IV. Source Mapping Before Silver | Not triggered (no mapping, no silver SQL). The policy sits orthogonal to the stage ordering; it only requires that an update which could regress a stage's gate re-pass it, never reordering the stages. |
| V. Agent Stops at Judgment Calls | A major-version / adapter compatibility verdict is a stop-and-ask: the policy routes the trigger and records evidence; a NAMED human decides (FR-007). Lane B/C mandate a named reviewer. No tool self-approves a merge that touches the readiness spine. |
| VI. Defaults Then Deviations | The lanes ARE the defaults (A auto on green; B review; C never automerge). A deviation (e.g. expediting a security patch) is recorded against the policy, never silent; the transitive-escalation rule defaults to the highest blast radius. |
| VII. C086 Is An Example | FR-011 / SC-005: the policy is generic, stated with placeholders (`<adapter>`, `<dependency>`, `<lane>`); concrete package names appear only as lane-membership examples, with zero C086 / `retail_store_sales` specifics. |
| VIII. Static-First, Live Deferred | This slice writes NO Python, NO rule, NO CLI, NO CI config; no new `retail check` rule is added (checker stays exit 0). The required checks reuse the EXISTING static gate; the live (`retail validate` fixture) and dbt/Dagster smoke checks are marked "once available", not added here. |
| IX. Secrets and Reproducibility | FR-006: no update may introduce a secret/credential/DSN/token/local path into a tracked file -- a hard merge blocker (the no-secrets / no-paths required check). The five planning files are ASCII + UTF-8 no BOM and reproducible. |

**Result**: PASS. No violations; Complexity Tracking left empty.

### Boundary gate (feature-specific, load-bearing)

The single biggest design risk is the apparent contradiction between "automerge" and
"no tool self-approves" (Principle V / Core Authority). The plan holds the boundary
explicitly:

- Lane A automerge is a MECHANICAL bump in the dependency/CI plane. It does NOT define
  business meaning, approve a metric/mapping/PII publish, publish Power BI, clear a
  blocker, or move a readiness stage to `pass`.
- The lanes ARE the encoding of where human judgment is mandatory (B always; C always,
  never automerge) versus where green gates suffice (A).
- The invariant (FR-005): no update in ANY lane may bypass a readiness gate or promote
  a stage. Automerge lives entirely below the readiness spine.

A second boundary: this slice does not bleed into the FUTURE deliverables. It writes
the five Spec-Kit files only; the two policy docs, the ADR, and the optional bot
config are PLANNED outputs, named but not created.

## Project Structure

### Documentation (this feature)

```text
specs/025-adapter-maintenance-policy/
|-- spec.md              # /speckit-specify output (done)
|-- plan.md              # This file (/speckit-plan output)
|-- tasks.md             # /speckit-tasks output
`-- checklists/
    |-- acceptance.md    # spec quality + acceptance checklist
    `-- governance.md    # Core-Authority / Principle-V / no-self-approval gate
```

No `analysis.md`, `research.md`, `data-model.md`, or `contracts/` directory is
generated: there is no code to research, no DB model, and no API contracts. The
"contracts" here are the policy docs themselves, which are FUTURE deliverables (below),
not Spec-Kit `contracts/` artifacts.

### Repository artifacts this feature PLANS (not created)

These are FUTURE outputs this feature ENUMERATES. They are NOT written in this slice.

```text
docs/operations/
|-- dependency-update-policy.md   # PLANNED -- lanes + required checks for toolchain + drivers
`-- adapter-update-policy.md      # PLANNED -- lanes + compatibility-review trigger for dbt/Dagster/Power BI adapters

docs/decisions/
`-- 0009-safe-auto-updates.md     # PLANNED -- ADR: automerge for Lane A on green CI, below the spine; B review; C never

.github/                          # OPTIONAL PLANNED config (one of):
|-- dependabot.yml                # PLANNED (optional) -- encodes the lanes as bot rules
`-- (or) renovate.json            # PLANNED (optional) -- alternative bot encoding
```

**Structure Decision**: docs/planning feature -- no `src/` or `tests/` change. The two
policy docs live in a new `docs/operations/` home (parallel to `docs/readiness/` and
`docs/decisions/`), keeping operations narrative separate from readiness-stage docs and
decision records. The ADR follows the existing `docs/decisions/000N-*.md` convention;
0009 is reserved for this feature (0007/0008 are claimed by sibling features in this
batch -- named here, created later, so no collision). The optional bot config, if
later created, lives under the existing `.github/` next to `workflows/ci.yml`.

## Phase 0 -- Research (no external research needed)

No unknowns requiring external research. The reference shapes are in-repo: the
existing ADRs (`docs/decisions/0001-0004`) for the ADR format; the existing CI
(`.github/workflows/ci.yml`) for the already-in-force required checks; Constitution
Principle II for the depend-not-fork frame and Principle IX for the secrets/paths
rule. The one design decision (the lane boundaries and the automerge-below-the-spine
invariant) is resolved in the spec, not deferred to research.

## Phase 1 -- Design (the artifact shapes)

**dependency-update-policy.md** (planned). Sections: purpose (operationalize Principle
II); the three lanes with their membership (Lane A dev tools / Actions patch-minor /
docs tooling; Lane B `dbt-core` / `dbt-postgres` / `dagster` / `dagster-dbt` /
`psycopg2` / Postgres driver / Power BI modeling utilities; Lane C Power BI execution
adapter / publish-capable / major DB-driver / credentials-auth / semantic-model
behavior); the transitive-escalation rule (highest blast radius wins); the required
checks for any update PR; the no-bypass invariant; the no-secrets/no-paths hard
blocker; the no-score rule. Generic placeholders throughout.

**adapter-update-policy.md** (planned). The adapter-specific overlay: the
major-version / adapter compatibility-review trigger, what the review must name (gates
that could regress, reviewer, outcome), the hand-off of the durable record to F032,
and the Lane B vs Lane C split for dbt/Dagster (B) versus the Power BI execution
adapter (C). Restates the no-fork-tax rule (Principle II): an update is taken by
upgrading the dependency, never by vendoring or re-implementing.

**0009-safe-auto-updates.md** (planned ADR). Decision: allow automerge for Lane A on
green CI, confined below the readiness spine; require human review for Lane B; forbid
automerge for Lane C. Context: Principle II needs a safe upgrade path; the apparent
tension with Principle V. Alternatives considered: (a) no automerge at all (rejected --
re-introduces a fork-tax-by-friction on every dev bump); (b) automerge everything on
green (rejected -- a green build does not prove an adapter's contract with the gates is
intact, and publish-capable/credential changes need a human); (c) the lane split
(chosen). Consequences + the no-bypass invariant.

**Optional bot config** (planned). If later created, encodes Lane A as auto-eligible
and Lane B/C as review-required, grouped by package class; itself subject to this
policy. The choice between `dependabot.yml` and `renovate.json` is the implementation
slice's decision (deferred).

## Phase 1 -- Constitution re-check

Re-checked after design: still PASS. The design adds only planning text now; the
future deliverables it describes are docs/ADR/optional-config that change no gate, add
no rule, read no data, and fork no adapter. Principle II is strengthened (a safe
upgrade path); Principle V is honored (B/C human review; compatibility verdict is the
human's); Principle IX is honored (no-secrets/no-paths hard check). The boundary gate
holds: automerge stays below the readiness spine; this slice creates none of the
future files.

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.
