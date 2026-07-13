---
name: bi-dax-knowledge
description: >-
  DAX knowledge base for teaching a BI agent to reason about, generate, review, and
  performance-tune DAX for Power BI / tabular models. Use when the task involves writing
  or auditing DAX measures, building time-intelligence / segmentation / ranking / customer
  / currency calculations, reviewing a semantic model, or explaining DAX concepts and
  pitfalls. Covers core concepts, best practices, anti-patterns, performance notes, a
  curated pattern library, reusable metric contracts, and machine-checkable analyzer rules.
---

# BI DAX Knowledge

A teaching + reference layer for a Business Intelligence agent working with DAX. It separates
**explanation** (Markdown, for reasoning and teaching) from **structured rules** (JSON, for
precise generation and automated review).

## When to use this skill

Trigger for any of: writing a DAX measure or calculated column; reviewing/auditing existing
DAX; building time intelligence (YTD, YOY, rolling, running totals), segmentation, ABC, ranking,
new/returning customers, events-in-progress, what-if parameters, or currency conversion;
reviewing a semantic model for DAX prerequisites; or explaining a DAX concept/pitfall.

## How to use it (recommended workflow)

1. **Ground the model.** Read `references/retail-schema.md`. Map the user's real
   tables/columns onto these roles, or substitute their model. Never assume column names.
2. **Reason from concepts first.** `knowledge/dax-core-concepts.md` is the mental model
   (filter vs row context, context transition, CALCULATE, VAR, ALLSELECTED, lineage). Most
   bugs are concept errors, not syntax errors.
3. **Pick the pattern.** Find the matching entry in `patterns/dax-patterns.json` (or read a
   worked version in `knowledge/dax-retail-examples.md`). Use its `dax_shape`, `key_rule`,
   `when_to_use`, `avoid_when`, and `common_mistakes`.
4. **Instantiate via a metric contract.** `patterns/metric-contract-patterns.json` gives the
   structured spec (grain, additivity, required model features, validation, phase support).
   Define the contract before writing code.
5. **Generate or review against the rules.** Apply `patterns/analyzer-rules.json` while
   generating, and as a checklist when auditing. Respect `knowledge/dax-best-practices.md`
   and avoid everything in `knowledge/dax-anti-patterns.md`.
6. **Tune.** Use `knowledge/dax-performance-notes.md` to choose between equivalent
   formulations and to explain *why* a rewrite is faster.

## Phases the agent supports

- **generate** — scaffold correct DAX from a metric contract + pattern.
- **analyze** — audit existing DAX/measures against `analyzer-rules.json`.
- **model_review** — check the semantic model for a contract's prerequisites (marked Date
  table, snapshot facts, disconnected param tables, config-table integrity, etc.).

Each pattern (`future_agent_use`) and contract (`phase_support`) declares which phases it serves.

## File map

```
bi-dax-knowledge/
├─ SKILL.md                         ← this file (interface)
├─ INDEX.md                         ← the router (open after this file)
├─ README.md                        ← overview, scope, boundaries
├─ references/
│  ├─ retail-schema.md              ← the fictional model all examples use
│  └─ source-map.md                 ← attribution + how content was derived
├─ knowledge/                       ← Markdown: teaches the agent (read for reasoning)
│  ├─ dax-core-concepts.md          ← concise on-ramp + index to the deep dives
│  ├─ dax-evaluation-context-deep-dive.md  ← CC-001..003,008,009,018 (Definitive Guide, Slice 1)
│  ├─ dax-calculate-deep-dive.md           ← CC-004..006,010,011,016,019 (Definitive Guide, Slice 1)
│  ├─ dax-function-semantics.md            ← per-function return type/blank/gotchas (Definitive Guide, Slice 2)
│  ├─ dax-engine-internals.md              ← SE vs FE, callbacks, VertiPaq/cardinality (Definitive Guide, Slice 3)
│  ├─ dax-performance-diagnostics.md       ← triage workflow + 8 diagnostic playbooks (Slice 3)
│  ├─ dax-best-practices.md         ← BP-xxx rules
│  ├─ dax-anti-patterns.md          ← AP-xxx mistakes
│  ├─ dax-performance-notes.md      ← intro perf primer (the "why" lives in engine-internals)
│  └─ dax-retail-examples.md        ← worked original examples
├─ patterns/                        ← JSON: precise reusable rules (read for generation/review)
│  ├─ dax-patterns.json             ← 20-pattern library (per-pattern schema)
│  ├─ metric-contract-patterns.json ← 21 reusable metric specs (+ concept links, phase support)
│  ├─ analyzer-rules.json           ← 20 enforceable AR-xxx rules (+ detectability/required_inputs/promoted_from)
│  └─ analyzer-rule-candidates.json ← ARC-xxx candidates; 10 promoted, 6 still staged (analyzer_v2/human)
└─ checklists/                      ← short copy-me checklists (the artifact a route ends on)
   ├─ metric-contract-checklist.md  ← fill a metric contract before writing DAX
   ├─ dax-measure-review-checklist.md ← pre-merge review of a measure
   └─ dax-model-review-checklist.md ← semantic-model DAX prerequisites

references/agent-training-set.md   ← graded Q&A bank (36 items, 7 categories) for teaching/eval
references/agent-training-set.json  ← machine-gradeable twin (same items)
```

## Cross-reference scheme

- Best practices: `BP-xxx` · Anti-patterns: `AP-xxx` · Analyzer rules: `AR-xxx`.
- Patterns link to contracts via `related_metric_contract`; contracts link back via
  `maps_to_patterns`; analyzer rules link to BP/AP docs via `refs`.

## Scope and boundaries

- Depth is **code + key rules**: the highest-value patterns with templates, rules, and
  original examples — not an exhaustive reproduction of any book.
- All DAX is **original teaching code on the fictional retail schema**. No verbatim
  copyrighted code or sample model is reproduced. See `references/source-map.md`.
- This is a knowledge layer, not an execution engine: it does not run queries against a
  live model. Pair it with the user's model metadata for concrete generation/review.
