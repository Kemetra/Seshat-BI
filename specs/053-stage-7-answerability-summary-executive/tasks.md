---
description: "Task list for Stage 7 Answerability Summary (executive-readable)"
---

# Tasks: Stage 7 Answerability Summary (executive-readable)

**Input**: Design documents from `specs/053-stage-7-answerability-summary-executive/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: No automated tests -- this is a docs/templates-first artifact (hard rule #8);
no runtime code and no new `retail check` rule. Verification is by the requirements
checklist + the adversarial plan-review against the spec Success Criteria.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency)
- **[Story]**: US1 / US2 / US3 (from spec.md)

## Path Conventions

Docs/template artifact -- no `src/` or `tests/`. Files are at repository root:
`templates/handoff/answerability-summary.md` (new) and `docs/readiness/publish-ready.md`
(edited).

---

## Phase 1: Setup (source review)

**Purpose**: Confirm the composed sources before authoring, so the template invents nothing.

- [ ] T001 Re-read the composed sources and record their exact vocabulary/paths:
      `skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md` (the five
      coverage statuses + no-percentage discipline), the 12
      `skills/retail-kpi-knowledge/domains/*.md` decision-question tables, and
      `skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md` (A1-A11 named policies).
      Confirm all are tracked under `skills/` (NOT `.claude/skills/` worktree copies).

---

## Phase 2: Foundational

No shared foundational code -- docs artifact. Proceed directly to the user stories.

---

## Phase 3: User Story 1 -- Sponsor reads what a table can answer today (P1)

**Goal**: The generic template presents the three status+blocker lists composed from F7+F8.

**Independent test**: Open the filled template for one table; each list is populated only
from existing F7/F8 rows; every blocked row names its field/policy; no percentage/score
appears.

- [ ] T002 [US1] Create `templates/handoff/answerability-summary.md` skeleton: header block
      (`<schema>.<table>`, source family, assembled-on/by, explicit sponsor/finance audience
      line + "not a Stage 7 required artifact"), and a "What this is / is not" section
      stating: presentation over the human publish seam, grants no approval, moves no stage,
      status + named blocker only (never a percentage; rule #9), generic/C086-by-reference.
      (FR-006, FR-005, FR-010)
- [ ] T003 [US1] Add the "Answerable today" list: one row per decision question whose F8
      coverage status is "Covered" (contract Seeded AND required fields present); include the
      empty-list "none today" note for the all-blocked edge case; forbid inference from field
      presence. (FR-002, FR-003; edge case)
- [ ] T004 [US1] Add the "Blocked -- pending decision" list: each row names its specific
      missing field OR its specific A1-A11 undecided policy as the blocker, never a softened
      adjective; the template resolves no policy. (FR-004)
- [ ] T005 [US1] Add the "Out of scope" list (KPI domain the table cannot serve) and the
      distinct "Planned / not yet contracted" note for Planned KPIs, outside the three
      headline lists. (FR-002, FR-013)
- [ ] T006 [US1] Assert paper-answerable framing: add an explicit note that "answerable
      today" means contract Seeded + fields present per F8, NOT live-validated, and that no
      live publish path / F016 adapter is assumed. (FR-009)

**Checkpoint**: US1 acceptance scenarios 1-4 pass against the template.

---

## Phase 4: User Story 2 -- Publish-ready doc points to the summary without gating (P2)

**Goal**: One non-gating reference from the stage authority.

**Independent test**: The reference sits in "See also", worded optional; it is absent from
"Required artifacts", "Required checks", and "Blocking reasons".

- [ ] T007 [US2] Edit `docs/readiness/publish-ready.md`: add ONE bullet under the existing
      "See also" section referencing `../../templates/handoff/answerability-summary.md`,
      worded as an optional executive/sponsor companion to the handoff pack -- explicitly not
      a required Stage 7 artifact and not a gate. Add it NOWHERE else. (FR-001, FR-007)
- [ ] T008 [US2] Verify no gating leak: confirm the answerability summary appears in NONE of
      "Required artifacts", "Required checks", or "Blocking reasons", and that Stage 7 pass
      conditions are unchanged. (FR-007, SC-003)

**Checkpoint**: US2 acceptance scenarios 1-2 pass.

---

## Phase 5: User Story 3 -- Template stays generic and schema-agnostic (P3)

**Goal**: No C086/pharmacy specifics baked into the generic template.

**Independent test**: Scan for pharmacy table/category/field names -> none; concrete example
reached only by reference.

- [ ] T009 [US3] Add a "See also" section to the template referencing `publish-ready.md`,
      the F7 domains, the F8 scorecard, the sibling `bi-handoff-pack.md` (referenced, not
      restated), and `docs/worked-examples/c086-pharmacy.md` as the cited concrete instance.
      (FR-008, FR-010)
- [ ] T010 [US3] C086-leak scan: confirm the template body contains only `<placeholder>`
      tokens and generic KPI/domain names -- zero pharmacy table/category/field names inlined;
      any concrete pharmacy instance is reached ONLY by reference to
      `docs/worked-examples/c086-pharmacy.md`, never copied inline. ALSO confirm the template
      invents no grouping / rollup / segment / ordering beyond the flat F7 domain-file routes
      (FR-011 + FR-015 flat-list ruling). (FR-008, FR-011, SC-004)

**Checkpoint**: US3 acceptance scenarios 1-2 pass.

---

## Phase 6: Principle-V open items + polish

- [ ] T011 [P] In the template, ENCODE the two human rulings (resolved 2026-07-01, Principle
      V; see spec FR-014 / FR-015): (a) a fixed PII-posture line stating "answerable today" is
      an answerability statement only and asserts NO publish-safety judgment, inheriting the
      caveats-note PII-exclusion stance; (b) render the blocked-pending list as a FLAT observed
      list with no severity/priority/rank ordering. Do NOT present these as open items -- they
      are ruled; the template reflects the rulings.
- [ ] T012 [P] Final constraints pass on BOTH authored files: ASCII + UTF-8 no BOM (`--`,
      `->`, no glyphs; rule IX), short paths, and a full sweep for any numeric
      coverage/confidence figure (must be zero; rule #9, SC-002). Confirm `retail check` rule
      count is unchanged at 38 (SC-006).

---

## Dependencies

- T001 (source review) before authoring (T002-T006).
- T002 (skeleton) before T003-T006 and T009-T011 (same file).
- US1 (T002-T006), US2 (T007-T008), US3 (T009-T010) are independently testable; US2 touches
  a different file and may proceed in parallel with US1/US3 authoring.
- T011-T012 are the final polish over both files.

## Parallel example

- T007-T008 (edit `publish-ready.md`) can run in parallel with T003-T006 (author the
  template) -- different files.
