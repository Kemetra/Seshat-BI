# Seshat BI Compass

## What this repo is

Seshat BI is an agent-first Retail BI readiness system that guides agents from
raw retail sources through source understanding, mapping, silver, gold, semantic
model, dashboard, and publish readiness using documented gates, evidence, and
human approvals. The agent is the interface; the CLI gates (`retail check`,
`retail validate`) are helpers it calls, never the product.

## Start here

```text
AGENTS.md
  -> COMPASS.md
    -> docs/readiness/readiness-model.md
    -> docs/knowledge-map.md
      -> relevant skill/router
        -> required artifact/checklist/verdict
```

## The one question to answer first

For every task, the agent must first answer:

**What readiness stage am I serving?**

Stages:

1. Source Ready
2. Mapping Ready
3. Silver Ready
4. Gold Ready
5. Semantic Model Ready
6. Dashboard Ready
7. Publish Ready

## Fast routing

| Task type | Route | Stop / End on |
|---|---|---|
| Source understanding / onboarding | `docs/readiness/readiness-model.md` + `docs/knowledge-map.md` | readiness status / source profile |
| Source profiling | `docs/readiness/readiness-model.md` + `docs/knowledge-map.md` | source profile |
| Source mapping / grain / PII / unresolved questions | `docs/readiness/readiness-model.md` + `docs/knowledge-map.md` | source map + unresolved questions |
| SQL validation / SQL reconciliation / transformation logic | `skills/bi-sql-knowledge/SKILL.md` then `skills/bi-sql-knowledge/INDEX.md` | SQL validation / reconciliation checklist |
| KPI business meaning / metric-contract definition / additivity / grain / ambiguity / KPI-pack selection | `skills/retail-kpi-knowledge/SKILL.md` then `skills/retail-kpi-knowledge/INDEX.md` | metric contract (business meaning) + implementation handoff note (SQL / DAX / Python / Big-data) |
| DAX / measure generation / measure review / semantic-model prerequisites (after the business contract is ready) | `skills/bi-dax-knowledge/SKILL.md` then `skills/bi-dax-knowledge/INDEX.md` | generated/reviewed measure + semantic-model handoff |
| Python / pandas / dataframe source-prep reasoning, cleaning, aggregation-grain review (single-node) | `skills/bi-python-knowledge/SKILL.md` then `skills/bi-python-knowledge/INDEX.md` | cleaning / aggregation-grain review artifact (planned routes deferred) |
| Big-data / distributed / larger-than-memory: engine selection, partitioning/shuffle, skew, distributed joins/aggregation, file formats, incremental, scale validation | `skills/bi-bigdata-knowledge/SKILL.md` then `skills/bi-bigdata-knowledge/INDEX.md` | engine-selection / partitioning / join-skew / pipeline-review / validation checklist or verdict |
| Dashboard / visual design / audience / layout | `.claude/skills/powerbi-dashboard-design/` (gated "design from contracts" verb: `.claude/skills/dashboard-design/`) | dashboard blueprint |
| Power BI execution / publish | STOP unless `semantic_model_ready` and publish gates have passed | blocked verdict or BI handoff pack |
| Unknown or ambiguous task | `docs/knowledge-map.md` | clarifying question or blocked verdict |

Power BI execution remains execution-only and gated: **F016** advances only when
`semantic_model_ready` and the publish gates have passed.

## The knowledge layer

The reasoning skills are the deepest assets the routes above point into. All are
*reasoning and validation* layers, never executors — they reason about SQL/DAX/Python,
they never run a query, run DAX, run Python, or touch a database.

| Skill | Foundation concept | Use for |
|---|---|---|
| `skills/retail-kpi-knowledge/` | **business KPI meaning** + metric contracts | defining a KPI in business terms, additivity/grain classification, ambiguity resolution (gross vs net, VAT, returns, cost method, same-store), required-field lists, KPI-pack selection, implementation handoff prep for SQL / DAX / Python / Big-data (*initial seed*) |
| `skills/bi-sql-knowledge/` | **table grain** + aggregation correctness | source profiling, grain/keys/uniqueness, joins & fan-out, COUNT/NULL semantics, dedup, validation & reconciliation queries, silver/gold transform logic, SQL anti-patterns |
| `skills/bi-dax-knowledge/` | **filter context** + context transition | measure generation/review, time-intelligence, ranking/segmentation, semantic-model prerequisites, DAX performance (implements a business contract from `retail-kpi-knowledge`) |
| `skills/bi-python-knowledge/` | **dataframe grain** + source-prep reasoning | pandas/dataframe source-prep reasoning, cleaning/standardization review, aggregation-grain review, Python BI analyzer candidates, reasoning training/eval seed (*initial seed*) |
| `skills/bi-bigdata-knowledge/` | **execution topology** (single-node → distributed) | engine selection (Spark/Dask/Polars/DuckDB/warehouse), partitioning/shuffle/skew, distributed joins & aggregation, file/table formats (Parquet/Delta/Iceberg), incremental/idempotent processing, validation & cost at scale; the scale-out sibling of bi-python (borrows its grain/additivity spine, owns only the distributed twist) |

Mandatory flow inside any of these skills: **`SKILL.md` → `INDEX.md` → ONLY the file(s)
the route names → an artifact** (checklist, metric/validation contract, or
analyzer-style verdict). Reading the whole base is an anti-pattern. Each `INDEX.md`
routes by *task* and by *symptom* — enter from the symptom if you have one.

### BI Python knowledge

Use `skills/bi-python-knowledge/SKILL.md` for Python / pandas / dataframe source-prep
reasoning. Route through `skills/bi-python-knowledge/INDEX.md` and open only the named
files.

Current seed coverage includes cleaning/standardization, aggregation-grain review,
analyzer rule candidates, and a training/eval seed. Treat this layer as an **initial
seed**: planned dataframe, dtype/profiling, merge/fan-out, validation, and performance
routes remain deferred until implemented.

This layer is reasoning/review only. It does not execute Python, define metrics,
approve readiness gates, replace SQL/DAX, or own dashboard design.

### BI Big-data knowledge (scale-out sibling of bi-python)

Use `skills/bi-bigdata-knowledge/SKILL.md` when the data is **too large for single-node
pandas** and the task is about *distributed or larger-than-memory execution*: choosing an
engine (Spark / Dask / Polars / DuckDB / push-down to the warehouse), controlling
partitioning and shuffle, avoiding skew and fan-out at scale, aggregating at a declared
grain over very large data, choosing a file/table format (Parquet / Delta / Iceberg),
incremental/idempotent processing, validating/reconciling at scale, or diagnosing
performance/cost. Route through `skills/bi-bigdata-knowledge/INDEX.md`; end on an
engine-selection / partitioning / join-skew / pipeline-review / validation checklist.

It is the scale-out companion to `bi-python-knowledge`: the shared spine (grain, fan-out,
additivity, null semantics, reconciliation) is **borrowed by `PY-` ID, not repeated** (see
its `references/cross-layer-map.md`); this layer owns only what changes when compute becomes
distributed. The single most important call it makes is often *"don't scale out — push this
heavy join/aggregation down to the SQL/warehouse layer"* — a boundary call, not a failure.

This layer is reasoning/review only. It does not run jobs, define metric meaning (that is
`retail-kpi-knowledge`), write SQL/DAX, approve readiness gates, or design dashboards. Stop
and route to `bi-python-knowledge` if the honest answer is "this fits on one machine".

### Retail KPI knowledge (business meaning — first stop for metric definition)

Use `skills/retail-kpi-knowledge/SKILL.md` whenever the task is *what a retail KPI
means* rather than *how to implement it*: defining a KPI in business terms,
classifying additivity (fully / semi / non-additive), declaring grain, listing the
required source fields, resolving ambiguity (gross vs net, VAT, returns, cost method,
same-store), or choosing an MVP KPI pack. Route through
`skills/retail-kpi-knowledge/INDEX.md` and open only the named files; end on a
`metric-contract-review-checklist` / `metric-ambiguity-checklist` /
`kpi-pack-review-checklist` verdict.

This is the **first stop** for metric-contract definition. A completed business
contract then hands off to **whichever layer implements its slice** — `skills/bi-sql-knowledge/`
for required fields, grain, transform and reconciliation; `skills/bi-dax-knowledge/` for the
measure and semantic-model prerequisites; `skills/bi-python-knowledge/` for single-node
source-prep (dtypes/cleaning of the required fields); `skills/bi-bigdata-knowledge/` for
distributed / at-scale aggregation and reconciliation when the data is too large for a
single node. Those layers implement meaning, they do not redefine it. Treat this layer as
an **initial seed**: 10 live metric contracts; the
KPIs named in `patterns/metric-contract-candidates.json` are planned/deferred and
their routes return a planned note, never a fabricated contract.

This layer is reasoning/definition + review only. It does not write DAX/SQL/Python,
approve readiness gates, or design dashboards. Stop and hand off when a KPI's policy
(VAT, returns, cost method, same-store, snapshot date) is an undecided owner ruling —
mark the contract **Needs business definition**; never invent the policy.

## Hard stops

- Stop if Mapping Ready is not `pass` before silver.
- Stop if validation has not passed before Power BI.
- Stop if metric contracts do not exist before dashboard design.
- Stop if a required human approval is missing.
- Stop if evidence is missing.
- Stop if the task crosses into the F016 execution adapter without gates passed.
- Stop rather than invent source meaning, metric meaning, or approval.
- Stop reading at the one file the knowledge `INDEX.md` names — never read a whole
  knowledge base; ground the grain (SQL) or the filter context (DAX) first.

## Valid outputs

Every agent run should end with one of:

- readiness status update
- source profile
- source map
- assumptions / unresolved questions
- data issues / blocking reasons
- SQL validation checklist
- SQL reconciliation checklist
- analyzer-style SQL or DAX review verdict
- diagnostic playbook verdict
- metric contract
- semantic model handoff
- dashboard blueprint
- BI handoff pack
- explicit blocked verdict with reasons

## What this file is not

This file is not the knowledge base, not a tutorial, not a runtime validator, not
a wiki, and not a vector index. It is a compass.

## See also

- Routing smoke test: `docs/quality/agent-routing-smoke-test.md` — a manual check that this routing layer still works.
