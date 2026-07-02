# Adversarial Plan-Review: Seed-Layer Route Honesty Rule (067)

**Date**: 2026-07-02 | **Reviewer**: single default-adverse skeptic (read-only;
reports fixes, does not edit) | **Artifacts**: spec.md, plan.md, tasks.md, analysis.md

Preconditions checked: analyze ran (analysis.md present, verdict clean), tasks.md
present, plan.md present. A draft missing analyze or tasks would be automatic
BLOCKED -- neither is missing.

## Axis 1 -- Hidden principle violation

- **Principle V (agent stops at judgment calls)**: The seed -> built promotion
  criterion is the one genuine judgment call, and it is correctly REFUSED: FR-016 is a
  live `[NEEDS CLARIFICATION]`, the carve-out is recorded, and T018 forces the
  implementer to CONFIRM no promotion logic is coded. I probed for a smuggled default
  (e.g. "a seed target with N children auto-becomes built") -- none exists in spec,
  plan, or tasks. PASS.
- **Principle VIII (static-first)**: verification is file-existence only; lazy yaml
  preserved (FR-010, T016). No probe of surface CONTENT completeness is proposed --
  which would be the tempting over-reach. PASS.
- No hidden violation found.

## Axis 2 -- Assumes deferred capability

- No dependence on F016 (Power BI Execution Adapter) or F031-F033 runtimes; FR-014 +
  T018 explicitly forbid it. The rule is a stdlib static check over committed YAML. The
  feature does not assume any unshipped seam: `_VALID_STATUS`, `check_routes_resolve()`,
  A3, `EXPECTED_RULE_IDS`, the severity fixture all EXIST today (verified). PASS.

## Axis 3 -- C086 leak

- FR-013 + T017 require a grep audit for pharmacy/C086 literals in the rule, the
  manifest edit, and fixtures. The spec cites the KPI-contract `Seeded` vocabulary and
  the knowledge-map "initial seed" prose as EXTERNAL declared facts, not as baked
  fixtures. Residual risk (flagged, not a defect): the implementer must ensure the new
  test fixtures use GENERIC route ids/paths, not a real retail-kpi contract path -- the
  grounding's stated c086_risk. T017 covers this; keep it a hard gate at build time.
  PASS with note.

## Axis 4 -- Fabricated confidence

- No numeric readiness/confidence score is asserted anywhere; the rule is categorical
  (FR-012) and the spec Status stays "Draft" (confirmed -- no "Ratified" line was
  written). analysis.md's "clean" verdict is backed by a real coverage matrix and
  tree-verified facts (A3 has zero `status` refs; the routes.py seam matches), not an
  unbacked assertion. The one Low finding (L1) is honestly surfaced rather than
  glossed. PASS.

## Axis 5 -- Over-scope

- This is the axis most worth pressing, and the spec DEFENDS well: C4/FR-008 and the
  tasks "Out of scope" block explicitly exclude a new rule id, the 5-place wiring seam,
  manifest/golden regen, the SC1 third-state change, and any executor. The change is a
  one-value `frozenset` widening + one loop arm + one manifest comment + tests. I could
  find no scope creep. If anything the cut is aggressively minimal -- correct for YAGNI.
  PASS.

## Residual notes (non-blocking)

- **N1 (build-time)**: T017 fixture-genericity is the single highest residual risk
  (C086 leak via a real contract path in a fixture). It is covered by a task but
  depends on implementer discipline; keep it a hard check.
- **N2 (soft ordering)**: tasks note Phase 4 (manifest doc) ordering vs Phase 3 is
  "soft" -- correct, since the manifest comment does not itself change a live route
  status. No risk.
- **N3 (open carve-out)**: FR-016 remains open by design. A human must eventually rule
  the promotion criterion; until then no route should be promoted seed -> built. This
  is correctly a human gate, not a drafting gap.

## Verdict

Verdict: PASS-WITH-NOTES

All five axes pass. The Principle-V promotion criterion is correctly refused and left
open (build-safe), scope is minimal and explicitly bounded, no deferred capability is
assumed, and the only material residual (C086 leak via fixtures, N1) is covered by a
build-time task. Not a clean PASS solely because N1 depends on implementer discipline
at build time and FR-016 stays open for a human ruling -- both intended, neither
blocking. No critical or high finding.
