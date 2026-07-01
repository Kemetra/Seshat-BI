# Cross-Artifact Analysis: First-Hour Compass / New-Table Author Onboarding Cockpit

**Branch**: `055-first-hour-compass-new-table` | **Date**: 2026-07-01
**Artifacts analyzed**: spec.md, plan.md, tasks.md (READ-ONLY consistency pass)

This is the repo-convention `/speckit-analyze` report: a non-destructive cross-artifact
consistency and quality analysis. It is the only file this stage writes.

## Verdict

**CLEAN** -- 0 critical, 0 high. Two LOW traceability notes recorded below (no action
required for ratification).

- Critical findings: 0
- High findings: 0
- Medium findings: 0
- Low findings: 2 (traceability polish only)

## Coverage matrix (spec requirement -> task)

| Requirement | Covered by | Status |
|-------------|-----------|--------|
| FR-001 (read one readiness-status.yaml, render card) | T001 | covered |
| FR-002 (current_stage verbatim) | T001, T003 | covered |
| FR-003 (next artifact = first non-pass stage; ordering) | T001, T009 | covered |
| FR-004 (all-pass -> no next artifact) | T001 | covered |
| FR-005 (generic cross-walk) | T002, T003, T008 | covered |
| FR-006 (surface blocking_reasons verbatim) | T003, T006 | covered |
| FR-007 (two-condition approval flag from stage doc) | T003, T006 | covered |
| FR-008 (read-only, no writes) | T003, T006, T011 | covered |
| FR-009 (no numeric score) | T001, T007 | covered |
| FR-010 (every value traces to a recorded field) | T001 (range FR-009..FR-012) | covered |
| FR-011 (surface gaps, never fabricate) | T001 (range FR-009..FR-012) | covered |
| FR-012 (surface conflicts, never resolve) | T001, T003, T006, T009 | covered |
| FR-013 (never a new gate; gate exit stays authority) | T003 (range FR-005..FR-014) | covered |
| FR-014 (four Principle-V seams surfaced-only) | T003, T006 | covered |
| FR-015 (docs/template/skill only) | T004 | covered |
| FR-016 (next_step.py deferred) | T004 | covered |
| FR-017 (generic, ASCII, UTF-8 no BOM) | T001..T005, T008, T010 | covered |
| SC-001 (correct stage/artifact/skill, all traceable) | T001, T009 (implicit) | covered (LOW-1) |
| SC-002 (no downstream-before-upstream) | T009 | covered |
| SC-003 (git status clean, zero writes) | T011 | covered |
| SC-004 (zero scores; decline) | T007 | covered |
| SC-005 (generic; no C086 specifics) | T008 | covered |
| SC-006 (author can self-orient from the card) | T001 (implicit) | covered (LOW-2) |

Every FR maps to at least one task. FR-010, FR-011, FR-013 are covered via task ranges
(T001 `FR-009..FR-012`, T003 `FR-005..FR-014`) rather than explicit single-ID mentions
-- verified, not a gap.

## Consistency checks

- **Terminology**: consistent across artifacts -- "orientation card", "you-are-here",
  "next artifact", "authoring skill", "cross-walk", "first non-pass stage", the seven
  named stages, the four statuses (`not_started`/`blocked`/`warning`/`pass`). No drift
  vs the readiness-viewer sibling vocabulary.
- **Scope alignment**: spec MVP (FR-015) == plan deliverables (three files + embedded
  cross-walk) == tasks Phase 1 (T001-T004). `next_step.py` is DEFERRED in all three
  (spec FR-016, plan "Deferred" section, tasks "Out of scope"). No scope drift.
- **Principle coverage**: all constraining principles (I, V, VII, VIII, hard rules
  #8/#9, pipeline ordering, renders-never-re-derives) appear in spec (FRs), plan
  (Constitution Check), and tasks (verification passes T006-T010). Symmetric.
- **No deferred-capability assumption**: none of the three artifacts reference F016
  (Power BI Execution Adapter) or F031-F033 spec-only runtimes. The Compass reads
  static committed files only. Confirmed.
- **Roadmap provenance**: no F-number is minted anywhere; all three artifacts state
  roadmap admission is an open human decision (spec Clarifications Q1, plan risk note).
  Consistent.
- **Open items**: the four Principle-V seams are OPEN in the spec (Clarifications) and
  surfaced-only in tasks (T006). No artifact answers them. Correct and consistent.

## Findings

### LOW-1 -- SC-001 not cited by an explicit task ID

**Where**: tasks.md. **What**: SC-001 is satisfied by T001 (authoring) + T009 (ordering
verification) but is not named by SC-ID in any task line. **Impact**: cosmetic
traceability only; the behavior is fully covered by FR-001..FR-003 tasks. **No action
required** for ratification.

### LOW-2 -- SC-006 not cited by an explicit task ID

**Where**: tasks.md. **What**: SC-006 (a new-table author can self-orient from the card
alone) is an outcome satisfied by the T001 card design but not named by SC-ID.
**Impact**: cosmetic traceability only. **No action required**.

## Summary

The three artifacts are mutually consistent, fully scope-aligned, principle-complete,
and free of deferred-capability assumptions and C086 leaks at the plan level. The only
findings are two low-severity traceability polish notes. The draft is analysis-clean and
ready for the adversarial plan-review (stage 6).
