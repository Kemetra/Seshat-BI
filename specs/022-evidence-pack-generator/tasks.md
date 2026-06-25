---
description: "Task list for Evidence Pack Generator (F028)"
---

# Tasks: Evidence Pack Generator

**Input**: Design documents from `specs/022-evidence-pack-generator/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Roadmap feature**: F028 (dir 022 == F028; F-number authoritative).

**Tests**: This is a planning-only slice (no runtime code) -- there are no unit
tests. Verification tasks (10-section contract complete, source map sound, F013 delta
explicit, publish-ready guardrail present, ASCII/no-BOM, generic-check) stand in for
tests and are included explicitly. The four FUTURE deliverables are authored as
PLANNED specs/templates ("Author spec for X"), never implemented here.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US4) or SETUP/FOUND/POLISH
- All paths are repo-relative from the worktree root

## Path Conventions

Planning/docs feature -- no `src/`/`tests/`. This slice authors the 5 spec-kit files
under `specs/022-evidence-pack-generator/`. The future module artifacts
(`.claude/skills/evidence-pack-generator/SKILL.md`, `docs/tools/evidence-pack-generator.md`,
`templates/evidence-pack-index.md`, `templates/evidence-pack-summary.md`) are
ENUMERATED as planned outputs and referenced by planning tasks only.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Pin the reference shapes and the authority vocabulary the spec reuses.

- [ ] T001 Confirm the spec-dir + checklist layout exists:
      `specs/022-evidence-pack-generator/{spec.md,plan.md,tasks.md,checklists/}`.
- [ ] T002 [P] Re-read the reference shapes -- F013 `templates/handoff/bi-handoff-pack.md`
      (composes-existing-evidence + completeness-checklist idiom; the section-08 source),
      `templates/readiness-status.yaml` + `docs/readiness/readiness-model.md` (four-status
      / no-score vocabulary), and F024 (product-module posture + Core-vs-Module authority)
      -- and capture the exact idioms to reuse so the spec matches house style.

**Checkpoint**: layout exists; the house-style idioms (status vocabulary, F013 idiom,
module-authority vocabulary) are pinned.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix the load-bearing contracts ALL stories depend on, so no artifact
drifts into F013's territory, manufactures publish authority, or invents content.

**CRITICAL**: These must be fixed before any user-story content is authored.

- [ ] T003 [FOUND] Fix the 10-section contract (fixed + ordered) and its committed
      source map verbatim for reuse across spec/plan: 01 source-profile <- source-profile.md;
      02 source-map-summary <- source-map.yaml; 03 assumptions-and-decisions <- assumptions.md
      + unresolved-questions.md + ADRs; 04 metric-contracts <- mappings/<table>/metrics/;
      05 validation-summary <- retail check + retail validate + F012 roll-up; 06
      semantic-model-summary <- F010 / retail semantic check; 07 dashboard-summary <- F011/F011A;
      08 handoff-pack <- F013 filled instance (EMBED); 09 known-limitations <- data-issues.md +
      caveats; 10 release-notes <- F015 ledger (+ F014 + approvals[]). [FR-001, FR-002]
- [ ] T004 [FOUND] Fix the "missing -> blocker, never invented" rule and the per-section
      record shape: status (one of four), source path(s), evidence[], blocking_reasons[];
      a blank template counts as missing. NO numeric confidence/health score anywhere
      (hard rule #9). [FR-003, FR-007]
- [ ] T005 [FOUND] Fix the F013 scope-delta statement (one-directional, verbatim): F013 =
      handoff TEMPLATE + owns the publish approval; F028 = GENERATOR that embeds F013 as
      section 08 and never re-authors/edits/redefines it or records the approval. [FR-004]
- [ ] T006 [FOUND] Fix the publish-ready guardrail: the pack SURFACES publish_ready +
      approval read from readiness-status.yaml and prints a publish-ready claim ONLY when
      publish_ready: pass + a named approval is recorded; the module writes no approval and
      moves no stage. [FR-005, FR-006]

**Checkpoint**: section contract + source map + missing-is-a-blocker rule + F013 delta
+ publish-ready guardrail are fixed and ready to drop into the artifacts identically.

---

## Phase 3: User Story 1 - Compose the 10-section pack from existing evidence (Priority: P1) MVP

**Goal**: Author the spec content for composing the ordered 10-section pack from
committed sources, each section linking back to its source artifact.

**Independent Test**: for a generic `<schema>.<table>` with sources committed, the
described pack renders all 10 sections in order, each links to its source path, and no
section content is non-derivable from a committed source.

- [ ] T007 [US1] Author the spec's US1 (compose pack) + Acceptance Scenarios in
      `specs/022-evidence-pack-generator/spec.md`, anchored to the T003 section contract
      and T002 idioms. [FR-001, FR-002]
- [ ] T008 [US1] Record FR-001 (10 fixed ordered sections) and FR-002 (each section
      composed from + linked to a committed source) in spec.md Requirements. [FR-001, FR-002]
- [ ] T009 [US1] In plan.md Phase 1, author the 10-to-source map (T003) and the per-section
      record shape (T004) as the pack's design contract. [FR-001, FR-002, FR-007]

**Checkpoint**: the pack-composition story + the section contract are fully specified. MVP done.

---

## Phase 4: User Story 2 - Missing source becomes a blocker, never invented (Priority: P1)

**Goal**: Specify the integrity guarantee -- a missing/unfilled/blank-template source
is recorded as a blocker, never fabricated, and rolls up into the summary.

**Independent Test**: with one section source absent, the described behavior records
that section as `blocked` with a blocker naming the missing source, the summary cannot
read "complete," and no substitute content is synthesized.

- [ ] T010 [US2] Author the spec's US2 (missing -> blocker) + Acceptance Scenarios,
      including the "blank template counts as missing" edge case and the "warning does not
      auto-promote to pass" rule. [FR-003, FR-007]
- [ ] T011 [US2] Record FR-003 (missing source -> blocker, never fabricated) and the
      warning/blocked edge cases in spec.md. [FR-003, FR-007]
- [ ] T012 [US2] Author the source-disagreement handling (FR-009): surface both sources +
      record a `warning` for human resolution; never silently reconcile. [FR-009]

**Checkpoint**: the integrity guarantee (compose, never invent) is fully specified.

---

## Phase 5: User Story 3 - Surface (never assert) the publish-ready state (Priority: P1)

**Goal**: Specify the Core-Authority guardrail -- the pack surfaces publish_ready +
approval and asserts publish-ready only on a recorded `pass` + named approval; it
writes no approval and moves no stage.

**Independent Test**: described behavior across a `publish_ready: pass` + approval
table vs a `publish_ready: blocked` table shows a claim only in the first; in both the
module writes no approval and moves no stage.

- [ ] T013 [US3] Author the spec's US3 (surface, never assert) + Acceptance Scenarios,
      anchored to the T006 guardrail. [FR-005, FR-006]
- [ ] T014 [US3] Record FR-005 (surface publish_ready + approval read-only; no approval
      write; no stage move; no source edit) and FR-006 (no claim without pass + named
      approval) in spec.md. [FR-005, FR-006]
- [ ] T015 [US3] Author spec.md "Human approval boundary", "Allowed operations",
      "Forbidden operations", and "Evidence required" so the surface/never-assert posture
      and Principle-V stop-and-ask items are explicit. [FR-005, FR-006, FR-009]

**Checkpoint**: the publish-ready guardrail + the human-approval boundary are specified.

---

## Phase 6: User Story 4 - In-progress pack at an earlier late stage (Priority: P2)

**Goal**: Specify the in-progress posture -- present sections render, absent downstream
sections are blockers, and the summary states the current stage without claiming an
unreached one.

**Independent Test**: described behavior at `semantic_model_ready: pass` with sections
07/08 absent renders the present sections, marks 07/08 as blockers, and the summary
states the current stage honestly.

- [ ] T016 [US4] Author the spec's US4 (in-progress pack) + Acceptance Scenarios, and
      record FR-008 (in-progress composition without claiming an unreached stage). [FR-008]
- [ ] T017 [US4] Confirm the in-progress posture does NOT weaken the US3 publish-ready
      guardrail (an in-progress pack never prints a publish-ready claim). [FR-006, FR-008]

**Checkpoint**: the pack works as a living progress view without overclaiming.

---

## Phase 7: Enumerate the FUTURE deliverables (planning tasks -- author specs, not code)

**Purpose**: Record the four future outputs as PLANNED artifacts so the build slice has
a clear contract. These tasks AUTHOR the planned enumeration in spec.md/plan.md; they do
NOT create the artifacts.

- [ ] T018 [P] Enumerate the planned skill `.claude/skills/evidence-pack-generator/SKILL.md`
      in plan.md "Repository artifacts this feature PLANS (not created)": invoke-and-compose
      verb (read sources, render 10-section pack, record per-section status + blockers,
      surface publish state, STOP). Do NOT create the skill. [FR-010, FR-013]
- [ ] T019 [P] Enumerate the planned doc `docs/tools/evidence-pack-generator.md`: the
      10-section contract, the source-artifact map, allowed/forbidden ops, the
      missing-source-is-a-blocker rule, and the F013 delta. Do NOT create the doc.
- [ ] T020 [P] Enumerate the planned templates `templates/evidence-pack-index.md` (ordered
      10-section index, each row -> source + status + blocker) and
      `templates/evidence-pack-summary.md` (surfaces stage + publish_ready + recorded
      approval + rolled-up blockers; asserts nothing). Do NOT create the templates.

**Checkpoint**: the four future deliverables are enumerated as planned outputs; nothing
is built.

---

## Phase 8: Polish & Cross-Cutting Verification

**Purpose**: Whole-feature gates spanning all stories and both checklists.

- [ ] T021 Author `specs/022-evidence-pack-generator/checklists/acceptance.md` (spec
      quality + acceptance items) covering the 10-section contract, missing->blocker,
      F013 delta, and publish-ready guardrail. [SC-001..SC-006]
- [ ] T022 Author `specs/022-evidence-pack-generator/checklists/governance.md` mapping
      the spec's Forbidden operations + Human approval boundary to Core-vs-Module authority,
      Principle V, no-self-approval, no-fake-confidence, generic, secrets/paths,
      allowed-vs-forbidden ops, and evidence-required. [Governance gate]
- [ ] T023 [P] Verify the F013 scope-delta is explicit and one-directional across spec +
      plan (F028 consumes/embeds F013; never re-authors or records the approval). [FR-004]
- [ ] T024 [P] Verify the publish-ready guardrail (surface, never assert; no approval
      write; no stage move) is an FR + edge case + governance item. [FR-005, FR-006]
- [ ] T025 [P] Grep all 5 files for C086 / retail_store_sales leakage (billing codes,
      segment rollups, PII columns, pharmacy grain keys) -- expect zero. [FR-011, SC-006]
- [ ] T026 [P] Confirm no file introduces a `retail check` rule, a new readiness stage, a
      live DB/PBIP read, a publish/Power BI-execution step, or a numeric confidence score.
      [FR-010, FR-013, hard rule #9]
- [ ] T027 Confirm all 5 files are ASCII + UTF-8 no BOM and repo-relative paths stay short
      (Windows `MAX_PATH`). [FR-012, Principle IX]

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies -- start immediately.
- **Foundational (Phase 2)**: depends on Setup; BLOCKS all user stories (fixes the
  section contract, the source map, the missing-is-a-blocker rule, the F013 delta, and
  the publish-ready guardrail that every artifact reuses verbatim).
- **User Stories (Phase 3-6)**: all depend on Foundational. US1 (P1) is the MVP and goes
  first; US2 and US3 (both P1) build on the same section contract and can follow; US4
  (P2) is additive.
- **Future-deliverable enumeration (Phase 7)**: depends on the section contract (T003) and
  the F013 delta (T005); records planned outputs, builds nothing.
- **Polish (Phase 8)**: depends on all stories + the enumeration; authors both checklists
  and runs the whole-feature gates.

### User Story Dependencies

- **US1 (P1)**: independent after Foundational -- the atomic deliverable (MVP).
- **US2 (P1)**: needs the section contract from US1/Foundational to define "missing".
- **US3 (P1)**: independent guardrail; reuses the Foundational publish-ready rule.
- **US4 (P2)**: needs US1 (the section contract) and must not weaken US3.

### Parallel Opportunities

- T002 (read references) runs parallel to T001.
- Phase 7 enumeration tasks (T018/T019/T020) touch different planned-output rows and can
  be authored in parallel.
- Polish greps/checks (T023/T024/T025/T026) are independent -- parallel.

## Parallel Example: Phase 7 + early Polish

```
# Enumerate the four future deliverables together (different planned-output rows):
Enumerate SKILL.md (T018)
Enumerate docs/tools/evidence-pack-generator.md (T019)
Enumerate templates/evidence-pack-index.md + evidence-pack-summary.md (T020)
```

## Implementation Strategy

**MVP first**: Setup -> Foundational -> US1 = the pack-composition story + the 10-section
contract. Then US2 (missing->blocker integrity) + US3 (publish-ready guardrail) + US4
(in-progress), then Phase 7 enumeration, then the Phase 8 whole-feature gates + both
checklists.

**Boundary discipline (the load)**: every artifact carries the same verbatim F013 delta
(T005) and publish-ready guardrail (T006); Phase 8 (T023/T024/T026) proves no F013
redefinition, no manufactured publish authority, no rule, no live read, no score -- the
ways this feature could fail its own scope.
