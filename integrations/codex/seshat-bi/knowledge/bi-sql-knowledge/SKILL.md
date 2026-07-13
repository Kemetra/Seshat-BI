---
name: bi-sql-knowledge
description: >-
  SQL reasoning, validation, reconciliation, transformation, diagnostics, and anti-pattern
  knowledge layer for Seshat BI agents. Use when a task involves reasoning about source SQL:
  source profiling, table grain, keys & uniqueness, joins & fan-out amplification, aggregation
  correctness, COUNT/NULL semantics, deduplication, validation queries, reconciliation queries,
  silver/gold transformation logic, window/date-time analytics, SQL anti-patterns, or basic SQL
  performance reasoning. The SQL counterpart to bi-dax-knowledge. It is a thinking & validation
  layer, not a database executor, runtime validator, dbt/Dagster project, or PostgreSQL
  execution-plan layer.
---

# BI SQL Knowledge (Seshat BI)

A navigational interface to a SQL **reasoning and validation** knowledge base. It teaches an
agent to reason about SQL correctly -- with table **grain** and **aggregation correctness** as
its foundation, the way filter context is the foundation of `bi-dax-knowledge`.

This file is short by design. **It does not contain the knowledge base.** Do not read every
file in this skill. Follow the flow below.

## Mandatory flow (do not skip a step, do not lose the compass)

```text
Router  ->  this SKILL.md  ->  INDEX.md  ->  ONLY the relevant file(s)  ->  output contract / checklist
```

1. **Open `INDEX.md` first.** It routes by task and by symptom to the specific file(s) you need.
2. **Read only what the route names** -- one or two knowledge files, one JSON, one checklist.
   Reading the whole base is an anti-pattern; it wastes context and dilutes the answer.
3. **Ground the grain before anything else.** State what one row of the input/result means
   (`knowledge/sql-core-concepts.md`, SC-003). Most SQL bugs are grain errors.
4. **End on an artifact:** a validation gate (`patterns/sql-validation-patterns.json`, VP-*),
   a checklist (`checklists/`), or a diagnostic verdict (`knowledge/sql-diagnostics-playbook.md`,
   PB-SQL-*). Never end on prose alone.

## What this skill is for

Reasoning about, reviewing, and validating SQL used in BI pipelines: profiling a source;
grain / keys / uniqueness; joins and **fan-out amplification**; aggregation correctness
(`COUNT` / `SUM` / `AVG`, `GROUP BY`); `COUNT` and `NULL` semantics; deduplication; **validation**
and **reconciliation** queries; silver/gold transformation logic (DML, reshaping, cleaning,
set operations, date recipes, gaps/islands, hierarchy, metadata-driven profiling); window and
date/time analytics; SQL anti-patterns; and basic performance reasoning.

## What this skill is NOT for

Not a SQL tutorial; not a chapter-by-chapter book summary; not a replacement for any book;
not a database execution tool; not a runtime validator; not a dbt/Dagster project; not a
PostgreSQL execution-plan layer (deferred -- see `INDEX.md`); not the Power BI dashboard or DAX
layer. It reasons about SQL; it never runs it.

## Routing boundaries (pick the right skill before working)

| The task is about... | Route to |
|---|---|
| Source mapping / retail pipeline readiness | `source-mapping` / `retail-onboard-table` (readiness spine: `docs/readiness/`) |
| SQL reasoning / profiling / validation / reconciliation / transformation logic | **`bi-sql-knowledge`** (this skill) |
| DAX generation / review / performance / model prerequisites | `bi-dax-knowledge` |
| Dashboard / visual / page design | `powerbi-dashboard-design` |

Where it sits in the pipeline:

```text
source -> [source-mapping / retail-onboard-table: mapping / readiness]
       -> [bi-sql-knowledge: profile / validate / reconcile / transform -> silver/gold]
       -> [bi-dax-knowledge: measures / model]
       -> [powerbi-dashboard-design: visuals / pages]
```

A validated gold table with a known grain and verified unique keys is the hand-off to
`bi-dax-knowledge`: grain and uniqueness feed DAX additivity reasoning.

## Stop rules

- **Stop and ask for metadata, do not guess.** When two cheap checks -- a `COUNT(*)` comparison
  and a uniqueness check -- can't localize a problem, request schema/source metadata (primary
  keys, expected grain, null semantics, SLA, expected volumes). Establishing these facts is the
  job; inventing them is not.
- **Stop at the routing boundary.** If the real task is DAX, a dashboard, or source mapping,
  hand off to the skill above instead of answering here.
- **Stop before executing.** This layer produces SQL *reasoning* and *gate shapes*. It does not
  run queries, wire a runtime, build a CLI, or publish anything.
- **Never fake a pass.** Validation/reconciliation results are evidence-based; a gate with no
  evidence is `blocked`, never `pass`.

## ID conventions (full detail in `references/id-conventions.md`)

Concepts `SC-001..070` - anti-patterns `SQL-AP-001..060` - validation gates `VP-*` -
diagnostic playbooks `PB-SQL-01..19` - analyzer-rule candidates `SARC-*` (staged) -
promoted draft analyzer rules `SAR-*` (static draft, not runtime-enforced).

## Boundaries

Not implementation, not database execution, not dbt/Dagster, not a runtime validator
(validation patterns are reasoning templates, not an executing engine), not a replacement for
any book, not the PostgreSQL execution-plan layer. An agent knowledge layer. All examples are
original Seshat BI / retail examples on a fictional schema; no book text or datasets are
reproduced (`references/copyright-safety.md`).
