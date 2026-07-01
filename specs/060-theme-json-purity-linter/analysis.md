# Cross-Artifact Analysis: Theme JSON Purity Linter

**Feature**: 060-theme-json-purity-linter
**Date**: 2026-07-01
**Scope**: Read-only consistency pass over spec.md, plan.md, tasks.md (with
research.md, data-model.md, contracts/rule-contract.md, quickstart.md as support).

## Method

Cross-checked: (1) every FR has coverage in a task and a contract row; (2) every
user story maps to a task phase; (3) every success criterion maps to a checkable
test; (4) terminology is consistent across artifacts; (5) constitution gate is
evaluated; (6) no duplicate or conflicting requirements; (7) no artifact assumes a
deferred capability.

## Requirements coverage (spec FR -> contract row -> task)

| FR | Contract row(s) | Task(s) | Status |
|----|-----------------|---------|--------|
| FR-001 forbidden-key scan | C1-C3 | T003, T008 | covered |
| FR-002 generic discovery | C11 | T008, T015, T017 | covered |
| FR-003 ERROR + file/pointer locator | C1, C2 | T007, T008 | covered |
| FR-004 one finding per occurrence | C3 | T006, T007, T008 | covered |
| FR-005 keys not values; no adjudication | C7 | T011, T012, T013 | covered |
| FR-006 allowed-only -> zero | C4, C5 | T009, T010, T012, T013 | covered |
| FR-007 generic vocabulary, no tenant literal | (design) | T003, T024 | covered |
| FR-008 fail closed (ERROR -> non-zero) | C1 | T008, T023 | covered |
| FR-009 malformed JSON -> finding, no crash | C8 | T014, T016, T017 | covered |
| FR-010 fixture exemption | C10 | T002, T016, T017 | covered |
| FR-011 fresh id, observed severity | (registration) | T001, T019, T021 | covered |
| FR-012 five-place wiring, drift fails closed | (registration) | T018-T021, T022 | covered |
| FR-013 forbidden-key literal boundary (OPEN) | (non-goal note) | Phase 6 GATE | deferred by design (Principle V) |

All non-deferred FRs are covered. FR-013 is intentionally OPEN (Principle-V human
ruling) and is correctly reflected as a wiring gate, not a planning-time gap.

## User story coverage

- US1 (P1) -> Phase 3 (T004-T008). Covered; independently testable MVP.
- US2 (P1) -> Phase 4 (T009-T013). Covered.
- US3 (P2) -> Phase 5 (T014-T017). Covered.

## Success criteria coverage

| SC | Verified by |
|----|-------------|
| SC-001 forbidden key -> ERROR + non-zero | C1 / T007-T008, T023 |
| SC-002 allowed-only -> zero false positives | C4-C5 / T012-T013 |
| SC-003 current starter theme -> zero | C6 / T013 |
| SC-004 two keys -> exactly two findings | C3 / T006-T008 |
| SC-005 new file scanned, no code change | C11 / T015, T017 |
| SC-006 id in registry + goldens, wiring test passes | (registration) / T018-T022 |

All six success criteria map to a checkable test.

## Terminology consistency

Consistent across artifacts: "forbidden-key vocabulary", "allowed styling
vocabulary", "file#/pointer locator", "five-place wiring", "observed (not declared)
severity", "test-fixture exemption path", "generic discovery". No divergent synonyms
that would confuse an implementer.

## Constitution / gate

plan.md evaluates Principles I, V, VII, VIII, IX and ratified 044 with an explicit
PASS and rationale for each; no Complexity Tracking entries (no violations). tasks.md
carries a matching Principle-V gating note on Phase 6. Consistent.

## Deferred-capability check

No artifact assumes F016 (Power BI Execution Adapter) or F031-F033 (spec-only
runtimes). The rule is stdlib-only over committed text; the token-to-theme fidelity
rule is explicitly named OUT OF SCOPE, not assumed present. Clean.

## Duplication / conflict check

No duplicate FRs. No conflicting requirements. The one tension worth naming -- "the
rule is plan-complete" versus "wiring MUST NOT be committed until the human ruling"
-- is not a contradiction: wiring is an implement-time step gated on the ruling, and
the planning artifacts are complete without it. The spec front-matter correctly
stays Status: Draft.

## Findings

| ID | Severity | Location | Finding | Recommended action |
|----|----------|----------|---------|--------------------|
| F1 | LOW | spec FR-013 | One [NEEDS CLARIFICATION] marker remains. | INTENTIONAL Principle-V deferral, recorded as an OPEN human ruling and reflected as a wiring gate. No action; do not auto-resolve. |
| F2 | LOW | T001 / research R4 | Possible EXPECTED_RULE_IDS vs decorator count drift on this branch (flagged by backlog reviewers). | Reconcile against the TRUE live registry at wiring time (already an explicit task, T001). No spec change needed. |

**Critical findings**: 0
**High findings**: 0
**Verdict**: clean (0 critical, 0 high). The two LOW items are by-design and each
already has an owning task or is an intentional Principle-V deferral.
