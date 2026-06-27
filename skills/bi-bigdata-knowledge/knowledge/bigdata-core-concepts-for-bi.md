# Big-Data Core Concepts for BI

Scope: the minimum distributed-compute vocabulary a BI agent needs to reason safely about
data too large for single-node pandas. Not a Spark course — only the ideas the rest of the
skill assumes. Engine-independent correctness concepts (grain, fan-out, additivity) are
**borrowed** from `bi-python-knowledge` via `references/cross-layer-map.md`.

---

## BD-CN-001 — Distributed means the data is split across machines

A distributed dataframe is one logical table physically split into many **partitions**
spread across executors. No single machine holds the whole table. Every correctness and
performance question becomes "what happens *across partitions*?" This is the central
mental shift from pandas, where the whole frame sits in one process.

## BD-CN-002 — Scale-out is a cost, not a default (single-node first)

Distributing work adds overhead: serialization, network shuffle, scheduling, cluster cost.
For data that fits on one machine — including large data via Polars/DuckDB streaming — a
single node is faster, cheaper, and simpler. **Best practice (BD-BP-003): prove the
workload needs scale-out before reaching for it.** The first question is always "does this
actually not fit on one (big) machine?" See `engine-selection.md`.

## BD-CN-003 — Lazy execution: you build a plan, not a result

Most distributed engines (Spark, Polars lazy, Dask) are **lazy**: transformations build a
plan (a DAG); nothing runs until an **action** triggers it. Two consequences for BI:
- You reason about a *plan*, and the engine may reorder/optimize it (e.g. Spark's AQE).
- An expensive mistake is invisible until the action fires — so reasoning about the plan
  *before* triggering it matters more than in eager pandas.

## BD-CN-004 — Partition: the unit of parallelism

A **partition** is a chunk of rows processed by one task on one core. Partition count and
size set the parallelism and the memory each task needs. Too few/large → spills and OOM;
too many/small → scheduling overhead and the small-files problem. Partitioning is the lever
behind most big-data performance reasoning (`partitioning-and-shuffle.md`).

## BD-CN-005 — Partition is not grain

A partition is a *physical* chunk; **grain** (`PY-CN-007`) is the *logical* meaning of a
row. Repartitioning never changes grain; aggregation changes grain regardless of
partitioning. Confusing the two leads to wrong reasoning ("I repartitioned, so duplicates
are gone" — false). Keep physical (partition) and logical (grain) separate.

## BD-CN-006 — Narrow vs wide transformations

- **Narrow**: each output partition depends on one input partition (filter, map, column
  math). Cheap, no data movement.
- **Wide**: output partitions depend on many input partitions (groupby, join, distinct,
  sort). Require a **shuffle** — moving data across the network. Wide transforms are where
  cost, skew, and most failures live (`partitioning-and-shuffle.md`).

The reasoning rule: count the wide steps; each is a shuffle to justify.

## BD-CN-007 — Shuffle: the expensive redistribution

A **shuffle** reorganizes rows across partitions so that rows sharing a key land together
(needed for joins, groupbys, distinct). It writes intermediate data to disk and moves it
across the network. Shuffles dominate runtime and are the root of skew and spill. Minimize
them, and make the unavoidable ones efficient (`partitioning-and-shuffle.md`,
`joins-and-skew.md`).

## BD-CN-008 — Skew: uneven work across partitions

**Skew** is when some keys have far more rows than others, so a few tasks do most of the
work while the rest sit idle. One slow straggler task can dominate the whole job. Skew is
the single most common big-data performance pathology and has its own playbook
(`joins-and-skew.md`).

## BD-CN-009 — Fan-out at scale is doubly dangerous

Fan-out (`PY-CN-046`: a non-unique join key multiplying rows) is the same correctness bug
as in pandas — but at scale it *also* explodes shuffle volume and can OOM the job, not just
inflate a sum. So the pandas fix (aggregate the many-side first, `PY-CN-051`) is both a
correctness and a performance necessity here.

## BD-CN-010 — The driver is a single point; don't funnel data to it

The **driver** coordinates the job; executors do the distributed work. Pulling distributed
results back to the driver (`collect()`, `toPandas()`) collapses all that data into one
process and routinely OOMs it. Inspect distributed data with distributed operations
(counts, samples, aggregates), not by collecting it (`performance-and-cost.md`).

## BD-CN-011 — Storage format is part of the computation

At scale, how data is stored (row vs columnar, partitioned, table format) changes what the
engine must read. Columnar partitioned formats (Parquet, and table formats Delta/Iceberg)
let the engine prune partitions and columns, reading a fraction of the data. Format choice
is a first-class performance and correctness lever (`file-formats-and-storage.md`).

## BD-CN-012 — Reproducibility: idempotent, incremental thinking

Big-data jobs are reruns waiting to happen (failures, backfills, late data). A job must be
**idempotent** — rerunning it produces the same result, not duplicates — and ideally
**incremental** — processing only what changed. This is a design property to reason about
up front, not patch later (`incremental-and-idempotency.md`).

---

### Ends on

`checklists/engine-selection-checklist.md` — confirm scale-out is actually warranted and
the basic execution model (partitions, wide steps, storage) is understood before designing
the pipeline.
