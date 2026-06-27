# File Formats and Storage

At scale, how data is stored decides how much the engine must read and whether reruns stay
correct. Storage is computation (BD-CN-011). Schema: `references/retail-bigdata-schema.md`.

---

## BD-CN-050 — Columnar beats row-oriented for BI reads

BI queries read a few columns over many rows. **Columnar** formats (Parquet) store each
column contiguously, so the engine reads only the columns and row groups it needs and skips
the rest — far less I/O than row-oriented CSV/JSON, which must parse whole rows. For any
data read more than once, columnar storage is the baseline. CSV/JSON are interchange
formats, not analytical storage (reuses `PY-CN-079`).

## BD-CN-051 — Partitioned layout enables pruning

Physically partitioning files by a column (e.g. `order_date=YYYY-MM-DD`) lets the engine
skip entire directories for filtered queries (BD-CN-032). Partition on a column that BI
queries filter on (usually date), with a granularity that keeps partitions a sensible size
— too fine (per-minute) creates the small-files problem; too coarse (per-year) defeats
pruning.

## BD-CN-052 — The small-files problem

Thousands of tiny files (from over-partitioning, streaming micro-batches, or many tasks
each writing a sliver) cripple performance: the engine spends more time listing and opening
files than reading data. Symptoms: slow job start, metadata pressure. Fixes: right-size
output partitions, compact small files periodically, and avoid `coalesce(1)`'s opposite
extreme of one task per sliver (BD-CN-030). Table formats automate compaction.

## BD-CN-053 — Table formats: Parquet vs Delta vs Iceberg

- **Parquet** — the columnar file format; fast reads, but a bare directory of Parquet has
  no transactions, no schema evolution, no row-level updates.
- **Delta Lake** and **Apache Iceberg** — *table formats* layered over Parquet that add
  **ACID transactions**, **schema evolution**, **time travel**, efficient **upserts/merge**,
  and metadata that keeps large tables queryable. Iceberg additionally supports **partition
  evolution** (changing the partitioning scheme without rewriting all data).

For BI tables that are updated, backfilled, or schema-evolving, a table format (Delta or
Iceberg) is usually right; bare Parquet suits append-only or one-shot extracts.

## BD-CN-054 — Schema evolution makes drift explicit

Schema drift (`PY-CN-022`) is handled structurally by table formats: a new column or type
change is a tracked schema change, not a silent re-inference per read. This both prevents
accidental drift and surfaces intentional changes for review — a correctness win, not just
convenience.

## BD-CN-055 — Predicate and projection pushdown

Columnar + table formats let the engine push **predicates** (row filters) and
**projections** (column selection) down to the storage layer, reading only matching row
groups and needed columns. Verify pushdown actually happens in the plan; a filter the
engine can't push down silently reads everything (BD-CN-032).

## BD-CN-056 — Compression and file sizing are real levers

Columnar formats compress well; sensible row-group/file sizes (large enough to amortize
overhead, small enough for parallelism) materially affect read speed. These are tuning
details, not correctness — apply them after the layout (columnar, partitioned, table
format) is right, and don't over-tune (reuses the "fast enough" rule, `PY-CN-082`).

---

### Ends on

`checklists/partitioning-shuffle-checklist.md` (storage section). Produce a **storage
verdict**: format (Parquet vs Delta/Iceberg), partition column + granularity, and the
small-files check.
