# Cross-Artifact Analysis: Seed-Layer Route Honesty Rule (067)

**Date**: 2026-07-02 | **Scope**: read-only consistency pass over spec.md, plan.md,
tasks.md (per repo convention this file is the only write the analyze stage makes).

## Method

Cross-checked the three artifacts for: requirement -> task coverage, task ->
requirement traceability, terminology consistency, constitution-gate coverage,
scope-boundary agreement, and factual soundness of the load-bearing claims (verified
against the tree where cheap).

## Coverage matrix (FR -> tasks / user story)

| FR | Requirement (short) | Tasks | Story |
|----|---------------------|-------|-------|
| FR-001 | add `seed` to `_VALID_STATUS` | T008 | US1/US2 |
| FR-002 | add `seed` to routes.yaml vocabulary docs | T012 | US1 |
| FR-003 | seed targets must resolve (else ERROR) | T003, T009, T011 | US1 |
| FR-004 | seed with no targets -> ERROR | T004, T009 | US1 |
| FR-005 | unknown-status guard preserved (3 values) | T005, T008 | US2 |
| FR-006 | built/planned behavior unchanged | T006, T011 | US2 |
| FR-007 | no auto-promote / self-grant | T009, T018 | US1 |
| FR-008 | no new id / no wiring / no regen | T013, T014 | US3 |
| FR-009 | A3 bijection non-regression | T015 | US3 |
| FR-010 | lazy yaml, static, read-only | T016 | US1 |
| FR-011 | missing/malformed manifest fails loud | (existing A1 behavior; T016 gate run) | edge |
| FR-012 | categorical, no score | T018 (audit) | US1 |
| FR-013 | generic, no C086 literal | T017 | US1 |
| FR-014 | no readiness stage / deferred cap | T018 | US1 |
| FR-015 | ASCII/UTF-8 no BOM | T010, T012 (authoring constraint) | all |
| FR-016 | seed->built promotion = OPEN (Principle V) | T018 (confirm NOT coded) | carve-out |

Every FR maps to at least one task. Every task maps back to an FR or a stated
non-regression / audit obligation. No orphan task, no uncovered requirement.

## Consistency findings

- **CONSISTENT (scope decision)**: spec C4 / FR-008, plan "Structure Decision" +
  "extend A1 in place", and tasks Phase 5 + "Out of scope" all agree: no new rule id,
  no wiring seam, no manifest/golden regen. The three artifacts state the same
  boundary in the same terms.
- **CONSISTENT (seed semantics)**: spec FR-003/FR-004 (seed = must-resolve, like
  built), plan Design notes (add seed to the built "must resolve" arm), and tasks
  T009 all describe identical behavior. US1 acceptance scenarios 1-3 match T002-T004.
- **CONSISTENT (Principle-V carve-out)**: FR-016 [NEEDS CLARIFICATION], the spec
  Clarifications carve-out, plan Constitution-Check Principle V, and tasks T018 all
  agree the promotion criterion is NOT invented and NOT coded; it is left open.
- **CONSISTENT (terminology)**: the token is `seed` (lowercase) everywhere; `Seeded`
  is referenced only as the sibling KPI-layer vocabulary, explicitly flagged as a
  cross-layer naming call (spec C2 / Assumptions). No drift between artifacts.
- **VERIFIED (factual, FR-009)**: `src/retail/rules/routes_coverage.py` (A3) contains
  ZERO references to `status` (grep confirmed) -- it reconciles id sets only. The
  "A3 status only indirectly / non-regression" claim is sound; T015 still verifies it
  with a fixture rather than assuming, which is the correct posture.
- **VERIFIED (factual, FR-008)**: A1 keeps its rule id and ERROR severity, so the
  severity-posture golden (`tests/unit/test_severity_posture.py`) and
  `rules-manifest.json` are keyed unchanged; T014's byte-identical assertion is
  well-founded.
- **VERIFIED (factual, seam)**: `_VALID_STATUS = frozenset({"built","planned"})` and
  the per-route `built`/`planned` branches exist in `src/retail/rules/routes.py`
  exactly as the plan describes; the edit is the minimal widening claimed.

## Constitution-gate coverage

Principles I, V, VII, VIII, rule IX, and hard-rule #9 each have an explicit
Constitution-Check line in plan.md and a corresponding task or authoring constraint
(T009/T016/T017/T018/T010). No gate is asserted without a task backing it.

## Ambiguity / marker audit

- Exactly ONE [NEEDS CLARIFICATION] marker remains, in FR-016, by design
  (Principle-V promotion criterion). It is documented as BUILD-SAFE in both spec and
  plan; the feature ships without resolving it. This is an intended open carve-out,
  not an unresolved drafting gap.

## Findings

- **Critical**: 0
- **High**: 0
- **Medium**: 0
- **Low**: 1 (advisory, non-blocking):
  - **L1** -- tasks T006 says "if the file lacks explicit planned-stale / built-broken
    cases, add them". Whether `tests/unit/test_routes.py` already pins those cases is
    not asserted from the tree in this draft; the task is correctly conditional, so
    this is a note for the implementer, not a spec defect. No action required at spec
    time.

## Verdict

**analyze_verdict: clean** (0 critical, 0 high). Artifacts are internally consistent,
fully traceable, and the load-bearing factual claims (A3 status-independence, id/
severity stability, the routes.py seam) are verified against the tree. The single
open marker (FR-016) is an intentional, build-safe Principle-V carve-out.
