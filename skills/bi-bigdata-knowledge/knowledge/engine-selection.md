# Engine Selection

The first decision in any big-data task: *which engine, or none?* Picking distributed
Spark when DuckDB on one node would do is the most expensive early mistake. Schema:
`references/retail-bigdata-schema.md`.

---

## BD-CN-021 — Single-node first, always

Before choosing a distributed engine, rule out a single node. Modern single-node engines
(Polars, DuckDB) stream larger-than-memory data from columnar storage and routinely handle
tens to hundreds of GB on one commodity machine. Distribution adds shuffle, serialization,
scheduling, and cluster cost. **Best practice (BD-BP-003):** justify scale-out with a real
constraint (data size, time budget, or memory), not a guess.

## BD-CN-022 — The size question is "after pruning", not "raw"

What matters is the data a query actually touches, not the dataset's total size. A query
over one day of `orders` from a date-partitioned table reads one partition, not the year.
Always estimate the **post-pruning** working set (after partition and column pruning)
before sizing the engine. Many "big data" problems are single-node once pruned.

## BD-CN-023 — Engine map (when to reach for what)

| Engine | Sweet spot | Reach for it when | Avoid when |
|---|---|---|---|
| **pandas** (`bi-python-knowledge`) | fits comfortably in RAM | small/medium, interactive prep | data exceeds memory |
| **Polars** | one big machine, larger-than-RAM via streaming | fast single-node, pandas-like API, complex column work | needs a cluster; extreme memory pressure |
| **DuckDB** | one machine, larger-than-memory, SQL-native | complex analytical SQL on big local/lake files; tight memory | true multi-node distribution |
| **Dask** | scale existing pandas across cores/cluster | a pandas pipeline that outgrew one core, minimal rewrite | brand-new heavy SQL-style work (Spark/warehouse better) |
| **Spark (PySpark)** | genuine multi-node distribution | data far exceeds one machine; cluster already in place | the data actually fits one node (overhead not worth it) |
| **Cloud warehouse** (BigQuery / Snowflake / Databricks SQL) | set-based transforms on governed data | the heavy join/aggregation is expressible in SQL on data already in the warehouse | logic is inherently procedural/ML and not SQL-shaped |

## BD-CN-024 — Prefer pushdown to the SQL/warehouse layer when you can

If the heavy step is a join or aggregation over data already living in a warehouse, the
cheapest and most governed option is usually to **push it down** to that warehouse (SQL
layer) rather than extracting it into distributed Python. This keeps data in place, reuses
the warehouse's optimizer, and respects the boundary that SQL owns SQL transformation
logic. Choosing pushdown is a correct outcome of this layer, not an evasion
(`references/cross-layer-map.md`).

## BD-CN-025 — Match the engine to the operation shape

- Heavy **set-based** work (filter/join/aggregate) → SQL-shaped engines shine (DuckDB,
  warehouse, Spark SQL).
- Heavy **column/expression** work on one big machine → Polars.
- **Lift-and-shift** of an existing pandas pipeline that just got too big → Dask.
- **Truly distributed** multi-TB pipelines with an existing cluster → Spark.

Choosing by operation shape avoids both over- and under-engineering.

## BD-CN-026 — Account for the operational cost, not just runtime

Engine choice carries operational weight: a Spark cluster needs provisioning, tuning, and
spend; DuckDB/Polars need neither. Factor in setup, maintenance, and cost — a job that
runs 20% faster on a cluster but costs 10× and needs ongoing tuning is usually the wrong
call for BI prep. Cheapest *correct* path wins (`performance-and-cost.md`).

## BD-PB-001 — Playbook: choosing an engine

1. Estimate the **post-pruning** working set (BD-CN-022).
2. If it fits one machine → Polars/DuckDB (or pandas) — stop; route to
   `bi-python-knowledge` if it's just prep.
3. If the heavy step is SQL-shaped and data is in a warehouse → **push down** (BD-CN-024).
4. If it's an existing pandas pipeline that outgrew one core → Dask.
5. If it genuinely exceeds one machine and a cluster exists → Spark.
6. Record the decision and its justification on the checklist.

---

### Ends on

`checklists/engine-selection-checklist.md` — an **engine verdict**: chosen engine (or
"single-node — route to Python" / "push down to SQL"), with the post-pruning size estimate
and justification.
