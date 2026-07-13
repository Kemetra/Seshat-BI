# Aggregation / Grain Checklist (at scale)

Artifact for the distributed aggregation route. Ends on a verdict with a before/after total
reconciliation and the exact-vs-approximate decision recorded.

## A. Grain & additivity (BD-CN-042, reuses PY-CN-052/053/054)

- [ ] Target grain stated: "one row per ___".
- [ ] Each measure classified: fully additive / semi-additive / non-additive.
- [ ] No non-additive measure (ratio, %, average, distinct count) summed.
- [ ] Averages computed as weighted (numerator/denominator aggregated separately).

## B. Distributed execution (BD-CN-043, BD-CN-044)

- [ ] Aggregation expressed to allow partial/map-side combine where possible.
- [ ] No attempt to combine non-additive sub-results; recomputed at target grain.

## C. Distinct counts (BD-CN-045, BD-CN-046)

- [ ] Exact vs approximate distinct count chosen deliberately and recorded.
- [ ] Approximate used only where bounded error is acceptable.
- [ ] Distinct counts computed at target grain, not summed from subgroups.

## D. Skew & null keys (BD-CN-047, BD-CN-048)

- [ ] Group-key skew checked; hot keys handled (AQE / salt) if present.
- [ ] Null group keys handled deliberately (excluded knowingly or made explicit).

## E. Reconciliation (BD-CN-049, reuses PY-CN-058)

- [ ] Upstream fan-out ruled out.
- [ ] Additive total after groupby equals total before (distributed compute).
- [ ] Any difference explained.

## Verdict

- **AGGREGATION SOUND** — grain declared, additivity respected, distinct-count choice
  recorded, totals reconcile.
- **NON-ADDITIVE MISUSE** — a ratio/average/distinct count summed; recompute at grain.
- **APPROX MISMATCH** — approximate count shipped where exact expected; switch or disclose.
- **BLOCKED** — totals don't reconcile; cause upstream (fan-out/skew/null keys); fix there.

Attach: target grain, before/after total reconciliation, exact-vs-approximate decision.
