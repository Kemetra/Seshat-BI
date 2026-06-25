---
description: "Task list for Readiness Viewer (F026)"
---

# Tasks: Readiness Viewer

**Input**: Design documents from `specs/020-readiness-viewer/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Roadmap feature**: F026 (spec-dir 020 = roadmap F026; roadmap F-number is authoritative)

**Tests**: This is a docs/templates/skill-only feature (no runtime code this slice) --
there are no unit tests. Verification tasks (template valid, ASCII/no-BOM, `retail check`
green, generic-check, read-only proof, delta-holds) stand in for tests and are explicit.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3) or SETUP/FOUND/POLISH
- All paths are repo-relative from the worktree root

## Path Conventions

Product Module (read-only) feature -- no `src/`/`tests/` change this slice. PLANNED future
deliverables: `.claude/skills/readiness-viewer/SKILL.md` (or a documented mode of
`.claude/skills/retail-control-room/SKILL.md`), `templates/readiness-view.md`,
`docs/tools/readiness-viewer.md`, and an OPTIONAL deferred `src/retail/tools/
readiness_viewer.py`. This slice authors ONLY the five spec-kit files; tasks that touch
the future deliverables are PLANNING/authoring tasks for the next slice.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Pin the reference shapes and the documented home before authoring.

- [ ] T001 [P] Re-read F012's shapes -- `.claude/skills/retail-control-room/SKILL.md` and
      `templates/data-quality-control-room.md` -- and capture the SKILL frontmatter idiom,
      the scope-boundary block, and the evidence-chain table style to reuse, so the viewer
      matches house style and is visibly the F012 sibling.
- [ ] T002 [P] Re-read the Core Authority input schema -- `templates/readiness-status.yaml`
      (ADR 0004) and `docs/readiness/readiness-model.md` -- and pin the exact field names
      the viewer renders: `current_stage`, per-stage `status` (four words), `evidence[]`,
      `blocking_reasons[]`, `approvals[]`, `next_action`, plus the seven-stage sequence.

**Checkpoint**: F012 house style is pinned; the readiness schema + seven stages are fixed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The F012 delta + read-only contract that ALL three stories depend on.

**CRITICAL**: No artifact may be authored until the delta and the read-only contract are
fixed, or the viewer will re-spec F012 or drift into creating truth.

- [ ] T003 [FOUND] Resolve the skill-vs-mode decision (plan.md Phase 0): evaluate the three
      deltas (seven-stage matrix / evidence-as-reference / approvals timeline) against
      F012's output and record the outcome -- shape (a) new `readiness-viewer` skill reusing
      F012's aggregation (recommended default) vs. shape (b) fold into F012 if the delta is
      thin (criterion: only durable difference is sort order + column labels). Record the
      chosen shape so every later artifact is consistent.
- [ ] T004 [FOUND] Write the F012-delta statement (single source of truth) to reuse in the
      skill/mode and the usage doc: SAME inputs as F012; three deltas only (stage matrix,
      evidence references, approvals timeline); `next_action` SHARED with F012 and NOT a
      delta. Keep it verbatim across artifacts.
- [ ] T005 [FOUND] Fix the read-only / no-create-truth contract to embed in every artifact:
      computes no status, advances no stage, writes no `pass`, infers/back-fills no
      approval, fabricates no evidence, runs no validator / SQL / DB connection, emits no
      numeric score (rule #9). Each violation is a Forbidden op mapped 1:1 to governance.md.

**Checkpoint**: chosen shape + delta statement + read-only contract are fixed and ready to
drop into each artifact identically.

---

## Phase 3: User Story 1 - The seven-stage status matrix across all items (Priority: P1) MVP

**Goal**: Author `templates/readiness-view.md`'s matrix block + the skill/mode procedure
that fills it from `readiness-status.yaml`.

**Independent Test**: with two or more items having a `readiness-status.yaml`, the rendered
matrix's every cell equals the recorded per-stage `status`, `current_stage` is marked,
`next_action` is shown, and nothing is modified.

- [ ] T006 [US1] Author the matrix block in `templates/readiness-view.md`: item rows x
      seven stage columns (Source Ready -> Publish Ready), each cell a `status` placeholder
      (one of four words), `current_stage` marked, `next_action` shown. Generic placeholders
      only; ASCII + UTF-8 no BOM. [FR-002, FR-004]
- [ ] T007 [US1] Author the matrix render procedure in
      `.claude/skills/readiness-viewer/SKILL.md` (or the F012 mode): scan each item's
      `readiness-status.yaml`, copy each per-stage `status` VERBATIM into the matrix, mark
      `current_stage`, show `next_action`; never recompute/upgrade a status. Embed the
      F012-delta statement (T004) and the read-only contract (T005). [FR-003, FR-004, FR-007,
      FR-011]
- [ ] T008 [US1] Add the honest-state handling to the matrix path: item with no
      `readiness-status.yaml` -> "no readiness file"; malformed/partial -> "readiness file
      incomplete: `<file>`"; never an invented stage status. [FR-009]
- [ ] T009 [US1] Verify the matrix: a manual generic render over two fixture items shows
      every cell = recorded `status`, `current_stage` marked, `next_action` shown, zero
      C086/retail_store_sales specifics, and `git status` shows zero modified per-item
      files. [SC-001, SC-003]

**Checkpoint**: the seven-stage matrix renders from recorded state. MVP done.

---

## Phase 4: User Story 2 - Evidence rendered as navigable references, missing shown as missing (Priority: P1)

**Goal**: Author the evidence-reference block + procedure (the F012 delta vs. counts).

**Independent Test**: a stage with populated `evidence[]` renders each entry as a navigable
reference; a `pass` stage with empty `evidence[]` is flagged "evidence missing"; an absent
referenced file is flagged "referenced file not found"; zero fabricated references.

- [ ] T010 [US2] Author the evidence-reference block in `templates/readiness-view.md`: per
      stage, each `evidence[]` entry as a reference placeholder (path + line/section), plus
      explicit "evidence missing" and "referenced file not found" rows. [FR-002, FR-005]
- [ ] T011 [US2] Author the evidence render procedure in the skill/mode: copy each
      `evidence[]` entry VERBATIM as its committed reference (the F012 delta -- references,
      not counts); render "evidence missing" with the expected artifact named for an empty
      `evidence[]`; render "referenced file not found" for an absent referenced file; NEVER
      fabricate or fill a reference, NEVER hide a missing-evidence `pass`. [FR-005, FR-010]
- [ ] T012 [US2] Verify evidence rendering: populated `evidence[]` -> references; `pass`
      with empty `evidence[]` -> "evidence missing" flag; absent file -> "referenced file
      not found"; zero fabricated references. [SC-004]

**Checkpoint**: evidence renders as auditable references; missing shown as missing.

---

## Phase 5: User Story 3 - The approvals timeline (Priority: P2)

**Goal**: Author the approvals-timeline block + procedure (the third F012 delta).

**Independent Test**: an item with recorded `approvals[]` renders all in date order with
{stage, owner, date} verbatim; a `pass` gate lacking its required approval is flagged
"approval not recorded"; the viewer adds no approval.

- [ ] T013 [US3] Author the approvals-timeline block in `templates/readiness-view.md`: each
      approval as {stage/gate, named owner, date} placeholder in chronological order, plus
      an "approval not recorded" flag row. [FR-002, FR-006]
- [ ] T014 [US3] Author the approvals render procedure in the skill/mode: render
      `approvals[]` VERBATIM in date order; flag a `pass` gate whose required approval is
      absent as "approval not recorded"; NEVER establish, infer, or back-fill an approval
      (no-self-approval; Principle V). Flag an approval that references a `not_started`
      stage as a conflict. [FR-006, FR-010]
- [ ] T015 [US3] Verify the timeline: recorded approvals render in date order verbatim; a
      `pass` gate without its required approval is flagged; an approval referencing a
      `not_started` stage is flagged a conflict; `git status` shows no added `approvals[]`
      entry and no modified per-item file. [SC-005]

**Checkpoint**: the approvals timeline renders recorded approvals and flags gaps; no
approval is created.

---

## Phase 6: Polish & Cross-Cutting Verification

**Purpose**: Whole-feature gates that span all three stories.

- [ ] T016 [POLISH] Author the no-fake-confidence guardrail in the skill/mode: a request
      for a single readiness / confidence / percent-ready score is DECLINED, cites
      readiness-model "No fake confidence", and returns the four explicit statuses across
      the seven stages. [FR-008, SC-007]
- [ ] T017 [POLISH] Author `docs/tools/readiness-viewer.md` (usage + boundary): what the
      viewer is, when to use it vs. F012 (the delta), the read-only module contract per
      F024's category, and how the matrix / evidence references / approvals timeline are
      read from `readiness-status.yaml`. [FR-011]
- [ ] T018 [POLISH] Author the `## Orchestration` pointer in the skill/mode so
      `retail-orchestrate` can invoke the viewer as the stage-progression READ after
      sequencing an item; it advances no stage and clears no blocker. [FR-012]
- [ ] T019 [POLISH] Enumerate (do NOT build) the OPTIONAL deferred CLI
      `src/retail/tools/readiness_viewer.py` in the usage doc's "deferred" section as a
      future read-only renderer (no new validator); confirm nothing in this slice creates
      it. [Non-goals]
- [ ] T020 [POLISH] Run `retail check` over the repo: confirm exit 0 and that the diff
      adds no new rule (this feature adds no rule, no validator). [SC-002]
- [ ] T021 [P] [POLISH] Grep the new skill/mode + template + usage doc for
      C086/retail_store_sales leakage (billing codes, segments, PII columns, grain keys) --
      expect zero. [SC-001]
- [ ] T022 [P] [POLISH] Confirm no artifact recomputes a status, infers an approval,
      fabricates evidence, reads a DB, or adds Python/CLI/rule -- the read-only /
      no-create-truth contract holds end-to-end. [FR-007, SC-006]
- [ ] T023 [POLISH] Confirm all new files are ASCII + UTF-8 no BOM and repo-relative paths
      stay short (Windows budget). [Principle IX]
- [ ] T024 [POLISH] Confirm the F012 delta holds: a reader can state F026 reads the SAME
      inputs as F012, differs only in the three named deltas, shares `next_action`, and that
      the recommended shape (a) + merge fallback (b) + thinness criterion are all stated.
      [SC-006]

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies -- start immediately (T001/T002 in parallel).
- **Foundational (Phase 2)**: depends on Setup; BLOCKS all user stories (fixes the chosen
  shape, the F012-delta statement, and the read-only contract every artifact reuses).
- **User Stories (Phase 3-5)**: all depend on Foundational. US1 (P1) is the MVP and goes
  first (it establishes the template + skill skeleton both later stories extend). US2 (P1)
  and US3 (P2) extend the same two files (`templates/readiness-view.md` + the skill/mode),
  so they are authored after US1 but in the same file passes.
- **Polish (Phase 6)**: depends on all three stories complete.

### User Story Dependencies

- **US1 (P1)**: independent after Foundational -- the matrix is the atomic MVP.
- **US2 (P1)**: extends US1's template + skill with the evidence block; soft dependency on
  US1's skeleton existing.
- **US3 (P2)**: extends the same files with the approvals block; soft dependency on US1.

### Parallel Opportunities

- T001 and T002 (reading references) run in parallel.
- US2 and US3 touch the SAME two files as US1 (`templates/readiness-view.md` + the
  skill/mode) -- author in grouped passes per file to minimize edit rounds rather than in
  parallel.
- Polish T021 and T022 are independent greps/checks -- parallel.

## Parallel Example: Setup

```
# Two independent reads run together:
Re-read F012 shapes (T001)
Re-read the readiness-status schema + seven stages (T002)
```

## Implementation Strategy

**MVP first**: Setup -> Foundational -> US1 = a usable seven-stage matrix rendered from
recorded state. Ship/commit there if needed. Then US2 (evidence references) + US3
(approvals timeline) extend the same template + skill, then the Phase 6 whole-feature
gates (no-fake-confidence, usage doc, orchestration pointer, `retail check` green, generic
+ read-only + delta-holds proofs).

**Boundary discipline (the load)**: every artifact carries the same verbatim F012-delta
statement (T004) and read-only / no-create-truth contract (T005); Phase 6 (T020/T022/T024)
proves no rule, no created truth, and that the viewer is the F012 DELTA -- the three ways
this feature could fail its own scope (re-spec F012, create truth, or invent a score).
