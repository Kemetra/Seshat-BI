---
description: "Task list for Release & Maturity Management (F033)"
---

# Tasks: Release & Maturity Management

**Input**: Design documents from `specs/027-release-maturity-management/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Roadmap feature**: F033 (spec-dir 027; the roadmap F-number is authoritative when the dir
number and F-number disagree).

**Tests**: This is a docs/planning slice (no runtime code). There are no unit tests. The
tasks below AUTHOR the five spec-kit files and PLAN (enumerate, never create) the four future
deliverables. Verification tasks (ASCII/no-BOM, `retail check` exit 0 + no new rule added,
no-score check, honest-current-state check) stand in for tests and are explicit.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3) or SETUP / FOUNDATIONAL / POLISH
- All paths are repo-relative from the worktree root

## Path Conventions

Docs/planning feature -- no `src/`/`tests/`. The artifacts WRITTEN this slice are the five
spec-kit files under `specs/027-release-maturity-management/`. The artifacts PLANNED (not
created) are `templates/release-notes.md`, `templates/maturity-report.md`,
`.claude/skills/release-notes-generator/SKILL.md`, and `docs/releases/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Pin the reference shapes and the numbering identity before authoring.

- [ ] T001 Confirm the spec-dir `specs/027-release-maturity-management/checklists/` exists and
      record the numbering identity (dir 027 = roadmap F033) in the spec + plan headers.
- [ ] T002 [P] Re-read the two reference shapes -- `.claude/skills/retail-control-room/SKILL.md`
      (F012 read-and-present posture: aggregate committed evidence, present, stop) and
      `docs/readiness/readiness-model.md` + `templates/readiness-status.yaml` (four-status /
      no-score vocabulary) -- and capture the header + status idiom to reuse for the planned
      templates so they match house style.

**Checkpoint**: numbering identity recorded; house style for the planned artifacts is pinned.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix the two load-bearing boundaries every artifact reuses verbatim.

**CRITICAL**: No user story may be authored until the no-fake-confidence reconciliation and
the consume-never-re-measure boundary are fixed, or the spec drifts into a maturity score or
into re-measuring evidence it should only consume.

- [ ] T003 Write the no-fake-confidence reconciliation (single source of truth): the maturity
      ladder is an EVIDENCE-GATED MILESTONE ladder -- a binary "evidence exists or not" test
      per rung, level = highest all-evidence-present rung -- analogous to the seven numbered
      readiness stages, NOT a percentage/score/average. Drop verbatim into spec FR-006 + the
      governance CHK + the planned `maturity-report.md` header note.
- [ ] T004 Write the consume-never-re-measure / never-self-approve boundary: the generator
      READS the F028 pack + F032 matrix + roadmap ledger and DRAFTS/ASSESSES; it never runs
      `retail check`/`validate`, opens a DB, reads `powerbi/`, self-approves a release,
      self-confirms a level, or publishes. Reuse identically across spec + governance + the
      planned SKILL.md header.
- [ ] T005 Pin the honest current state to verify against the repo: L1/L2 achieved (c086 +
      retail_store_sales worked examples on disk), L3 reported with the repeatable-silver/gold
      caveat for those two tables, L4 (dbt) / L5 (Dagster) / L6 (Power BI execution) NOT BUILT
      with the missing artifact named. This is the evidence the acceptance bar checks.

**Checkpoint**: the no-score reconciliation + the consume/never-self-approve boundary + the
honest current-state pin are fixed and ready to drop into each artifact identically.

---

## Phase 3: User Story 1 - Generate evidence-backed release notes (Priority: P1) MVP

**Goal**: Author the spec content + plan/tasks/checklist coverage for the per-release note --
the seven required blocks with evidence citation -- and PLAN `templates/release-notes.md`.

**Independent Test**: the spec defines all seven release-note blocks (FR-004) with
evidence-citation required and a `draft -- awaiting release-owner approval` status; the plan
enumerates `templates/release-notes.md` as a future deliverable (not created).

- [ ] T006 [US1] In spec.md, specify the seven release-note blocks as FR-004 (what became
      possible / what changed / readiness stages affected / new modules+adapters / known
      limitations / migration notes / next best slice) with every "became possible" claim
      requiring a cited committed source. [spec FR-004, FR-011]
- [ ] T007 [US1] In spec.md, add US1 acceptance scenarios: all seven blocks filled; an
      unsupported capability is NOT listed under "what became possible"; the draft status is
      `draft -- awaiting release-owner approval`. [spec US1]
- [ ] T008 [US1] In plan.md, enumerate `templates/release-notes.md` under "artifacts this
      feature PLANS (not created)" with its block layout + `status`/`approvals[]` fields, and
      add the corresponding planning task "Author spec for the release-notes template" (NOT
      "create the template"). [plan Phase 1]
- [ ] T009 [US1] In tasks.md (this file), record the future authoring tasks as PLANNING tasks
      (author the template + the skill draft-procedure for notes), never as implementation of
      the template itself this slice.

**Checkpoint**: the per-release note shape is fully specified + planned; MVP of the record.

---

## Phase 4: User Story 2 - Evidence-gated maturity assessment (Priority: P1)

**Goal**: Specify the seven-rung evidence-gated ladder + PLAN `templates/maturity-report.md`,
with the honest current-state pin.

**Independent Test**: the spec defines exactly seven rungs (L0..L6) each with a binary
evidence test and verdict; the level = highest all-evidence-present rung; today's assessment
yields L2 achieved + L4/L5/L6 not achieved with missing artifacts named; no rung is a number.

- [ ] T010 [US2] In spec.md, specify the seven rungs as FR-005 (L0 docs only; L1 one worked
      example; L2 two worked examples; L3 repeatable silver/gold for the worked tables; L4 dbt
      adapter; L5 Dagster orchestration; L6 official Power BI execution adapter) with a binary
      evidence test per rung and level = highest all-evidence-present rung. [spec FR-005]
- [ ] T011 [US2] In spec.md, add FR-006 (no numeric maturity score; rungs are milestones not a
      score -- the T003 reconciliation) and FR-007 (honest current state: L2 achieved, L3
      caveated, L4-6 not built, the T005 pin). [spec FR-006, FR-007]
- [ ] T012 [US2] In spec.md, add US2 acceptance scenarios: L2 achieved cites both worked
      examples; L4/L5/L6 not achieved name the missing artifact; a "score out of 100" request
      is declined citing hard rule #9. [spec US2]
- [ ] T013 [US2] In plan.md, enumerate `templates/maturity-report.md` under "artifacts this
      feature PLANS (not created)" with the seven-rung row layout (rung / capability / binary
      test / verdict / cited-or-missing evidence) + the reported-level line, and add the
      planning task "Author spec for the maturity-report template". [plan Phase 1]

**Checkpoint**: the evidence-gated ladder is fully specified + planned, pinned honestly to L2-3.

---

## Phase 5: User Story 3 - The honesty guard (Priority: P1)

**Goal**: Specify the constitutional guard -- no marketing, no self-approval, no unbacked
claim, no level above the evidence -- and PLAN the `release-notes-generator` skill carrying it.

**Independent Test**: the spec forbids (FR-008/FR-010) unbacked capability claims, numeric
scores, self-approval, self-level-bump, and reporting a level above the supported rung; the
governance checklist maps each forbidden op to a CHK item.

- [ ] T014 [US3] In spec.md, write the Human approval boundary (release owner approves
      `draft -> approved` + confirms level; the skill drafts/assesses only -- Core Authority)
      and the Allowed / Forbidden operations sections. [spec FR-010; approval boundary]
- [ ] T015 [US3] In spec.md, add FR-008 (no capability/"production ready"/"GA" claim without a
      backing evidence rung) + FR-012 (surface conflicting inputs, never resolve them), and US3
      acceptance scenarios (refuse approval with no named owner; refuse a level above the
      evidence; refuse a marketing claim). [spec FR-008, FR-012, US3]
- [ ] T016 [US3] In plan.md, enumerate `.claude/skills/release-notes-generator/SKILL.md` under
      "artifacts this feature PLANS (not created)" with its draft-and-assess procedure carrying
      the two boundaries verbatim + the `## Orchestration` pointer, and add the planning task
      "Author spec for the release-notes-generator skill". [plan Phase 1]
- [ ] T017 [US3] In plan.md, enumerate `docs/releases/` as the planned durable output home
      (one set per approved release), created only when a human approves a release -- NOT this
      slice. [plan Phase 1]

**Checkpoint**: the honesty guard is fully specified; the skill + output dir are planned.

---

## Phase 6: Polish & Cross-Cutting Verification

**Purpose**: Whole-feature gates spanning all three stories.

- [ ] T018 Fill `checklists/acceptance.md` (spec quality + acceptance) and
      `checklists/governance.md` (Core-Authority / Principle-V / no-fake-confidence / generic /
      allowed-vs-forbidden / evidence-required), modeled on the 010 checklist style.
- [ ] T019 [P] Verify the no-fake-confidence reconciliation appears in BOTH spec.md (FR-006)
      AND governance.md as a dedicated CHK -- the crux gate (the ladder is milestones, not a
      score). [SC-002]
- [ ] T020 [P] Verify the honest current-state pin (L2 achieved with two worked examples;
      L4/L5/L6 NOT built with missing artifacts named) is present and matches the repo
      (`mappings/c086/` + `mappings/retail_store_sales/` exist; no dbt/Dagster/PBI-exec). [SC-003]
- [ ] T021 [P] Confirm the five spec-kit files ENUMERATE the four future deliverables and
      CREATE none of them; grep the spec dir to confirm no `templates/`, `.claude/skills/`, or
      `docs/releases/` file was written this slice. [SC-001]
- [ ] T022 Confirm all five files are ASCII + UTF-8 no BOM (no Unicode arrows/dashes/quotes;
      `->`/`--` only), repo-relative paths stay short, and `retail check` stays exit 0 with
      no new rule added (this feature adds no rule). [Principle IX, SC-001]

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies -- start immediately.
- **Foundational (Phase 2)**: depends on Setup; BLOCKS all user stories (fixes the no-score
  reconciliation, the consume/never-self-approve boundary, and the honest current-state pin
  every artifact reuses verbatim).
- **User Stories (Phase 3-5)**: all depend on Foundational. US1 (notes) and US2 (ladder) are
  the two halves and can be authored in parallel once Foundational is fixed; US3 (the guard)
  references both and should follow them, though its forbidden-ops text is independent.
- **Polish (Phase 6)**: depends on all three stories complete.

### User Story Dependencies

- **US1 (P1)**: independent after Foundational -- the per-release note half (MVP).
- **US2 (P1)**: independent after Foundational -- the maturity-ladder half; shares the
  honest current-state pin (T005) with the spec body.
- **US3 (P1)**: references US1 + US2 (it guards the claims they make); author after them.

### Parallel Opportunities

- T002 (read references) runs parallel to T001.
- US1 (release-note spec content + plan enumeration) and US2 (ladder spec content + plan
  enumeration) edit different sections and the same two spec-kit files -- author US1 then US2
  in one spec pass to minimize edit rounds.
- Polish T019/T020/T021 are independent verifications -- parallel.

## Parallel Example: after Foundational is fixed

```
# US1 and US2 specify the two halves of the record -- author together in one spec pass:
Specify release-note blocks + plan templates/release-notes.md   (US1: T006-T009)
Specify maturity ladder + plan templates/maturity-report.md     (US2: T010-T013)
```

## Implementation Strategy

**MVP first**: Setup -> Foundational -> US1 = the per-release note shape is specified and the
template is planned (a release can be recorded). Then US2 (the evidence-gated ladder) and US3
(the honesty guard) which depend on the same fixed boundaries, then the Phase 6 whole-feature
gates.

**Boundary discipline (the load)**: every artifact carries the same verbatim no-score
reconciliation (T003) and consume/never-self-approve boundary (T004); Phase 6 (T019-T022)
proves the ladder is milestones not a score, the current state is honestly pinned, no future
deliverable was created early, and no rule/score/Unicode leaked -- the four ways this feature
could fail its own scope.
