# Partitioning and Shuffle

Partitioning sets parallelism; shuffle moves data. Together they drive most big-data cost
and most failures. Schema: `references/retail-bigdata-schema.md`.

---

## BD-CN-027 — Partition count and size are a balance

- **Too few / too large** partitions → each task needs more memory → disk **spill** and
  executor OOM, and under-uses the cluster.
- **Too many / too small** partitions → scheduling overhead dominates, and writes produce
  the small-files problem (`file-formats-and-storage.md`).

Aim for partitions large enough to amortize overhead but small enough to fit comfortably in
task memory. The right number depends on data size and cluster cores, not a fixed constant.

## BD-CN-028 — Minimize shuffles; justify each one

Every wide transform (join, groupby, distinct, sort) is a shuffle (BD-CN-006/007). The
cheapest shuffle is the one you avoid:

- **Filter early** — prune rows before the wide step.
- **Project early** — drop unused columns before the shuffle (less data to move).
- **Broadcast** a small side of a join to avoid shuffling the large side
  (`joins-and-skew.md`).
- **Pre-aggregate** the many-side before a join to cut both fan-out and shuffle volume
  (`PY-CN-051`, BD-CN-009).

When reviewing a plan, list the shuffles and require a justification for each.

## BD-CN-029 — Let Adaptive Query Execution help, but understand it

Modern Spark uses **Adaptive Query Execution (AQE)** (enabled by default in recent
versions) to adjust the plan at runtime from actual statistics:

- it **coalesces** many small post-shuffle partitions into fewer right-sized ones;
- it can switch a join to broadcast when a side turns out small;
- it **splits skewed partitions** in sort-merge joins automatically.

Relevant switches (facts, not tuning advice): `spark.sql.adaptive.enabled`,
`spark.sql.adaptive.coalescePartitions.enabled`, `spark.sql.adaptive.skewJoin.enabled`.
AQE reduces manual partition tuning but does not remove the need to reason about skew and
shuffle — it handles common cases, not pathological ones (`joins-and-skew.md`).

## BD-CN-030 — repartition vs coalesce

- **repartition(n)** — full shuffle to exactly `n` partitions (or by a key). Use to
  *increase* parallelism or to co-locate by a key before a keyed operation. It is a
  shuffle, so it has a cost.
- **coalesce(n)** — reduces partition count *without* a full shuffle by merging adjacent
  partitions. Use to *shrink* partition count (e.g. before writing) cheaply.

**Anti-pattern (BD-AP-002): `coalesce(1)`** to force a single output file — it funnels all
data through one core, killing parallelism and risking OOM. To control output file count,
prefer right-sizing partitions or the table format's file management, not `coalesce(1)`.

## BD-CN-031 — Partition the data for the dominant operation

Choose the on-disk and in-memory partitioning to serve the heaviest downstream step
(BD-CN-016):

- Date-partition `orders`/`clickstream` so date-bounded BI queries prune partitions.
- If a large table is repeatedly joined/grouped on the same key, partitioning (or
  bucketing) by that key co-locates rows and avoids repeated shuffles.

Partitioning for the load step instead of the query step is a common waste.

## BD-CN-032 — Partition pruning is a correctness-adjacent win

Reading only the needed partitions (e.g. one `order_date`) is the biggest single
performance lever and depends on (a) a partitioned layout and (b) filters the engine can
push to the storage layer. A filter that the engine cannot push down (e.g. wrapped in a
non-pushable expression) silently scans everything — verify pruning actually happens in the
plan.

## BD-CN-033 — Spill is a symptom, not a setting

When shuffle/aggregation data exceeds task memory, the engine **spills** to disk, slowing
the job sharply. Spill usually means partitions are too large, a key is skewed, or a wide
transform is unnecessarily broad. Treat spill as a signal to revisit partitioning and skew,
not as something to silence (`performance-and-cost.md`).

## BD-PB-002 — Playbook: job spills / executors OOM

1. Check partition sizing — are partitions too few/large for task memory (BD-CN-027)?
2. Check for skew — is one partition far larger than the median (BD-CN-008)? If so →
   `joins-and-skew.md`.
3. Reduce shuffle volume — filter and project before the wide step (BD-CN-028).
4. Confirm AQE is enabled and coalescing/skew-join are on (BD-CN-029).
5. Re-measure; record on the checklist.

---

### Ends on

`checklists/partitioning-shuffle-checklist.md` — a verdict on partition sizing, shuffle
count, pruning, and spill, with before/after evidence.
