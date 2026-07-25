# BI Python Knowledge

An expanded Python/pandas reasoning and review layer for BI and data agents in the
Seshat BI project. It mirrors the SQL and DAX knowledge layers: a thin router, an
index, and focused knowledge files that always end on an artifact (checklist / JSON
patterns / verdict).

> **Core routes live.** The router covers dataframe semantics, profiling, dtypes,
> missing values, cleaning, merges, aggregation grain, dates/calendars, validation,
> performance, analyzer-style review, recommended patterns, and pipeline review.

## This is a reasoning layer, not an executor

- It does **not** run pipelines or notebooks.
- It does **not** define metrics, semantic logic, or business meaning.
- It does **not** own stage/gating (readiness does).
- It is **not** a generic Python tutorial.

It helps an agent reason about dataframe work — profiling, dtypes, cleaning, merge
fan-out, groupby grain, dates, validation, performance — and hand off cleanly into
the SQL, DAX, readiness, and dashboard layers. It is the pandas/dataframe/source-prep
reasoning counterpart to `bi-sql-knowledge` and `bi-dax-knowledge`.

## The flow

```
SKILL.md  ->  INDEX.md  ->  relevant file(s)  ->  artifact / checklist / verdict
```

Always start at `SKILL.md`, then `INDEX.md`. Let the router select the file(s) you
need. Do not read the whole `knowledge/` directory.

## Current live coverage

- **Semantics and provenance** — dataframe role, grain, identity, alignment, and
  deterministic transformation boundaries.
- **Source inspection** — structure, candidate keys, missingness, cardinality,
  ranges, and observation-versus-expectation.
- **Dtypes and schema** — logical/storage type separation, precision, identifiers,
  booleans, categories, and drift classification.
- **Missing values** — null/blank/sentinel classification with named-decision stops.
- **Cleaning and standardization** — strings, categories, currency, units,
  sentinels, and duplicates with a row-count ledger.
- **Joins and fan-out** — declared input grains, cardinality, unmatched keys,
  multiplicity, and post-merge controls.
- **Aggregation and grain** — additive behavior, groupby grain, and reconciliation.
- **Dates and calendars** — parse validity, timezone, business date, fiscal/ISO
  calendar roles, and snapshot-policy stops.
- **Validation and reconciliation** — independent controls, scope/tolerance parity,
  segment checks, and governed evidence handoff.
- **Performance and memory** — measured single-node diagnosis, SQL pushdown, and
  Big Data boundary decisions.
- **Active/candidate patterns** — evidence-based active rules, recommended positive
  patterns, and separately labeled proposed candidates.
- **Review artifacts** — dataframe, cleaning, merge/fan-out, aggregation,
  validation/reconciliation, and pipeline-review checklists.
- **Worked example/eval assets** — fictional trace and the original training seed;
  neither is observed project evidence.

## Extension rule

New capabilities are not implied by this pack. They must add a task or symptom route,
focused resource, terminal artifact, stable IDs where applicable, reviewed public
classification, and route-contract evidence.

## Conventions

- **IDs:** stable families (`PY-CN-*`, `PY-AP-*`, `PY-AR-*`, …) — see
  `references/id-conventions.md`.
- **Examples:** original, fictional retail only — see
  `references/retail-dataframe-schema.md`.
- **Copyright:** no book text, examples, datasets, or domains — see
  `references/copyright-safety.md`.

## Integration status

`COMPASS.md` and `docs/knowledge-map.md` route Python work into this layer. Public
Claude and Codex copies are generated from canonical files only after explicit
allowlist review.
