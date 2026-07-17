---
description: "Task list for activating the dagster-dbt engine seam"
---

# Tasks: Activate the dagster-dbt Engine Seam

**Input**: Design documents from `/specs/135-activate-dagster-dbt-seam/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Included. Every implementation task follows RED -> GREEN: the fixture
test is written first and MUST fail before the implementation that turns it green.
Fixture tests use a fake dbt runner and monkeypatched gate commands -- no database,
no secrets.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependencies)
- **[Story]**: which user story this task serves (US1..US5) or SETUP/FOUND/POLISH
- Exact file paths are absolute-from-repo-root

## Path Conventions

- Orchestration project: `orchestration/dagster/src/tower_bi_orchestration/` and
  `orchestration/dagster/tests/`
- Main-package control layer: `src/seshat/dagster_adapter/` and
  `tests/unit/dagster_adapter/`
- No new project is created; this feature edits two existing projects.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: make the orchestration environment able to run the dbt engine, with
the main package unchanged.

- [x] T001 [SETUP] In `orchestration/dagster/pyproject.toml`: REMOVE the
  `dagster-dbt==0.29.14` pin (FR-011 owner decision resolving plan-review R3:
  it excludes dbt-core 1.12 and sits on no execution path) and ADD
  `seshat-bi[dbt]`; do NOT touch the main package `pyproject.toml`. Prove the
  resulting solve in a fresh venv (dagster 1.13.14 + seshat-bi[dbt] ->
  dbt-core 1.12.0 + dbt-postgres 1.10.2) and record the solver output. Then
  reconcile every surface asserting the old dagster/dagster-dbt pinned pair to
  the dagster-only reality: `seshat.dagster_adapter` PINNED_* constants and
  doctor findings, the definitions-load smoke, spec-134-era contract tests that
  pin the pair, and living docs -- each recording the removal as a deliberate
  owner decision, never silently.
- [x] T002 [P] [SETUP] Confirm the `.gitignore` baseline still ignores raw dbt
  `target/`/`logs/`/local lock files and `.seshat/dagster/runs/` (spec 133 FR-030
  / spec 134); add nothing that ignores a committed `definition/`, `dbt/models`,
  or evidence markdown.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the guard that keeps the main package clean, and the engine resolver
every build branch depends on. BLOCKS all user stories.

- [x] T003 [FOUND] Extend/confirm the base-import guard test so importing base
  `seshat` (and running a non-dbt CLI path) loads NO `dagster`, `dagster_dbt`, or
  `dbt` module -- in `tests/unit/dagster_adapter/` or the existing import-guard
  test module. RED first (assert the modules are absent), then keep it green by
  NOT adding any main-package dependency.
- [x] T004 [FOUND] Write `orchestration/dagster/tests/test_engine_resolution.py`
  (RED): fixtures for `absent`, `engine: migrations`, `engine: dbt`,
  `engine: <malformed>` -> assert only exact `dbt` resolves to `dbt` and all others
  to `migrations`; assert no exception leaks a path/secret. (US2/SC-003)
- [x] T005 [FOUND] Implement
  `orchestration/dagster/src/tower_bi_orchestration/engine.py`:
  `resolve_build_engine(root, table, layer) -> "migrations" | "dbt"`, fail-closed
  default `migrations`, exact-match only, generic/placeholder config source
  (Principle VII). Turn T004 GREEN.

**Checkpoint**: engine resolution exists and fails closed; the main package is
provably clean. User stories can begin.

---

## Phase 3: User Story 1 - dbt engine builds through the governed path with identical gate semantics (Priority: P1) MVP

**Goal**: `engine: dbt` runs the governed `seshat.dbt` build into shadow schemas,
then the SAME `seshat check` gate; non-zero fails and skips downstream; zero
materializes.

**Independent Test**: `engine: dbt`, gate cleared, fake successful dbt runner ->
governed plan computed + digest recomputed (no raw selector) + shadow-only +
`seshat check` runs; forced non-zero check fails the asset and skips downstream;
no readiness/`Gate status`/`approvals[]` changed.

### Tests for User Story 1 (write first, must fail)

- [x] T006 [P] [US1] Write `orchestration/dagster/tests/test_dbt_engine_build.py`
  (RED): with a fake `seshat.dbt` runner, assert the governed plan is computed and
  the accept-plan digest recomputed (no raw dbt selector/argument), the build
  targets shadow schemas only, and `seshat check` is invoked; assert exit 0 ->
  materialized with dbt engine + selector + measured recorded (never `pass`,
  never a score). (SC-001)
- [x] T007 [P] [US1] In the same module, add the fail-closed case (RED): a forced
  non-zero `seshat check` under the dbt engine -> asset failed, all downstream
  skipped, evidence records the non-zero exit -- identical to migrations. (SC-002)

### Implementation for User Story 1

- [x] T008 [US1] Implement
  `orchestration/dagster/src/tower_bi_orchestration/dbt_build.py`:
  `build_layer(context, table, layer, root)` delegating to `seshat.dbt`
  (`gate.resolve_working_set` + mapping-gate eval, `planning` execution plan for
  the fixed `seshat_table_<table>` selector, accept-plan digest recompute +
  refuse-on-drift, `runner` shadow-schema build); return
  `(exit_code, measured, dbt_evidence_path)`; reject any raw dbt argument; run all
  surfaced text through the shared redaction. (FR-002/FR-003)
- [x] T009 [US1] Edit `_build_layer` in
  `orchestration/dagster/src/tower_bi_orchestration/assets/gates.py` to branch on
  `resolve_build_engine(...)`: keep the DSN/deferred preamble and the trailing
  `commands.run_gate_command(commands.checker_argv(), cwd=root)` gate UNCHANGED;
  `migrations` -> existing migration loop; `dbt` -> `dbt_build.build_layer(...)`.
  Record `engine` in `measured`; under the dbt engine also record
  `warehouse_updated: false` and the self-accepted-plan marker (FR-014/FR-015).
  Turn T006/T007 GREEN. (FR-004/FR-005)

**Checkpoint**: the dbt engine builds through the governed path with the gate
identical to migrations, proven in-process with no DB.

---

## Phase 4: User Story 2 - engine is explicit and fails closed to migrations (Priority: P1)

**Goal**: only exact `engine: dbt` engages dbt; everything else uses migrations.

**Independent Test**: covered by the engine-resolution fixtures (T004/T005) plus
an asset-level assertion that the migrations branch runs for non-`dbt` values.

### Tests for User Story 2 (write first, must fail)

- [x] T010 [P] [US2] Add to `test_dbt_engine_build.py` (RED): assert that with
  `engine` absent / `migrations` / malformed, `_build_layer` takes the migrations
  branch and records `engine: migrations`; only exact `dbt` takes the dbt branch.
  (SC-003)

### Implementation for User Story 2

- [x] T011 [US2] Confirm `_build_layer` (T009) consumes `resolve_build_engine`
  such that T010 passes with no additional inference; add the `engine` field to the
  recorded `measured` for both branches. (FR-001)

**Checkpoint**: the fail-closed default is enforced at the asset boundary.

---

## Phase 5: User Story 3 - dbt engine unavailable or no live profile (Priority: P2)

**Goal**: `engine: dbt` with no DSN records `deferred`; with the dbt runtime absent
it blocks with a concrete remedy; neither fabricates a pass; no traceback.

**Independent Test**: `engine: dbt` fixtures with (a) no DSN and (b) dbt extra
absent -> (a) `deferred` + timestamp, (b) blocked + enable remedy; neither writes a
readiness pass.

### Tests for User Story 3 (write first, must fail)

- [x] T012 [P] [US3] Write
  `orchestration/dagster/tests/test_dbt_engine_deferred.py` (RED): `engine: dbt`
  + no DSN -> `deferred` outcome with timestamp, blocked fail-closed, no pass;
  `engine: dbt` + dbt runtime unimportable -> `blocked` with concrete
  `blocking_reason` + named owner, no traceback. ALSO (plan-review F4/R6): a dbt
  error containing a fake DSN/host must be absent from the dagster record
  (redaction fixture on the dbt path), and lock contention must surface as a
  concrete redacted `blocking_reason` per `seshat.dbt` bounded-lock semantics --
  a stale-lock gap found in `seshat.dbt` is surfaced to the owner, not patched
  here. (SC-004)

### Implementation for User Story 3

- [x] T013 [US3] Ensure `_build_layer` records `deferred` when
  `db.resolve_dsn()` is None under the dbt engine (reuse the existing preamble),
  and `dbt_build.build_layer` maps an unimportable dbt runtime / `seshat.dbt`
  `unavailable` to a dagster `blocked` outcome with a redacted reason. Turn T012
  GREEN. (FR-006)

**Checkpoint**: the dbt engine degrades truthfully; live drive stays deferred.

---

## Phase 6: User Story 4 - doctor surfaces the resolved engine mode (Priority: P2)

**Goal**: `seshat dagster doctor` reports the resolved engine per table and dbt
availability, truthfully, no score.

**Independent Test**: doctor over mixed-engine fixtures reports each table's
resolved engine and dbt availability; no score, no fabricated live pass.

### Tests for User Story 4 (write first, must fail)

- [x] T014 [P] [US4] Write
  `tests/unit/dagster_adapter/test_doctor_engine_mode.py` (RED): fixtures with
  `engine: dbt` and `engine: migrations` -> assert the categorical engine finding
  per table, plus a deferred/enable finding under `dbt` when the runtime or DSN is
  absent; assert no numeric score and DSN never echoed. ALSO (plan-review R2 /
  FR-015): a table whose layers resolve to MIXED engines produces a WARNING
  finding naming the mix. (FR-010)

### Implementation for User Story 4

- [x] T015 [US4] Edit `run_doctor` / add an engine-mode finding in
  `src/seshat/dagster_adapter/doctor.py` (read-only, categorical, concrete
  remedy). Turn T014 GREEN. (FR-010)

**Checkpoint**: the engine mode is visible in the preflight.

---

## Phase 7: User Story 5 - migrations remain the untouched oracle and rollback (Priority: P1)

**Goal**: activating dbt never mutates/deletes a migration and never writes
migration-owned gold; reverting to `migrations` reproduces prior behavior.

**Independent Test**: with `engine: dbt` active, `warehouse/migrations/` unchanged
and dbt wrote shadow only; flip to `migrations` -> pre-feature behavior reproduced.

### Tests for User Story 5 (write first, must fail)

- [x] T016 [P] [US5] Write
  `orchestration/dagster/tests/test_migrations_unchanged.py` (RED): assert a
  dbt-engine run touches no `warehouse/migrations/*.sql` file and requests only
  shadow-schema targets from the fake dbt runner; assert a reverted
  `engine: migrations` run is byte-identical in behavior to the pre-feature path.
  (SC-007)

### Implementation for User Story 5

- [x] T017 [US5] Verify no code path in `dbt_build.py` or `gates.py` deletes,
  edits, or supersedes a migration or targets migration-owned `silver`/`gold`;
  add an explicit guard/assertion if the fake-runner test surfaces a gap. Turn
  T016 GREEN. (FR-003)

**Checkpoint**: the rollback and parity oracle are intact.

---

## Phase 8: Docs, Evidence, and Cross-Cutting

**Purpose**: reconcile the documented seam and prove the invariants.

- [x] T018 [POLISH] Reconcile EVERY living doc claiming the seam is future:
  `docs/integrations/dagster-adapter.md` section "The dagster-dbt engine seam
  (activates after spec 133 merges)" AND `orchestration/dagster/README.md`, plus
  a grep-sweep for remaining "activates after spec 133" / seam-as-future claims
  in living docs -- activated selectable-engine reality, fail-closed default,
  `[PENDING LIVE PROFILE]` live status, history preserved, no live-pass claim.
  Frozen artifacts (specs/134 dir, CHANGELOG history, docs/releases/*) MUST NOT
  be reworded. (FR-013, plan-review R4)
- [x] T019 [P] [POLISH] Add a schema-and-topology invariant test (RED->GREEN):
  assert `git diff` shows no change to `schemas/dagster-run-evidence.schema.json`
  and no change to asset deps/edges; assert a dbt-engine evidence record still
  validates against the unchanged schema (only `gate_command`/`measured` differ,
  including the new `engine`, `warehouse_updated`, and self-accepted-plan
  measured fields). ALSO the STATIC no-bypass oracle (plan-review R5): assert no
  module in `tower_bi_orchestration` imports `dagster_dbt` execution APIs
  (`DbtCliResource` / `@dbt_assets`) and the bridge invokes dbt only through
  `seshat.dbt.runner`. (SC-006/FR-008)
- [x] T020 [P] [POLISH] Add an evidence-distinctness assertion: the dagster record
  may cite the `mappings/<table>/dbt-evidence/` path but never merges/overwrites
  it. (FR-009)
- [x] T022 [P] [POLISH] Readiness-no-write negative test on the dbt path
  (plan-review F1, the spec-134 US3 git-diff oracle): after a full dbt-engine
  fixture run, assert `git diff` shows ZERO changes to readiness `status:`
  fields, `Gate status:` lines, `approvals[]` entries, mappings, and metric
  definitions -- the oracle sits ON the untrusted write path. (FR-007/SC-005)
- [x] T021 [POLISH] Full verification: run the main pytest suite + the
  orchestration tests, ruff format/lint, `seshat check`, and the base-import guard;
  record the dagster-dbt 0.29.14 <-> dbt-core 1.12.0 live-drive status as
  `[PENDING LIVE PROFILE]` (compile still pending per
  `docs/operations/dbt-activation-status.yaml`); do NOT claim a live pass. (SC-008)

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): no dependencies.
- Foundational (Phase 2): depends on Setup; BLOCKS all user stories (engine
  resolver + import guard).
- User stories (Phases 3-7): depend on Foundational. US1 is the MVP and must land
  first (the dbt branch other stories assert against). US2 depends on US1's branch;
  US3/US4/US5 depend on US1's branch but are otherwise independent.
- Docs/cross-cutting (Phase 8): depends on the user stories being complete.

### Within Each User Story

- The fixture test is written and FAILS before its implementation.
- The engine resolver (T005) precedes the build branch (T009).
- The build branch (T009) precedes US2/US3/US5 assertions against it.

### Parallel Opportunities

- T002 (gitignore confirm) runs parallel to T001.
- T006/T007/T010 target one test module (US1/US2) -- keep sequential to avoid the
  same-file conflict; T012, T014, T016 are separate modules and are `[P]`.
- T019/T020 are separate assertions and are `[P]`.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Setup (Phase 1) + Foundational (Phase 2).
2. User Story 1 (the governed dbt branch with the identical gate).
3. STOP and VALIDATE: US1 fixture tests pass in-process, no DB.

### Incremental Delivery

1. Setup + Foundational -> engine resolves, main package clean.
2. US1 -> dbt engine builds governed with identical gate (MVP).
3. US2 -> explicit fail-closed default enforced at the asset.
4. US3 -> deferred/unavailable truthfulness.
5. US4 -> doctor engine-mode surfacing.
6. US5 -> migrations-oracle intactness.
7. Phase 8 -> doc reconcile + invariant proofs.

## Notes

- [P] = different files, no dependencies.
- Verify each fixture test fails before implementing.
- Commit after each task or logical group.
- Do NOT mark any checkbox done here; completion is claimed per verified
  deliverable during implementation, never by a bulk sweep.
- Live dbt drive stays `[PENDING LIVE PROFILE]`; no task may fabricate a live
  pass.
