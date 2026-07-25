# Validation and Reconciliation Checklist

Terminal artifact for dataframe validation before handoff.

## Contract and scope

- [ ] Input/output grain and source/profile revisions recorded.
- [ ] Expected boundary is independent of the dataframe path.
- [ ] Period, filters, exclusions, currency, precision, and null policy match.
- [ ] Tolerances were declared before observing deltas.

## Checks

- [ ] Schema and required fields match (PY-VP-005).
- [ ] Row count matches or the delta is explained (PY-VP-006).
- [ ] Output grain is unique (PY-VP-007).
- [ ] Critical keys meet null policy (PY-VP-008).
- [ ] Domains/ranges meet contracts (PY-VP-009).
- [ ] Unmatched keys reconcile to the merge verdict (PY-VP-010).
- [ ] Additive controls reconcile (PY-VP-011).
- [ ] Segment controls expose no cancelling differences (PY-VP-012).
- [ ] Null distributions have no unexplained shift (PY-VP-013).
- [ ] Date coverage/freshness matches the comparison scope (PY-VP-014).
- [ ] Repeated deterministic production yields the same artifact (PY-VP-015).

## Evidence handoff

- [ ] Each check records expected, actual, delta, tolerance, evidence source, and owner.
- [ ] Samples are labeled diagnostic only.
- [ ] The packet states that it grants no readiness (PY-VP-016).

## Verdict

Choose exactly one: **RECONCILED**, **OPEN FINDINGS**, **NOT RECONCILED**, or
**BLOCKED**. Attach one next action and destination layer.
