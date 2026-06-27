# Validation / Reconciliation Checklist (at scale)

Artifact for the validation route and the pre-handoff gate input. Ends on a verdict plus a
reconciliation record. Patterns: `patterns/validation-patterns.json`.

## A. Internal validation, distributed (BD-CN-063, BD-CN-067)

- [ ] Grain uniqueness holds globally (BD-VP-002) — duplicates can hide across partitions.
- [ ] Null rates per column computed as distributed aggregates.
- [ ] Category-domain drift checked via distinct-count.
- [ ] Value ranges plausible; out-of-range flagged.
- [ ] No checks performed by collecting rows to the driver.

## B. Reconciliation to external truth (BD-CN-064, BD-CN-065)

- [ ] Row-count parity vs source (BD-VP-001).
- [ ] Control totals (quantity, revenue) match source and/or SQL (BD-VP-003).
- [ ] Reconciliation done at each stage/shuffle boundary.
- [ ] Aggregation conservation holds (BD-VP-004); join row-count reconciles (BD-VP-005).

## C. Scale-specific (BD-CN-045, BD-CN-057, BD-CN-066)

- [ ] Distinct counts labeled exact vs approximate, with error bound (BD-VP-007).
- [ ] Idempotency rerun check passed (BD-VP-006).
- [ ] Partition pruning verified (BD-VP-009).
- [ ] Sampling used only to support intuition, not as proof.

## D. Tolerances & evidence (BD-CN-070)

- [ ] Tolerances declared (0 for counts/keys; epsilon for currency; bound for approx).
- [ ] Every reconciliation carries numeric evidence (expected, actual, delta).

## E. Handoff (BD-CN-069)

- [ ] Reconciliation record assembled (totals + per-stage ledger + quality results + findings).
- [ ] Record handed to SQL/readiness; this layer does not self-gate.
- [ ] Big-data tooling not used to bypass any validation gate.

## Verdict

- **RECONCILED** — distributed checks pass, totals agree within declared tolerance, rerun
  idempotent; record attached for the gate.
- **DISCREPANCY** — a control total diverges; localize via stage reconciliation and fix.
- **FINDINGS OPEN** — valid but quality/integrity violations exist; hand to gate with counts.
- **NOT RECONCILED** — no full-dataset evidence (only a sample / job-succeeded); cannot
  claim pass (stop rule).

Attach: reconciliation record (control totals, per-stage ledger, quality results, findings).
