# bi-bigdata-knowledge

A big-data / distributed-compute **reasoning and review layer** for BI and data agents in
the Seshat BI project. It is the scale-out companion to `bi-python-knowledge` and mirrors
the same methodology: a thin router, an index, and focused knowledge files that always end
on an artifact (checklist / JSON patterns / verdict).

## This is a reasoning layer, not an executor

- It does **not** run Spark/Dask jobs or notebooks.
- It does **not** define metrics, semantic logic, or business meaning.
- It does **not** own stage/gating (readiness does).
- It is **not** a Spark/Dask/Polars tutorial.

It helps an agent reason about distributed and larger-than-memory data work — engine
choice, partitioning, shuffle, skew, joins, aggregation grain at scale, file formats,
incremental/idempotent processing, validation, performance/cost — and hand off cleanly
into SQL, DAX, readiness, and dashboard layers.

## Relationship to bi-python-knowledge

The conceptual spine is shared. **Grain, fan-out, additivity, null semantics, and
reconciliation are engine-independent** — true in pandas, Spark, and SQL alike. This
layer references those concepts (`references/cross-layer-map.md`) rather than restating
them, and adds only what changes at scale: distributed execution, partitioning, shuffle,
skew, broadcast joins, lazy DAGs, file/table formats, incrementality, and cost.

Rule of thumb: **single-node first.** If the workload fits on one machine (even a big
one, via Polars/DuckDB chunking), it belongs to `bi-python-knowledge`. This layer is for
genuinely distributed or larger-than-memory-cluster work — or for deciding to push the
heavy step to the SQL/warehouse layer.

## Entry point

Always start at `SKILL.md`, then `INDEX.md`. Let the router select the file(s) you need.

## Layout

```
SKILL.md      thin router + boundaries + stop rules
INDEX.md      task routes, symptom routes, cross-layer routes, file map
knowledge/    one distributed-reasoning domain per file
patterns/     analyzer rules, validation patterns, pattern sets (JSON)
checklists/   the artifacts each route ends on
references/   retail schema, IDs, sources/copyright, cross-layer map, research, training set
```

## Conventions

- **IDs:** stable families (`BD-CN-*`, `BD-AP-*`, `BD-AR-*`, …) — see
  `references/id-conventions.md`.
- **Examples:** original, fictional retail-at-scale only — see
  `references/retail-bigdata-schema.md`.
- **Sources:** grounded in current public best practice, cited in
  `references/research-notes.md`; no copied text — see
  `references/copyright-and-sources.md`.

## Engine focus

Centered on **PySpark** (the most common BI distributed engine), with explicit guidance on
**Polars / DuckDB** for larger-than-memory single-node work, **Dask** for scaling pandas,
and **cloud warehouse pushdown** (BigQuery / Snowflake / Databricks SQL) as a first-class
alternative to distributed Python.
