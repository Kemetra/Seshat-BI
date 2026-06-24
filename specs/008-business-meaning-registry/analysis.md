# Cross-Artifact Analysis: feature 008 -- business meaning registry + Arabic<->English retail term dictionary

**Date**: 2026-06-24 | **Branch**: `008-business-meaning-registry` (roadmap F007)

**Inputs analyzed**: `spec.md`, `plan.md`, `tasks.md` (this dir);
`.specify/memory/constitution.md`; `docs/roadmap/roadmap.md`;
`docs/readiness/source-ready.md`; `docs/readiness/readiness-model.md`;
`templates/source-profile.md`; `docs/data-dictionary.md`.

This is the /speckit-analyze cross-artifact consistency pass run at the close of the
spec -> plan -> tasks chain. Detection categories: duplication, ambiguity, underspecification,
constitution alignment, coverage gaps, inconsistency.

## Summary

The three artifacts are internally consistent and constitution-aligned. One real
traceability gap was found and FIXED during this pass (FR-005 was substantively covered by
the leakage tasks but not cited by ID; citations were added to T002/T007/T012/T016). After
the fix, all 10 functional requirements and all 5 success criteria are traced to tasks, and
all three artifacts are ASCII + UTF-8 no BOM. No CRITICAL or HIGH issues remain open.

## Coverage matrix (post-fix)

| Spec item | Covered by | Status |
|-----------|-----------|--------|
| FR-001 (registry template) | T003 | covered |
| FR-002 (registry per-entry schema, no score) | T004 | covered |
| FR-003 (dictionary template) | T008 | covered |
| FR-004 (dictionary per-entry schema, RC8) | T009, T010 | covered |
| FR-005 (strictly generic, cite-not-inline) | T002, T007, T012, T016 | covered (fixed this pass) |
| FR-006 (proposed-not-invented discipline) | T005 | covered |
| FR-007 (Layer-2 explainer doc) | T013 | covered |
| FR-008 (additive source-ready.md edit) | T014 | covered |
| FR-009 (retail check exit 0, no code/dep) | T018 | covered |
| FR-010 (See-also cross-links) | T006, T011 | covered |
| SC-001 (templates exist, ASCII/no-BOM, no score) | T007, T012, T017 | covered |
| SC-002 (leakage scan = zero C086 values) | T016 | covered |
| SC-003 (retail check exit 0 + suite green) | T018 | covered |
| SC-004 (trace example, no new vocabulary) | T013, T015, T020 | covered |
| SC-005 (discipline present, no score) | T019 | covered |
| US1 / US2 / US3 | Phase 3 / 4 / 5 | covered |

No requirement is uncovered; no task is orphaned (every task maps to an FR/SC or is an
explicit setup/verify step).

## Findings

### Resolved this pass

- **[MEDIUM -> RESOLVED] FR-005 not traced by ID.** The strictly-generic / cite-not-inline
  requirement was implemented by the leakage tasks (T002/T007/T012/T016) but none cited
  FR-005. Fixed by adding the (FR-005) citation to those four tasks. Rationale: FR-005
  is the load-bearing Principle VII constraint and must be explicitly traceable, since the
  whole feature value depends on the templates staying generic.

### Constitution alignment (no issues)

- **Principle VII (C086 is an example, not the schema) -- the central gate.** Spec
  (generic/instance boundary section, FR-005, SC-002), plan (Constitution Check row VII
  flagged as the highest-risk failure mode), and tasks (T002 forbidden-token list +
  T007/T012/T016 leakage scans) are mutually reinforcing. The artifacts cite
  docs/data-dictionary.md as the filled instance and never inline its values. The spec/
  plan/tasks themselves carry NO real Arabic source terms, Z-codes, or PHARMA values
  (verified: 0 non-ASCII bytes in all three).
- **Principle V (Agent Stops at Judgment Calls).** Consistently encoded: spec US1 scenario 3
  + edge cases route rollup/PII/grain meanings to unresolved-questions.md; FR-006; plan
  Constitution Check row V; task T005. No artifact lets the agent self-confirm a judgment
  call. These remain open_for_human items (see decision record), not auto-answered.
- **Principle VI / RC8 (returns from the authoritative column).** Baked into the dictionary
  schema (FR-004, T010), not just the prose. Consistent with source-profile.md and
  data-dictionary.md returns discipline.
- **Hard rule #8 (docs/templates first).** All three artifacts agree the deliverable is
  template/doc text only -- no code, no CLI, no checker rule (plan Architecture decision;
  FR-009; tasks T018). Consistent with features 001-006 posture.
- **Hard rule #9 (no fake confidence).** Uniformly enforced: NO numeric score/confidence
  field in either template (FR-002, FR-004); status vocabulary is proposed/confirmed
  for entry meaning, distinct from the four-value spine stage status; plan + tasks (T019)
  verify absence of a score field. Consistent with readiness-model.md.
- **Readiness spine.** The feature reuses the EXISTING Source Ready stage and adds no new
  stage/status/blocking-reason. The proposed/confirmed entry-meaning status is correctly
  distinguished from the stage status; the source-ready.md edit is additive (FR-008,
  T014) and preserves the single required artifact (source-profile.md) and the review gate.

### Consistency checks (no issues)

- **Status vocabulary** is consistent across artifacts: spec/plan/tasks all use
  proposed/confirmed for entry meaning and reserve the four-value not_started/
  blocked/warning/pass for the Source Ready stage status. No conflation.
- **File placement** agrees between plan (Project Structure) and tasks (path conventions):
  templates in templates/, explainer at docs/source-intelligence.md, additive edit to
  docs/readiness/source-ready.md, citations (not edits) to docs/data-dictionary.md.
- **Optional vs required** is consistent: every artifact states the registry/dictionary are
  OPTIONAL strengthening evidence and the profile stays the sole REQUIRED Source Ready
  artifact -- the feature does NOT widen the gate.

### Notes / accepted (not defects)

- **Roadmap number vs directory number.** The roadmap lists this as F007; the spec is filed
  in specs/008-business-meaning-registry/. The spec "Roadmap and stage alignment" section
  documents the discrepancy and states the roadmap row (not the directory number) is
  authoritative for sequence. Accepted and explicitly recorded; not an inconsistency to fix
  (directory numbers are allocated per-branch to avoid parallel-worktree collisions).
- **Empty Foundational phase (Phase 2 in tasks).** Intentional -- the two templates are
  independent files with no shared code/schema foundation. Kept for template parity, marked
  intentionally empty. Not a gap.
- **Deferred decisions** in the spec (filled instance, ASCII/no-BOM lint, machine-readable
  YAML format, drift-detector linkage, promotion to required artifact) are all recorded as
  future specs/issues, not built -- consistent with hard rule #8 and the YAGNI posture.

## Open items for a human (Principle V -- NOT auto-answered)

These are surfaced by the feature own design and are deliberately left for a human; the
chain did NOT invent answers for them (they are judgment calls per Principle V):

1. **Exact placement of the Layer-2 explainer** -- docs/source-intelligence.md (default
   chosen in plan) vs a new section inside docs/readiness/. Low-stakes, reversible; the
   plan flags it as a tasks-time choice.
2. **Whether the registry should ever become a REQUIRED Source Ready artifact** -- deferred
   (the spec keeps it optional). A governance/analyst decision once the optional artifact
   proves useful on a real onboarding.

(No grain, PII publish-safety, business-rollup/segment, or product-identity decision is made
by these artifacts -- by design they ROUTE such decisions to unresolved-questions.md. The
chain auto-answered no Principle-V question.)

## Gate result

- Coverage: 10/10 FR, 5/5 SC traced to tasks. PASS.
- Constitution: PASS (Principles V, VI/RC8, VII, VIII, IX + spine + hard rules #7/#8/#9).
- ASCII + UTF-8 no BOM across spec/plan/tasks/analysis: PASS.
- No CRITICAL/HIGH findings open. One MEDIUM found and fixed in-pass (FR-005 traceability).

The chain is ready for /speckit-implement when scheduled. No blocking issues.