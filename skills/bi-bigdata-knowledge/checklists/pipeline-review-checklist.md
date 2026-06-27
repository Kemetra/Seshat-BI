# Distributed Pipeline Review Checklist

Artifact for reviewing a distributed BI pipeline end to end. Walk the stages, fire the
analyzer rules (`patterns/analyzer-rules.json`), and end on an analyzer-style verdict
listing which rules fired with evidence. Inherited correctness checks (fan-out, additivity)
come via `references/cross-layer-map.md`.

## How to use

For each stage, check the items; when a check fails, record the anti-pattern (`BD-AP-*`),
the analyzer rule (`BD-AR-*`) that fired, and the evidence.

## 1. Engine & architecture

- [ ] Scale-out justified by post-pruning size (BD-AP-001 / BD-AR-001).
- [ ] Storage layout serves the dominant query (BD-AP-003 / BD-AR-003).
- [ ] Pushdown to SQL/warehouse considered where applicable.

## 2. Storage & I/O

- [ ] Columnar / table format used for analytical data (BD-AP-010-adjacent / BD-ARC-005).
- [ ] Partition + column pruning verified in the plan (BD-AP-009 / BD-AR-009).
- [ ] No small-files problem in output (BD-AP-010 / BD-AR-010).

## 3. Shuffle & partitioning

- [ ] Wide steps justified; filter/project early (BD-AP-004 / BD-AR-004).
- [ ] No `coalesce(1)` to force one file (BD-AP-002 / BD-AR-002).
- [ ] Partitions right-sized; AQE enabled.

## 4. Joins & skew

- [ ] Small side broadcast where it fits (BD-AP-006 / BD-AR-006).
- [ ] Skew detected and mitigated (BD-AP-007 / BD-AR-007).
- [ ] No sum after one-to-many fan-out (BD-AP-011 / BD-AR-011).
- [ ] Key hygiene + row-count reconciliation done.

## 5. Aggregation

- [ ] Target grain declared; additivity classified.
- [ ] No non-additive measure summed (BD-AP-013 / BD-AR-013).
- [ ] Exact vs approximate distinct count labeled (BD-AP-012 / BD-AR-012).
- [ ] Before/after total reconciles.

## 6. Driver & performance

- [ ] No `collect()`/`toPandas()` on large frames (BD-AP-005 / BD-AR-005).
- [ ] No row-at-a-time UDFs for engine-expressible logic (BD-AP-008 / BD-AR-008).
- [ ] Caching deliberate and released (BD-AP-014 / BD-AR-014).

## 7. Reliability (idempotency / incremental)

- [ ] Writes idempotent (overwrite/merge), rerun leaves output unchanged (BD-AP-015 / BD-AR-015).
- [ ] Late-data lookback policy present (BD-AP-016 / BD-AR-016).
- [ ] Dedup is global on grain key (BD-AP-017 / BD-AR-017).

## 8. Validation & boundary

- [ ] Distributed control-total reconciliation, not "job succeeded" (BD-AP-018 / BD-AR-018).
- [ ] Full-dataset checks, not sample-as-proof (BD-AP-019 / BD-AR-019).
- [ ] Gate not bypassed; no metrics/semantics defined here (BD-AP-020 / BD-AR-020).

## Analyzer-style verdict

```
DISTRIBUTED PIPELINE REVIEW: <name>
rules fired:
  - BD-AR-0XX (severity) — <evidence>
  - ...
highest severity: <high/medium/low/none>
verdict: PASS | PASS-WITH-FINDINGS | FAIL
required fixes: <ordered list, highest severity first>
```

- **PASS** — no high/medium rules fired; safe to hand off.
- **PASS-WITH-FINDINGS** — only low-severity rules fired; record findings for the gate.
- **FAIL** — one or more high-severity rules fired; fix before handoff.
