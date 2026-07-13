# Source Map & Attribution

## Primary source

- **DAX Patterns, 2nd edition** — Marco Russo & Alberto Ferrari, SQLBI Corp., 2020.
  ISBN 978-1-7353652-0-6. Companion site: https://www.daxpatterns.com
- Supporting concepts: **The Definitive Guide to DAX, 2nd edition** — Russo & Ferrari.

## What was derived, and how

This knowledge base distills the **ideas, rules, structure, and naming of patterns** from the
source, then re-expresses them as original teaching material. Specifically:

- **Concepts, best practices, anti-patterns, performance notes** — paraphrased and reorganized
  in our own words, synthesized with widely established DAX guidance.
- **DAX code** — all measures, columns, and templates shown here are **original code written
  for this knowledge base**, demonstrated on a **fictional retail star schema** of our own
  design (`retail-schema.md`). They illustrate the canonical *shape* of each pattern.
- **Pattern selection** — a curated, high-value subset (≈14 patterns) at "code + key rules"
  depth. This is deliberately **not** an exhaustive reproduction of the book's ~20+ chapters
  and their many variations.

## What was deliberately NOT done (copyright boundary)

- No verbatim copying of the book's DAX code listings (note: the source renders code as
  images, which were not transcribed).
- No reproduction of the book's sample data model, figures, tables, or extended prose.
- No attempt to substitute for the book. Users wanting full coverage, every variation, and the
  authors' complete explanations should buy **DAX Patterns** and use **daxpatterns.com**.

## Pattern → source chapter map

| pattern_id | Source chapter (DAX Patterns 2nd ed.) |
|---|---|
| ti-ytd | Standard time-related calculations |
| ti-py-yoy | Comparing different time periods |
| ti-rolling-12 | Custom time-related calculations |
| cumulative-running-total | Cumulative total |
| semi-additive-balance | Semi-additive calculations |
| static-segmentation | Static segmentation |
| dynamic-segmentation | Dynamic segmentation |
| abc-classification | ABC classification |
| new-returning-customers | New and returning customers |
| related-distinct-count | Related distinct count |
| events-in-progress | Events in progress |
| ranking | Ranking |
| parameter-table-whatif | Parameter table |
| currency-conversion | Currency conversion |

## Enrichment pass — The Definitive Guide to DAX (Slice 1)

- **Source:** *The Definitive Guide to DAX, 2nd edition* — Marco Russo & Alberto Ferrari,
  Microsoft Press, 2019. ISBN 978-1-5093-0697-8.
- **Role:** theory / internals / context-reasoning layer that complements the DAX Patterns
  catalog.
- **What Slice 1 delivered (this pass):**
  - `knowledge/dax-evaluation-context-deep-dive.md` — concept cards CC-001, CC-002, CC-003,
    CC-008, CC-009, CC-018.
  - `knowledge/dax-calculate-deep-dive.md` — concept cards CC-004, CC-005, CC-006, CC-010,
    CC-011, CC-016, CC-019.
  - `knowledge/dax-core-concepts.md` updated to a concise on-ramp/index with deep-dive pointers.
  - `patterns/analyzer-rule-candidates.json` — staged ARC-xxx candidates (NOT merged into the
    enforceable `analyzer-rules.json`).
- **Source chapters distilled (Slice 1):** Ch 4 (evaluation contexts), Ch 5 (CALCULATE &
  modifiers), Ch 10 (working with the filter context), Ch 14–15 (relationships, expanded tables,
  shadow filter contexts) — concepts only.
- **Derivation method:** ideas, rules, and terminology paraphrased in our own words; every code
  example is original and written on the fictional retail schema. No book text, code listings,
  figures, or sample model were reproduced. The PDF is read locally for grounding and is **not**
  added to the repository.
- **Slice 2 delivered (this pass):**
  - `knowledge/dax-function-semantics.md` — per-function semantics (return type, blank handling,
    key rule, gotcha) for the high-leverage function set; return-type quick table; reasoning
    questions. Distilled from Ch 2–3, 7, 10, 12–13 (concepts only).
  - `patterns/analyzer-rule-candidates.json` — added staged candidates ARC-FUNC-01, ARC-FUNC-02
    (still NOT merged into the enforceable rule set).
  - Index/map pointers updated in `dax-core-concepts.md` and `SKILL.md`.
- **Slice 3 delivered (this pass):**
  - `knowledge/dax-engine-internals.md` — Storage Engine vs Formula Engine, CallbackDataID,
    VertiPaq compression & cardinality, `DISTINCTCOUNT` internals (concept cards CC-013, CC-014).
    Distilled from Ch 17–19 (concepts only; no query plans or xmSQL listings reproduced).
  - `knowledge/dax-performance-diagnostics.md` — SE/FE triage workflow and 8 diagnostic playbooks
    (PB-WRONG-TOTAL, PB-IGNORES-SLICER, PB-SLOW-MEASURE, PB-TI-WRONG, PB-BLANK-ZERO,
    PB-PROPAGATION, PB-CONTEXT-TRANSITION, PB-PERCENT-OF-TOTAL).
  - `patterns/analyzer-rule-candidates.json` — added staged candidate ARC-PERF-04 (callbacks).
  - Index/map pointers updated in `dax-core-concepts.md`, `SKILL.md`.
- **Training set delivered (this pass):**
  - `references/agent-training-set.md` + `references/agent-training-set.json` — 36 graded items
    across 7 categories (context reasoning, CALCULATE behavior, function semantics, performance
    smells, measure review, model prerequisites, diagnostic scenarios), each linked to concept
    cards / rules / playbooks, with a 0–3 grading rubric. Original items on the retail schema.
- **Analyzer-rule promotion delivered (this pass):** graduated all 10 `analyzer_v1` candidates
  from `analyzer-rule-candidates.json` into the enforceable `analyzer-rules.json`. 7 enriched
  existing rules (`promoted_from` set on AR-TI-001, AR-CALC-001, AR-PERF-001, AR-PERF-002,
  AR-PERF-004, AR-ALL-001, AR-BIDI-001); 3 added as new rules (AR-REL-001, AR-FUNC-001,
  AR-STYLE-004). The live rule schema gained operational fields (`detectability`,
  `required_inputs`, `related_concepts`, `promoted_from`). The 6 remaining candidates
  (`analyzer_v2` / `human_guidance_only`) stay staged. Now 20 enforceable rules.
- **Enrichment plan status: COMPLETE.** All 7 planned deliverables (concept cards, deep-dive
  files, analyzer candidates, diagnostic playbooks, training set, copyright methodology,
  integration) are built.
- **Optional extensions delivered (this pass):**
  - Linked `concepts:[CC-xxx]` into every metric contract.
  - Added the 6 previously-skipped patterns — week-related (custom calendar), parent-child
    hierarchy, transition matrix, survey, basket analysis, budget-vs-actual — to
    `dax-patterns.json` (now 20 patterns) with matching new metric contracts (now 21) and original
    retail examples (now 19 in `dax-retail-examples.md`). Schema doc extended with the supporting
    tables (Account, Budget, Answers + survey bridge, custom-calendar Date columns, and the
    disconnected helper tables). Source chapters: Week-related, Parent-child hierarchies,
    Transition matrix, Survey, Basket analysis, Budget — distilled, original examples only.

## Recommended further reading

- DAX Patterns (book + daxpatterns.com) — full pattern library with all variations.
- The Definitive Guide to DAX — deep theory (contexts, engines, optimization).
- DAX Guide (https://dax.guide) — per-function reference and return types.

## Provenance note

Generated as a teaching/reference layer for a BI agent on 2026-06-26. Treat the source
attribution above as the authoritative origin of the underlying patterns; treat the code and
examples as original derivative teaching material.
