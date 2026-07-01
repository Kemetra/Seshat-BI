# Adversarial Plan-Review: 061-wiring-meta-gate

**Reviewer stance**: single default-adverse skeptic. Read-only; findings only, no
edits. Five axes: hidden-principle-violation, assumes-deferred-capability,
c086-leak, fabricated-confidence, over-scope.

**Date**: 2026-07-02

**Artifacts present**: spec.md, plan.md, tasks.md, research.md, data-model.md,
contracts/meta-gate-contract.md, analysis.md. (A draft missing analyze or tasks
is auto-BLOCKED; none are missing here.)

## Axis 1 -- Hidden principle violation

- **PASS**. The design reads committed text + the in-process registry object and
  executes nothing (no DB/network/Power BI/DAX/agent), honoring Principle VIII.
  The posture cross-check reads the committed golden statically rather than
  re-observing (which would inherit severity_posture.py's version-control
  subprocess) -- a deliberate, correct choice recorded in research Decision 2. The
  contract is a fail-closed test with no advisory-only mode (Principle I,
  FR-007). Determinism/UTF-8/BOM/MAX_PATH addressed (Principle IX, FR-013).
- **Minor note (not a finding)**: the meta-gate imports `EXPECTED_RULE_IDS` from
  a sibling TEST module (`tests/unit/test_rules_wiring.py`), a test-to-test
  import. This is acceptable (that constant is the designated single source of
  truth and is only reachable from tests), but the implementer must import it, not
  re-declare it, or the meta-gate would create a SIXTH copy of the id set --
  defeating its own purpose. Called out so implement does not fork the constant.

## Axis 2 -- Assumes deferred capability

- **PASS**. Nothing depends on F016 (Power BI Execution Adapter) or F031-F033
  (spec-only runtimes). Every seam the meta-gate reads (registry.all_rules, the
  rules package __all__/imports, EXPECTED_RULE_IDS, rules-manifest.json,
  severity-posture.json, ADR-0007) was confirmed present on disk in this worktree.
  The feature is fully satisfiable with today's static artifacts.

## Axis 3 -- c086 / example-domain leak

- **PASS**. The meta-gate references only generic registry infrastructure. It
  plants NO domain fixtures (unlike severity_posture.py). Verified: the one
  non-registered surface it exempts is `L3:verdict_to_finding` (a governance
  surface, not a domain token), confirmed by reading docs/rules/severity-posture.json.
  FR-014 forbids example-domain identifiers and T021 verifies it. No pharmacy /
  c086 / retail_store_sales token is required or introduced.

## Axis 4 -- Fabricated confidence

- **PASS (claims verified against source)**. Two load-bearing claims were checked
  against the actual repo rather than taken from the seed:
  1. "ADR-0007 says the L3 surface adds no EXPECTED_RULE_ID" -- CONFIRMED:
     docs/decisions/0007-dax-governance-layers.md lines 64-65 state L3 is
     explicitly NOT registered and NOT added to EXPECTED_RULE_IDS.
  2. "The posture golden carries exactly one non-registered surface keyed
     L3:verdict_to_finding" -- CONFIRMED by parsing the JSON (top-level keys
     `l3` + `registered`; l3 = {"L3:verdict_to_finding": ...}).
- The spec asserts NO readiness score and grants NO readiness pass. Counts cited
  (40 ids, 16 submodules, one non-registered surface) match the live files.
- **LOW annotation (not blocking)**: spec/quickstart cite "40 registered ids" and
  "16 on-disk submodules" as of today. These are live-moving numbers; because the
  meta-gate keys every check off the LIVE registry and never hard-codes a count
  (mirroring the existing test's `len(EXPECTED_RULE_IDS)` discipline), the prose
  numbers are illustrative only and will not rot the gate. Implement must keep the
  no-hard-coded-count discipline (already stated in tasks T015-T016).

## Axis 5 -- Over-scope

- **PASS**. Exactly one new file (tests/unit/test_wiring_meta_gate.py); no src
  change, no new golden file, no new @register rule, no new EXPECTED_RULE_ID. The
  ADD-not-REPLACE decision (Clarifications) keeps the three existing per-place
  tests intact, so no working guard is deleted in this change. YAGNI honored:
  consolidation and roadmap-row assignment are explicitly out of scope. Task count
  (22) is proportionate to seven checks x (RED/GREEN/live) plus polish.

## Open item returned to the human (not build-blocking)

- Whether a governance-internal wiring meta-gate earns a lettered roadmap
  governance row (A/B/SC/DF family) or stays test-only with no roadmap row. It
  maps to no data-readiness stage and no F-number. Recorded in spec Assumptions +
  Out of Scope; does not block the build. The build can proceed either way.

## Verdict

Verdict: PASS

All five axes clear. Analyze was clean (0 critical / 0 high). The two
load-bearing external claims (ADR-0007 exemption; posture surface key) were
independently verified against the repo, not assumed. The one behavioral risk
(re-declaring vs importing EXPECTED_RULE_IDS) is called out for implement and is
already implied by tasks T011. No CRITICAL uncertainty. Ready for human
ratification.
