# Requirements Checklist: Worked-Example Factory

**Purpose**: Self-validation of `spec.md` against Spec-Kit quality bar and this
repo's constitution before proceeding to `plan.md`.
**Created**: 2026-07-03
**Feature**: `specs/084-worked-example-factory/spec.md`

## Completeness

- [x] CHK001 User Scenarios section present, with >=1 prioritized user story
      and independent tests (3 stories, all P1 -- each is independently
      checkable per its own Acceptance Scenarios).
- [x] CHK002 Edge Cases section present and non-trivial (6 edge cases, each
      with a stated resolution, not just a question).
- [x] CHK003 Functional Requirements are individually testable (FR-001..FR-012,
      each a single checkable MUST/MUST NOT statement).
- [x] CHK004 Key Entities section present (candidate domain, artifact set,
      completeness tier, maturity rung).
- [x] CHK005 Success Criteria are measurable and technology-agnostic
      (SC-001..SC-006 -- each has an observable pass condition).
- [x] CHK006 Assumptions section records every judgment call made without a
      human available (A-001..A-005).
- [x] CHK007 [NEEDS CLARIFICATION] count is <= 3 (actual: 0 -- every open
      question resolved to an Assumption with cited precedent).

## Constitution / repo-rule alignment

- [x] CHK008 No fabricated metric, KPI contract, or approval appears anywhere
      in spec.md (grep-checked manually: only `<placeholder>`-style and
      cited-precedent statements).
- [x] CHK009 No C086-specific fact (billing code, segment rollup, insurance
      column) appears; C086 is mentioned only as "archived, must not be
      resurrected" (Non-Goals, FR-007, edge case).
- [x] CHK010 Docs-maturity-vs-runtime-capability distinction is explicit and
      load-bearing, not a footnote (FR-005, User Story 3, SC-005).
- [x] CHK011 The four named-human approval seams are named explicitly and the
      spec states the factory process never fills them (SC-006, Human-Approval
      Boundaries, Non-Goals).
- [x] CHK012 Relationship to sibling `083-demo-harness` is stated (FR-010) -- runs-vs-defines distinction, no subsumption claim either direction.
- [x] CHK013 Safety Constraints explicitly forbid `src/**` edits, new rule IDs,
      CI changes, new dependencies, and any commit/push/PR/merge during this
      spec's own production.
- [x] CHK014 Stop Conditions cover: a candidate domain needing a new rule/
      default; any drift toward actually scaffolding an example; any
      unbacked acceptance-criteria item.

## Internal consistency

- [x] CHK015 Every "MUST cite X" requirement (FR-008, Evidence Requirements)
      names a file that was actually read during spec authoring (verified:
      `templates/*`, `docs/worked-examples/retail-store-sales.md`,
      `templates/maturity-report.md`, `docs/readiness/readiness-model.md`).
- [x] CHK016 The two-tier completeness split (FR-004) does not contradict the
      Constitution's Principle V (no self-granted approval) or Principle VIII
      (static-first, live-deferred) -- cross-checked against both.
- [x] CHK017 Non-Goals list and Functional Requirements do not conflict (e.g.
      no FR silently asks for something a Non-Goal forbids).

## Self-validation history

- **Pass 1** (2026-07-03): Authored spec.md directly from the read source set
  (constitution, AGENTS.md, README, RELEASE_NOTES, readiness-model,
  retail-store-sales.md, the five mapping-gate templates, maturity-report.md,
  worked-examples/README.md) plus advisor guidance. All CHK items above
  verified against the written spec.md text; no revision needed before
  proceeding to plan.md.

## Notes

- This checklist was produced by the spec author in the same pass as spec.md
  (single self-validation cycle), per the task's "self-validate <= 3x"
  instruction. Two further passes are available if plan/tasks authoring
  surfaces a spec gap; none was needed.
