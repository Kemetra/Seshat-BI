---
name: bi-bigdata-knowledge
description: >
  Big-data / distributed-compute reasoning and review layer for BI and data agents in
  the Seshat BI project. Use when data is too large for single-node pandas and the agent
  must reason about distributed or larger-than-memory processing — choosing an engine
  (Spark / Dask / Polars / DuckDB / warehouse), controlling partitioning and shuffle,
  avoiding skew and fan-out, aggregating at a declared grain at scale, choosing file
  formats (Parquet / Delta / Iceberg), incremental/idempotent processing, validating and
  reconciling at scale, and diagnosing performance/cost. This is a reasoning layer, not
  an executor and not a Spark tutorial. It does not run jobs, define metrics, or own gating.
---

# BI Big-Data Knowledge

A thin router into a distributed / large-scale data-processing reasoning layer for
BI/data agents. It helps an agent **think correctly** about big-data work and **hand off
cleanly** into the SQL, DAX, readiness, and dashboard layers. It does not execute jobs or
define business meaning.

This layer is the scale-out companion to `bi-python-knowledge`. The conceptual spine —
grain, fan-out, additivity, null semantics, reconciliation — is shared and **referenced,
not repeated** (see `references/cross-layer-map.md`). This layer owns only what changes
when compute becomes distributed or larger-than-memory.

## How to use this skill

1. **Do not read the whole knowledge base.** Start at `INDEX.md`.
2. Match the task or symptom to a route in `INDEX.md`.
3. Open **only** the knowledge file(s) that route names.
4. Finish on the route's named artifact — a checklist, a JSON pattern set, or a verdict.

```
SKILL.md  ->  INDEX.md  ->  only the relevant file(s)  ->  checklist / verdict / handoff
```

## Use when

The agent needs to:
- decide whether a workload needs distributed/larger-than-memory processing at all;
- choose an engine (Spark, Dask, Polars, DuckDB, or push to a cloud warehouse);
- reason about partitioning, shuffle, and skew;
- choose join strategy (broadcast vs shuffle) and avoid fan-out at scale;
- aggregate at a declared grain over very large data;
- choose a storage/file format (Parquet, Delta, Iceberg) and avoid the small-files problem;
- design incremental, idempotent processing and handle late-arriving data;
- validate and reconcile results at scale (control totals, sampling, scalable checks);
- diagnose performance/cost (caching, spill, `collect()`, UDFs);
- review a distributed pipeline.

## Do not use when

- writing production Spark/job code (this layer reasons, it does not run);
- defining what a KPI *means* — definition, additivity, grain intent, required fields
  (`retail-kpi-knowledge` owns metric meaning; implement its ready contract at scale);
- defining the *measure* or semantic logic (DAX owns that);
- writing SQL transformation logic (SQL layer owns that);
- single-node pandas source-prep (use `bi-python-knowledge`);
- approving readiness / granting a gate (readiness owns that);
- designing dashboard visuals (dashboard layer owns that).

## Boundaries

- **Readiness** owns stage and gating.
- **Retail KPI knowledge** owns the *business meaning* of a KPI (definition, additivity,
  grain intent, required fields, ambiguity). This layer implements a ready contract at
  scale; it never defines the meaning.
- **SQL knowledge** owns SQL reasoning, SQL reconciliation, SQL transformation logic.
- **DAX knowledge** owns measures, semantic-model prerequisites (implements a business
  contract; does not define KPI meaning).
- **Python knowledge** owns single-node dataframe / source-prep reasoning.
- **Big-data knowledge** owns distributed / larger-than-memory execution reasoning and
  distributed-pipeline review.
- **Dashboard design** owns visual/page design after metric contracts.
- **Execution adapters** run jobs; they never define meaning, mapping, metrics, semantic
  logic, or approval.

Reason up to your edge, then hand off. Frequently the right big-data answer is "push this
step to the SQL/warehouse layer" — that is a boundary call, not a failure.

## Stop rules

- Do not scale out before confirming the workload truly needs it (single-node first).
- Do not shuffle/repartition before knowing the data's size and key distribution.
- Do not join before knowing key cardinality, skew, and which side is broadcastable.
- Do not aggregate before declaring grain and additivity.
- Do not `collect()` / pull a distributed result to the driver to "check" it.
- Do not claim reconciliation passed without scale-appropriate evidence.
- Do not write production job code in this reasoning layer.
- Do not use big-data tooling to bypass SQL/readiness validation gates.
- Do not read the whole knowledge base when a router can select files.
- Do not copy source/article text; see `references/copyright-and-sources.md`.

## Conventions

- ID families: `references/id-conventions.md`.
- Sources & copyright: `references/copyright-and-sources.md`.
- Shared concepts & boundaries with the Python layer: `references/cross-layer-map.md`.
- All examples use the fictional retail schema in `references/retail-bigdata-schema.md`.
