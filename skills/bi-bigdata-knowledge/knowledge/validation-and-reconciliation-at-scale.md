# Validation and Reconciliation at Scale

How a distributed result earns trust before handoff. The currency is the same as the
Python layer — control totals (`PY-CN-068`) — but the techniques adapt to volume: you can't
eyeball billions of rows, and you can't collect them. Schema:
`references/retail-bigdata-schema.md`.

---

## BD-CN-063 — Validation vs reconciliation (unchanged) but computed distributed

Validation = internal consistency (grain holds, keys unique, nulls accounted, ranges
plausible). Reconciliation = agreement with external truth (totals match source/SQL). The
distinction is the same as `PY-CN-067`; at scale **every check is a distributed aggregate**
(count, sum, distinct), never an inspection of collected rows (BD-CN-010).

## BD-CN-064 — Control totals are still the currency

Compute additive control totals (row count, total quantity, total revenue) on both sides as
distributed aggregates and compare (`PY-CN-068`). Equal within a declared tolerance = 
evidence. This is cheap even on huge data because additive totals use partial aggregation
(BD-CN-043). "The job succeeded" is not reconciliation; matching totals is.

## BD-CN-065 — Reconcile at each shuffle boundary

As in pandas (`PY-CN-069`), reconcile at each structural step — after load, after dedup,
after each join, after each aggregation. At scale these boundaries coincide with shuffles
and stages, so a divergence localizes to the stage where totals first break. Cheap totals
at each boundary save expensive debugging of the whole DAG.

## BD-CN-066 — Sampling complements totals; it doesn't replace them

You cannot manually inspect billions of rows, but you can:
- compute **distributed aggregate checks** over the whole dataset (the primary evidence),
  and
- **sample** a small, representative subset to eyeball row-level plausibility and spot
  shapes totals miss.

Sampling supports intuition; control totals provide the proof. Never substitute a sample's
"looks fine" for a full-dataset total (reuses the no-evidence stop rule, `PY-CN-068`).

## BD-CN-067 — Scalable data-quality checks

Express data-quality rules as distributed aggregates that scan the whole dataset cheaply:
null rate per column, distinct-count of category domains (drift), min/max ranges,
referential-integrity orphan counts, and grain uniqueness (rows vs distinct keys). Mature
setups codify these as a quality suite (Deequ-style on Spark, or expectation frameworks)
that runs in-pipeline and can pause downstream on failure — but the *reasoning* is the same
set of checks, expressed to scale. Results are findings handed to the gate, not auto-fixes.

## BD-CN-068 — Approximate checks for cheap monitoring

For continuous monitoring where small error is acceptable, approximate aggregates
(approx-distinct, sampled quantiles) give fast health signals. Use them for trend
monitoring, not for the financial reconciliation that must be exact (BD-CN-045). Record
which checks are approximate.

## BD-CN-069 — Python validates and reconciles; readiness gates

Unchanged boundary (`PY-CN-070`): this layer produces a reconciliation record (control
totals, per-stage ledger, quality-check results, unresolved findings) and hands it to the
gate. It does **not** self-approve, and big-data tooling must never be used to *skip* the
SQL/readiness validation gates (a stop rule).

## BD-CN-070 — Tolerances explicit, especially with approximation

Declare tolerances (`PY-CN-073`): zero for exact counts/keys; a small epsilon for currency
rounding; and an explicit bounded error where approximate aggregates are used. An
undeclared tolerance is how a real break gets rationalized away — more tempting at scale
where "close enough on a billion rows" feels safe.

## BD-PB-006 — Playbook: totals don't match the source at scale

1. Identify which control total diverges (rows / quantity / revenue).
2. Walk the per-stage reconciliation points (BD-CN-065) to the first divergence.
3. Inspect that stage: fan-out, skew-dropped/duplicated rows, non-idempotent rerun,
   dropped null keys, pruning that filtered too much.
4. Fix at the stage; re-run downstream; re-reconcile.
5. Record cause and resolution in the reconciliation record.
6. Verdict on `checklists/validation-reconciliation-checklist.md`.

---

### Ends on

`checklists/validation-reconciliation-checklist.md` — a **validation/reconciliation
verdict** plus the reconciliation record handed to SQL/readiness. Reusable checks live in
`patterns/validation-patterns.json`.
