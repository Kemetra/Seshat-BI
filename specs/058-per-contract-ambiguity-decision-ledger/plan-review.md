# Adversarial Plan Review: Per-Contract Ambiguity Decision Ledger

**Date**: 2026-07-01 | **Branch**: `058-per-contract-ambiguity-decision-ledger`
**Reviewer stance**: single default-adverse skeptic, read-only. Reports fixes; edits nothing.
**Inputs reviewed**: spec.md, plan.md, tasks.md, data-model.md,
contracts/ambiguity-ledger.schema.md, quickstart.md, analysis.md.

**Precondition check**: analyze ran (analysis.md present, clean); tasks present (13 tasks).
Neither auto-BLOCKED condition holds.

## Axis 1 -- Hidden principle violation

Tested: does any artifact let the agent self-grant a ruling, emit fake confidence, or drift
the verbatim boundary/readiness text?

- Agent records-not-invents is stated in spec (FR-004), plan (Principle I), data-model, and
  contract. An undecided material ambiguity is an unclearable block. No self-grant path.
- No numeric confidence field anywhere (FR-005; verified 0 score/confidence fields in authored
  artifacts). PASS.
- The sibling-block decision (FR-017) is specifically chosen to AVOID drifting the verbatim
  readiness block; T003/T004 instruct keeping the readiness text and boundary text unchanged.
- Verified against the repo: the store guide's "no more ready than its least-ready contract"
  sentence genuinely exists (metric-contract-store.md:97), so FR-009's "confirm, do not invent"
  is truthful, not a fabricated seam.

No hidden violation found.

## Axis 2 -- Assumes a deferred capability

Tested: does the plan lean on the enforcing CHECK rule, a Power BI model read, an execution
adapter, or live data?

- The enforcing static CHECK rule (AL1) is confirmed a SEPARATE, unbuilt idea-backlog entry
  (idea-backlog.md, "Assumption Ledger Rule (AL1)"). The spec/plan/tasks explicitly exclude it
  (FR-010; tasks "Out of scope"); the blocker is called a human-honored convention, not an exit
  code, consistently.
- No `powerbi/` read, no execution adapter, no live data referenced as a dependency. FR-010
  and T011 verify the negative.

No deferred-capability assumption found.

## Axis 3 -- C086 / domain leak

Tested: does any generic artifact inline a pharmacy/C086-specific ambiguity ruling?

- Motivating example is the generic retail-store-sales discounted-transaction-rate case
  (FR-012), which is verified real in the repo (0007 ADR + retail-kpi-catalog.md). C086 is
  cited, never inlined (FR-007). T010 verifies.

No leak found.

## Axis 4 -- Fabricated confidence

Tested: does the spec claim certainty (readiness pass, resolved judgment) it has not earned?

- The four Principle-V carve-outs (headline-moving criterion, roadmap placement, per-ruling
  correctness, decision-status vocabulary pick) are RECORDED, not answered -- 2 remain as
  [NEEDS CLARIFICATION] markers on FR-013/FR-014 and all 4 sit in ## Clarifications. The
  Status line stays "Draft". No fabricated ratification.
- The three advisor-resolved items (Q1/Q2/Q3 -> FR-015/16/17) are DESIGN decisions (schema
  shape/placement), correctly distinguished from business judgment; each is labeled reversible.
  Reasonable, not overreaching.

No fabricated confidence found.

## Axis 5 -- Over-scope

Tested: does the plan build more than the first-step seam?

- Scope is two existing artifacts extended in place (template block + store-guide prose) plus a
  confirmation of existing rollup. No new module, no file strictly required beyond spec-dir
  design docs. YAGNI respected: "add the seam, not the implementation."
- No task builds a check, a runtime, or a filled contract. T003+T004 batched on one file
  (edit-round discipline). PASS.

No over-scope found.

## Low notes (non-blocking)

- **N1**: The decision-status vocabulary is deferred (FR-006), so the authored template must
  present BOTH candidate vocabularies without silently committing to one. If the implementer
  picks one, that would quietly pre-empt a human carve-out. T003/T013 already guard this;
  flagged so the implementer does not "helpfully" resolve it.
- **N2**: FR-010 is a MUST-NOT constraint with only negative verification (T011). Correct, but
  the implementer should resist adding even a "harmless" example check rule -- that would breach
  the DEFINE-only boundary.
- **N3**: The verbatim idea title retains "A1-A10" in the spec title/Input line (by
  instruction) while all substance uses A1..A11. Intentional and documented; noted only so a
  future reader does not "correct" the title and lose provenance.

## Verdict

**Verdict**: PASS-WITH-NOTES

**plan_review_verdict: PASS-WITH-NOTES**

All five adversarial axes pass. Three low, non-blocking notes recorded for the implementer.
The artifact set is DEFINE-only, scope-bounded, principle-aligned, assumes no deferred
capability, and leaks no domain specifics. analyze was clean (0 critical / 0 high). The four
Principle-V carve-outs remain correctly reserved for a human; Status stays Draft pending human
ratification.
