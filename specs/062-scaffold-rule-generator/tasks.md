---
description: "Task list for feature 062 scaffold-rule generator + doctor"
---

# Tasks: Scaffold-Rule Authoring Generator + Doctor

**Input**: Design documents from `specs/062-scaffold-rule-generator/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/scaffold-cli.md

**Tests**: TDD is used -- test tasks precede the implementation they cover
(the spec's User Story 1 scenario 3 and SC-002 require the scaffold to leave an
honest RED state, so test-first is intrinsic to the feature).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 (author mode), US2 (doctor mode), US3 (place-list guard)

## Path Conventions

Single project: `src/retail/`, `tests/unit/` at repository root.

---

## Phase 1: Setup

- [ ] T001 Confirm the editable install is current in this worktree so
  `retail` resolves to this src (memory: editable-install cross-worktree hazard),
  then run `pytest -m unit` once to capture a green baseline before any change.
- [ ] T002 [P] Create the value objects module skeleton `src/retail/scaffold.py`
  with the immutable value types from data-model.md (WiringPlace, RuleIdentity,
  ScaffoldResult, DoctorReport) as frozen dataclasses / NamedTuples -- no logic
  yet. stdlib imports only.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the declared five-place model every mode depends on.

- [ ] T003 [US3] In `src/retail/scaffold.py`, declare the immutable five-place
  list (register, import_all, expected_ids, golden, glossary) with each place's
  target file(s) and `write_mode` (write vs print) per data-model.md.
- [ ] T004 [US3] Write the guard test in `tests/unit/test_scaffold.py` asserting
  the declared five-place list matches the wiring places the repo actually has
  (FR-017); include a sub-assertion that removing a declared place would fail.
  RED first (list intentionally not yet final), then GREEN.

---

## Phase 3: User Story 1 -- Author mode (Priority: P1) -- MVP

**Goal**: one command writes the three write-targets and prints the follow-ups.

**Independent test**: run scaffold for a throwaway id in a scratch/tmp repo copy;
assert the three writes happened, the golden/glossary files are untouched, and the
regen commands + glossary row were printed.

- [ ] T005 [P] [US1] Write tests (RED) in `tests/unit/test_scaffold.py` for input
  validation (FR-010): malformed id and empty title are rejected with a clear
  message and zero writes.
- [ ] T006 [P] [US1] Write tests (RED) for the refusal paths (FR-009): already-
  registered id, and pre-existing stub module -> refuse, no changes.
- [ ] T007 [US1] Write tests (RED) for the write/print SPLIT (FR-002..FR-008,
  SC-004): scaffold writes exactly {stub module, test stub, EXPECTED_RULE_IDS
  insertion} and writes NOTHING to either golden record or the glossary; the two
  regen commands + a glossary row are captured on stdout. Use a tmp_path repo
  fixture so no real repo file is mutated by the test.
- [ ] T008 [US1] Write test (RED) that the generated stub is generic (FR-003,
  Principle VII): the written module + test contain no worked-example tokens
  (no example table/column/code/report-path strings).
- [ ] T009 [US1] Write test (RED) for the honest-red contract (SC-002, US1
  scenario 3): immediately after scaffolding, the generated test stub FAILS.
- [ ] T010 [US1] Implement author-mode logic in `src/retail/scaffold.py` to make
  T005-T009 GREEN: id/title validation; refusal checks; render + write the
  generic stub module and failing test stub; insert the id into
  EXPECTED_RULE_IDS; print the two regen commands, the glossary row, and the
  import/__all__ edit. Enforce UTF-8 no BOM + ASCII (FR-019).
- [ ] T011 [US1] Wire the `scaffold` subparser + author-mode dispatch into
  `src/retail/cli.py` mirroring the `manifest`/`severity-posture` pattern
  (FR-020); return the author-mode exit codes from the CLI contract.

**Checkpoint**: author mode is independently usable and fully tested.

---

## Phase 4: User Story 2 -- Doctor mode (Priority: P2)

**Goal**: read-only per-id / sweep report across all five places with a defined
exit-code contract.

**Independent test**: run doctor sweep against the current repo; assert the known
drifted rule is reported present in four places, missing from the glossary; assert
a fully-wired id is present in all five.

- [ ] T012 [P] [US2] Write tests (RED) in `tests/unit/test_scaffold.py` for the
  per-place readers: registry (place #1), import list + __all__ (#2),
  EXPECTED_RULE_IDS (#3), the two golden JSON records (#4), glossary rows (#5) --
  each returns present/missing for a given id, and `unverifiable` when a file is
  absent (FR-015). Use fixtures, not the live repo, for the missing-file case.
- [ ] T013 [US2] Write test (RED) for the sweep + single-id modes (FR-011,
  FR-012): single id verifies one id; no id sweeps every registered id; the known
  drift instance is reported missing-from-glossary (SC-003), cited generically.
- [ ] T014 [US2] Write test (RED) for the doctor exit-code contract (FR-014):
  exit 0 when no drift, non-zero when any checked id is missing in any place,
  unknown id reported without crash-exit.
- [ ] T015 [US2] Write test (RED) that doctor writes NOTHING (FR-013): capture
  file mtimes/hashes before+after a doctor run; assert unchanged.
- [ ] T016 [US2] Implement doctor-mode logic in `src/retail/scaffold.py` to make
  T012-T015 GREEN: the five read-only place-readers, single/sweep dispatch, the
  DoctorReport with has_drift, and unverifiable handling. Read-only; no write
  capability in the doctor path.
- [ ] T017 [US2] Extend the `cli.py` `scaffold` dispatch with the `--doctor`
  path + `--id`/sweep args; return the doctor exit codes from the contract.

**Checkpoint**: doctor mode is independently usable and fully tested.

---

## Phase 5: Polish & cross-cutting

- [ ] T018 [P] Add a stdlib-only guard test (or extend an existing import guard)
  asserting `src/retail/scaffold.py` imports no third-party package and opens no
  DB/network (FR-016, Principle VIII).
- [ ] T019 [P] Confirm `dependencies = []` is unchanged and the static import
  path stays driver-free (no new runtime dependency introduced).
- [ ] T020 Run the full CI gate set in this worktree: `ruff`, `pytest -m unit`,
  `retail check`, `retail semantic-check` -- all green. Confirm `retail check`
  still reports the SAME rule count (this feature adds NO new `retail check` rule;
  it is tooling), matching the manifest/severity-posture "adds no rule" posture.
- [ ] T021 [P] Update the CLI help / any subcommand index doc so `scaffold` is
  discoverable next to the other subcommands (docs-only, no new rule).

---

## Dependencies & ordering

- Phase 1 -> Phase 2 -> (Phase 3 = MVP) -> Phase 4 -> Phase 5.
- US1 (Phase 3) is the MVP and is independently shippable.
- US2 (Phase 4) depends only on the Phase 2 five-place model, not on US1's writer.
- US3 guard (Phase 2) blocks both, since both modes iterate the place list.
- Within a phase, [P] tasks touch different files or different test functions and
  may run in parallel; the implementation task in each story (T010, T016) follows
  its RED tests.

## Notes on scope discipline (YAGNI)

- No dynamic five-place discovery -- the declared+guarded list is the seam.
- No auto-repair, no golden regen execution, no glossary prose write.
- No new `retail check` rule, no readiness stage/score, no DB/network/execution.
