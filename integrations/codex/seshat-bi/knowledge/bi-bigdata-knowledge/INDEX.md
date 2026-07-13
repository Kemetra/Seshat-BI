# INDEX — BI Big-Data Knowledge Router

Route the task to the **fewest** files that answer it. Open those files only. End on the
named artifact. Do not pre-load the whole `knowledge/` directory.

---

## Task routes

| If the agent needs to… | Open | End on |
|---|---|---|
| Decide whether to scale out at all / pick an engine | `knowledge/engine-selection.md` | `checklists/engine-selection-checklist.md` |
| Understand the distributed dataframe model (partitions, lazy DAG) | `knowledge/distributed-dataframe-model.md`, `knowledge/bigdata-core-concepts-for-bi.md` | engine-selection checklist |
| Tune partitioning / reduce shuffle | `knowledge/partitioning-and-shuffle.md` | `checklists/partitioning-shuffle-checklist.md` |
| Join two large datasets safely | `knowledge/joins-and-skew.md` | `checklists/join-skew-checklist.md` |
| Fix a skewed key / hot partition | `knowledge/joins-and-skew.md`, `knowledge/partitioning-and-shuffle.md` | `checklists/join-skew-checklist.md` |
| Aggregate at a grain over very large data | `knowledge/aggregation-and-grain-at-scale.md` | `checklists/aggregation-grain-checklist.md` |
| Choose a storage / file format | `knowledge/file-formats-and-storage.md` | partitioning-shuffle checklist |
| Design incremental / idempotent processing | `knowledge/incremental-and-idempotency.md` | `checklists/pipeline-review-checklist.md` |
| Validate / reconcile at scale before handoff | `knowledge/validation-and-reconciliation-at-scale.md`, `patterns/validation-patterns.json` | `checklists/validation-reconciliation-checklist.md` |
| Diagnose slowness / cost | `knowledge/performance-and-cost.md` | performance/cost verdict (in file) |
| Review a distributed pipeline | `knowledge/bigdata-anti-patterns.md`, `patterns/analyzer-rules.json` | `checklists/pipeline-review-checklist.md` |
| Find an original worked retail example | `knowledge/bigdata-retail-examples.md` | n/a (reference) |

---

## Symptom routes

| Symptom the agent observes | Likely cause | Open | End on |
|---|---|---|---|
| One task runs forever while others finish | Data skew / hot key | `knowledge/joins-and-skew.md` | `checklists/join-skew-checklist.md` |
| Job spills to disk / executors OOM | Too few/large partitions, wide transform | `knowledge/partitioning-and-shuffle.md`, `knowledge/performance-and-cost.md` | partitioning-shuffle checklist |
| Driver OOM | `collect()`/`toPandas()` pulling too much | `knowledge/performance-and-cost.md` | performance/cost verdict |
| Row count exploded after a join | Fan-out from non-unique key (at scale) | `knowledge/joins-and-skew.md` | `checklists/join-skew-checklist.md` |
| Thousands of tiny output files | Small-files problem / over-partitioning | `knowledge/file-formats-and-storage.md`, `knowledge/partitioning-and-shuffle.md` | partitioning-shuffle checklist |
| Sums too big after grouping | Wrong grain / non-additive summed / upstream fan-out | `knowledge/aggregation-and-grain-at-scale.md` | `checklists/aggregation-grain-checklist.md` |
| Reruns create duplicates | Non-idempotent writes / no partition overwrite | `knowledge/incremental-and-idempotency.md` | `checklists/pipeline-review-checklist.md` |
| Totals don't match the source/SQL | Reconciliation gap at scale | `knowledge/validation-and-reconciliation-at-scale.md` | `checklists/validation-reconciliation-checklist.md` |
| Job is slow and expensive but "works" | Caching/UDF/shuffle inefficiency | `knowledge/performance-and-cost.md` | performance/cost verdict |
| Late data changes yesterday's totals | Late-arriving data not modeled | `knowledge/incremental-and-idempotency.md` | `checklists/pipeline-review-checklist.md` |

---

## Cross-layer routes

| If the question is really about… | Go to |
|---|---|
| Single-node pandas source-prep | `bi-python-knowledge` (this layer references its concepts) |
| Grain / fan-out / additivity / null semantics (engine-independent) | `references/cross-layer-map.md` → `bi-python-knowledge` |
| What a KPI *means* (definition, additivity, grain intent, required fields) | `skills/retail-kpi-knowledge/` — implement its ready contract at scale; never invent the meaning here |
| SQL transformation or SQL reconciliation logic | SQL knowledge layer |
| The measure / semantic-model logic for a ready contract | DAX knowledge layer (DAX implements; it does not define the KPI's meaning — that is `retail-kpi-knowledge`) |
| Whether work may proceed | Readiness layer (gating) |

---

## File map

```
knowledge/   distributed-reasoning content, one domain per file
patterns/    machine-readable rule + pattern sets (JSON)
checklists/  the artifacts routes end on
references/  schema, IDs, sources/copyright, cross-layer map, research notes, training set
```

## Stop rules (router level)

- If a single route answers the need, do not open a second file "for context".
- If you cannot name the artifact you will end on, you are not ready to start.
- If the honest answer is "this fits on one machine", route to `bi-python-knowledge`.
- If the task is metric *meaning*/definition — stop; it belongs to `retail-kpi-knowledge`.
  If it is the measure/semantic logic, or gating — stop; it belongs to
  DAX / readiness.
