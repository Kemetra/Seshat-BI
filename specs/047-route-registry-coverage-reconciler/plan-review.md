# Adversarial Plan-Review: Route-Registry Coverage Reconciler (A3)

**Reviewer posture**: single default-adverse skeptic. READ-ONLY -- findings name
fixes, never edit. Five axes: hidden-principle-violation, assumes-deferred-capability,
c086-leak, fabricated-confidence, over-scope. Generated 2026-06-30 (stage 6).

**Inputs reviewed**: spec.md, plan.md, tasks.md, research.md, data-model.md,
contracts/a3-rule-contract.md, analysis.md. All present (analyze + tasks both
exist, so the auto-BLOCKED condition does not apply).

## Axis 1 -- Hidden principle violation

- Probed: does A3 secretly execute, open a connection, or import a DB/network lib at
  module scope (B1 would flag it), or write to either source doc?
- Finding: NO violation. The plan, contract, and data-model all pin A3 as a pure
  (ctx)->findings function with a lazy in-handler `import yaml` and a hand-rolled
  stdlib map parse; both sources are read-only; nothing is executed. Verified the
  shipped A1 sibling uses exactly this shape, so the pattern is proven, not aspirational.
- Probed: does adding A3 silently break the wiring symmetry the project was bitten by?
- Finding: NO. T017 adds "A3" to EXPECTED_RULE_IDS in the same change; the wiring
  test keys its count to len(EXPECTED_RULE_IDS), so 33->34 follows. Verified the live
  test holds 33 today. The G6-class trap is explicitly closed.
- Verdict: PASS.

## Axis 2 -- Assumes a deferred capability

- Probed: does any artifact lean on F016 (Power BI execution adapter) or the
  spec-only live runtimes (F031-F033), or on the deferred `retail validate` live run?
- Finding: NO. A3 is a static read of two committed text files. plan Technical
  Context explicitly states "No deferred runtime is assumed." The gate-run task (T021)
  uses only `retail check` / `retail semantic-check` / `pytest` / `ruff` -- all
  shipped surfaces. The live guard (T019) shells `git ls-files`, not a database.
- Verdict: PASS.

## Axis 3 -- C086 / pharmacy leak

- Probed: any pharmacy/billing/segment/PII/table-name specific in spec, plan, tasks,
  contract, or proposed fixtures?
- Finding: NO leak. All ids used as examples are abstract ("1", "2", "12a", "17d",
  "99"). FR-012 + the contract's generic-message clause + T022's final leak-sweep
  enforce it. Re-verified the real map/manifest id set is purely structural route
  numbers; no example route VALUE is read by the rule. Residual risk: an implementer
  could hard-code an example route value in a fixture -- T022 is the catch; TDD review
  must hold the line.
- Verdict: PASS (with the standing T022 guard noted).

## Axis 4 -- Fabricated confidence

- Probed: does any artifact assert a readiness pass, a numeric score, or trust the
  synthesis's "already 34" baseline?
- Finding: NO fabrication. Spec Status stays "Draft" (not Ratified). The 33->34
  baseline is stated as ground-truth-verified and the synthesis "34" is explicitly
  distrusted in spec Assumptions, research R6, and tasks T002. No confidence number is
  invented. SC-001 ("zero findings on main") is independently verified true: I
  re-checked the live map id set == manifest id set (both = {1-22, 12a/b/c, 17a-d}),
  so the clean-on-main claim is fact, not optimism.
- Verdict: PASS.

## Axis 5 -- Over-scope (YAGNI)

- Probed: does the plan build past the idea's verbatim first step?
- Finding: NO over-scope. Scope is exactly: one rule, one test file, the
  EXPECTED_RULE_IDS bump, the __init__ wiring, one roadmap ledger row. The two
  widening temptations are explicitly DEFERRED, not built: (a) COMPASS fast-routing
  reconciliation is parked under Clarifications with a "Route by task only" v1 default;
  (b) intra-source duplicate detection is declared out of scope. Both are recorded as
  reversible, not silently dropped.
- One watch-item (not a finding): the new submodule (vs folding into routes.py) adds a
  second file and an __init__ edit. The plan justifies this (different source, focused
  rule, pkgutil-discovery). Defensible; not over-scope.
- Verdict: PASS.

## Principle-V human-ratify carve-outs (recorded, not resolved)

Three governance-posture questions are OPEN by design and reserved for the human
ratify gate -- the workflow is structurally forbidden to answer them:

1. Roadmap stage ownership (advisor default: outside the 7-stage spine, no stage).
2. Bijection scope -- "Route by task" only vs also COMPASS (advisor default: task-only).
3. Severity posture -- ERROR both directions vs one-direction WARNING (advisor
   default: ERROR-both, matching A1; aligns with the severity-posture-lock work).

Each default is reversible with a localized edit. They do NOT block the build; they
block RATIFICATION until a human rules.

## Overall verdict: PASS-WITH-NOTES

All five adversarial axes PASS. No CRITICAL, no HIGH. The notes are: (1) the three
Principle-V posture questions must be ruled on by a human at the ratify gate before
implementation proceeds on anything other than the recorded defaults; (2) the
generic-only invariant rests on TDD discipline at fixture-authoring time (T022 is the
backstop). The spec remains Status: Draft; no readiness pass is self-granted.
