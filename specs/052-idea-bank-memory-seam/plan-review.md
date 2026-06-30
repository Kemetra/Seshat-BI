# Adversarial Plan-Review: Idea-Bank Memory Seam (IL1)

**Feature**: 052-idea-bank-memory-seam | **Date**: 2026-06-30 | **Reviewer**: single default-adverse skeptic | **Mode**: read-only (reports fixes, never edits)

Preconditions for a verdict: spec.md, plan.md, tasks.md, analysis.md all present on this
branch. Verified present. analyze verdict was CLEAN (0 critical / 0 high). Proceeding.

## Axis 1 -- hidden-principle-violation

Probe: does any artifact smuggle a roadmap write, a self-promotion, a self-granted readiness
pass, or a single-owner-of-ship-status breach behind innocuous wording?

- The seam is evidence-OF-shipped: FR-003 forbids any code path writing/assigning an F-row;
  T007 asserts it and SC-002 makes it measurable. The ledger's f_row records a placement a
  human already made; "none" is first-class. No promotion path exists.
- Single-owner-of-ship-status: the Memory edit (T005) keeps git_corroborated:false and adds a
  DISK read of a curated file, not a git read. Ground stays the only git reader. The one place
  this COULD be violated -- "may the engine APPEND to the ledger?" -- is NOT designed in; it is
  recorded as an open human judgment call (spec ## Clarifications, FR-008). Correctly left to
  the human rather than silently decided.
- No self-granted readiness pass: the spec Status stays Draft; no readiness score is produced.

Verdict: clean. No hidden violation. The riskiest boundary (engine-append) is honestly parked.

## Axis 2 -- assumes-deferred-capability

Probe: does the plan lean on F016 (Power BI Execution Adapter), F031-F033 (spec-only
runtimes), a live DB, or any not-yet-built consumer?

- The consumer (idea-engine Memory stage, phase('Memory')) is VERIFIED to exist in source;
  this feature adds a third input to an existing prior_ideas[] list, not a new runtime.
- No F016/F031-F033 reference in any task. No live DB, no executor. The read is a disk read in
  an existing agent step. data-model/contract introduce no new dependency.

Verdict: clean. Buildable today against committed files.

## Axis 3 -- c086-leak

Probe: does any generic artifact carry pharmacy/C086 or sample-data specifics?

- FR-007 + data-model + contract restrict values to idea-ids, PR/SHA, F-row labels. T003
  asserts the generic-only invariant.
- The seed cites real PR SHAs (e.g. "PR #62 abbbd73") and rejection-rationale locations --
  these are GOVERNANCE identifiers (PR/commit refs, file pointers), not metric values, not
  mapping content, not pharmacy domain data. They are the correct evidence for a shipped-ledger
  and do not constitute a C086 leak.

Verdict: clean. No domain specifics; the guard test makes the invariant enforceable.

## Axis 4 -- fabricated-confidence

Probe: any invented count, fake "N+1", or asserted-without-evidence claim?

- The grounding flagged a 32/33/34 rule-count ambiguity. The artifacts reconcile to 38 (the
  live EXPECTED_RULE_IDS frozenset length, independently re-counted in analysis.md section F)
  and explicitly mark the prose "33/34" as stale.
- Because the optional rule is OUT of scope, NO "N+1" rule claim is encoded anywhere -- so the
  off-by-one cannot be inherited. Any future rule is stated as "38 -> 39 against the live
  frozenset, not prose", which is the correct guard.
- No readiness/maturity score is asserted.

Verdict: clean. The one count that mattered was verified, not assumed.

## Axis 5 -- over-scope

Probe: does the plan build more than the idea's first step?

- Idea first step = "shipped-ideas.yaml consumed by the engine Memory stage; human still rules
  promotion; add IL1 rule separately if budget allows."
- Plan/tasks deliver exactly: the yaml + the Memory read step + a guard test. The optional rule
  is explicitly OUT (FR-010, no task). The "replace the prose appendix" edit is explicitly OUT
  (left to the human scope call); the yaml sits alongside as authoritative-for-the-read -- the
  YAGNI-minimal non-destructive default.

Verdict: clean. Tightly scoped to the seam.

## Notes (non-blocking)

- N-A: The Memory stage is an LLM AGENT step, so US1's "engine labels shipped ids as
  known-history" is prompt-driven, not a deterministic unit test. The spec/quickstart correctly
  validate it by (a) a deterministic guard test on the ledger file and (b) a manual wiring/
  labeling inspection. This is an honest limitation of editing an agent prompt, not a defect;
  the deterministic guarantees (file validity, generic-only, fail-loud, no-promotion) ARE
  testable and tasked. Implementer should not over-claim a deterministic behavior test for the
  labeling itself.
- N-B: Two Principle-V markers remain open (ledger authorship; yaml-replaces-prose). These are
  intended human ratify-gate inputs, not planning gaps. The build can proceed on the
  human-curated + sits-alongside defaults; if the human rules otherwise, FR-008/FR-009 and the
  relevant tasks would need a follow-up.

## Verdict

PASS-WITH-NOTES.

All five axes clean (0 critical, 0 high). The two notes are honest limitations/open human
calls, not blockers. The spec remains Draft; ratification is a human action this workflow is
forbidden to take.
