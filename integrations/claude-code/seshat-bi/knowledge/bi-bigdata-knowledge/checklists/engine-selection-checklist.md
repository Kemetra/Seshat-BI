# Engine Selection Checklist

Artifact for the engine-selection and distributed-model routes. Run before designing any
distributed pipeline. Ends on an engine verdict.

## A. Need for scale-out (BD-CN-021, BD-CN-002)

- [ ] Post-pruning working-set size estimated (after partition + column pruning).
- [ ] Confirmed the data does **not** fit a single (big) machine via Polars/DuckDB.
- [ ] A real constraint named: data size / time budget / memory (not a guess).

## B. Operation shape (BD-CN-025)

- [ ] Dominant heavy step classified: set-based (join/aggregate) vs column/expression vs
      lift-and-shift pandas.
- [ ] Checked whether the heavy step is SQL-shaped and data already in a warehouse
      (pushdown candidate).

## C. Distributed model understood (BD-CN-013..020)

- [ ] Grain stated (global, `PY-CN-007`); uniqueness verifiable via distinct-count.
- [ ] Partitioning strategy identified (date / key / default).
- [ ] Wide steps (shuffles) counted.
- [ ] Skew risk on key columns noted (e.g. flagship `store_id`).
- [ ] Write/output plan considered (file count, partitioning, idempotency).

## D. Cost (BD-CN-026)

- [ ] Operational cost considered (cluster provisioning, tuning, spend), not just runtime.
- [ ] Cheapest correct path identified.

## Verdict

State one of:

- **SINGLE-NODE → route to bi-python-knowledge** — fits one machine; no scale-out needed.
- **PUSH DOWN → SQL/warehouse** — heavy SQL-shaped step belongs in the warehouse.
- **POLARS / DUCKDB** — larger-than-memory single node.
- **DASK** — scale an existing pandas pipeline.
- **SPARK** — genuine multi-node distribution.

Record: post-pruning size estimate, chosen engine, and one-line justification.
