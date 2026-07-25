---
name: bi-python-knowledge
description: >
  Python/pandas reasoning and review layer for BI and data agents in the Seshat BI
  project. Use when an agent must reason about dataframe work — profiling a source,
  judging dtypes/schema, cleaning and standardizing, merging without fan-out,
  aggregating at a declared grain, parsing dates, validating/reconciling against
  SQL and readiness, diagnosing performance/memory, or reviewing a Python pipeline.
  This is a reasoning layer, not an executor and not a Python tutorial. It does not
  run pipelines, define metrics, or own gating. See INDEX.md for the live routes.
---

# BI Python Knowledge Skill

A thin router into a Python/pandas reasoning layer for BI/data agents. It helps an
agent **think correctly** about dataframe work and **hand off cleanly** into the
SQL, DAX, readiness, and dashboard layers. It does not execute code or define
business meaning.

> **Status: core routes live.** Dataframe semantics, profiling, dtypes, missing
> values, cleaning, merge/fan-out, aggregation grain, dates/calendars, validation,
> performance, active-rule review, positive patterns, and pipeline review all resolve
> through `INDEX.md`.

## Use this skill when

Source profiling, dtype/schema issues, cleaning and standardization, merge/fan-out
reasoning, groupby/grain reasoning, null handling, date parsing, validation /
reconciliation preparation, Python pipeline review, or performance/memory diagnosis.

## Do not use this skill for

Metric definition, DAX measures, SQL transformation logic, readiness approval,
dashboard design, or Power BI execution. Those belong to other layers (see boundaries
below). Reason up to your edge, then hand off.

## Mandatory workflow

1. **Open `INDEX.md`.** Do not read the whole knowledge base.
2. **Pick the smallest route** that matches the task or symptom.
3. **Open only the file(s)** that route names.
4. **End on the route's named artifact** — a checklist, a JSON pattern set, or an
   analyzer-style verdict. Never end on an open-ended explanation.
5. **Stop at boundaries.** If the task is metric definition, semantic logic, SQL
   transformation, or gating, hand off.

```
SKILL.md  ->  INDEX.md  ->  only the named file(s)  ->  artifact / checklist / verdict
```

## What this layer owns

Dataframe / pandas / source-prep reasoning and Python pipeline review.

## What this layer does NOT own

- **Readiness** owns stage and gating.
- **SQL knowledge** owns SQL reasoning, SQL reconciliation, SQL transformation logic.
- **Retail KPI knowledge** owns metric meaning and contracts.
- **DAX knowledge** owns measures and semantic-model prerequisites for ready contracts.
- **Dashboard design** owns visual/page design after metric contracts.
- **Execution adapters** run things; they never define meaning, mapping, metrics,
  semantic logic, or approval.

## Global stop rules

- Do not clean data before source meaning and grain are understood.
- Do not merge dataframes before join keys and cardinality are known.
- Do not aggregate before declaring grain and additivity.
- Do not infer business meaning from column names alone.
- Do not claim reconciliation passed without evidence.
- Do not fill nulls, coerce dtypes, or join frames without an evidence ledger.
- Do not write production pipeline code in this layer.
- Do not use Python to bypass SQL/readiness validation gates.
- Do not read the whole knowledge base when a router can select files.
- Do not copy book examples or prose. See `references/copyright-safety.md`.

## Conventions

- ID families and their meaning: `references/id-conventions.md`.
- Copyright rules for all content: `references/copyright-safety.md`.
- All examples use the fictional retail schema in `references/retail-dataframe-schema.md`.
