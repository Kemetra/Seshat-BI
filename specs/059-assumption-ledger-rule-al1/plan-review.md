# Adversarial Plan-Review: Assumption Ledger Rule (AL1)

**Feature**: `053-assumption-ledger-rule-al1` | **Date**: 2026-07-01
**Reviewer stance**: single default-adverse skeptic, READ-ONLY (reports fixes,
edits nothing). Artifacts reviewed: spec.md, plan.md, tasks.md, analysis.md, plus
research.md, data-model.md, contracts/rule-contract.md, quickstart.md.

**Precondition check**: spec + plan + tasks + analysis all present; analyze verdict
is clean (0 critical / 0 high). Not an automatic BLOCKED.

## Axis 1 -- hidden-principle-violation

Probe: does AL1 quietly RESOLVE a Principle-V judgment call rather than surface it?

- AL1's marker is the EXISTING `readiness.status: blocked` + `blocking_reasons`
  state; the rule only READS it and emits an ERROR when a filled `binds_to`
  coexists. No code path writes, clears, resolves, or auto-answers the assumption or
  the readiness state (spec FR-008, contracts C7, tasks T004/T005). It fails closed.
- The DECISION "a blocked+bound contract is an ERROR" is a governance ruling. It is
  made as an advisor DEFAULT and its governance MEANING is recorded to open_for_human
  (spec ## Clarifications) for optional human override -- not silently baked as
  settled truth. This is the correct Principle-V posture: fix the mechanical
  convention so the rule is buildable, defer the business meaning to a human.
- No grain / PII / rollup / product-identity call is answered anywhere.

Verdict: no violation.

## Axis 2 -- assumes-deferred-capability

Probe: does any artifact assume an unshipped capability exists?

- FR-017 / Clarif C3 explicitly resolve AL1 as STANDALONE, NOT gated on the unshipped
  T1.2 define-half. Because the marker is an existing field, no unshipped DEFINE
  artifact is required.
- No DAX evaluation, no DB/network/Power BI connection, no F016, no F031-F033, no
  live runtime (spec FR-007/FR-012, plan Constitution Check, tasks Out-of-scope).
- The 043 manifest + wiring test + `retail manifest` CLI are VERIFIED present, not
  assumed.

Verdict: no assumed deferred capability.

## Axis 3 -- c086-leak

Probe: any pharmacy/C086 specific baked into a generic artifact?

- The rule keys only on the generic contract SHAPE (`readiness.status`,
  `blocking_reasons`, `binds_to.gold_table`/`columns`). No `retail_store_sales`
  path, no `DiscountedTransactionRate`/`gold.fct_sales_rss`, no Q2 discount ruling
  in the rule (spec FR-011, data-model, tasks T003/T010).
- Fixtures use generic labels (`mappings/demo_table/metrics/DemoMetric.yaml`).
- The on-main baseline check names `mappings/retail_store_sales/metrics/` only as the
  EXISTING instance set to verify a genuine pass -- it is CITED, not inlined into the
  rule (Principle VII). tasks T010 greps the module for leaks as a gate.

Verdict: no leak. (Watch item for the implementer: keep the docstring's C086
reference a citation, never a hard-coded path in code.)

## Axis 4 -- fabricated-confidence

Probe: any invented number, score, or unearned certainty?

- Count 33 -> 34 is verified against the in-tree `EXPECTED_RULE_IDS` frozenset, and
  the wiring test keys off set LENGTH, not a literal (research R4, analysis D).
- No numeric readiness/confidence score anywhere (spec FR-006, contracts C10, tasks
  T011).
- The "genuine (not vacuous) zero-findings baseline" claim is SUBSTANTIATED: all five
  on-main contracts are `status: "pass"` (verified), so none present the blocked+bound
  contradiction -- the pass is earned by a checked convention over a real tree, not by
  an absent convention (analysis D, research R6).

Verdict: no fabricated confidence.

## Axis 5 -- over-scope

Probe: is the plan bigger than a one-rule first step?

- Deliverables: one new module `src/retail/rules/assumptions.py`, one new id in
  `EXPECTED_RULE_IDS`, the regenerated manifest, one new test file. This is exactly
  the PP1/SC1/DF1 sibling scope.
- No new marker token, no template edit, no committed-contract edit, no readiness
  write, no new dependency/executor/severity tier (tasks scope guard + Out-of-scope).
- Because C1 keys on the EXISTING field, the earlier define-then-check DEFINE step
  (a template edit) is CORRECTLY dropped -- this shrinks scope rather than expanding
  it, and closes the define-then-check gap.

Verdict: correctly scoped.

## Notes / carry-forward

- Two LOW observations from analysis.md (partial-placeholder `columns` handling;
  empty-columns case) are implementation-docstring notes, not spec defects -- T004
  already exercises the empty/placeholder-columns case.
- open_for_human (non-blocking): the governance MEANINGS of C1 ("a blocked contract
  == an unresolved assumption") and C2 ("blocked-and-bound is always a defect"). A
  human may confirm or override at the ratify gate without re-planning; the build
  proceeds on the advisor default.

## Verdict

**Verdict**: PASS-WITH-NOTES

**PASS-WITH-NOTES.** All five axes clear. Artifacts are present, consistent,
grounded, and constitution-aligned; analyze is clean. The only carry-forwards are
two LOW implementation notes and two non-blocking open_for_human governance meanings.
No CRITICAL or HIGH finding. Not overriding anything; no retry performed.
