---
description: "Task list for the data quality control room (feature 013)"
---

# Tasks: data quality control room

**Input**: Design documents from `specs/013-data-quality-control-room/`

**Prerequisites**: plan.md (done), spec.md (done)

**Tests**: No new test framework is requested. The feature adds NO Python; acceptance
is verified by (a) the existing unit suite staying green, (b) `retail check` staying
exit 0 at the unchanged rule count (26), and (c) the multi-table measured-cell replay
(every numeric cell equals its underlying per-table source; `git status` shows zero
modified per-table files). Those verification steps appear as explicit tasks below.

**Organization**: Tasks are grouped by the three P1 user stories from spec.md so each
is independently demonstrable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency)
- **[Story]**: US1 / US2 / US3 (or SETUP / FOUND / POLISH)
- Exact paths are given. `<control-room-skill>` is the chosen short skill name.

## Path Conventions

- New skill: `.claude/skills/<control-room-skill>/SKILL.md`
- New template: `templates/data-quality-control-room.md`
- Read-only inputs (NOT modified): `templates/{readiness-status.yaml,data-issues.md,blocking-reasons.md,readiness-scorecard.md}`, `mappings/<table>/`
- Spec/plan: `specs/013-data-quality-control-room/`

---

## Phase 1: Setup (shared)

**Purpose**: pick the name and stand up the two empty files in the right places.

- [ ] T001 [SETUP] Choose the short skill name `<control-room-skill>` (target repo-relative path <= 200 chars, Principle IX) and record it at the top of `specs/013-data-quality-control-room/tasks.md`. Recommended default: `retail-control-room`.
- [ ] T002 [P] [SETUP] Create `.claude/skills/<control-room-skill>/SKILL.md` with valid frontmatter (`name`, `description`), ASCII + UTF-8 no BOM (empty body for now) (FR-001).
- [ ] T003 [P] [SETUP] Create `templates/data-quality-control-room.md` (empty placeholder for now), ASCII + UTF-8 no BOM.

**Checkpoint**: both new files exist and are registered by the harness; no input touched.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: lock the evidence chain and the read-only/no-new-check posture before any
view content is authored. EVERY later task depends on these being settled.

**CRITICAL**: no user-story work begins until Phase 2 is complete.

- [ ] T004 [FOUND] In SKILL.md, write the "Scope boundary (read first)" section: READ-ONLY; aggregates existing evidence only; runs NO new validator and adds NO new gate; opens no DB; runs no SQL; never edits an input; never clears/self-assigns a blocker; never writes a `pass` (FR-003, FR-006). Mirror `retail-validate`'s "invoke-and-interpret only" framing.
- [ ] T005 [FOUND] In SKILL.md, embed the evidence-chain table (spec "Aggregates, never re-derives"): each control-room column -> the exact existing committed source it reads -> the severity it carries. Establishes FR-008 traceability as the contract.
- [ ] T006 [FOUND] In `templates/data-quality-control-room.md`, author the GENERIC roll-up shape: the per-table summary table (table id, source family, current stage, status, static-WARN count, live-finding count, open-blocker count, next action) + the portfolio open-blockers list (table, stage blocked, reason, measured evidence, named owner). Placeholders only; no worked-example specifics (FR-002, FR-004, FR-005, Principle VII).

**Checkpoint**: the output shape and the read-only/no-new-check contract are fixed.

---

## Phase 3: User Story 1 - One consolidated view of every table's findings + blockers (P1) [MVP]

**Goal**: a row per table with current stage, status, measured WARN/live/blocker
counts, and the single next action, sorted worst-first.

**Independent Test**: with >= 2 tables having per-table evidence, every numeric cell in
the view equals the count in the underlying per-table file, ordering is
`blocked` > `warning` > `pass`, and no per-table file is modified.

- [ ] T007 [US1] In SKILL.md, write the aggregation procedure: discover tables (scan `mappings/<table>/` + per-table readiness files), then for each table READ `readiness-status.yaml` (`current_stage`, per-stage `status`, `next_action`), `data-issues.md` rows, `blocking-reasons.md` open rows, and the recorded `retail check` WARN count + `retail validate` finding count (FR-003, FR-004).
- [ ] T008 [US1] In SKILL.md, specify the per-table row fill: each numeric cell is a COUNT copied from its source (never an adjective); record the source path/line beside each so it stays traceable (FR-004, FR-008).
- [ ] T009 [US1] In SKILL.md, specify worst-first ordering (`blocked`/`error` rows above `warning` above `pass` above `not_started`) and the empty-portfolio render ("no tables onboarded yet") (US1 acceptance #1, edge case zero-tables).
- [ ] T010 [US1] In SKILL.md, specify missing/partial-evidence handling: a table with no or malformed per-table files renders as `not_started` / "evidence incomplete: <file>", never an invented status or count (FR-009, US1 acceptance #3).

**Checkpoint**: US1 view renders from existing evidence and modifies nothing.

---

## Phase 4: User Story 2 - The next blocker to clear, portfolio-wide (P1)

**Goal**: a prioritized portfolio-wide open-blockers list with stage, concrete reason,
measured evidence, and named owner -- so the single most valuable next action is clear.

**Independent Test**: open blockers across tables are listed with their named owner
copied from source; an `error` live finding (V-RC2/V-RC15/V-RC16) sorts above a
`warning` static WARN; the skill self-assigns no owner and clears nothing.

- [ ] T011 [US2] In SKILL.md, write the open-blockers roll-up: gather every "Open blockers" row from each table's `blocking-reasons.md` into one list with {table, stage blocked, concrete reason, measured evidence, named owner} -- all copied from source, nothing invented (FR-005, US2 acceptance #1).
- [ ] T012 [US2] In SKILL.md, specify severity ordering for the blockers list: `error`/`blocked` (proven defect) above `warning` (suspect pattern) -- the constitution's severity asymmetry (US2 acceptance #3).
- [ ] T013 [US2] In SKILL.md, specify approval-type and unassigned blockers: show the required owner but take NO clearing action; an owner-less blocker reads "UNASSIGNED" and is flagged; never self-assign (FR-006, Principle V; US2 acceptance #2, edge case no-owner).

**Checkpoint**: US1 + US2 together give the full "what is broken and what to fix next" view.

---

## Phase 5: User Story 3 - Aggregation honesty: no new check, no fabricated number (P1)

**Goal**: the constitutional guardrail -- no new validator, no input mutation, no
number that is not traceable; a confidence/health score is refused.

**Independent Test**: a request for "one health score per table" is declined with the
no-fake-confidence rationale; every shown number names its source; the skill issued no
state-mutating gate run of its own and edited no per-table file.

- [ ] T014 [US3] In SKILL.md, write the no-fake-confidence guard: refuse any numeric health/confidence score; on request, decline, cite readiness-model "No fake confidence", and return the four statuses + measured counts instead (FR-007, US3 acceptance #1).
- [ ] T015 [US3] In SKILL.md, write the staleness + conflict honesty rules: show recorded gate results with their timestamp and mark stale live results "not run since <date>" rather than running the live check (FR-010); surface a status-vs-blocker conflict as a finding rather than resolving it (FR-011; edge cases staleness, conflict).
- [ ] T016 [US3] In SKILL.md, write the read-only self-check: the procedure ends by asserting it opened no DB, ran no new check, and modified no input (a `git status`-clean expectation), and that every cell cites a committed source (FR-006, FR-008, US3 acceptance #2/#3).

**Checkpoint**: all three P1 stories are authored; the guardrails are explicit in the skill.

---

## Phase 6: Polish & Cross-Cutting

**Purpose**: wire orchestration, add See-also/cross-links, and run the verification gates.

- [ ] T017 [POLISH] Append an `## Orchestration` section to SKILL.md (the control room is the portfolio-level read `retail-orchestrate` can call after sequencing a table; it reports state, advances no stage) and add the reciprocal pointer in `.claude/skills/retail-orchestrate/SKILL.md` (FR-012).
- [ ] T018 [P] [POLISH] Add a `## See also` section to SKILL.md and a header note to the template cross-linking: `templates/readiness-scorecard.md` (the per-table sibling), `templates/{data-issues.md,blocking-reasons.md,readiness-status.yaml}` (the sources), `docs/readiness/readiness-model.md` + `readiness-pipeline.md`, and `docs/roadmap/roadmap.md` (F012; rules 7/8/9).
- [ ] T019 [POLISH] Verify generic + encoding: grep both new files for worked-example specifics (billing codes, segment names, PII column names, per-table grain keys) and confirm ASCII + UTF-8 no BOM and short repo-relative paths (Principle VII, IX; SC-001).
- [ ] T020 [POLISH] Run the no-new-check / green invariants: `retail check` exits 0 at rule count 26; the full unit suite is green; NO new Python added; `dependencies = []` unchanged (SC-002). (Run command per `memory/run-commands.md`: the package is not pip-installed; use `PYTHONPATH=src` / pytest.)
- [ ] T021 [POLISH] Run the measured-cell replay (SC-003): with `mappings/c086/` plus a second generic stub table, render the view; assert every numeric cell equals the count in its underlying per-table source, ordering is worst-first, and `git status` shows zero modified per-table files (read-only proven).
- [ ] T022 [POLISH] Run the aggregation-not-fabrication check (SC-004): request a single health/confidence score; assert the skill declines with the no-fake-confidence rationale and that every shown number is traceable to a named committed source path.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (P1)**: no dependency; start immediately.
- **Foundational (P2)**: depends on Setup; BLOCKS all user stories (it fixes the
  output shape + the read-only/no-new-check contract every story relies on).
- **User Stories (P3-P5)**: each depends on Foundational. US1 is the MVP; US2 and US3
  build on the same SKILL.md so they are sequential in practice (same file), though
  each is independently demonstrable.
- **Polish (P6)**: depends on the user stories being authored.

### Within each story

- All three stories edit the single `SKILL.md`, so their tasks are sequential within
  that file (avoid same-file conflicts). The template (T006) is foundational and done
  once.

### Parallel opportunities

- T002 and T003 ([P]) create two different files -> parallel.
- T018 ([P]) edits cross-link sections and can overlap with verification prep.
- The verification tasks T020 / T021 / T022 are independent checks and can run in any
  order once authoring is done.

---

## Implementation Strategy

### MVP first (User Story 1)

1. Phase 1 Setup -> Phase 2 Foundational (CRITICAL: fixes shape + contract).
2. Phase 3 US1: the consolidated per-table view.
3. STOP and VALIDATE: render against >= 2 tables; confirm measured cells match and
   nothing is modified. This alone is a usable portfolio view (MVP).

### Incremental delivery

1. Setup + Foundational -> shape + guardrails ready.
2. US1 -> the consolidated view (MVP).
3. US2 -> the prioritized portfolio open-blockers list.
4. US3 -> the honesty guardrails (no score, traceable, read-only).
5. Polish -> orchestration wiring + the verification gates.

---

## Notes

- [P] = different files, no dependency. The three user stories share `SKILL.md` and are
  therefore sequential within it.
- The feature adds NO validator, NO gate, NO Python, NO CLI -- verification leans on
  the unchanged rule count (26), unchanged `dependencies = []`, the green suite, and
  the read-only measured-cell replay.
- Every authored line must keep a finding's MEASURED NUMBER + its source path; an
  adjective or an untraceable number is a defect (hard rule #9, FR-008).
- Commit after each phase or logical group; keep artifacts ASCII + UTF-8 no BOM.
