# Cross-Layer Map

How this layer relates to the others, and which concepts it **borrows rather than
restates**. The point is to avoid duplicating the Python layer and to keep boundaries
crisp.

## Shared spine (borrowed from bi-python-knowledge)

These are engine-independent. They are true in pandas, Spark, Dask, Polars, DuckDB, and
SQL. This layer cites them by their `PY-` IDs and only adds the distributed twist.

| Concept | Owned in | Borrowed here as | Distributed twist this layer adds |
|---|---|---|---|
| Grain ("one row per ___") | `PY-CN-007` | basis for all aggregation/join reasoning | grain must hold across partitions; partition ≠ grain |
| Keys & cardinality | `PY-CN-008` | basis for join reasoning | cardinality also drives skew and broadcast eligibility |
| Fan-out (row multiplication) | `PY-CN-046`, `PY-CN-051` | join correctness | fan-out at scale also causes shuffle blow-up, not just wrong sums |
| Additivity | `PY-CN-053` | what may be summed | partial/tree aggregation must preserve additivity |
| count vs nunique vs size | `PY-CN-055`, `PY-CN-056` | counting correctness | distinct counts are expensive at scale (approx vs exact) |
| Null / blank / sentinel semantics | `PY-CN-039`, `PY-CN-040`, `PY-CN-043` (others in the `038–044` range planned in the Python seed) | data-quality reasoning | same rules; checks run as scalable aggregates |
| Reconciliation by control totals | `PY-CN-068` | validation currency | totals computed distributed; sampling supplements |
| Schema drift | `PY-CN-022` | source stability | handled via table-format schema evolution |

When reasoning about any of the above, do **not** re-derive it here — cite the `PY-` ID and
move to the distributed concern.

> **Borrowed-ID status (honesty note).** `PY-` IDs are *provenance tags* for the shared
> single-node spine, not navigation links to open. `bi-python-knowledge` is an **initial
> seed**, so some cited spine concepts are **not yet authored there** (e.g. parts of the
> null-semantics range, some key-hygiene and reconciliation concepts). A `PY-` tag with no
> authored target means **"borrowed from the shared spine, definition planned in the Python
> seed"** — treat it as the named concept, not as a broken reference, and never fabricate the
> pandas definition here. As the Python seed fills in, these tags resolve to authored entries.

## What this layer owns (not in the Python layer)

Distributed/larger-than-memory execution: engine selection, partitioning, shuffle, skew,
broadcast vs shuffle joins, lazy DAG/stage reasoning, file & table formats
(Parquet/Delta/Iceberg), the small-files problem, incremental & idempotent processing,
late-arriving data, scale-appropriate validation (sampling, Deequ-style checks), and
cost/performance at cluster scale.

## Boundaries (who owns what)

- **Readiness** — stage and gating; pass/block.
- **Retail KPI knowledge** — the business meaning of a KPI (definition, additivity, grain
  intent, required fields). The contract this layer implements at scale comes from here.
- **SQL knowledge** — SQL reasoning, SQL reconciliation, SQL transformation logic.
- **DAX knowledge** — measures, semantic-model prerequisites (implements the contract).
- **Python knowledge** — single-node dataframe / source-prep reasoning.
- **Big-data knowledge (this layer)** — distributed / larger-than-memory execution
  reasoning and distributed-pipeline review.
- **Dashboard design** — visual/page design after metric contracts.
- **Execution adapters** — run jobs; never define meaning, mapping, metrics, semantics,
  or approval.

## The most important boundary call

Often the correct big-data answer is **"don't process this in distributed Python — push
the heavy join/aggregation down to the SQL/warehouse layer."** That is a legitimate,
encouraged outcome of this layer's reasoning, not a gap. See
`knowledge/engine-selection.md`.
