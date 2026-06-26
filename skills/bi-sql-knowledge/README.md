# bi-sql-knowledge

The SQL **reasoning and validation** knowledge layer of Seshat BI. It is the upstream trust and
transformation brain: it helps an agent profile, validate, reconcile, and transform data so that
a clean, correctly-grained, verified table is handed to the modeling and presentation layers. It
is the SQL counterpart to `bi-dax-knowledge`.

## How to use it

This is a **routed** knowledge base, not a document to read top to bottom.

```text
Router  ->  SKILL.md  ->  INDEX.md  ->  ONLY the relevant file(s)  ->  output contract / checklist
```

1. Start at `SKILL.md` (the interface).
2. Open `INDEX.md` and find the row for your task or symptom.
3. Read only the file(s) that row names.
4. End on an artifact: a validation gate (`patterns/sql-validation-patterns.json`), a checklist
   (`checklists/`), or a diagnostic verdict (`knowledge/sql-diagnostics-playbook.md`).

Grounding rule: **state the grain first** ("one row of this result is one ___"). Most SQL bugs
are grain errors; naming the grain usually reveals them.

## What is here

- **`knowledge/`** -- concept cards (`SC-001..070`), anti-patterns (`SQL-AP-001..060`), the
  consolidated diagnostics playbook (`PB-SQL-01..19`), and the transformation / Cookbook-extension
  notes. Markdown for reasoning.
- **`patterns/`** -- structured JSON: practical pattern cards (`SP-*`), validation/reconciliation
  gate shapes (`VP-*`), staged analyzer-rule candidates (`SARC-*`), and 10 promoted **draft**
  analyzer rules (`SAR-*`). The `SAR-*` rules are **static skill artifacts**, not runtime
  enforcement -- there is no analyzer wired here.
- **`references/`** -- the graded training set (84 items), the source map / attribution, the
  copyright-safety note, and the ID conventions.
- **`checklists/`** -- short, copy-me checklists for review, validation, and reconciliation.

## Scope

A thinking and validation layer for SQL in BI pipelines: source profiling; table grain; keys and
uniqueness; joins and fan-out amplification; aggregation correctness and COUNT/NULL semantics;
deduplication; validation and reconciliation queries; silver/gold transformation logic (DML,
reshaping, string cleaning, set operations, date recipes, gaps/islands, hierarchy, metadata-driven
profiling); window and date/time analytics; SQL anti-patterns; and basic performance reasoning.

## What this is NOT

- not a SQL tutorial or a chapter-by-chapter book summary;
- not a replacement for any book;
- not a database execution tool, and not a runtime validator -- it reasons about SQL, it does
  not run it;
- not a dbt / Dagster project, and not a CLI;
- not the PostgreSQL execution-plan layer (see below);
- not the Power BI dashboard layer and not the DAX layer.

## Routing boundaries

| The task is about... | Route to |
|---|---|
| Source mapping / retail pipeline readiness | `retail-bi` |
| SQL reasoning / profiling / validation / reconciliation / transformation logic | **`bi-sql-knowledge`** (this skill) |
| DAX generation / review / performance / model prerequisites | `bi-dax-knowledge` |
| Dashboard / visual / page design | `powerbi-dashboard-design` |

## Future extension

**PostgreSQL execution-plan reasoning is deferred to a later EP slice.** Engine-specific plan
reading (EXPLAIN/ANALYZE, costs, index/join strategy) is intentionally out of scope here; the
performance content is correctness-oriented reasoning, not plan analysis.

## Copyright safety

Every example is an original Seshat BI / retail example on a fictional schema (`sales`, `product`,
`customer`, `store`, `date`, `branch`, `fact_sales`, `dim_product`, `dim_branch`, `dim_date`). No
book text, recipes, or datasets are reproduced. Source books were read locally for grounding only
and are not in the repository. See `references/copyright-safety.md` and `references/source-map.md`.
