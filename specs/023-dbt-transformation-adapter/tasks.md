---
description: "Task list for dbt Transformation Adapter (F029)"
---

# Tasks: dbt Transformation Adapter

**Input**: Design documents from `specs/023-dbt-transformation-adapter/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Roadmap feature**: F029 (spec-dir 023; roadmap F-number is authoritative).

**Tests**: This is a PLANNING-ONLY slice (no runtime code, no dbt files) -- there are no
unit tests. The tasks author the five spec-kit files and ENUMERATE the future dbt project +
docs/decision/templates/skill as PLANNED outputs ("Author spec for X" / "Enumerate X"),
never "implement X". Verification tasks (ASCII/no-BOM, zero dbt files added, zero
`retail_store_sales` leak, gate/evidence/parity rules stated) stand in for tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US4) or SETUP/FOUNDATION/POLISH
- All paths are repo-relative from the worktree root

## Path Conventions

Planning slice -- no `src/`, no `dbt/`. Files written this slice live under
`specs/023-dbt-transformation-adapter/`. Everything under `dbt/`, `templates/dbt-*`,
`docs/integrations/`, `docs/decisions/`, and `.claude/skills/dbt-transformation-adapter/`
is a PLANNED future output, ENUMERATED only.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the reconciliation target and the reference house style.

- [ ] T001 Re-read `warehouse/migrations/0003_create_silver_retail_store_sales.sql` and
      `0004_create_gold_retail_store_sales_star.sql` to pin the EXACT parity target:
      `gold.fct_sales_rss` (transaction grain, `transaction_id` degenerate dim, four entity
      dims + -1 unknown members, `dim_date_rss` a contiguous `generate_series` calendar,
      additive measures `price_per_unit`/`quantity`/`total_spent`). This is the migration
      output the dbt mart must reproduce AS COMMITTED. NOTE: migration 0004 currently inserts
      a -1 member into `dim_date_rss` (line ~89), which `retail check` S8 flags; F029
      reproduces the committed gold as-is and does NOT resolve that pre-existing S8/docs
      tension (16110d8 split-brain). If S8 is fixed later, the mart follows the migration.
- [ ] T002 [P] Re-read `specs/010-metric-contract-store/` (spec/plan/tasks/checklist) for
      house style, and `docs/roadmap/roadmap.md` for the spine + the numbering note.

**Checkpoint**: parity target pinned; house style + numbering pinned.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix the three load-bearing rules every artifact reuses verbatim.

**CRITICAL**: No user-story content may be authored until these are fixed, or the spec will
drift into letting dbt define meaning or auto-approve a stage.

- [ ] T003 Fix the ENTRY-GATE rule: dbt may run NO staging/silver/gold model for a table
      whose Mapping Ready is not `pass` (Principle IV). Pin it for reuse across spec +
      checklists.
- [ ] T004 Fix the EVIDENCE-NOT-APPROVAL rule: dbt test results are recorded as `evidence[]`
      / `blocking_reasons[]`; a green `dbt test` NEVER moves Silver/Gold Ready to `pass` --
      Tower readiness + a named human do, citing dbt evidence + the approval. Pin verbatim.
- [ ] T005 Fix the OPTIONAL-ALTERNATIVE + PARITY rule: migrations stay the DEFAULT;
      dbt becomes a table's build path only after the parity test passes (equal row count,
      `transaction_id` distinct count preserved, additive-measure sum within tolerance vs
      `gold.fct_sales_rss`) AND a named human approves. Pin verbatim.

**Checkpoint**: entry-gate, evidence-not-approval, and parity rules are fixed and ready to
drop into the spec + both checklists identically.

---

## Phase 3: User Story 1 - dbt builds only after Mapping Ready = pass (Priority: P1)

**Goal**: The spec encodes the entry gate as the adapter's first refusal point.

**Independent Test**: confirm the spec states REFUSE + record a `blocking_reason` when
Mapping Ready is not `pass`, and permit only when it is `pass`.

- [ ] T006 [US1] In spec.md, confirm FR-001 + US1 acceptance scenarios encode the entry gate
      (T003) and the no-extend-the-map rule (a model citing meaning the map lacks is a defect).
- [ ] T007 [US1] In plan.md, confirm the planned SKILL.md is enumerated as running dbt ONLY
      behind Mapping Ready=`pass` (planned future output -- not authored this slice).

**Checkpoint**: the entry gate is unambiguous in spec + plan.

---

## Phase 4: User Story 2 - Every dbt model cites its source-map evidence (Priority: P1)

**Goal**: The spec + the planned model contract bind every model to approved map rows.

**Independent Test**: confirm the planned `dbt-model-contract.md` is enumerated as citing the
approved `source-map.yaml` (path + git ref + rows) for grain/PK/each column.

- [ ] T008 [US2] In spec.md, confirm FR-002 + US2 acceptance scenarios require map citation
      per model and treat a missing citation / stale citation (after a map version change) as
      a defect (reconciles with F008 mapping-diff review).
- [ ] T009 [US2] In plan.md, ENUMERATE `templates/dbt-model-contract.md` as a PLANNED generic
      template (source-map citations, grain, tests) -- not authored this slice; generic, no
      `retail_store_sales` values.

**Checkpoint**: the citation requirement and its planned template home are recorded.

---

## Phase 5: User Story 3 - dbt tests produce evidence; readiness + a human decide (Priority: P1)

**Goal**: The spec encodes the governance hinge -- evidence, never auto-approval.

**Independent Test**: confirm there is NO path by which a green `dbt test` alone writes
`pass`; every transition cites dbt evidence + a named human approval.

- [ ] T010 [US3] In spec.md, confirm FR-004 + US3 acceptance scenarios encode the
      evidence-not-approval rule (T004), the basic-tests set (`unique`/`not_null`/
      `relationships` + reconciliation), and the stop-and-ask Principle V list (FR-003).
- [ ] T011 [US3] In plan.md, ENUMERATE `templates/dbt-adapter-contract.md` + the ADR
      `docs/decisions/0007-dbt-is-transformation-adapter.md` as PLANNED outputs that state the
      evidence-not-approval rule and the auto-update policy (T004 + FR-010) -- not authored now.
- [ ] T012 [US3] In spec.md, confirm the Human approval boundary + Forbidden operations
      sections list: no self-granted Silver/Gold Ready, no defining mapping/metric contracts,
      no business meaning, no publishing Power BI, no silent grain change.

**Checkpoint**: the governance hinge is stated in spec + plan + the planned contract/ADR.

---

## Phase 6: User Story 4 - dbt output must reconcile to the existing gold tables (Priority: P2)

**Goal**: The spec encodes the parity test as the precondition for dbt to become a build path.

**Independent Test**: confirm the parity test asserts equal row count, preserved
`transaction_id` distinct count, and additive-measure sum within tolerance vs
`gold.fct_sales_rss`, and that a mismatch keeps Gold Ready `blocked` + migrations default.

- [ ] T013 [US4] In spec.md, confirm FR-006 + FR-007 + US4 acceptance scenarios encode the
      optional-alternative posture (T005), the three parity assertions, and the
      human-approved build-path switch.
- [ ] T014 [US4] In plan.md, ENUMERATE the PLANNED `dbt/tests/` reconciliation test + the
      first-MVP scope (one `retail_store_sales` staging model + one mart model + basic tests)
      against `gold.fct_sales_rss` -- enumerated, not authored.
- [ ] T015 [US4] In spec.md, confirm the parity TOLERANCE is recorded as a stated default
      (cent-level, given `NUMERIC(12,2)`) and listed under Deferred decisions for human
      confirmation at build time.

**Checkpoint**: the parity gate + first-MVP scope are recorded as the dbt-becomes-default
precondition.

---

## Phase 7: Polish & Cross-Cutting Verification

**Purpose**: Whole-feature gates spanning all four stories.

- [ ] T016 Confirm this slice creates ZERO dbt files and ZERO runtime code -- only the five
      spec-kit files under `specs/023-dbt-transformation-adapter/` (diff check). [SC-005,
      FR-011]
- [ ] T017 [P] Confirm every GENERIC planned artifact (the two contract templates, the ADR,
      the integration doc, the skill) is enumerated as carrying ZERO `retail_store_sales`/C086
      values; `retail_store_sales` appears only as the cited filled example. [SC-004, FR-012]
- [ ] T018 [P] Confirm the no-secrets rule is stated: only `profiles.example.yml`
      (placeholders) planned for commit; `profiles.yml` enumerated as git-ignored; no
      DSN/credential/host anywhere. [SC-006, FR-008]
- [ ] T019 Confirm the auto-update policy is explicit: pin dbt-core + dbt-postgres together;
      patch/minor -> PR; major -> human review; no automerge for minor/major until
      compatibility tests exist. [SC-007, FR-010]
- [ ] T020 Confirm all five files are ASCII + UTF-8 no BOM and repo-relative paths stay short
      (`<= 200` chars). [Principle IX]
- [ ] T021 Confirm spec header carries BOTH numbers (Roadmap F029 / spec-dir 023) + the
      numbering note, and that no task edited the roadmap.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies -- start immediately.
- **Foundational (Phase 2)**: depends on Setup; BLOCKS all user stories (fixes the entry
  gate, evidence-not-approval, and parity rules every artifact reuses verbatim).
- **User Stories (Phase 3-6)**: all depend on Foundational. US1/US2/US3 (P1) are the MVP
  boundary -- the gate, the citation, and the evidence-not-approval hinge. US4 (P2, parity)
  follows because parity is only meaningful once dbt is allowed to build (US1) and produces
  evidence (US3).
- **Polish (Phase 7)**: depends on all four stories complete.

### User Story Dependencies

- **US1 (P1)**: the entry gate -- independent after Foundational.
- **US2 (P1)**: the map-citation rule -- independent after Foundational.
- **US3 (P1)**: the evidence-not-approval hinge -- independent after Foundational.
- **US4 (P2)**: parity -- depends conceptually on US1 (dbt allowed to build) + US3 (dbt
  produces evidence) being stated first.

### Parallel Opportunities

- T002 (read references) runs parallel to T001.
- The five spec-kit files are authored in one pass (this slice already wrote them); the
  task list documents the intended ordering for a reviewer.
- Polish T017/T018 are independent confirmations -- parallel.

## Parallel Example

```
# Setup reads run together:
Re-read warehouse/migrations 0003/0004 (T001: parity target)
Re-read specs/010 + roadmap (T002: house style + numbering)
```

## Implementation Strategy

**MVP first**: Setup -> Foundational -> US1 + US2 + US3 = the gate, the citation, and the
evidence-not-approval hinge (the three P1 rules that keep dbt a build engine, not the
brain). Then US4 (parity, the precondition for dbt to become a table's default), then the
Phase 7 whole-feature gates.

**Boundary discipline (the load)**: every artifact carries the same verbatim entry-gate
(T003), evidence-not-approval (T004), and parity (T005) rules; Phase 7 proves zero dbt
files, zero `retail_store_sales` leak, no secrets, and the explicit auto-update policy --
the ways this DB-connected adapter could rot into the brain or leak a secret.

**Planning-only discipline**: every `dbt/` artifact, both contract templates, the ADR, the
integration doc, and the skill are ENUMERATED as planned future outputs. No task implements
them this slice; the deliverables are the five spec-kit files only.
