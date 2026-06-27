# Big-Data BI Anti-patterns

Named failure modes to flag when reviewing a distributed BI pipeline. Each maps to an
analyzer rule (`BD-AR-*`) in `patterns/analyzer-rules.json` where one exists. Use with
`checklists/pipeline-review-checklist.md`. Correctness anti-patterns inherited from the
Python layer (fan-out, summing non-additive, etc.) still apply via
`references/cross-layer-map.md`.

---

## Engine / architecture

### BD-AP-001 — Scaling out when one node would do
Reaching for Spark/cluster when post-pruning data fits Polars/DuckDB or a warehouse
pushdown. *Fix:* single-node-first; size post-pruning (BD-CN-021/022). → BD-AR-001.

### BD-AP-002 — `coalesce(1)` to force one output file
Funnels all data through one core, killing parallelism and risking OOM. *Fix:* right-size
partitions or use table-format file management (BD-CN-030). → BD-AR-002.

### BD-AP-003 — Partitioning for the load step, not the query step
On-disk layout that doesn't serve the dominant downstream operation. *Fix:* partition by
the column BI queries filter/join on (BD-CN-016/031). → BD-AR-003.

## Shuffle / partitioning

### BD-AP-004 — Unjustified wide transforms
Joins/groupbys/distinct/sorts with no attempt to filter, project, broadcast, or
pre-aggregate first. *Fix:* minimize and justify each shuffle (BD-CN-028). → BD-AR-004.

### BD-AP-009 — Reading without pruning
Filters the engine can't push down, so the job full-scans. *Fix:* make filters pushable;
verify pruning in the plan (BD-CN-032/055). → BD-AR-009.

### BD-AP-010 — Over-partitioning into tiny files (small-files problem)
Thousands of slivers crush metadata/listing. *Fix:* right-size; compact; table format
(BD-CN-052). → BD-AR-010.

## Joins / skew

### BD-AP-006 — Shuffle join where a broadcast would do
Shuffling a billion-row side against a small dimension. *Fix:* broadcast the small side
(BD-CN-035). → BD-AR-006.

### BD-AP-007 — Ignoring known skew
Letting a hot key create a straggler with no mitigation. *Fix:* AQE skew-join / broadcast /
salt (BD-CN-039). → BD-AR-007.

### BD-AP-011 — Fan-out at scale (summing after one-to-many join)
Same as `PY-AP-003` but also explodes shuffle volume. *Fix:* pre-aggregate the many-side
(`PY-CN-051`, BD-CN-009). → BD-AR-011.

## Aggregation

### BD-AP-012 — Exact distinct count everywhere by default
Heavy `COUNT(DISTINCT)` where approximate would do, or approximate where exact is required —
either way undisclosed. *Fix:* choose and label exact vs approximate (BD-CN-045). → BD-AR-012.

### BD-AP-013 — Summing non-additive measures / averaging averages at scale
Inherited correctness bug (`PY-AP-016`); also defeats partial aggregation. *Fix:* recompute
at target grain (BD-CN-044). → BD-AR-013.

## Driver / execution

### BD-AP-005 — `collect()` / `toPandas()` on a large frame
Funnels distributed data to the driver → OOM. *Fix:* inspect with distributed ops; collect
only sized, bounded results (BD-CN-073). → BD-AR-005.

### BD-AP-008 — Row-at-a-time Python UDFs for engine-expressible logic
Opaque to the optimizer; serialization overhead. *Fix:* built-in/column expressions; else
vectorized UDFs (BD-CN-074). → BD-AR-008.

### BD-AP-014 — Caching everything
Cached data starves shuffle memory → spill. *Fix:* cache only multi-use frames; unpersist
(BD-CN-075). → BD-AR-014.

## Reliability / correctness

### BD-AP-015 — Append-only writes (non-idempotent)
Reruns/backfills duplicate data. *Fix:* partition overwrite or merge-on-key; rerun test
(BD-CN-058). → BD-AR-015.

### BD-AP-016 — No late-data policy
Frozen daily totals miss or double late events. *Fix:* idempotent lookback window
(BD-CN-060). → BD-AR-016.

### BD-AP-017 — Per-partition dedup instead of global
Duplicates that span partitions survive. *Fix:* global dedup on grain key (BD-CN-017/061). → BD-AR-017.

## Validation / boundary

### BD-AP-018 — "Job succeeded" treated as reconciliation
No control totals; success ≠ correctness. *Fix:* distributed control-total parity
(BD-CN-064). → BD-AR-018.

### BD-AP-019 — Sampling passed off as full-dataset proof
"Looks fine on a sample." *Fix:* full-dataset aggregate checks; sample only supports
(BD-CN-066). → BD-AR-019.

### BD-AP-020 — Using big-data tooling to bypass the gate / define metrics
Self-approving, or encoding metric/semantic logic in the job. *Fix:* hand record to gate;
a KPI's *meaning* belongs to `retail-kpi-knowledge` and its *measure* to DAX — never define
either in a distributed job (BD-CN-069, `references/cross-layer-map.md`). → BD-AR-020.

---

### Ends on

`checklists/pipeline-review-checklist.md` — an **analyzer-style verdict** listing which
anti-patterns/rules fired, with evidence.
