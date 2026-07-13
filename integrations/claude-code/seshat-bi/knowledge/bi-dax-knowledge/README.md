# bi-dax-knowledge

The DAX **reasoning, generation, and review** knowledge layer of Seshat BI. It is the modeling
and metrics brain: it helps an agent define metric contracts, generate correct DAX, audit existing
measures, and check a semantic model's prerequisites — so a governed model with measures bound to
approved contracts is handed to the dashboard layer. It is the DAX counterpart to `bi-sql-knowledge`.

## How to use it

This is a **routed** knowledge base, not a document to read top to bottom.

```text
Router  ->  SKILL.md  ->  INDEX.md  ->  ONLY the relevant file(s)  ->  contract / measure / verdict / checklist
```

1. Start at `SKILL.md` (the interface).
2. Open `INDEX.md` and find the row for your task or symptom.
3. Read only the file(s) that row names.
4. End on an artifact: a metric contract (`patterns/metric-contract-patterns.json`), a generated
   measure shape (`patterns/dax-patterns.json`), an analyzer-style verdict (`patterns/analyzer-rules.json`),
   or a checklist (`checklists/`).

Grounding rule: **establish the filter context first** ("what filters are active when this
measure evaluates, and what does one row of the result mean?"). Most DAX bugs are context errors,
not syntax errors — the counterpart to "state the grain first" in `bi-sql-knowledge`.

## What is here

- **`knowledge/`** — Markdown for reasoning: the core concepts (`CC-xxx`) and deep dives
  (evaluation context, CALCULATE, function semantics, engine internals, performance diagnostics),
  best practices (`BP-xxx`), anti-patterns (`AP-xxx`), a performance primer, and worked original
  retail examples.
- **`patterns/`** — structured JSON: the pattern library (`dax-patterns.json`), reusable metric
  specs (`metric-contract-patterns.json`), enforceable analyzer rules (`AR-xxx`,
  `analyzer-rules.json`), and staged analyzer-rule candidates (`ARC-xxx`). The `AR-*` rules are
  **static skill artifacts** — a generation/review checklist, not a wired runtime analyzer.
- **`references/`** — the fictional retail schema all examples use, the graded training set, and
  the source map / attribution.
- **`checklists/`** — short, copy-me checklists for defining a metric contract, reviewing a
  measure, and reviewing a semantic model's DAX prerequisites.

## Scope

A thinking, generation, and review layer for DAX in Power BI / tabular models: filter vs row
context and context transition; CALCULATE and its modifiers; metric contracts (grain, additivity,
filter behavior, required model features); base-measure composition; time-intelligence
(YTD/YOY/rolling/running totals); ranking, segmentation, ABC, new/returning customers, what-if
parameters, currency conversion; semantic-model prerequisite checks (marked Date table, star
schema, relationships, uniqueness); analyzer-style review; and DAX performance reasoning.

## What this is NOT

- not a DAX tutorial or a chapter-by-chapter book summary;
- not a replacement for any book;
- not a Power BI execution tool, and not a runtime validator — it reasons about DAX, it does
  not run it against a live model;
- not the Power BI publish / execution adapter (F016, gated and execution-only);
- not the SQL layer and not the dashboard/visual-design layer.

## Routing boundaries

| The task is about... | Route to |
|---|---|
| Source mapping / retail pipeline readiness | `source-mapping` / `retail-onboard-table` (readiness spine: `docs/readiness/`) |
| SQL reasoning / profiling / validation / reconciliation / transformation logic | `bi-sql-knowledge` |
| DAX generation / review / performance / model prerequisites | **`bi-dax-knowledge`** (this skill) |
| Dashboard / visual / page design | `powerbi-dashboard-design` |

A validated gold table with a known grain and verified unique keys is the hand-off **into** this
skill: grain and uniqueness feed DAX additivity reasoning. A semantic model whose measures bind to
approved metric contracts is the hand-off **out** to the dashboard-design layer.

## Copyright safety

Every example is an original Seshat BI / retail example on a fictional schema (see
`references/retail-schema.md`). No book text, sample model, or copyrighted DAX is reproduced;
source books were read locally for grounding only and are not in the repository. See
`references/source-map.md`.
