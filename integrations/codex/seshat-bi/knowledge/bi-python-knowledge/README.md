# BI Python Knowledge

An **initial seed** of a Python/pandas reasoning and review layer for BI and data
agents in the Seshat BI project. It mirrors the SQL and DAX knowledge layers: a thin
router, an index, and focused knowledge files that always end on an artifact
(checklist / JSON patterns / verdict).

> **This layer is not complete yet.** This PR seeds the skeleton, the router, the
> shared references, and a first slice of content. Most knowledge slices are still
> to come — see **Not yet complete** below. The router (`INDEX.md`) marks every
> unbuilt route as *planned / not yet implemented* so nothing points at a missing
> file.

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

## Current seed coverage

This PR ships:

- **Router / shell** — `SKILL.md`, `INDEX.md`, `README.md`.
- **References** — `references/copyright-safety.md`, `references/id-conventions.md`,
  `references/source-map.md`, `references/retail-dataframe-schema.md`.
- **Cleaning and standardization** — `knowledge/cleaning-and-standardization.md`
  (string/category/currency/sentinel/dedup reasoning), ending on its terminal artifact
  `checklists/cleaning-review-checklist.md` (a categorical cleaning verdict + row-count
  ledger).
- **Aggregation / grain checklist** — `checklists/aggregation-grain-checklist.md`
  (a standalone review artifact for groupby work).
- **Analyzer rule candidates** — `patterns/analyzer-rule-candidates.json` (proposed
  rules **only**, not active enforced rules).
- **Training / eval seed** — `references/agent-training-set.json` and
  `references/agent-training-set.md` (a machine-readable plus human-readable Q&A seed
  for evaluating Python reasoning; **a seed/eval set, not proof the layer is
  complete**).

## Not yet complete

The following slices are intended but **not built in this seed**:

- full dataframe mental model
- full dtype / profiling slice
- merge / fan-out slice
- groupby / aggregation knowledge file (the checklist ships; the knowledge file does not)
- dates / calendar slice
- validation / reconciliation slice
- performance / memory slice
- full (active) analyzer rules
- full Markdown training set

## Conventions

- **IDs:** stable families (`PY-CN-*`, `PY-AP-*`, `PY-AR-*`, …) — see
  `references/id-conventions.md`.
- **Examples:** original, fictional retail only — see
  `references/retail-dataframe-schema.md`.
- **Copyright:** no book text, examples, datasets, or domains — see
  `references/copyright-safety.md`.

## Integration status

Repo-level routing (COMPASS / knowledge-map integration) is **intentionally not part
of this PR**. It is wired only after the Python skill is reviewed and stable, the same
way the SQL and DAX layers were added before being routed.
