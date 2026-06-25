---
description: "Task list for Approval Console (F027)"
---

# Tasks: Approval Console

**Input**: Design documents from `specs/021-approval-console/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Scope of this slice**: PLANNING artifacts only -- the five Spec-Kit files. The runtime
deliverables (1 skill + 2 templates + 1 docs page) are ENUMERATED here as planned future
outputs; the tasks below "Author spec for X", not "implement X". No runtime code, no
template, no skill, no docs page is created in this slice.

**Tests**: This is a planning slice (no runtime code) -- there are no unit tests.
Verification tasks (ASCII/no-BOM, internal consistency, boundary-discipline checks,
`retail check` stays green) stand in for tests and are included explicitly. The
deliverable-authoring tasks carry their future verification (templates valid, `retail
check` -- no new rule added) as acceptance notes, to be exercised when the deliverables
are later authored.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3) or SETUP/FOUNDATION/POLISH
- All paths are repo-relative from the worktree root

## Path Conventions

Planning slice -- the five files under `specs/021-approval-console/`. The PLANNED future
deliverables (enumerated, not created): `.claude/skills/approval-console/SKILL.md`,
`templates/approval-request.md`, `templates/approval-decision.md`,
`docs/tools/approval-console.md`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Pin the reference shapes the spec + planned artifacts reuse.

- [ ] T001 Confirm the `specs/021-approval-console/` dir + `checklists/` subdir exist (this
      slice's home).
- [ ] T002 [P] Re-read the write targets -- `templates/readiness-status.yaml` (the
      `approvals[]` shape: stage / owner / at; the four statuses) and
      `templates/unresolved-questions.md` (the Open-questions table, the `Who must answer`
      authority classes, the `Resolution` column) -- and capture the exact field idiom the
      request packages and the decision writes through to, so the planned templates match
      house style.

**Checkpoint**: slice home exists; the write-target field shapes are pinned.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix the load-bearing boundary + vocabulary that ALL three stories depend on.

**CRITICAL**: No user story may be authored until the transcribe-never-author boundary, the
authority-class set, and the four-status/no-score rule are fixed, or the spec will drift
into a self-approving surface.

- [ ] T003 Write the transcribe-never-author boundary statement (single source of truth)
      to reuse verbatim in the spec, plan, both planned templates' headers, and the planned
      docs page: the console TRANSCRIBES a human decision and EXECUTES an already-approved
      step; it does NOT pick the option, supply/forge the owner, invent the rationale,
      auto-accept a default, or move a stage to `pass` without the required evidence AND a
      named human approval.
- [ ] T004 Fix the readiness vocabulary the request + decision use: the four statuses
      (`not_started` / `blocked` / `warning` / `pass`) + `evidence[]` + `blocking_reasons[]`,
      NO numeric score field anywhere (hard rule #9). Pin the `pass`-needs-approval-AND-
      evidence rule (FR-007).
- [ ] T005 Enumerate the four authority classes to embed in every artifact: analyst
      (business meaning / grain / rollups), governance (PII / publish-safety), data-owner
      (source semantics / upstream truth), metric-owner (metric contracts). The decider's
      class MUST match the question class (FR-009).

**Checkpoint**: boundary text + four-status/no-score rule + authority-class set are fixed
and ready to drop into each artifact identically.

---

## Phase 3: User Story 1 - Package a raised judgment call into a request (Priority: P1) MVP

**Goal**: Specify and PLAN `templates/approval-request.md` -- the generic decision package.

**Independent Test**: take one open `unresolved-questions.md` row for a GENERIC table and
(on paper) fill the planned request; confirm question_id, stage, subject, decision_needed,
evidence (with source paths), options, impact, owner_required (matching the question
class), and artifacts_to_update are all present, and NO selected option exists.

- [ ] T006 [US1] In spec.md, finalize US1 acceptance scenarios + the request Key Entity
      (the full request field list from the feature input). [FR-002]
- [ ] T007 [US1] In plan.md Phase 1, finalize the `approval-request.md` shape: header in
      `source-map.yaml` style (principles V/VII/IX, no-score #9, boundary text from T003),
      then the fields `question_id`, `stage`, `subject`, `decision_needed`, `evidence`,
      `options`, `impact`, `recommended_default` (with an explicit NOT-auto-accepted note),
      `owner_required` (from T005), `artifacts_to_update_after_decision`; NO
      `selected_option`. [FR-002, FR-006, FR-012]
- [ ] T008 [US1] Author the PLANNED-deliverable task line in this file (T019) for
      `templates/approval-request.md`; do NOT create the template in this slice.
- [ ] T009 [US1] Verify in checklists/acceptance.md that US1 has a measurable outcome
      (SC-001) and that the request carries no fabricated number and no selected option.
      [SC-001, SC-006]

**Checkpoint**: the request shape is fully specified + planned. MVP of the spec done.

---

## Phase 4: User Story 2 - Record the human's decision into the artifacts (Priority: P1)

**Goal**: Specify and PLAN `templates/approval-decision.md` + the write-back into
`unresolved-questions.md` + `readiness-status.yaml`.

**Independent Test**: given a packaged request + a human's answer (option + owner +
rationale), confirm the planned decision records selected_option/owner/date/rationale/
artifacts_updated/remaining_blockers, and the write-back fills the matching
`unresolved-questions.md` Resolution + status and appends a `readiness-status.yaml`
`approvals[]` entry; the stage flips to `pass` ONLY if the required evidence is present.

- [ ] T010 [US2] In spec.md, finalize US2 acceptance scenarios + the decision Key Entity
      (selected_option / owner / date / rationale / artifacts_updated / remaining_blockers),
      and state that `remaining_blockers` is exactly why a recorded decision does NOT always
      mean `pass`. [FR-003]
- [ ] T011 [US2] In plan.md Phase 1, finalize the `approval-decision.md` shape (header +
      boundary text from T003) and the write-back mapping: Resolution + `answered` status in
      `unresolved-questions.md`; an `approvals[]` entry (stage + owner + `at`, where `at` is
      the decision's `date`) in `readiness-status.yaml`. [FR-003, FR-008]
- [ ] T012 [US2] In spec.md, fix the `pass`-flip rule (FR-007): mechanical, gated on a named
      approval AND the stage's required evidence; otherwise record the decision with
      `remaining_blockers` and leave the stage unchanged. [FR-007, FR-008]
- [ ] T013 [US2] Author the PLANNED-deliverable task lines in this file (T020, T022) for
      `templates/approval-decision.md` and `docs/tools/approval-console.md`; do NOT create
      them in this slice.
- [ ] T014 [US2] Verify in checklists/acceptance.md that the write-back is traceable
      (no chat-only approval) and every written cell is the human's answer or a source path.
      [SC-002, SC-006]

**Checkpoint**: the decision shape + the write-back into Core-Authority artifacts are fully
specified + planned.

---

## Phase 5: User Story 3 - The no-self-approval guard (Priority: P1)

**Goal**: Specify the guardrail and PLAN `.claude/skills/approval-console/SKILL.md` +
`docs/tools/approval-console.md` to enforce it.

**Independent Test**: confirm the spec requires the console to decline self-approval (no
named human answer), refuse the wrong authority class, refuse a no-evidence `pass`, and
surface (not overwrite) a contradicting prior approval -- each citing Principle V.

- [ ] T015 [US3] In spec.md, finalize US3 acceptance scenarios + the Forbidden operations
      list (pick option / supply owner / invent rationale / auto-accept default / pass
      without evidence / wrong authority / overwrite prior approval / numeric score / new
      rule-CLI-Python). [FR-005, FR-007, FR-009, FR-010, FR-011]
- [ ] T016 [US3] In spec.md, fill the Human approval boundary + Allowed operations +
      Evidence required sections so the transcribe-never-author boundary is stated three
      times (NOT-section, boundary section, allowed-vs-forbidden ops). [FR-005..FR-010]
- [ ] T017 [US3] In plan.md Phase 1, finalize the SKILL.md procedure (package -> transcribe
      -> write-back -> refuse-to-decide -> surface-conflict) and the docs-page guard
      sections; both as PLANNED deliverables (task lines T019/T021/T022 below). [FR-001, FR-004]
- [ ] T018 [US3] Author checklists/governance.md mapping each Forbidden operation + the
      Human approval boundary to a `[ ]` CHK item (Core-vs-Module authority, Principle V
      stop-and-ask, no-self-approval, no-fake-confidence, generic, secrets/paths, allowed-
      vs-forbidden, evidence-required). [SC-003]

**Checkpoint**: the constitutional guardrail is fully specified; the governance checklist
maps every forbidden operation.

---

## Phase 6: Planned future deliverables (ENUMERATED -- not created this slice)

**Purpose**: Record the four runtime deliverables as planned outputs so a later slice can
author them. These are NOT created now; each line is the future authoring task.

- [ ] T019 [PLANNED] Author `templates/approval-request.md` -- the generic decision-package
      shape (T007 fields), ASCII + UTF-8 no BOM, generic (no C086). Future verification:
      template valid; no new `retail check` rule added; no selected option; no numeric
      score. [FR-002]
- [ ] T020 [PLANNED] Author `templates/approval-decision.md` -- the generic recorded-
      decision shape (T011 fields + write-back mapping), ASCII + no BOM, generic. Future
      verification: every cell transcribed or source-cited; `remaining_blockers` present. [FR-003]
- [ ] T021 [PLANNED] Author `.claude/skills/approval-console/SKILL.md` -- the package ->
      transcribe -> write-back -> refuse -> surface-conflict procedure + `## Orchestration`
      pointer (so `retail-orchestrate` can invoke the console), valid frontmatter, ASCII +
      no BOM. Future verification: skill registered; declines self-approval / no-evidence
      pass. [FR-001, FR-014]
- [ ] T022 [PLANNED] Author `docs/tools/approval-console.md` -- operator guide + transcribe-
      never-author boundary + four authority classes + `pass`-needs-approval-AND-evidence +
      the `approvals[]` / Resolution write-back mapping + guards. ASCII + no BOM, generic. [FR-004]

**Checkpoint**: the four future deliverables are enumerated as planned tasks; none created.

---

## Phase 7: Polish & Cross-Cutting Verification (this slice's planning files)

**Purpose**: Whole-feature gates over the five planning files.

- [ ] T023 Verify all five planning files are ASCII + UTF-8 no BOM and repo-relative paths
      stay short (`<= 200` chars). [Principle IX]
- [ ] T024 [P] Grep the five files for C086/pharmacy leakage (billing codes, segment
      rollups, insurance/PII columns, pharmacy grain keys) -- expect zero. [SC-004]
- [ ] T025 [P] Confirm the spec states three times that the console transcribes-never-
      authors and never flips a stage to `pass` without approval AND evidence, and that NO
      planning file proposes a `retail check` rule, a CLI verb, or Python. [SC-003, SC-005]
- [ ] T026 Confirm the numbering note (dir 021 / roadmap F027, F-number wins) appears in
      both spec.md and plan.md headers, and that Status reads "Planned (spec only -- no
      runtime code this slice)".
- [ ] T027 Run `/speckit-analyze` style cross-artifact consistency over spec.md / plan.md /
      tasks.md (every FR maps to a task; every SC maps to an acceptance CHK; every Forbidden
      op maps to a governance CHK). Record findings.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies -- start immediately.
- **Foundational (Phase 2)**: depends on Setup; BLOCKS all user stories (fixes the
  transcribe-never-author boundary, the authority-class set, the four-status/no-score rule
  every artifact reuses verbatim).
- **User Stories (Phase 3-5)**: all depend on Foundational. US1 (request) is the MVP and
  goes first because US2's decision references the request's `artifacts_to_update` and US3's
  guard reasons about both. US2 and US3 both depend on US1's request shape existing.
- **Planned deliverables (Phase 6)**: enumerated after the stories define their shapes;
  authored in a later slice, not now.
- **Polish (Phase 7)**: depends on all three stories complete.

### User Story Dependencies

- **US1 (P1)**: independent after Foundational -- the atomic deliverable (the request).
- **US2 (P1)**: needs US1's request shape (the decision answers a request and writes through
  to its `artifacts_to_update`).
- **US3 (P1)**: needs US1 + US2 (it guards both the request and the recording path).

### Parallel Opportunities

- T002 (read write-targets) runs parallel to T001.
- Within a story the spec/plan edits touch the same files -- author in one pass.
- Phase 7 T024/T025 are independent greps -- parallel.

## Parallel Example: after US1 ships

```
# Once the request shape (US1) is fixed, the decision (US2) and the guard (US3) can be
# specified together -- they touch different spec sections + different planned deliverables:
Specify US2 (decision shape + write-back) -> plan T011, deliverable T020/T022
Specify US3 (no-self-approval guard) -> plan T017, governance.md T018, deliverable T021
```

## Implementation Strategy

**MVP first**: Setup -> Foundational -> US1 = the request shape fully specified + planned (a
judgment call can be packaged). Then US2 (the decision + write-back) and US3 (the guard) in
parallel, then enumerate the four planned deliverables (Phase 6), then the Phase 7 whole-
feature gates over the five planning files.

**Boundary discipline (the load)**: every artifact carries the same verbatim transcribe-
never-author boundary (T003) and four-status/no-score rule (T004); Phase 7 (T024-T025)
proves no C086 leak, no new rule/CLI/Python, and that the boundary is stated three times --
the three ways this feature could fail its own scope (drift into deciding, into a self-
approving surface, or into a fabricated score).
