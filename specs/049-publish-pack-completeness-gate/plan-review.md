# Adversarial Plan-Review: Publish-pack completeness gate (PP1)

A single default-adverse skeptic over `spec.md`, `plan.md`, `tasks.md`, `analysis.md`
(read-only; fixes are reported, never applied). Prerequisite artifacts all present
(spec + plan + tasks + analysis + contracts/data-model/research). Five axes below.

## Axis 1 -- Hidden principle violation

- Principle V (the most-scrutinized axis): the rule's approval contract is asserted
  three times consistently (spec FR-006, plan Constitution Check, contract C8) as
  presence-and-non-placeholder ONLY, with explicit "never read owner/date/legitimacy,
  never write an approval." T012 tests it. The readiness-stage assignment and the
  boundary confirmation are NOT answered by the workflow -- recorded under "Open for
  human." VERDICT: no violation; the judgment call is correctly stopped at.
- Principle II: the reuse seam is fixed in research.md (lift G6's one-line pattern
  into a shared helper, or import it; either way no second parser). A skeptic notes
  option (B) edits `g6.py` to import from a new shared helper -- this is a real touch
  on a shipped rule. Mitigation already present: research.md states G6's behavior is
  unchanged (identical pattern) and the wiring/snapshot tests guard it; implement-time
  must keep G6 green. Recorded as NOTE N1, not a finding.
- Anti-fabricated-confidence: the rule emits Findings only, no score; FR-014/T015
  forbid self-granting a stage. No violation.

## Axis 2 -- Assumes deferred capability

- The spec/plan/research explicitly disclaim dependence on F016 (Power BI execution
  adapter), F031-F033 (spec-only runtimes), a live DB, and spec 041 (Publish Approval
  Receipt). The Session 2026-06-30 clarification resolves receipt-presence to an
  OPTIONAL, out-of-first-step check -- so the build does NOT assume the receipt
  exists. VERDICT: no deferred-capability assumption.

## Axis 3 -- C086 leak

- The rule keys off the GENERIC template's required-section index + placeholder/GAP
  convention; FR-007/SC-006/C10 forbid any specific table/column/KPI/PII rule. The
  four MANDATORY caveats are explicitly NOT decomposed (which would risk encoding
  c086's PII/returns/-1-row specifics). Fixtures are synthetic generic packs; c086 is
  cited by reference only (and has no `mappings/c086/handoff/` dir to inline from).
  T013 asserts genericity. VERDICT: no c086 leak.

## Axis 4 -- Fabricated confidence

- No readiness score, health number, or invented metric anywhere. The two advisor
  recommendations (required-section set; severity=ERROR) are presented AS reversible
  recommendations grounded in named precedent (G6/B1/B3) and the template's own
  "cannot reach complete" language -- not as settled fact. The coverage/metrics in
  analysis.md are mechanical counts (14 FR, 15 tasks, 100% mapped), not a confidence
  claim. VERDICT: no fabricated confidence.

## Axis 5 -- Over-scope (YAGNI)

- Scope is one rule module + one constant + the wiring-id update + regenerated
  manifest + tests. Explicitly OUT: per-caveat decomposition, receipt dependency, any
  new stage/severity tier, any production-artifact write. The tasks guard rail
  restates this. A skeptic flags US2 (missing-section) + US4 (approval boundary) as
  potential scope creep beyond the MVP US1 -- but both are minimal extensions of the
  same single checker (presence is a precondition of "filled"; the approval slot is
  one of the six required sections), not new machinery. Recorded as NOTE N2, not a
  finding. VERDICT: in scope.

## Notes (non-blocking)

- N1: Implement-time must keep `G6` green if the shared-helper reuse seam (research.md
  option B) is chosen; the 043 snapshot + wiring tests are the guard. Verify `retail
  check` stays green on the current tree.
- N2: US2/US4 are minimal extensions of the single US1 checker, not separate features;
  they keep the MVP boundary intact.
- N3 (carried, not a finding): the registry id `PP1`, the final required-section-set
  membership, the severity posture, AND the readiness-stage/roadmap-provenance row are
  all CONFIRMED at the human ratify gate. The workflow recorded recommendations for the
  first three (reversible) and left the Principle-V stage/boundary items unanswered.

## Verdict

PASS-WITH-NOTES. All required artifacts present (spec, plan, tasks, analysis,
contracts, data-model, research). analyze = clean (0 critical, 0 high). No
hidden-principle-violation, no assumes-deferred-capability, no c086-leak, no
fabricated-confidence, no over-scope finding. Three non-blocking notes (N1-N3) and
the recorded ratify-gate confirmations carry into the human ratify decision.
