# Cross-Artifact Analysis: Text/JSON Output Equivalence Property Test

**Date**: 2026-06-29 | **Branch**: `045-output-parity`
**Artifacts analyzed**: spec.md, plan.md, tasks.md (read-only consistency pass)

## Method

Cross-checked the three artifacts for: requirement->task coverage, success-criteria->task
coverage, terminology drift, scope contradictions, constitution-alignment, and unresolved
ambiguity. Severity scale: CRITICAL (blocks ratify), HIGH (must fix before plan), MEDIUM (note),
LOW (cosmetic).

## A. Requirement -> Task coverage

| Requirement | Covered by | Status |
|-------------|------------|--------|
| FR-001 new parity test file; text-multiset == json-multiset | T004, T006, T007, T008 | Covered |
| FR-002 order-insensitive Counter over 4-field tuple | T006, T007, T008 | Covered |
| FR-003 exit-code equality + gate semantics | T010 | Covered |
| FR-004 SYNTHETIC fixtures, not real registry | T005 | Covered |
| FR-005 fixtures cover all severities + a multi-finding rule | T005 | Covered |
| FR-006 fixtures render to unambiguously parseable lines | T005, T006 | Covered |
| FR-007 treat Finding as immutable; fresh Counter | T006, T008 | Covered |
| FR-008 no new rule / no new EXPECTED_RULE_ID | T012 | Covered |
| FR-009 no change to runner.py / core.py | T012 | Covered |
| FR-010 stdlib-only; no retail.rules / psycopg2 import | T004, T011 | Covered |
| FR-011 C086-agnostic fixtures | T005, T011 | Covered |
| FR-012 capsys capture; handle trailing newline | T006, T010 | Covered |

All 12 functional requirements map to at least one task. No orphan requirements.

## B. Success-Criteria -> Task coverage

| Criterion | Covered by | Status |
|-----------|------------|--------|
| SC-001 any path divergence caught 100% | T008, T010 | Covered |
| SC-002 deterministic, no DB/network/PBI, no flakiness | T013 | Covered |
| SC-003 zero new rule/EXPECTED_RULE_ID; runner/core unchanged | T012, T014, T015 | Covered |
| SC-004 zero C086 identifiers | T005, T011, T015 | Covered |
| SC-005 multiset distinguishes order from content | T005, T008 | Covered |

All 5 success criteria are verifiable by a named task. No unverifiable criteria.

## C. User-Story -> Task coverage

| Story | Tasks | Status |
|-------|-------|--------|
| US1 findings-multiset parity (P1) | T004-T009 | Covered |
| US2 exit-code parity (P1) | T010 | Covered |
| US3 generic / no-gate-change guardrails (P2) | T011, T012 | Covered |

Each user story has an independently testable task slice. US1 and US2 are both P1 (the two halves
of the property); US3 is the P2 guardrail. Setup (T001-T003) and verification (T013-T015) are
cross-cutting.

## D. Terminology consistency

- "multiset" / `collections.Counter` -- used consistently in spec (FR-002, Key Entities), plan
  (Summary, Constraints), tasks (T006-T008). No drift.
- "four-field tuple `(rule_id, severity, message, locator)`" -- identical phrasing across all three;
  matches `FindingDict` / `Finding.to_dict()` in `src/retail/core.py`. No drift.
- "synthetic `RegisteredRule` fixtures" -- consistent; explicitly contrasted with the real
  `all_rules()` registry (Q1) in spec, plan, and tasks Out-of-Scope. No drift.
- "exit code 1 iff any ERROR" -- consistent with `_exit_code` semantics in `src/retail/runner.py`
  and with `Severity.ERROR` in `core.py`. No drift.
- The text format string "[{severity.value}] {rule_id} {message} ({locator})" is quoted
  identically in spec (Assumptions, Edge Cases), plan (Constraints), and tasks (T001, T006), and
  matches `_format` verbatim. No drift.

## E. Scope / contradiction check

- No artifact proposes modifying run(), run_json(), _format, _collect, _exit_code, or core.py.
  All three explicitly forbid it (FR-009, plan Structure Decision, tasks T012 + Out-of-Scope).
  Consistent.
- No new registered rule / EXPECTED_RULE_ID anywhere (FR-008, plan Principle-I check, tasks T012
  + Out-of-Scope). Consistent with the wiring-test invariant.
- No DB/network/Power BI/executor wiring; no deferred capability (F016, F031-F033) assumed. Stated
  identically in spec Assumptions, plan (Principle VIII), and tasks Out-of-Scope. Consistent.
- The real-registry-fixture option and the robust-parser option are BOTH explicitly deferred
  (Q1/Q2 in spec; tasks Out-of-Scope). No artifact silently assumes either. Consistent.

## F. Constitution alignment

| Principle / rule | Spec | Plan | Tasks | Verdict |
|------------------|------|------|-------|---------|
| I (gate-enforced; exit code is contract) | US2, FR-003 | Constitution Check | T010 | Aligned -- hardens, never weakens |
| V (stops at judgment calls) | Clarifications (owner item reserved) | Constitution Check | n/a | Aligned -- roadmap item NOT self-answered |
| VII (C086 is an example) | US3, FR-011, SC-004 | Constitution Check | T005, T011 | Aligned -- generic synthetic only |
| VIII (static-first, stdlib-only) | FR-010 | Constitution Check | T004, T011 | Aligned -- no DB/network/PBI; no retail.rules import |
| IX (Windows-safe text / reproducibility) | FR-012, Edge Cases | Constitution Check | T006 | Aligned -- trailing-newline handling; no committed artifact read |
| Hard rule #7 (generic only) | FR-011 | Constitution Check | T005, T011 | Aligned |
| Hard rule #9 (no fabricated score) | -- | Constitution Check | -- | Aligned -- asserts exact equality, emits no score |
| Coding-style (immutability) | FR-007 | Constraints | T006, T008 | Aligned -- frozen Finding, fresh Counter |

No principle conflict detected.

## G. Unresolved ambiguity

- ZERO [NEEDS CLARIFICATION] markers remain in the spec.
- ONE Principle-V item is OPEN by design (roadmap promotion / F-numbering), reserved for the human
  owner in the spec's Clarifications block and surfaced to open_for_human. It is NOT build-blocking:
  the test is fully specifiable and implementable without that ruling (the work proceeds spec-only
  by conservative default). This is the correct Principle-V posture, not a gap.

## Findings

| ID | Severity | Finding | Disposition |
|----|----------|---------|-------------|
| -- | -- | (none) | -- |

- CRITICAL: 0
- HIGH: 0
- MEDIUM: 0
- LOW: 0

## Verdict

CLEAN. All 12 FRs, 5 SCs, and 3 user stories have task coverage; terminology is consistent across
the three artifacts; no scope contradiction; no constitution conflict; zero unresolved
[NEEDS CLARIFICATION] markers. The single open item is a deliberate Principle-V owner judgment
call (roadmap promotion), correctly reserved and non-blocking. No CRITICAL or HIGH findings ->
analyze verdict is CLEAN.
