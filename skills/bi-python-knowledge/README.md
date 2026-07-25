# BI Python Knowledge

An expanded Python/pandas reasoning and review layer for BI and data agents in the
Seshat BI project. It mirrors the SQL and DAX knowledge layers: a thin router, an
index, and focused knowledge files that always end on an artifact (checklist / JSON
patterns / verdict).

> **Foundation live; diagnostics still expanding.** Dataframe semantics, profiling,
> dtypes, missing values, cleaning, merges, aggregation grain, and date/calendar
> reasoning are live. The router (`INDEX.md`) keeps every unbuilt diagnostic slice
> explicit as *planned / not yet implemented*.

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
- **Review artifacts** — dataframe, cleaning, merge/fan-out, and aggregation
  checklists.
- **Candidate/eval assets** — proposed analyzer candidates and the original training
  seed; neither proves active enforcement.

## Not yet complete

The following slices remain explicit and **not yet live**:

- validation / reconciliation slice
- performance / memory slice
- active analyzer and positive-pattern catalogs
- end-to-end worked example
- validation and pipeline-review checklists

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
