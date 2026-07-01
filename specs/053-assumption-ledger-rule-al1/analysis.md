# Cross-Artifact Analysis: Assumption Ledger Rule (AL1)

**Feature**: `053-assumption-ledger-rule-al1` | **Date**: 2026-07-01
**Scope**: read-only consistency pass over spec.md, plan.md, tasks.md (+ research,
data-model, contracts, quickstart). No artifact edited by this pass.

## Method

Checked: (A) requirement -> task coverage; (B) terminology / convention consistency
across artifacts; (C) constitution + repo-rule alignment; (D) grounding of factual
claims against the live tree; (E) duplication / ambiguity / conflict.

## A. Requirement coverage (spec FR -> tasks)

| FR | Covered by | Status |
|----|-----------|--------|
| FR-001 new AL1 module | T005 | OK |
| FR-002 EXPECTED_RULE_IDS 33->34 | T007 | OK |
| FR-003 scan mappings/<table>/metrics/*.yaml | T005 | OK |
| FR-004 exclude template + is_test_path | T005, T009 | OK |
| FR-005 lazy yaml import | T001, T005, T010 | OK |
| FR-006 categorical, no score | T005, T011 | OK |
| FR-007 no DAX/connection | T005, T010 | OK |
| FR-008 never resolve assumption (read-only) | T004, T005 | OK |
| FR-009 ERROR on marker+binding coexistence | T003, T005 | OK |
| FR-010 fail-loud on unreadable | T004, T005 | OK |
| FR-011 no C086 literal | T003, T010 | OK |
| FR-012 no stage advance / no F016 | tasks scope guard + Out-of-scope | OK |
| FR-013 no new token (existing field) | tasks scope guard | OK |
| FR-014 ASCII/UTF-8 no BOM | T011 | OK |
| FR-015 marker = blocked+blocking_reasons | resolved (Clarif C1); T002/T005 | OK |
| FR-016 binding = filled binds_to | resolved (Clarif C2); T002/T005 | OK |
| FR-017 standalone | resolved (Clarif C3); tasks Out-of-scope | OK |

Every FR maps to at least one task. No orphan FR; no task without a spec anchor.

## B. Terminology consistency

- "unresolved-assumption marker" == `readiness.status: blocked` + non-empty
  `blocking_reasons[]` -- used consistently in spec (FR-015/C1), plan (Summary),
  research (R2/R6), data-model (marker predicate), contracts (C1/C2), tasks (T005).
- "settled measure binding" == filled non-placeholder `binds_to.gold_table` +
  non-empty non-placeholder `binds_to.columns` -- consistent across all artifacts.
- Rule id `AL1`, module `src/retail/rules/assumptions.py`, test
  `tests/unit/test_assumptions.py` -- consistent everywhere.
- Count "33 -> 34" consistent in spec (FR-002/SC-002), plan, research (R4), tasks
  (T007). No conflicting count appears.

## C. Constitution / repo-rule alignment

- Principle V: spec FR-008, plan Constitution Check, contracts C7, tasks T004/T011
  all assert AL1 reads-and-reports only, never resolves. The governance MEANINGS of
  C1/C2 are recorded to open_for_human in spec ## Clarifications -- correctly NOT
  self-answered as business rulings while the mechanical convention is fixed. OK.
- Principle VII: generic-shape-only + c086-cited-never-inlined asserted in spec
  (FR-011/SC-006), plan, research (R2/R3), tasks (T003/T010). OK.
- Principle VIII / B1 / B3: lazy yaml, no connection, no DAX -- spec (FR-005/FR-007),
  plan, research (R1), contracts, tasks (T005/T010). OK.
- ADR 0007 (L2 not L3): spec Assumptions, plan Constitution Check assert AL1 is an
  L2 @register rule adding one id, not a semantic.py L3 hook. OK.
- Rule #9 (no fake confidence): categorical-only asserted spec (FR-006), plan,
  contracts (C10), tasks (T011). OK.
- 043 snapshot + wiring test: manifest regen + firing test covered T007/T008 and the
  wiring-latent-gap obligation (research R5, contracts C8, tasks T003). OK.

## D. Grounding of factual claims (verified against the live tree)

- `EXPECTED_RULE_IDS` frozenset lists 33 ids (verified in
  `tests/unit/test_rules_wiring.py`); AL1 -> 34. CONFIRMED.
- PP1/SC1/DF1 are @register per-table-scanning rules with template exclusion + lazy
  yaml (verified `publish_pack.py`, `status_claims.py`, `parked_on.py`). CONFIRMED.
- `metric_drift.load_definition()` does an in-function lazy `import yaml`. CONFIRMED.
- `is_test_path(p)` == `p.startswith("tests/")` (verified `core.py`). CONFIRMED.
- The generic template `templates/metric-contract.yaml` has NO explicit
  open-assumption token; its open-state mechanism is `readiness.status` +
  `blocking_reasons`. CONFIRMED (grounder + template read).
- All five on-main contracts under `mappings/retail_store_sales/metrics/` are
  `status: "pass"` (verified AvgTransactionValue, DiscountedTransactionRate,
  TotalQuantity, TotalSales, TransactionCount). CONFIRMED -> the zero-AL1-findings
  baseline is GENUINE, not vacuous (SC-005 / R6 substantiated).
- `retail manifest --repo .` regenerates `docs/rules/rules-manifest.json`; the
  `manifest` subcommand exists in `cli.py`. CONFIRMED.

## E. Duplication / ambiguity / conflict

- No conflicting requirements found. FR-013 (no new token) is consistent with the
  C1 resolution (existing field), removing the earlier define-then-check gap.
- The angle-bracket placeholder test appears in both the settled-binding predicate
  (data-model) and research R2; consistent polarity with PP1/G6. No fork implied
  (Principle II) -- research R1 explicitly reuses the pattern, not a second parser.
- No ambiguous [NEEDS CLARIFICATION] markers remain in spec prose (verified). The
  only literal occurrence is a checklist line asserting none remain -- not a live
  marker.

## Findings

No critical findings. No high findings.

Optional observations (non-blocking, LOW):

- L1: The settled-binding predicate treats a `columns` list containing at least one
  non-placeholder entry as "filled" even if OTHER entries remain placeholders. This
  is a reasonable default (any real bound column = a real binding) but the exact
  rule for a partially-placeholder `columns` list could be stated explicitly in the
  rule docstring at build time. Not a spec defect.
- L2: FR-016's placeholder detection relies on the `<...>` convention holding in
  `binds_to.gold_table`; a contract that fills `gold_table` with a real value but
  leaves `columns` empty is (correctly) NOT bound. Covered by C2; the empty-columns
  case is exercised by T004.

## Verdict

**analyze = clean** (0 critical, 0 high). Artifacts are internally consistent,
fully cross-referenced, grounded against the live tree, and constitution-aligned.
Two LOW observations are implementation notes, not blocking defects.
