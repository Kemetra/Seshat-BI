# Seshat BI Knowledge Map

## Purpose

This is a router, not the knowledge base. Use it to select the smallest relevant
skill/docs path, then end with an artifact/checklist/verdict. It does not teach
SQL, DAX, or readiness; it points you at the one layer that does.

## Routing rule

Open only what the route names. Do not read the whole repo. Do not duplicate
knowledge from skills into this file. For a knowledge-layer route (SQL or DAX),
the two-hop is mandatory: open the skill's `SKILL.md`, then its `INDEX.md`, then
ONLY the file(s) that `INDEX.md` names — never the whole knowledge base.

## Route by task

| Task | Route | Open first | End on |
|---|---|---|---|
| 1. Source onboarding | Readiness | `docs/readiness/readiness-model.md` | readiness status + source profile |
| 2. Source profiling | Readiness | `docs/readiness/source-ready.md` | source profile |
| 3. Source mapping | Readiness | `docs/readiness/mapping-ready.md` | source map |
| 4. Grain detection | Readiness | `docs/readiness/mapping-ready.md` | declared grain + uniqueness evidence |
| 5. Mapping diff / mapping review | Readiness | `docs/readiness/mapping-ready.md` | reviewed/accepted unresolved questions + gate verdict |
| 6. SQL validation | SQL | `skills/bi-sql-knowledge/SKILL.md` then `skills/bi-sql-knowledge/INDEX.md` | SQL validation checklist |
| 7. SQL reconciliation | SQL | `skills/bi-sql-knowledge/SKILL.md` then `skills/bi-sql-knowledge/INDEX.md` | SQL reconciliation checklist |
| 8. Silver/gold SQL transformation | SQL | `skills/bi-sql-knowledge/SKILL.md` then `skills/bi-sql-knowledge/INDEX.md` | SQL review checklist |
| 9. SQL anti-pattern review | SQL | `skills/bi-sql-knowledge/INDEX.md` | analyzer-style SQL verdict |
| 10. DAX measure generation | DAX | `skills/bi-dax-knowledge/SKILL.md` then `skills/bi-dax-knowledge/INDEX.md` | generated measure + contract assumptions |
| 11. DAX measure review | DAX | `skills/bi-dax-knowledge/SKILL.md` then `skills/bi-dax-knowledge/INDEX.md` | analyzer-style DAX verdict |
| 12. Metric contract definition (business meaning) | Retail KPI | `skills/retail-kpi-knowledge/SKILL.md` then `skills/retail-kpi-knowledge/INDEX.md` | `skills/retail-kpi-knowledge/checklists/metric-contract-review-checklist.md` (+ implementation handoff note to SQL / DAX / Python / Big-data) |
| 12a. KPI additivity / grain / ambiguity | Retail KPI | `skills/retail-kpi-knowledge/SKILL.md` then `skills/retail-kpi-knowledge/INDEX.md` | metric-contract-review / metric-ambiguity checklist verdict |
| 12b. KPI-pack selection (MVP / first dashboard) | Retail KPI | `skills/retail-kpi-knowledge/INDEX.md` | `skills/retail-kpi-knowledge/checklists/kpi-pack-review-checklist.md` |
| 12c. Measure generation / semantic-model prerequisites for a *ready* business contract | DAX | `skills/bi-dax-knowledge/INDEX.md` | generated/reviewed measure + model prerequisites |
| 13. Semantic model readiness | DAX + Readiness | `skills/bi-dax-knowledge/INDEX.md` + `docs/readiness/semantic-model-ready.md` | model-review checklist / semantic model handoff |
| 14. Python cleaning / standardization review | Python | `skills/bi-python-knowledge/SKILL.md` then `skills/bi-python-knowledge/INDEX.md` | cleaning review artifact / shipped cleaning route |
| 15. Python aggregation / groupby grain review | Python | `skills/bi-python-knowledge/SKILL.md` then `skills/bi-python-knowledge/INDEX.md` | `skills/bi-python-knowledge/checklists/aggregation-grain-checklist.md` |
| 16. Python / pandas dataframe pipeline review | Python | `skills/bi-python-knowledge/SKILL.md` then `skills/bi-python-knowledge/INDEX.md` | analyzer-candidate / review artifact if available; otherwise planned/deferred |
| 17. Python source-prep reasoning | Python | `skills/bi-python-knowledge/SKILL.md` then `skills/bi-python-knowledge/INDEX.md` | relevant shipped or planned route (planned routes deferred) |
| 17a. Decide whether to scale out / choose a compute engine | Big-data | `skills/bi-bigdata-knowledge/SKILL.md` then `skills/bi-bigdata-knowledge/INDEX.md` | `skills/bi-bigdata-knowledge/checklists/engine-selection-checklist.md` |
| 17b. Distributed partitioning / shuffle / skew / large joins | Big-data | `skills/bi-bigdata-knowledge/SKILL.md` then `skills/bi-bigdata-knowledge/INDEX.md` | partitioning-shuffle / join-skew checklist |
| 17c. Aggregate at grain over very large data / incremental & idempotent processing / file formats | Big-data | `skills/bi-bigdata-knowledge/INDEX.md` | aggregation-grain / pipeline-review checklist |
| 17d. Distributed pipeline review / validation & reconciliation at scale / cost-perf diagnosis | Big-data | `skills/bi-bigdata-knowledge/SKILL.md` then `skills/bi-bigdata-knowledge/INDEX.md` | pipeline-review / validation-reconciliation checklist or perf/cost verdict |
| 18. Dashboard design | Dashboard | `.claude/skills/powerbi-dashboard-design/` (see boundary below) | dashboard blueprint |
| 19. Data quality control room | Readiness | `docs/readiness/readiness-model.md` | data issues / blocking reasons |
| 20. BI handoff pack | Readiness | `docs/readiness/publish-ready.md` | BI handoff pack |
| 21. Power BI execution adapter | Roadmap (gated) | `docs/roadmap/roadmap.md` | blocked verdict (gated F016 / execution-only / later) |
| 22. Unknown / ambiguous request | Compass | `COMPASS.md` | clarifying question or blocked verdict |

## Route by symptom (knowledge layer)

If you arrive with a *symptom* rather than a task label, jump straight to the
matching knowledge skill's symptom index — do not diagnose from this file. This
map only points; the cause → checks → fix → stop rule lives in the skill.

| Symptom family | Layer | Open first → then |
|---|---|---|
| Gross and net sales mixed, discount looks double-counted, return rate differs by report, "is this KPI additive?", a tile has no agreed definition, KPI means different things in different reports | Retail KPI | `skills/retail-kpi-knowledge/SKILL.md` → `skills/retail-kpi-knowledge/INDEX.md` → "Symptom routes" → metric-ambiguity / metric-contract-review checklist (planned routes deferred) |
| Totals doubled / inflated, row count changed after a join, COUNT/AVG wrong, reload doubled the data, gold won't reconcile to source, slow-but-correct SQL | SQL | `skills/bi-sql-knowledge/INDEX.md` → "Route by symptom" → PB-SQL-* verdict |
| Measure ignores slicers, total row wrong, YOY/YTD wrong, ranking changes unexpectedly, DISTINCTCOUNT off, measure slow | DAX | `skills/bi-dax-knowledge/INDEX.md` → "Route by symptom" → analyzer-style verdict |
| Messy category/string/currency cleaning, dataframe grain/aggregation question, pandas source-prep review (single-node) | Python | `skills/bi-python-knowledge/SKILL.md` → `skills/bi-python-knowledge/INDEX.md` → cleaning / aggregation-grain review artifact (planned routes deferred) |
| One task runs forever / executor or driver OOM / spill to disk, row count exploded after a large join, thousands of tiny output files, reruns create duplicates, job slow-and-expensive but "works", late data changes yesterday's totals | Big-data | `skills/bi-bigdata-knowledge/SKILL.md` → `skills/bi-bigdata-knowledge/INDEX.md` → "Symptom routes" → join-skew / partitioning-shuffle / pipeline-review / perf-cost verdict |

Supporting references:

- `AGENTS.md` — the short operating contract.
- `COMPASS.md` — the shortest operational entry point.
- `docs/readiness/readiness-pipeline.md` and `docs/architecture/readiness-pipeline.md`
  — the stage sequence and transitions.
- `docs/glossary.md` — terms, abbreviations, and the static rule-id families.
- `docs/faq.md` — common questions, each answer source-cited.
- `docs/worked-examples/README.md` — the two end-to-end worked examples (index).
- `skills/retail-kpi-knowledge/` — the business-meaning reasoning layer (definition,
  additivity, grain, ambiguity, KPI packs). Route here to *reason about and review* a KPI's
  meaning and produce a governed metric contract.
- `skills/bi-bigdata-knowledge/` — the distributed / larger-than-memory execution reasoning
  layer (engine selection, partitioning/shuffle/skew, distributed joins & aggregation, file
  formats, incremental, scale validation). The scale-out sibling of `bi-python-knowledge`;
  route here only when the data is too large for a single node.
- `docs/metrics/retail-kpi-catalog.md` — the generic retail KPI *menu* (F009: intent +
  typical binding) to copy a starting contract from. The menu lists candidates; the
  `retail-kpi-knowledge` skill governs and reviews their meaning. They do not compete: menu
  = what KPIs exist, skill = what each one means and whether its contract is complete.
- Smoke test: `docs/quality/agent-routing-smoke-test.md` — a manual routing/governance check for this layer.

Dashboard design: `.claude/skills/powerbi-dashboard-design/` exists and is the
route (the design vocabulary/router; the gated "design from approved contracts"
verb is `.claude/skills/dashboard-design/`, with supporting docs in
`docs/powerbi/`). There is no `skills/powerbi-dashboard-design/`.

Power BI execution: route to `docs/roadmap/roadmap.md` and treat as gated **F016
/ execution-only / later**. Do not create execution docs.

## Routing boundaries

- **Readiness** owns stage and gating.
- **Retail KPI knowledge** owns the *business meaning* of a KPI: definition, additivity,
  grain, required fields, ambiguity resolution, owner rulings, and KPI-pack selection.
  It produces a governed metric contract and hands off to **all four** implementation
  layers — SQL (fields/grain/transform/reconciliation), DAX (the measure), Python
  (single-node source-prep of the required fields), Big-data (distributed/at-scale
  aggregation & reconciliation). It never writes DAX/SQL/Python, grants readiness,
  or designs dashboards. Initial seed (10 live contracts); planned KPIs stay deferred.
- **SQL knowledge** owns SQL correctness and reconciliation reasoning.
- **DAX knowledge** owns measures, DAX review, and DAX model prerequisites — it
  *implements* a ready business contract from Retail KPI knowledge; it does not define or
  redefine a KPI's business meaning.
- **Python knowledge** assists with pandas/dataframe source-prep reasoning, cleaning,
  and aggregation-grain review (single-node), and may produce review artifacts and
  source-prep evidence. It is an initial seed; planned routes stay deferred. It does not
  execute Python, run notebooks, define metrics, approve readiness gates, or replace SQL/DAX.
- **Big-data knowledge** owns distributed / larger-than-memory execution reasoning —
  engine selection, partitioning/shuffle/skew, distributed joins & aggregation, file
  formats, incremental/idempotent processing, validation & cost at scale. The scale-out
  sibling of Python; it borrows the shared grain/additivity spine rather than redefining it,
  and does not run jobs, define metric meaning, write SQL/DAX, or grant readiness.
- **Dashboard design** owns visual/page design after metric contracts.
- **Execution adapters** cannot define mappings, metrics, semantic logic, or
  dashboard design.

Cross-layer guards: a metric-*meaning*/definition request (what a KPI means, its
additivity/grain/ambiguity) routes to **Retail KPI knowledge** (not DAX, not Python); a
measure-*implementation* request for a ready contract routes to DAX (and DAX must stop
and route back to Retail KPI if no upstream business contract exists — it does not invent
the meaning); a SQL transformation/reconciliation request routes to SQL/readiness (not
Python); a readiness-gate approval routes to readiness (not Retail KPI, not Python); a
dashboard-design request routes to dashboard design (not Retail KPI, not Python); a
data-processing request routes to **Python if it fits on one machine** and to **Big-data
only when it is genuinely too large for single-node** (Big-data must route back to Python
if the honest answer is "this fits on one machine", and may recommend pushing the work down
to SQL/warehouse instead of scaling out).

## Do not use this map for

- learning SQL from scratch
- learning DAX from scratch
- learning Python/pandas from scratch
- learning Spark/big-data engineering from scratch (it routes scale-out reasoning; it does not teach Spark)
- learning retail KPIs from scratch (it routes to KPI meaning; it does not teach retail)
- running database queries
- executing Python or running notebooks
- running Spark/distributed jobs (Big-data is reasoning only; it never runs jobs)
- scaling out work that fits on a single machine (route to Python first)
- publishing Power BI
- approving mappings automatically
- replacing human business decisions
- bypassing readiness gates
- treating the Python layer as complete (it is an initial seed)
- treating the Retail KPI layer as complete (it is an initial seed: 10 live contracts)
- redefining a KPI's business meaning inside the DAX layer (meaning lives in Retail KPI)
- treating C086 as a generic schema
