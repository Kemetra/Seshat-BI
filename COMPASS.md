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
| DAX / metric contracts / semantic model prerequisites | `skills/bi-dax-knowledge/SKILL.md` then `skills/bi-dax-knowledge/INDEX.md` | metric contract / semantic model handoff |
| Dashboard / visual design / audience / layout | `.claude/skills/powerbi-dashboard-design/` (gated "design from contracts" verb: `.claude/skills/dashboard-design/`) | dashboard blueprint |
| Power BI execution / publish | STOP unless `semantic_model_ready` and publish gates have passed | blocked verdict or BI handoff pack |
| Unknown or ambiguous task | `docs/knowledge-map.md` | clarifying question or blocked verdict |

Power BI execution remains execution-only and gated: **F016** advances only when
`semantic_model_ready` and the publish gates have passed.

## The knowledge layer

Two reasoning skills are the deepest assets the routes above point into. Both are
*reasoning and validation* layers, never executors — they reason about SQL/DAX,
they never run a query, run DAX, or touch a database.

| Skill | Foundation concept | Use for |
|---|---|---|
| `skills/bi-sql-knowledge/` | **table grain** + aggregation correctness | source profiling, grain/keys/uniqueness, joins & fan-out, COUNT/NULL semantics, dedup, validation & reconciliation queries, silver/gold transform logic, SQL anti-patterns |
| `skills/bi-dax-knowledge/` | **filter context** + context transition | metric contracts, measure generation/review, time-intelligence, ranking/segmentation, semantic-model prerequisites, DAX performance |

Mandatory flow inside either skill: **`SKILL.md` → `INDEX.md` → ONLY the file(s)
the route names → an artifact** (checklist, metric/validation contract, or
analyzer-style verdict). Reading the whole base is an anti-pattern. Each `INDEX.md`
routes by *task* and by *symptom* — enter from the symptom if you have one.

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
