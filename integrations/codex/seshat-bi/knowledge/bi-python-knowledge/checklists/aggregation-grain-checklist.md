# Aggregation / Grain Checklist

Artifact for the groupby/aggregation route. Ends on a verdict with a before/after total
reconciliation.

## A. Grain declaration (PY-CN-052, PY-CN-059)

- [ ] Current grain stated.
- [ ] Target grain stated as "one row per ___".
- [ ] Group keys = the target grain (no mixed-grain result).

## B. Additivity (PY-CN-053, PY-CN-054)

- [ ] Each measure classified: fully additive / semi-additive / non-additive.
- [ ] No non-additive measure (ratio, %, average, distinct count) is summed.
- [ ] Averages computed as weighted (numerator and denominator aggregated separately).
- [ ] Semi-additive measures not summed across the forbidden dimension (usually time).

## C. Counting semantics (PY-CN-055, PY-CN-056)

- [ ] Correct counter chosen: size vs count vs nunique.
- [ ] "Number of orders" uses nunique(order_id), not row count.
- [ ] Distinct counts computed at the target grain, never summed from subgroups.

## D. Null keys (PY-CN-057)

- [ ] Null group keys handled deliberately (excluded knowingly, or made an explicit
      "Unknown" group).

## E. Reconciliation (PY-CN-058)

- [ ] Upstream fan-out ruled out (merge checklist passed).
- [ ] Additive measure total after groupby equals total before groupby.
- [ ] Any difference explained.

## Verdict

- **AGGREGATION SOUND** — grain declared, additivity respected, counts correct, totals
  reconcile.
- **NON-ADDITIVE MISUSE** — a ratio/average/distinct count was summed; recompute at the
  target grain.
- **GRAIN UNCLEAR** — target grain not stated; stop and declare it.
- **BLOCKED** — totals don't reconcile and cause is upstream (fan-out/filter); fix there.

Attach: target grain sentence + before/after total reconciliation.
