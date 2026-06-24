---
description: "Task list -- source drift detector (F014, spec 015)"
---

# Tasks: source drift detector (F014, spec 015)

**Input**: Design documents from `specs/015-source-drift-detector/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: This is a docs/templates slice. There are no code tests; verification is
`retail check` exit 0, a green unit suite (nothing in `src/` changes), ASCII/no-BOM
+ cross-link checks, and the baseline-vs-observed replay (SC-003). Test tasks below
are these doc-gate checks, not unit tests.

**Organization**: Tasks are grouped by the three user stories so each is
independently testable. US1 (shape drift report) is the MVP; US2 (Principle-V
hard-stops) and US3 (spine wiring) build on it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency)
- **[Story]**: US1 / US2 / US3 (or SETUP / FOUND / POLISH)
- All paths are repo-relative from the repo root.

## Path Conventions

Docs slice -- no `src/`/`tests/`. Deliverables under `docs/`, `templates/`, and the
drift-report INSTANCE convention under `mappings/<table>/` (ADR 0003). No code paths.

---

## Phase 1: Setup (Shared)

**Purpose**: confirm placement conventions before authoring (Phase 0 of plan).

- [ ] T001 [SETUP] Confirm the checklist home: check whether `docs/checklists/`
  (or an equivalent repo checklist directory) exists; if not, plan to create
  `docs/checklists/source-drift.md`. Record the chosen path. (Auto-default:
  `docs/checklists/source-drift.md`.)
- [ ] T002 [P] [SETUP] Confirm the drift-report INSTANCE location is
  `mappings/<table>/source-drift-report.md` (ADR 0003, co-located with the baseline
  `source-profile.md`). No file created here -- a convention to encode in the template.
- [ ] T003 [P] [SETUP] Re-read the shapes to mirror: `templates/source-profile.md`
  (template posture), `docs/readiness/source-ready.md` (stage-doc shape),
  `.specify/templates/checklist-template.md` (checklist shape). No edits.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the drift taxonomy + status model that BOTH the template and the
checklist depend on. Must exist before US1/US2/US3 artifacts are authored.

**CRITICAL**: the taxonomy doc is the contract the other two artifacts fill.

- [ ] T004 [FOUND] Author `docs/readiness/source-drift.md` skeleton with the
  stage-companion shape: Purpose; baseline-vs-observed model; the nine-class drift
  taxonomy table (class / what changed / default severity / Principle-V flag);
  Source Ready status mapping; Blocking reasons; Required owner/approval;
  What the agent must NOT do; See also. ASCII, UTF-8 no BOM.
- [ ] T005 [FOUND] In `source-drift.md`, write the no-fake-confidence rule (#9):
  measured per-class magnitudes are allowed/required; a rolled-up drift score is
  forbidden until scoring rules exist (cite `readiness-model.md`).
- [ ] T006 [FOUND] In `source-drift.md`, write the measure/judge boundary: design-
  only this slice (#8); the mechanical re-profile is the deferred-live `profile.py`
  seam (Principle VIII); `[PENDING LIVE RE-PROFILE]` + `warning` when absent.

**Checkpoint**: the taxonomy + status model + boundaries are fixed; the template
and checklist can now be authored against them.

---

## Phase 3: User Story 1 - Shape drift report as Source-Ready evidence (Priority: P1) -- MVP

**Goal**: a fillable `source-drift-report.md` that records added/removed/retyped
columns + missingness/cardinality shifts with before/after numbers, and sets the
Source Ready status.

**Independent Test**: two profiles (baseline + a modified copy) -> a filled report
classifies every shape diff to the right class + severity and lands the right
status (a removed column -> `blocked`), with no missing template fields.

### Verification for US1 (doc gates)

- [ ] T007 [P] [US1] Replay check: take a committed `source-profile.md` as baseline
  and a hand-modified copy (one added, one removed, one retyped non-key column, one
  missingness shift) and fill `source-drift-report.md` by hand; assert each diff
  classifies correctly and Source Ready = `blocked` (removed column), `blocking_reasons`
  names the column. (This is SC-003; run after T009.)

### Implementation for US1

- [ ] T008 [US1] Author `templates/source-drift-report.md` -- top instructions
  ("copy to `mappings/<table>/source-drift-report.md`"; ASCII; cite numbers not
  adjectives; read-only connection, secrets only in `.env`, no inline DSN); Header
  (baseline profile ref + commit/date; observed re-profile date/by; source id).
  ASCII, UTF-8 no BOM.
- [ ] T009 [US1] In the template, add the per-class FINDINGS table with before/after
  MEASURED cells for the shape classes: column added / removed / retyped,
  missingness shift (`'' OR NULL` count+%, RC5), cardinality shift (distinct count).
  Each row carries class, before, after, severity, note.
- [ ] T010 [US1] In `source-drift.md`, document the shape-class severity defaults +
  the retype escalation rule (retype of a key/measure escalates `warning` ->
  `blocked`); cross-reference the template table.
- [ ] T011 [US1] In the template, add the "resulting Source Ready status" block:
  `pass` (no material drift) / `warning` (only non-fatal) / `blocked` (any fatal),
  with `blocking_reasons` enumerated; map to the four spine statuses ONLY (no number).

**Checkpoint**: US1 delivers a complete, fillable shape-drift report + the taxonomy
doc rows that govern it. MVP is testable via the replay (T007).

---

## Phase 4: User Story 2 - Grain/identity/returns/PII drift hard-stops (Priority: P1)

**Goal**: the Principle-V classes MEASURE + CLASSIFY + raise to a human, never
auto-rejudge.

**Independent Test**: a baseline+observed pair where the recorded candidate PK is no
longer unique -> report records `grain/PK drift = blocked`, proposes NO new grain,
raises an `unresolved-questions.md` row naming the owner.

### Implementation for US2

- [ ] T012 [US2] In `source-drift.md`, write the Principle-V seam table: `grain/PK
  drift`, `returns-rule drift`, `PII surface drift`, identity-bearing
  `semantic-pair drift` -- each a HARD-STOP (`blocked`), each NEVER auto-resolved by
  proposing a new grain/returns/PII/identity ruling; PII default stays `drop`.
- [ ] T013 [P] [US2] In the template findings table, add the Principle-V class rows:
  grain/PK (reuse RC2 proof: `COUNT(*) = COUNT(DISTINCT pk)`, `0` NULL PK),
  returns-rule (from the authoritative column, RC8), PII surface (both directions:
  new PII-looking column AND dropped-PII reappearance -- call out the reappearance),
  semantic-pair (1:1 rate before/after).
- [ ] T014 [US2] In the template, add the Principle-V HANDOFF section: every fatal
  judgment class produces an `unresolved-questions.md` entry naming the owner
  (analyst / governance / data-owner); the report records the question, not an answer.
- [ ] T015 [US2] In `source-drift.md` "What the agent must NOT do", forbid:
  proposing a new grain/PK, re-picking the returns column, ruling PII publish-safe,
  asserting a new identity equivalence, or auto-`pass`-ing past any Principle-V class.

**Checkpoint**: US1 + US2 -- every drift class (shape + judgment) is recordable, and
the judgment classes are designed AS human seams.

---

## Phase 5: User Story 3 - Drift wires into the readiness spine (Priority: P2)

**Goal**: a filled drift report updates `readiness-status.yaml` and flags downstream
stages SUSPECT, without auto-demoting them.

**Independent Test**: a `blocked` drift report for a table whose `mapping_ready` was
`pass` -> Source Ready becomes `blocked` AND `mapping_ready` (+ further passes) are
noted SUSPECT (re-check required), not silently flipped.

### Implementation for US3

- [ ] T016 [US3] In `source-drift.md`, specify the readiness-status wiring (no
  schema change): a filled report sets `source_ready.status`, appends the report to
  `evidence[]`, populates `blocking_reasons[]` from fatal classes, updates
  `last_checked_at` / `checked_by`. If a `drift` sub-record turns out necessary, it
  is a deferred decision (record, do not add).
- [ ] T017 [US3] In `source-drift.md`, write the DOWNSTREAM-INVALIDATION rule: a
  `warning`/`blocked` drift makes downstream `pass` stages (Mapping/Silver/Gold/...)
  SUSPECT and requiring RE-confirmation; the detector FLAGS this and MUST NOT demote
  or auto-`pass` any downstream stage.
- [ ] T018 [P] [US3] Add a short generic `readiness-status.yaml` example to
  `source-drift.md` showing a `blocked` drift outcome (status + evidence +
  blocking_reasons + downstream-suspect note), `<schema>.<table>` placeholders only,
  NO drift score.

**Checkpoint**: all three stories complete -- detection, judgment seams, and spine
wiring.

---

## Phase 6: Polish & Cross-Cutting

- [ ] T019 [P] [POLISH] Author the re-profile/compare checklist at the path chosen
  in T001 (`docs/checklists/source-drift.md`): ordered steps pin baseline ->
  re-profile with the SAME measures (RC2/RC5/RC8) -> classify each diff -> set status
  -> hand Principle-V classes to a human. Follow the speckit checklist shape.
- [ ] T020 [POLISH] Cross-link the spine: add a See-also link in
  `docs/readiness/source-ready.md` -> `source-drift.md`; ensure `source-drift.md`
  See-also points to `readiness-model.md`, `readiness-pipeline.md`, `source-ready.md`,
  `templates/source-profile.md`, `templates/source-drift-report.md`, the checklist,
  RC defaults (ADR 0002), `profile.py`, ADR 0003, and `docs/roadmap/roadmap.md`.
- [ ] T021 [P] [POLISH] (Optional) Note in `docs/roadmap/roadmap.md` that F014
  "Source Drift Detector" is filed under spec dir 015 (cross-reference only; do not
  renumber the roadmap).
- [ ] T022 [POLISH] Verify the generic rule (#7): grep the three new files for any
  worked-example specific term (pharmacy/billing-code/segment/PII column names);
  C086 may appear ONLY as a cited filled-baseline example. Fix any leakage.
- [ ] T023 [POLISH] Run the doc gates: `retail check` exit 0 over the new text;
  unit suite green; ASCII/UTF-8-no-BOM on the three new files; every See-also target
  resolves.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies; start immediately.
- **Foundational (Phase 2)**: after Setup. BLOCKS all user stories (the taxonomy +
  status model is the contract the template and checklist fill).
- **User Stories (Phases 3-5)**: after Foundational.
  - US1 (P1) is the MVP and should land first (shape report + taxonomy rows).
  - US2 (P1) extends the SAME two files (taxonomy doc + template) with the
    Principle-V classes -- author after US1 to avoid editing the same files in
    parallel.
  - US3 (P2) wires the (now complete) report into the spine.
- **Polish (Phase 6)**: after the stories; the checklist (T019) can be drafted in
  parallel with US3 since it is a different file.

### Within Each User Story

- US1: T008 (template scaffold) before T009/T011 (table + status block, same file);
  T010 edits the doc (different file, can parallel with T009/T011); T007 verifies
  after T009.
- US2: T012/T015 edit the doc; T013/T014 edit the template -- T013 is `[P]` vs the
  doc edits; T014 follows T013 (same file).
- US3: T016/T017 edit the doc; T018 is `[P]` (example block, same file -> sequence
  after T016/T017 in practice).

### Parallel Opportunities

- T002, T003 (Setup) in parallel.
- Across stories, the DOC file (`source-drift.md`) and the TEMPLATE file
  (`source-drift-report.md`) are different files: a doc-edit task and a template-edit
  task in the same story can run in parallel where marked `[P]`.
- T019 (checklist, separate file) parallel with US3.
- T021, T022 in parallel during Polish.

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1 Setup -> Phase 2 Foundational (taxonomy + status model).
2. Phase 3 US1: the shape-drift report + governing taxonomy rows.
3. STOP and VALIDATE: the two-profile replay (T007) classifies shape diffs and lands
   the right status. This alone delivers value: shape drift becomes a Source-Ready
   blocker.

### Incremental Delivery

1. Foundational -> US1 (shape drift) -> validate (MVP).
2. US2 (Principle-V hard-stops) -> validate the grain/PK-no-longer-unique replay.
3. US3 (spine wiring) -> validate the downstream-suspect flagging.
4. Polish (checklist, cross-links, generic-check, doc gates).

---

## Notes

- [P] = different file, no dependency. The two long-lived files (the doc and the
  template) are edited by several stories -- sequence same-file tasks, parallelize
  across the two files.
- No code, no tests in `src/`/`tests/`; "tests" here are doc gates + the replay.
- Commit after each story (or logical group); keep `retail check` green throughout.
- Avoid: any drift "score"; any auto-resolution of a Principle-V class; any
  worked-example specifics in the generic artifacts; any inline DSN/secret.
