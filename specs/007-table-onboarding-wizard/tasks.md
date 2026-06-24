---
description: "Task list for the table onboarding wizard (Source -> Mapping readiness workflow)"
---

# Tasks: table onboarding wizard -- the Source -> Mapping readiness workflow

**Input**: Design documents from `specs/007-table-onboarding-wizard/`

**Prerequisites**: plan.md (done), spec.md (done). No research.md / data-model.md /
contracts/ for this feature (agent-skill + docs only).

**Tests**: No new Python is added, so there are no new Python test tasks. Acceptance
is text review + the existing `retail check` exit 0 + the existing unit suite staying
green (see the Verification phase). This matches features 004-006.

**Organization**: Tasks are grouped by the three user stories from spec.md so each
slice is independently reviewable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency)
- **[Story]**: US1 (onboard nothing->map), US2 (human-seam hard-stops), US3 (resume / no-skip)
- All paths are repo-relative from the repository root.

## Path conventions

- New skill: `.claude/skills/<wizard-skill-name>/SKILL.md` (default name
  `retail-onboard-table`, settled in plan.md Phase 0).
- New checklist: `docs/readiness/onboarding-checklist.md`.
- Reused (not modified): `.claude/skills/source-mapping/SKILL.md`,
  `templates/readiness-status.yaml`, `docs/readiness/source-ready.md`,
  `docs/readiness/mapping-ready.md`.
- Edited (small): `.claude/skills/retail-orchestrate/SKILL.md`.

---

## Phase 1: Setup (Shared scaffolding)

**Purpose**: stand up the skill directory and the checklist file shell.

- [ ] T001 Confirm the wizard skill name (`retail-onboard-table`, plan.md Phase 0)
  and create `.claude/skills/retail-onboard-table/` with an empty `SKILL.md`
  (ASCII, UTF-8 no BOM).
- [ ] T002 [P] Create `docs/readiness/onboarding-checklist.md` shell (title +
  section headers for Stage 1 / Stage 2 / the human seams), ASCII + UTF-8 no BOM.
- [ ] T003 [P] Re-read `docs/readiness/source-ready.md` and `mapping-ready.md` and
  list, verbatim, each stage's `pass` definition-of-done to anchor the checklist
  (no invention -- the checklist must mirror the existing stage docs).

**Checkpoint**: skill dir + checklist shell exist; the stage definitions-of-done
are captured for reuse.

---

## Phase 2: Foundational (the load-bearing skeleton both stories ride on)

**Purpose**: the wizard's normative spine -- the frontmatter, the scope boundary,
and the run-state-from-disk rule -- that every later behavior depends on.

**CRITICAL**: No user-story behavior is correct until this skeleton fixes the
agent-first / no-silver / no-self-grant posture.

- [ ] T004 Author the `SKILL.md` frontmatter: `name` + a precise `description` that
  triggers on "onboard a new table" / "walk a table from source to map / map a new
  bronze table toward Power BI", and states it ENDS at Mapping Ready and does NOT
  write silver. (FR-001)
- [ ] T005 Write the "Scope boundary (read first)" section: agent-first (no CLI);
  ENTERS Source Ready, EXITS Mapping Ready; never `silver.*`; never self-grant
  `Gate status: CLEARED`; ASCII/UTF-8-no-BOM. (FR-001, FR-008, FR-009)
- [ ] T006 Write the "Run-state: read mappings/<table>/ FIRST" rule -- compute the
  current stage from disk (dir presence, the five artifacts, `Gate status`); resume,
  never restart; create NO separate run-state file. (FR-003)

**Checkpoint**: the skill's posture and resume rule are fixed; stage behavior can
now be authored on top.

---

## Phase 3: User Story 1 - Onboard a new table from nothing to a reviewable map (Priority: P1)

**Goal**: the core walk -- Stage 1 profile -> Stage 2 map (delegated) -> seed
readiness-status -> emit reconciliation blank -> state next action -> STOP.

**Independent Test**: run on a generic placeholder table with no prior artifacts;
assert the five `mappings/<table>/` artifacts + a `readiness-status` with
`current_stage: mapping_ready`, `source_ready: pass` (or `warning` deferred) +
evidence, `mapping_ready: blocked` + reason, a printed next-action, and NO silver /
NO approval.

- [ ] T007 [US1] Write the "Stage 1 -- Source Ready" section: drive the mechanical
  profile over a READ-ONLY connection; record row/col counts, `'' OR NULL`
  missingness (never `IS NULL` alone, RC5), candidate-PK uniqueness proof, returns-
  column population into `mappings/<table>/source-profile.md`; PROPOSE semantics,
  never invent. Definition-of-done = `source-ready.md` `pass`. (FR-004)
- [ ] T008 [US1] Write the "Stage 2 -- Mapping Ready (delegate to source-mapping)"
  section: invoke the `source-mapping` skill to author `source-map.yaml` +
  `assumptions.md` (RC1-RC16 adopted/deviated, each deviation citing a data fact) +
  `unresolved-questions.md`, and emit the `reconciliation-report.md` blank -- the
  wizard does NOT duplicate the mapping procedure. (FR-005)
- [ ] T009 [US1] Write the "Readiness-status bookkeeping" section: seed/update the
  per-table status from `templates/readiness-status.yaml` -- `source_ready` (pass/
  warning/blocked + evidence/blockers), `mapping_ready: blocked` (review pending),
  `current_stage`, `next_action`, `last_checked_at`/`checked_by`; every `pass`
  carries `evidence[]`; every `blocked` carries `blocking_reasons[]`; NO numeric
  confidence score. (FR-006)
- [ ] T010 [US1] Write the "Terminal: Mapping Ready -- STOP" section: emit the
  reconciliation blank, state the single next allowed action (human review/approval),
  and explicitly confirm NO silver written + NO approval self-granted. (FR-008)
- [ ] T011 [P] [US1] Fill the checklist's Stage 1 + Stage 2 steps in
  `docs/readiness/onboarding-checklist.md`, each pointing at its definition-of-done
  in `source-ready.md` / `mapping-ready.md`. (FR-002)

**Checkpoint**: a generic table walks nothing -> reviewable map -> Mapping Ready
(blocked, review pending), with the readiness-status seeded; SC-003 reviewable.

---

## Phase 4: User Story 2 - Hard-stop at the Principle-V human seams (Priority: P1)

**Goal**: the four reserved judgment calls (grain, PII, business rollup, product
identity) each HARD-STOP -- proposed with a data fact, raised as an
`unresolved-questions.md` row with a named owner, recorded as a blocking reason --
never auto-answered.

**Independent Test**: feed a table whose candidate PK is not unique; assert the
wizard raises the grain question (with duplicate-count evidence), records
`mapping_ready: blocked` + `blocking_reasons: ["grain not confirmed unique on data"]`,
and STOPS -- it picks no PK, collapses no grain, clears no gate.

- [ ] T012 [US2] Write the "Human seams -- HARD-STOP (Principle V)" table in
  `SKILL.md`: one row each for (1) grain ambiguity (PK not unique), (2) PII
  publish-safety (default drop; governance signs off), (3) business rollup/segment
  (analyst supplies the value->group table), (4) product identity (which column
  authoritatively identifies the entity). Each row: the trigger, the PROPOSE-with-
  data-fact action, the named owner, and "never satisfiable by a silent default."
  (FR-007)
- [ ] T013 [US2] Wire each seam to its readiness-status effect: raising any seam ->
  `mapping_ready: blocked` with the matching `blocking_reasons[]` entry and a
  `next_action` naming the owner; the wizard STOPS (does not clear the gate). (FR-006, FR-007)
- [ ] T014 [US2] Add the "conflicting answer" rule: if an analyst answer contradicts
  a profiled data fact, surface the conflict and STOP to reconcile -- do not proceed
  (Principle V evidence-cross-check). (FR-007)
- [ ] T015 [P] [US2] Fill the checklist's "Human seams" section in
  `onboarding-checklist.md` as four explicit STOP rows mirroring the skill table.
  (FR-002)

**Checkpoint**: all four seams demonstrably hard-stop with named owners + evidence;
SC-004 reviewable.

---

## Phase 5: User Story 3 - Resume safely and never skip ahead (Priority: P2)

**Goal**: idempotent re-invocation (resume from disk, never clobber committed
artifacts) and the no-skip-ahead guarantee (refuse to pass Mapping Ready), plus the
deferred-boundary mode.

**Independent Test**: run twice on the same table -- the second run detects existing
artifacts + `Gate status`, reports the stage, overwrites nothing; with `Gate status:
CLEARED` it reports "Mapping Ready reached" and refuses to author silver.

- [ ] T016 [US3] Write the "Resume / idempotency" rule in `SKILL.md`: resume from
  the first incomplete artifact; never clobber a committed (reviewed) artifact;
  re-running with `Gate status: OPEN` reports the open questions + current stage
  without overwriting. (FR-003)
- [ ] T017 [US3] Write the "Mapping Ready reached (human-approved)" branch: when
  `Gate status: CLEARED` + an `approvals[]` entry exist, promote `mapping_ready: pass`
  (evidence = artifacts + approval), state "next stage is Silver Ready, OUT of scope",
  and STOP -- never author silver, never self-grant. (FR-008, SC-005)
- [ ] T018 [US3] Write the "Deferred-boundary mode" section: no DSN / no `db` extra ->
  do not traceback, do not fabricate; mark mechanical rows `[PENDING LIVE PROFILE]`,
  record `source_ready: warning` (never `pass`), print enable steps
  (`pip install 'retail[db]'`; set `DATABASE_URL` in git-ignored `.env`; never commit
  a real DSN), and still drive the semantic stop-and-ask + the gate. (FR-011)
- [ ] T019 [P] [US3] Fill the checklist's "Resume + deferred mode" notes in
  `onboarding-checklist.md`. (FR-002)

**Checkpoint**: re-runs resume safely; deferred mode is honest; the wizard refuses
to cross into silver.

---

## Phase 6: Integration + Polish (cross-cutting)

**Purpose**: wire the wizard into the conductor and finish the cross-links.

- [ ] T020 Append a `## Orchestration` pointer to the wizard `SKILL.md` (it does its
  Source->Mapping leg and STOPS; the cross-table self-heal loop lives only in
  `retail-orchestrate`). (FR-010)
- [ ] T021 Edit `.claude/skills/retail-orchestrate/SKILL.md`: add the reciprocal
  pointer naming the wizard as the Source->Mapping leg (small, surgical edit; do not
  change the conductor's run-state or gate rules). (FR-010)
- [ ] T022 [P] Add the "See also" cross-links in `SKILL.md` and
  `onboarding-checklist.md`: `source-ready.md`, `mapping-ready.md`,
  `readiness-model.md`, `readiness-pipeline.md`, `templates/readiness-status.yaml`,
  `source-mapping/SKILL.md`, the roadmap F006 row, and the relevant constitution
  principles. Cite the C086 worked example as the filled instance only. (FR-009)
- [ ] T023 [P] Generic-leakage sweep: grep the new + edited files for C086/pharmacy
  specifics (billing codes, segments, named PII columns, grain keys); assert ZERO --
  placeholders only. (FR-009, SC-001)

---

## Phase 7: Verification (gate must pass before done)

**Purpose**: prove the feature ships green and inside its boundary.

- [ ] T024 Run `retail check` over the repo; assert exit 0 (current rule count) with
  the new skill + checklist + status-seed usage added. (SC-002)
- [ ] T025 Run the full existing unit suite; assert green; confirm no new Python and
  `dependencies = []` unchanged. (SC-002)
- [ ] T026 ASCII + UTF-8-no-BOM check on all new/edited files; valid skill
  frontmatter; harness registers the new skill. (SC-001)
- [ ] T027 Dry-run acceptance (text review): walk the generic placeholder table
  scenario end to end and confirm SC-003 (five artifacts + seeded status, no silver,
  no approval), SC-004 (four seams hard-stop), and SC-005 (Mapping Ready terminal,
  silver out of scope) all hold.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependencies -- start immediately.
- **Foundational (Phase 2)**: depends on Phase 1; BLOCKS all user stories (it fixes
  the skill posture + resume rule every story rides on).
- **US1 (Phase 3)** and **US2 (Phase 4)**: both P1; both depend only on Phase 2.
  US2's seam logic references US1's Stage 1 profile output, so prefer US1 first if
  sequential; they may proceed in parallel by different authors after Phase 2.
- **US3 (Phase 5)**: P2; depends on Phase 2; reads the artifacts US1 defines.
- **Integration (Phase 6)**: depends on the skill body (Phases 3-5) existing.
- **Verification (Phase 7)**: last -- depends on everything.

### Within each story

- Skill prose before the checklist mirror (the checklist mirrors the skill).
- Different files marked [P] may proceed in parallel (e.g. checklist edits vs skill
  edits), but the SAME file (`SKILL.md`) must be edited in one batched pass per
  global token rules -- collect a story's `SKILL.md` edits and apply together.

### Parallel opportunities

- T002 / T003 (Setup) are [P].
- T011 / T015 / T019 (checklist fills) are [P] vs the skill-body tasks (different file).
- T022 / T023 (cross-links + leakage sweep) are [P].

---

## Implementation strategy

### MVP first (US1)

1. Phase 1 Setup -> Phase 2 Foundational (skill posture + resume rule).
2. Phase 3 US1 -> a generic table walks nothing -> reviewable map -> Mapping Ready
   (blocked, review pending) with the readiness-status seeded. STOP and review
   (SC-003). This alone is a usable onboarding front door.

### Incremental delivery

1. US1 -> the walk + seeded status (MVP).
2. US2 -> the four human-seam hard-stops (the Principle-V floor).
3. US3 -> resume + deferred-mode robustness + the no-skip-ahead guarantee.
4. Phase 6 wires it into the conductor; Phase 7 proves the gate stays green.

---

## Notes

- [P] = different files, no dependency. Batch all edits to the SAME file in one pass.
- This feature adds NO Python; "tests" = `retail check` exit 0 + existing suite green
  + the text-review dry-run.
- The wizard ENDS at Mapping Ready -- no task authors silver, calls a build verb, or
  self-grants approval. That boundary is the feature's load-bearing invariant.
- The four human seams (grain, PII, business rollup, product identity) are NOT tasks
  to "answer" -- they are tasks to make the wizard STOP and raise them.
