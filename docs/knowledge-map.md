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
| 12. Metric contract definition | DAX | `skills/bi-dax-knowledge/INDEX.md` | metric contract |
| 13. Semantic model readiness | DAX + Readiness | `skills/bi-dax-knowledge/INDEX.md` + `docs/readiness/semantic-model-ready.md` | model-review checklist / semantic model handoff |
| 14. Python cleaning / standardization review | Python | `skills/bi-python-knowledge/SKILL.md` then `skills/bi-python-knowledge/INDEX.md` | cleaning review artifact / shipped cleaning route |
| 15. Python aggregation / groupby grain review | Python | `skills/bi-python-knowledge/SKILL.md` then `skills/bi-python-knowledge/INDEX.md` | `skills/bi-python-knowledge/checklists/aggregation-grain-checklist.md` |
| 16. Python / pandas dataframe pipeline review | Python | `skills/bi-python-knowledge/SKILL.md` then `skills/bi-python-knowledge/INDEX.md` | analyzer-candidate / review artifact if available; otherwise planned/deferred |
| 17. Python source-prep reasoning | Python | `skills/bi-python-knowledge/SKILL.md` then `skills/bi-python-knowledge/INDEX.md` | relevant shipped or planned route (planned routes deferred) |
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
| Totals doubled / inflated, row count changed after a join, COUNT/AVG wrong, reload doubled the data, gold won't reconcile to source, slow-but-correct SQL | SQL | `skills/bi-sql-knowledge/INDEX.md` → "Route by symptom" → PB-SQL-* verdict |
| Measure ignores slicers, total row wrong, YOY/YTD wrong, ranking changes unexpectedly, DISTINCTCOUNT off, measure slow | DAX | `skills/bi-dax-knowledge/INDEX.md` → "Route by symptom" → analyzer-style verdict |
| Messy category/string/currency cleaning, dataframe grain/aggregation question, pandas source-prep review | Python | `skills/bi-python-knowledge/SKILL.md` → `skills/bi-python-knowledge/INDEX.md` → cleaning / aggregation-grain review artifact (planned routes deferred) |

Supporting references:

- `AGENTS.md` — the short operating contract.
- `COMPASS.md` — the shortest operational entry point.
- `docs/readiness/readiness-pipeline.md` and `docs/architecture/readiness-pipeline.md`
  — the stage sequence and transitions.
- Smoke test: `docs/quality/agent-routing-smoke-test.md` — a manual routing/governance check for this layer.

Dashboard design: `.claude/skills/powerbi-dashboard-design/` exists and is the
route (the design vocabulary/router; the gated "design from approved contracts"
verb is `.claude/skills/dashboard-design/`, with supporting docs in
`docs/powerbi/`). There is no `skills/powerbi-dashboard-design/`.

Power BI execution: route to `docs/roadmap/roadmap.md` and treat as gated **F016
/ execution-only / later**. Do not create execution docs.

## Routing boundaries

- **Readiness** owns stage and gating.
- **SQL knowledge** owns SQL correctness and reconciliation reasoning.
- **DAX knowledge** owns measures, DAX review, and DAX model prerequisites.
- **Python knowledge** assists with pandas/dataframe source-prep reasoning, cleaning,
  and aggregation-grain review, and may produce review artifacts and source-prep
  evidence. It is an initial seed; planned routes stay deferred. It does not execute
  Python, run notebooks, define metrics, approve readiness gates, or replace SQL/DAX.
- **Dashboard design** owns visual/page design after metric contracts.
- **Execution adapters** cannot define mappings, metrics, semantic logic, or
  dashboard design.

Cross-layer guards: a metric-definition request routes to DAX (not Python); a SQL
transformation/reconciliation request routes to SQL/readiness (not Python); a
readiness-gate approval routes to readiness (not Python); a dashboard-design request
routes to dashboard design (not Python).

## Do not use this map for

- learning SQL from scratch
- learning DAX from scratch
- learning Python/pandas from scratch
- running database queries
- executing Python or running notebooks
- publishing Power BI
- approving mappings automatically
- replacing human business decisions
- bypassing readiness gates
- treating the Python layer as complete (it is an initial seed)
- treating C086 as a generic schema
