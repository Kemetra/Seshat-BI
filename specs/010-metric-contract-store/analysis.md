# Specification Analysis Report: Metric Contract Store + Retail KPI Packs (010)

**Analyzed**: 2026-06-24 | **Artifacts**: spec.md, plan.md, tasks.md | **Mode**: read-only

Cross-artifact consistency + constitution-alignment analysis run after tasks. This analysis
modified no chain artifact (spec/plan/tasks); findings are recorded here as the analyze output.

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| C1 | Constitution | NONE (pass) | plan Constitution Check; spec FR-007/FR-012 | Principles I-IX each addressed; gold-only (III), stop-and-ask (V), generic (VII), static-first/no-rule (VIII), no-BOM (IX) carried into FRs + tasks | No action -- documented PASS |
| B1 | Boundary | NONE (pass) | spec define/check boundary; plan Boundary gate; tasks T003/T020 | F009-vs-F010 (define vs check) boundary stated identically in all three, enforced by T020 (no powerbi/ read, no rule) | No action -- the load-bearing risk is mitigated |
| V1 | Underspecification | LOW | spec FR-002 / plan Phase 1 | binds_to cardinality (one gold table vs many) not pinned; example metrics are single-table | Show a single bound table + column list in the template; note multi-table as a deviation if it arises |
| V2 | Ambiguity | LOW | spec US1 AC#2 / grain edge case | "flags grain mismatch for review" -- mechanism is a blocking_reason (FR-009) but not named in the AC | Cosmetic; FR-009 + T005/T009 already bind it. No change needed |
| D1 | Duplication | LOW | spec FR-003 vs FR-010 | both touch readiness/evidence | Intentional split (status vocabulary vs promotion rule); keep |
| I1 | Inconsistency | LOW | spec "F010 / on-disk 011" vs roadmap "010 Semantic Model Readiness" | roadmap feature number differs from on-disk spec number; spec disambiguates in-text | Already disambiguated; expected per the naming-discrepancies memory |
| T1 | Coverage | NONE (pass) | tasks Phase 6 | every SC maps to a verification task (SC-001->T010, SC-002->T010/T013/T019, SC-003->T018, SC-004->T016/17, SC-005->T017, SC-006->T020) | No action |
| E1 | Edge coverage | NONE (pass) | spec Edge Cases vs T005/T009/T015 | all 6 edge cases resolve to a blocking_reason or a review-catches-defect rule | No action |

## Coverage Summary

| Requirement | Has Task? | Task IDs |
|-------------|-----------|----------|
| FR-001 generic metric-contract template | yes | T006, T010 |
| FR-002 required fields | yes | T007 |
| FR-003 four statuses + no score | yes | T004, T008 |
| FR-004 kpi-pack + example pack | yes | T011, T012 |
| FR-005 store layout + guide | yes | T014, T015 |
| FR-006 generic (no C086) | yes | T012, T019 |
| FR-007 no Python/CLI/rule/PBIP | yes | T018, T020 |
| FR-008 intent not DAX | yes | T007 |
| FR-009 Principle-V stop-and-ask | yes | T005, T009, T015 |
| FR-010 pass = owner evidence | yes | T008, T009, T015 |
| FR-011 resolve semantic-model-ready note | yes | T016, T017 |
| FR-012 binds_to gold only | yes | T007 |
| SC-001..SC-006 | yes | T010/T013/T018/T016-17/T020 |

Coverage: 12/12 FRs and 6/6 SCs have >=1 task (100%).

## Constitution Alignment Issues

None. The two highest-risk principles for this feature -- VIII (static-first: add NO rule/code)
and VII (generic: no C086 leak) -- each have a dedicated verification task (T018, T019).
Principle V judgment calls are surfaced as stop-and-ask blockers (FR-009), not auto-answered.

## Unmapped Tasks

None. Setup (T001-T002) and Foundational (T003-T005) feed the per-story tasks; Polish
(T018-T021) are whole-feature gates. All trace to an FR or SC.

## Metrics

- Total functional requirements: 12 (FR-001..FR-012)
- Total success criteria: 6 (SC-001..SC-006)
- Total tasks: 21 (T001..T021)
- Coverage: 100%
- Ambiguity findings: 1 (V2, LOW)
- Duplication findings: 1 (D1, LOW, intentional)
- Critical issues: 0
- Constitution violations: 0

## Next Actions

No CRITICAL or HIGH findings. The spec/plan/tasks set is internally consistent, fully covered,
and constitution-aligned. Ready to implement when desired. The LOW findings (V1, V2, I1, D1)
are cosmetic and can be absorbed during template authoring (e.g. show a single bound table to
settle V1).

## Open decision carried forward (recommended default, reversible)

- O-1 (filled-contract storage path): mappings/<table>/metrics/ per-table + top-level
  metrics/packs/ for reusable packs (ADR 0003 cohesive-per-table-working-set rationale).
  Reversible; not a blocker.

## Items explicitly LEFT for a human (Principle V -- not auto-answered)

Surfaced, never invented, when a contract is FILLED later:
- The grain a given metric is valid at (and any grain-finer-than-fact conflict).
- PII publish-safety of a bound column (governance sign-off; default drop).
- Business-rollup / segment mappings behind a metric's formula intent (analyst supplies the
  full value->group table; the agent never invents it).
