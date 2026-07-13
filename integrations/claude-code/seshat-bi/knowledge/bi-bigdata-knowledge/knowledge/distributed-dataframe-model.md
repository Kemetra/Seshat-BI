# Distributed Dataframe Model

How a BI agent should *picture* a distributed dataframe so that joins, aggregations, and
writes come out right and cheap. Grounding schema: `references/retail-bigdata-schema.md`.
Engine-independent correctness concepts are borrowed (`references/cross-layer-map.md`).

---

## BD-CN-013 — Picture five things, not two

A distributed dataframe is:

1. **Rows** at a fixed grain (`PY-CN-007`).
2. **Columns**, typed (a schema claim, `PY-CN-013`).
3. **Partitions** — the physical chunks rows are split into (BD-CN-004).
4. **A lazy plan** — the DAG of transformations not yet executed (BD-CN-003).
5. **A physical layout on storage** — format + partitioning on disk (BD-CN-011).

Pandas reasoning uses the first two. Big-data reasoning must hold all five at once.

## BD-CN-014 — The plan is the thing you reason about

Because execution is lazy, the artifact you inspect is the **plan** (in Spark, the physical
plan / `explain`). Read it for: the number of **stages** (each shuffle starts a new stage),
which joins are broadcast vs shuffle, and where wide transforms sit. Reasoning about the
plan before triggering an action is the big-data equivalent of declaring grain before
transforming.

## BD-CN-015 — Stages and shuffle boundaries

A **stage** is a span of narrow transforms that run without moving data; a **shuffle**
ends one stage and begins the next. Fewer stages generally means less data movement and a
faster job. When reviewing a plan, count stages and ask whether each shuffle is necessary
(can a filter, a broadcast, or a pre-aggregation remove it?).

## BD-CN-016 — Partitioning strategy is a design decision

How rows are partitioned (by count, by a key, by date) determines parallelism, shuffle
cost, and join efficiency:

- **By date** (e.g. `orders` by `order_date`) — enables partition pruning on date filters.
- **By join/group key** — co-locates rows so a later join/groupby avoids a shuffle.
- **Default/round-robin** — fine for narrow work, poor for repeated keyed operations.

Choose the partitioning that serves the dominant downstream operation, not the load step.

## BD-CN-017 — Grain holds across partitions

A frame's grain is a global property; partitioning must never be mistaken for it
(BD-CN-005). "One row per `order_line_id`" must hold across the whole distributed table,
not per partition. Duplicate keys can hide in different partitions, so a uniqueness check
is a distributed aggregate (count vs distinct), not a per-partition glance.

**Retail illustration:** producer retries can write the same `event_id` into two different
hourly partitions of `clickstream`. Grain is only verified by a global distinct-count, and
deduplication must be global, not within a partition.

## BD-CN-018 — Columns and schema at scale

Columnar formats store each column separately, so reading fewer columns reads less data
(column pruning). The schema is still a *claim* to verify (`PY-CN-013`), but at scale
schema is often managed by the table format (Delta/Iceberg schema evolution) rather than
re-inferred each read — which both prevents drift and makes drift explicit
(`file-formats-and-storage.md`).

## BD-CN-019 — Caching is a deliberate, costly choice

Persisting (caching) a distributed frame in cluster memory avoids recomputing a reused
plan, but consumes memory that executors need for shuffles. Cache only a frame reused
multiple times, and release it when done. Indiscriminate caching causes spills and is a
common anti-pattern (`performance-and-cost.md`).

## BD-CN-020 — Writes are part of the model

In pandas a result is just an in-memory frame; at scale the **write** is a major step with
its own correctness and performance properties: number of output files (small-files
problem), partitioning of the output, and whether the write is idempotent on rerun. Reason
about the write, not only the computation (`file-formats-and-storage.md`,
`incremental-and-idempotency.md`).

---

## Worked frame: reasoning about `orders` at scale before any transform

Before transforming `orders`, an agent should assert:

- **Grain:** one row per `order_line_id` (global; verify via distinct-count).
- **Partitioning:** by `order_date`; a date-bounded query prunes partitions.
- **Skew:** `store_id` is skewed (flagship stores) — any join/groupby on `store_id` risks
  straggler tasks.
- **Join plan:** `stores`/`products` are small → broadcast; `customers` is large → shuffle.
- **Wide steps:** count them; each is a shuffle to justify.
- **Write:** how many output files, partitioned how, idempotent on rerun?

Only once these are stated is the frame safe to process at scale.

---

### Ends on

`checklists/engine-selection-checklist.md` — confirm the five-part model (grain,
partitions, plan, layout, write) is understood and scale-out is warranted.
