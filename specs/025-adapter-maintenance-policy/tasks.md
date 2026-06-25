---
description: "Task list for Adapter Maintenance and Auto-Update Policy (F031)"
---

# Tasks: Adapter Maintenance and Auto-Update Policy

**Input**: Design documents from `specs/025-adapter-maintenance-policy/` (F031, spec dir 025)

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: This is a docs/planning-only slice (no runtime code) -- there are no unit
tests. Verification tasks (lane table total, required-checks list exact, no-bypass
invariant provable, `retail check` exit 0 + no new rule added, ASCII/no-BOM,
generic-check) stand in for tests and are included explicitly. The future
deliverables are written as PLANNING tasks ("Author the policy for X"), never as
"implement X" -- nothing under `docs/operations/`, `docs/decisions/`, or `.github/`
is created in this slice.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3) or SETUP/POLISH
- All paths are repo-relative from the worktree root

## Path Conventions

Docs/planning feature -- no `src/`/`tests/`. This slice writes ONLY the five Spec-Kit
files under `specs/025-adapter-maintenance-policy/`. The future deliverables
(`docs/operations/dependency-update-policy.md`,
`docs/operations/adapter-update-policy.md`,
`docs/decisions/0009-safe-auto-updates.md`, optional `.github/dependabot.yml` /
`renovate.json`) are ENUMERATED, not created.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Pin the reference shapes and the one invariant the whole policy hangs on.

- [ ] T001 Re-read the reference shapes: Constitution Principle II ("Depend, Never
      Fork") and Principle IX ("Secrets and Reproducibility") in
      `.specify/memory/constitution.md`; the existing CI required checks in
      `.github/workflows/ci.yml` (ruff format check, ruff lint, `pytest -m unit`,
      `retail check`); and the ADR format in `docs/decisions/0001-0004`.
- [ ] T002 [P] Pin the load-bearing invariant verbatim for reuse across all artifacts:
      "No update in ANY lane may bypass a readiness gate or move any stage to `pass`;
      automerge lives entirely below the readiness spine." Capture it once so spec,
      plan, and both planned docs state it identically.

**Checkpoint**: Principle II/IX framing + the no-bypass invariant are fixed and ready
to drop into each artifact identically.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The lane definition + required-checks list + no-score/no-secrets rules
that ALL three user stories depend on.

**CRITICAL**: No user story may be authored until the lanes, the required checks, and
the guardrails are fixed, or the artifacts will drift (an unclassified update, a
self-approving automerge, or a fabricated maturity score).

- [ ] T003 Fix the three-lane definition (single source of truth) to reuse in the spec
      and both planned docs: Lane A (Ruff / Pytest / pre-commit / dev tools / GitHub
      Actions patch-minor / docs tooling -- automerge-eligible on green CI); Lane B
      (`dbt-core` / `dbt-postgres` / `dagster` / `dagster-dbt` / `psycopg2` /
      Postgres-driver / Power BI modeling utilities -- human review required); Lane C
      (official Power BI MCP / execution adapter / publish-capable / major DB-driver /
      credentials-auth / semantic-model-behavior -- never automerge). [FR-001]
- [ ] T004 Fix the required-checks list for ANY update PR: ruff format check, ruff
      lint, `pytest -m unit`, `retail check`, `retail validate` fixture mode (if
      available), semantic check fixture mode (if available), dbt compile/build smoke
      (once dbt exists), Dagster definitions-load smoke (once Dagster exists),
      no-secrets scan, no-raw-data scan, dependency-invariants note. Mark which are
      already in CI vs "once that adapter exists / if available". [FR-004, FR-009]
- [ ] T005 Fix the guardrail set every artifact reuses: the no-bypass invariant (T002);
      the transitive-escalation rule (highest blast radius wins); the no-secrets /
      no-paths hard blocker (Principle IX); the no-score rule (hard rule #9); the
      compatibility-verdict-is-the-human's rule (Principle V). [FR-005, FR-006, FR-007,
      FR-008, FR-010]

**Checkpoint**: lanes + required checks + guardrails are fixed and ready to drop into
each artifact identically.

---

## Phase 3: User Story 1 - Every update is classified into a lane before it can merge (Priority: P1) MVP

**Goal**: The spec + planned dependency-update-policy fully define the three lanes and
the classification rule.

**Independent Test**: classify the six representative update PRs (Ruff patch, GitHub
Action minor, `dbt-core` minor, `psycopg2` change, major DB-driver bump, Power BI
execution-adapter bump) -- each lands in exactly one lane and only Lane A is
automerge-eligible.

- [ ] T006 [US1] In `spec.md`, state the three-lane table (T003) with the
      automerge-eligibility column and the transitive-escalation rule, and the US1
      acceptance scenarios. [FR-001, FR-008]
- [ ] T007 [US1] Author the PLANNING task for `docs/operations/dependency-update-policy.md`
      (NOT the doc itself): record that it will carry the lane table, the
      transitive-escalation rule, the required checks, and the no-bypass invariant.
      Enumerate it in plan.md's "Repository artifacts this feature PLANS (not created)"
      list with its exact path. [FR-011, SC-001]
- [ ] T008 [US1] Verify the lane table is TOTAL and unambiguous: every example package
      class in FR-001 maps to exactly one lane, the six representative PRs classify
      with no tie and no gap, and only Lane A is automerge-eligible. [SC-002]

**Checkpoint**: any update can be classified into exactly one lane; MVP done.

---

## Phase 4: User Story 2 - An update PR merges only when all required checks are green (Priority: P1)

**Goal**: The spec + planned policy fix the required checks and prove a red check
blocks merge in every lane, and that Lane A automerge is conditional on all-green.

**Independent Test**: a PR with one required check red is non-mergeable in every lane
(including Lane A automerge); the same PR all-green (plus a named reviewer for B/C) is
mergeable.

- [ ] T009 [US2] In `spec.md`, state the exact required-checks list (T004) and the rule
      that ALL must pass before merge; state that Lane A automerge is conditional on
      all-green and a red/absent check blocks merge in every lane. [FR-003, FR-004]
- [ ] T010 [US2] In `spec.md`, state the "not applicable yet (<reason>)" handling for a
      required check that does not yet exist (dbt/Dagster smoke, fixture modes), and
      that its absence never unblocks a merge another check is blocking. [FR-009]
- [ ] T011 [US2] Author the PLANNING task for the no-secrets / no-raw-data / no-local-paths
      required check as a HARD merge blocker in every lane (Principle IX), to be
      documented in the planned dependency-update-policy. [FR-006]
- [ ] T012 [US2] Verify the required-checks list is exact and enforceable: every check
      is either already in `.github/workflows/ci.yml` or marked "once available", and
      a red check is provably non-mergeable in every lane. [SC-003]

**Checkpoint**: an update PR's mergeability is fully determined by the required checks
plus (for B/C) a named reviewer.

---

## Phase 5: User Story 3 - A major-version or adapter update triggers an explicit compatibility review (Priority: P2)

**Goal**: The spec + planned adapter-update-policy + the ADR define the
major-version / adapter compatibility-review trigger and the hand-off to F032.

**Independent Test**: a major-version adapter bump is Lane B/C, requires an explicit
compatibility-review record (gates affected, reviewer, outcome), and references F032's
matrix as the durable home; the policy makes no self-verdict.

- [ ] T013 [US3] In `spec.md`, state the major-version / adapter compatibility-review
      trigger: what the review must name (gates that could regress, named reviewer,
      outcome) and that the durable record lives in F032 (spec 026). [FR-007]
- [ ] T014 [US3] Author the PLANNING task for `docs/operations/adapter-update-policy.md`
      (NOT the doc): the adapter-specific overlay -- Lane B for dbt/Dagster, Lane C for
      the Power BI execution adapter, the compatibility-review trigger, the no-fork-tax
      restatement (Principle II). Enumerate it in plan.md's PLANS list. [FR-007, SC-001]
- [ ] T015 [US3] Author the PLANNING task for `docs/decisions/0009-safe-auto-updates.md`
      (NOT the ADR): the automerge decision (Lane A on green CI, below the spine; B
      review; C never), the alternatives (no-automerge-at-all; automerge-everything;
      the lane split chosen), and the no-bypass invariant. Enumerate it in plan.md's
      PLANS list; note 0009 is reserved (0007/0008 claimed by sibling features).
      [SC-001, SC-004]
- [ ] T016 [US3] Author the PLANNING task for the OPTIONAL bot config
      (`.github/dependabot.yml` / `renovate.json`): if later created it ENCODES the
      lanes (A auto-eligible, B/C review-required) and is itself subject to this
      policy; the dependabot-vs-renovate choice is DEFERRED. Enumerate it in plan.md's
      PLANS list as OPTIONAL. [FR-012]

**Checkpoint**: the adapter overlay, the ADR, and the optional config are fully
planned (named, not created), with the compatibility verdict routed to a human + F032.

---

## Phase 6: Polish and Cross-Cutting Verification

**Purpose**: Whole-feature gates that span all three stories.

- [ ] T017 Verify the no-bypass invariant is provable across the spec + governance
      checklist: no lane (including Lane A automerge) can move a stage to `pass`, clear
      a blocker, or skip a gate -- automerge is confined to the dependency/CI plane.
      [SC-004]
- [ ] T018 Run `retail check` over the repo: confirm exit 0 and that the diff adds no new rule
      (this feature adds no rule). [Principle VIII]
- [ ] T019 [P] Grep the five planning files for C086 / `retail_store_sales` /
      pharmacy leakage (billing codes, segment rollups, PII columns, grain keys) --
      expect zero; confirm placeholders (`<adapter>`, `<dependency>`, `<lane>`) only.
      [FR-011, SC-005]
- [ ] T020 [P] Confirm no `docs/operations/`, `docs/decisions/`, or `.github/` file was
      created this slice and no new Python/CLI/rule was added -- the planning boundary
      holds; only the five Spec-Kit files exist. [SC-001]
- [ ] T021 Confirm a "dependency health score" request is DECLINED in the spec with the
      no-fake-confidence rationale, and that status is explicit checks + lane +
      reviewer only. [FR-010, SC-005]
- [ ] T022 Confirm all five files are ASCII + UTF-8 no BOM and repo-relative paths stay
      short (`<= 200` chars). [Principle IX]
- [ ] T023 Record FR-002 traceability: the "all updates PR-based; no direct push to a
      protected branch; no `--no-verify` / gate-skip" requirement is satisfied-by-assumption
      -- it is inherited from the global git rules + branch protection (spec Assumptions:
      "assumes, not re-establishes"), enforced by `checklists/governance.md`, not re-authored
      here. Confirm this note so FR-002 is traceable rather than silently unmapped. [FR-002]

---

## Dependencies and Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies -- start immediately.
- **Foundational (Phase 2)**: depends on Setup; BLOCKS all user stories (fixes the
  lanes, the required checks, and the guardrails every artifact reuses verbatim).
- **User Stories (Phase 3-5)**: all depend on Foundational. US1 (P1) is the MVP and
  goes first because US2's required-checks rule and US3's compatibility trigger both
  build on the lane classification. US2 (P1) depends on US1's lanes. US3 (P2) depends
  on US1's lanes and US2's checks.
- **Polish (Phase 6)**: depends on all three stories complete.

### User Story Dependencies

- **US1 (P1)**: independent after Foundational -- the lane classification (MVP).
- **US2 (P1)**: needs US1's lanes (a check's blocking effect is stated per lane).
- **US3 (P2)**: needs US1's lanes and US2's checks (the compatibility review sits atop
  Lane B/C and the required checks).

### Parallel Opportunities

- T002 (pin the invariant) runs parallel to T001.
- Within a user story, the spec edits touch ONE file (`spec.md`) -- author in one pass
  (not parallel); the planning-task enumerations land in `plan.md` and `tasks.md`.
- Polish T019/T020 are independent greps -- parallel.

## Parallel Example: after US1 ships

```
# US2 and US3 build on US1's lanes; their spec sections touch different parts of spec.md
# and their PLANS entries touch plan.md -- sequence the spec edits, parallelize the greps:
US2: required-checks rule + not-applicable-yet handling (T009-T012)
US3: compatibility-review trigger + planned adapter doc/ADR/config (T013-T016)
```

## Implementation Strategy

**MVP first**: Setup -> Foundational -> US1 = the three-lane classification (any update
lands in exactly one lane). Then US2 (required checks gate the merge) + US3
(compatibility review + the planned adapter doc/ADR/config) build on it, then the
Phase 6 whole-feature gates.

**Boundary discipline (the load)**: every artifact carries the same verbatim no-bypass
invariant (T002) and lane/required-check definitions (T003/T004); Phase 6 (T017-T021)
proves the three ways this feature could fail its own scope -- a lane that bypasses a
gate, a created future deliverable, or a fabricated maturity score.
