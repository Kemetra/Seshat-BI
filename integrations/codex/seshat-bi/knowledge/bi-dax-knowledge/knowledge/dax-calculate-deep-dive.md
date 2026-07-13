# DAX CALCULATE — Deep Dive

> `CALCULATE` is the only function that changes filter context, and almost every non-trivial
> measure depends on understanding exactly how it does so. This file teaches the agent to predict
> CALCULATE behavior precisely. Concise summary lives in `dax-core-concepts.md` §3; this is the
> depth. Examples use the reference retail schema (`references/retail-schema.md`). Original
> teaching material — no book text or examples reproduced.

Concept cards in this file: **CC-004, CC-005, CC-006, CC-010, CC-011, CC-016, CC-019.**
(Cross-reference: CC-008 expanded tables and table-vs-column filters live in the evaluation-context
deep dive; CC-012 table-vs-column filters is summarized here in CC-005's perf note.)

---

## CC-004 — CALCULATE evaluation order

**What it is.** `CALCULATE ( <expression>, <filter1>, <filter2>, … )` evaluates the expression in a
filter context modified by the filter arguments. The order is fixed and worth memorizing:

1. **Filter arguments are evaluated first**, in the *outer* (current) filter context — before any
   change is applied. (Variables declared outside also captured their values in this same outer
   context.)
2. **Context transition** happens next, if `CALCULATE` is running inside a row context (CC-003).
3. **Filter arguments are applied.** By default each one **replaces** any existing filter on the
   same column(s) — it does not intersect.
4. **The expression is evaluated** in the resulting context.

**Why it matters.** It explains "why did my filter override the slicer?", why a filter argument
sees the *old* context (useful for `MAX('Date'[Date])`-style captures), and exactly where
`KEEPFILTERS` changes the story (step 3 → intersect instead of replace).

**Common mistake.** Assuming filter arguments are evaluated in the *new* context, or that they
narrow (intersect) an existing selection. Both are wrong by default.

**Retail example.**
```dax
Sales vs Audio :=
VAR AllAudio = CALCULATE ( [Sales Amount], 'Product'[Category] = "Audio" )  -- replaces any Category filter
RETURN AllAudio
```
On a row already filtered to `Category = "Video"`, this still returns Audio sales — the predicate
replaced the Video filter (step 3).

**Analyzer candidate.** ARC-CALC-01 — filter expected to intersect but replaces (extends
AR-CALC-001).

**Phases.** analyzer, generator, human guidance.

---

## CC-005 — Predicate filter is sugar for FILTER(ALL(column), …)

**What it is.** A boolean filter argument such as `'Product'[Color] = "Red"` is shorthand for
`FILTER ( ALL ( 'Product'[Color] ), 'Product'[Color] = "Red" )`. The hidden `ALL` on the filtered
column is precisely *why* a simple predicate replaces (overrides) that column's existing filter.

**Why it matters.** It demystifies replace-vs-intersect and frames the **table-vs-column filter**
performance choice (a column predicate is a storage-engine-friendly filter; `FILTER(wholeTable,…)`
materializes more — see perf note below).

**Deeper behavior.**
- The implicit `ALL` is scoped to the *column(s)* in the predicate, not the whole table.
- A multi-column predicate (e.g. referencing two columns) expands to `FILTER(ALL(col1,col2),…)`
  and replaces filters on both.
- To **intersect** instead of replace, wrap in `KEEPFILTERS` (CC-006).

**Common mistake.** Not realizing the predicate clears that column's filter; or writing
`FILTER('Product', 'Product'[Color]="Red")` (table filter) when a column predicate suffices.

**Perf note (table vs column filter, CC-012).** Prefer `CALCULATE([m], 'Product'[Color]="Red")`
(column filter, pushed to the storage engine) over `CALCULATE([m], FILTER('Product', …))`
(materializes a filtered table in the formula engine). Use `FILTER` only when the condition needs
a measure or several columns; then filter the smallest thing, e.g. `FILTER(VALUES('Product'[Color]),…)`.

**Retail example.**
```dax
Red Sales (keeps other Product filters too) :=
CALCULATE ( [Sales Amount], KEEPFILTERS ( 'Product'[Color] = "Red" ) )
```

**Analyzer candidate.** ARC-CALC-02 (implicit ALL unintended) · ARC-PERF-03 (FILTER where predicate
suffices, extends AR-PERF-002).

**Phases.** analyzer, generator.

---

## CC-012 — Table filters vs column filters

**What it is.** A *column filter* is a predicate on a single column (`'Product'[Color] = "Red"`,
which CC-005 shows desugars to `FILTER(ALL('Product'[Color]), …)`). A *table filter* is a
`FILTER` over a whole table (`FILTER('Product', …)` or `FILTER('Sales', …)`). They are
semantically close but have very different cost.

**Why it matters.** A column filter is a small, storage-engine-friendly set the engine can push
down; a table filter materializes a (potentially large) filtered table in the formula engine.
Choosing the column form is the single most common DAX performance lever (see
`dax-engine-internals.md` for SE vs FE).

**Key rule.** Prefer `CALCULATE([m], 'Product'[Color] = "Red")` (column filter) over
`CALCULATE([m], FILTER('Product', …))` (table filter). Use `FILTER` only when the condition needs
a measure or several columns, and then iterate the smallest thing —
`FILTER(VALUES('Product'[Color]), …)`, not the whole fact.

**Common mistake.** Wrapping a simple column constant in `FILTER(wholeTable, …)`; iterating
`FILTER('Sales', …)` over fact grain when a dimension column predicate would do.

**Analyzer candidate.** ARC-PERF-03 (FILTER where a predicate suffices, extends AR-PERF-002).

**Phases.** analyzer, generator.

---

## CC-006 — CALCULATE modifiers (USERELATIONSHIP, CROSSFILTER, KEEPFILTERS, ALL-in-CALCULATE)

**What it is.** Special arguments that change *how* filtering works rather than *what* is filtered.
They are the safe, surgical alternatives to blanket model changes (like bidirectional
relationships) and manual hacks.

- **`KEEPFILTERS(<filter>)`** — apply the filter by **intersecting** with the existing context
  instead of replacing. Use whenever a computed/explicit filter must respect the user's selection.
- **`USERELATIONSHIP(col1, col2)`** — activate an *inactive* relationship for this evaluation
  (role-playing dates: analyze by DeliveryDate instead of the active OrderDate). See CC-016.
- **`CROSSFILTER(col1, col2, direction)`** — change cross-filter direction (`OneWay`, `Both`,
  `None`) for this evaluation only — the per-measure alternative to a model-wide bidirectional
  relationship.
- **`ALL/REMOVEFILTERS/ALLEXCEPT` used as CALCULATE modifiers** — remove filters as part of the
  filter-application step (clearer intent than passing big table filters).

**Why it matters.** These let the agent express precise intent and avoid the correctness/perf
traps of bidirectional relationships and over-broad table filters.

**Common mistake.** Turning on a model-wide bidirectional relationship to "make filtering work"
instead of a scoped `CROSSFILTER`; forgetting `USERELATIONSHIP` for role-playing dates; using
`ALL('Table')` when only one column should be cleared.

**Retail example.**
```dax
-- Analyze sales by the date the order was delivered (inactive relationship)
Sales by Delivery Date :=
CALCULATE (
    [Sales Amount],
    USERELATIONSHIP ( 'Sales'[DeliveryDate], 'Date'[Date] )
)

-- Intersect a computed top-product set with the user's current selection
Sales Top Products :=
CALCULATE (
    [Sales Amount],
    KEEPFILTERS ( TOPN ( 10, VALUES ( 'Product'[ProductKey] ), [Sales Amount], DESC ) )
)
```

**Analyzer candidate.** ARC-MODEL-01 (bidirectional default) · ARC-REL-01 (role-playing date not
using USERELATIONSHIP).

**Phases.** analyzer, generator, model_review, human guidance.

---

## CC-015 — Relationship cross-filter direction and ambiguity

**What it is.** A relationship propagates filters from the *one* side to the *many* side by
default (single direction). *Cross-filter direction* (single vs both) decides whether filters
also flow back the other way. When two tables can reach each other by more than one path, the
engine faces **ambiguity** and either disables a path or refuses to evaluate deterministically.

**Why it matters.** Filter propagation is what makes a measure slice correctly across
dimensions; getting direction or path wrong silently changes results or kills performance. The
scoped, per-measure controls live in CC-006 (`CROSSFILTER`, `USERELATIONSHIP`); this concept is
the *model-level* picture they operate on.

**Key rule.** Keep relationships single-direction by default and reach across with a scoped
`CROSSFILTER`/`USERELATIONSHIP` or `TREATAS` (CC-010) rather than a model-wide bidirectional
relationship. Avoid creating two active paths between the same tables (ambiguity).

**Common mistake.** Turning on a model-wide bidirectional relationship "to make filtering work,"
which introduces ambiguity and over-broad propagation; leaving two active paths between tables.

**Analyzer candidate.** ARC-MODEL-01 (bidirectional default, promoted to AR-BIDI-001) ·
ARC-REL-01 (role-playing relationship).

**Phases.** analyzer, model_review, human guidance.

---

## CC-010 — Data lineage & TREATAS

**What it is.** Every column value carries **data lineage** — a tag for which model column it came
from. A table produced by `VALUES('Product'[ProductKey])` still filters the model on ProductKey.
`TREATAS ( <table>, <targetColumn> )` re-stamps the lineage of an arbitrary table onto a chosen
model column, creating a "virtual relationship."

**Why it matters.** It is the clean, fast way to apply a **disconnected/configuration table** as a
filter and to bridge tables without enabling bidirectional relationships.

**Deeper behavior.**
- The number/order of `TREATAS` target columns must match the source table's columns.
- It is generally faster and clearer than `INTERSECT` or `CONTAINS`-based filtering.
- Because the result has real lineage, it propagates through relationships like any other filter.

**Common mistake.** Using `INTERSECT`/bidirectional relationships where `TREATAS` is clearer; or
applying a disconnected table without giving it correct lineage (so it filters nothing).

**Retail example.**
```dax
-- A disconnected parameter table buckets categories; apply it as a real filter on Product
Sales for Selected Buckets :=
CALCULATE (
    [Sales Amount],
    TREATAS ( VALUES ( 'Category Bucket'[Category] ), 'Product'[Category] )
)
```

**Analyzer candidate.** ARC-LINEAGE-01 — disconnected/config table applied without TREATAS/correct
lineage.

**Phases.** analyzer, generator, human guidance.

---

## CC-011 — VALUES vs DISTINCT vs FILTERS vs HASONEVALUE / SELECTEDVALUE

**What it is.** Several subtly different ways to read "what is in the current context":
- **`VALUES(col)`** — distinct values visible in the current filter context, **including** a blank
  row if the relationship has invalid/missing keys.
- **`DISTINCT(col)`** — like `VALUES` but **excludes** the auto-generated blank row.
- **`FILTERS(col)`** — the values actually being *filtered* on that column (what's applied), which
  can differ from what's visible.
- **`HASONEVALUE(col)`** — TRUE when exactly one value is in context.
- **`SELECTEDVALUE(col, alternate)`** — returns the single value in context, or `alternate` when
  zero or many — the concise replacement for `IF(HASONEVALUE(col), VALUES(col), alternate)`.

**Why it matters.** Picking the wrong one silently changes totals (blank row in/out) and breaks
single-selection logic (titles, parameter reads, conditional measures).

**Common mistake.** `IF(HASONEVALUE('Store'[Channel]), VALUES('Store'[Channel]))` with no
alternate, instead of `SELECTEDVALUE('Store'[Channel], "All Channels")`; or using `VALUES` where a
blank row throws off a count.

**Retail example.**
```dax
Channel Label := SELECTEDVALUE ( 'Store'[Channel], "All Channels" )
```

**Analyzer candidate.** ARC-STYLE-01 — `IF(HASONEVALUE,VALUES)` idiom → `SELECTEDVALUE`.

**Phases.** analyzer, generator, human guidance.

---

## CC-016 — Active vs inactive relationships

**What it is.** Between any two tables, at most one relationship can be **active** (used
automatically for filter propagation). Additional **inactive** relationships exist in the model but
only filter when explicitly activated via `USERELATIONSHIP` inside `CALCULATE`.

**Why it matters.** Role-playing dimensions — most commonly dates (OrderDate vs DeliveryDate) — and
any multi-role dimension depend on this. A measure "not filtering" is often an unactivated inactive
relationship.

**Deeper behavior.**
- The active relationship is what plain measures use; switching requires `USERELATIONSHIP` (CC-006).
- You cannot have two active relationships between the same tables; design which role is the default.

**Common mistake.** Expecting an inactive relationship (e.g. `'Sales'[DeliveryDate]` → `'Date'`) to
filter without activation, then concluding "DAX is broken."

**Retail example.** See CC-006's `Sales by Delivery Date`. Without `USERELATIONSHIP`, that measure
would silently report by OrderDate.

**Analyzer candidate.** ARC-REL-01 — role-playing date not activated with USERELATIONSHIP.

**Phases.** analyzer, model_review, human guidance.

---

## CC-019 — REMOVEFILTERS / ALL / ALLEXCEPT as filter removers

**What it is.** The family that *removes* filters during CALCULATE's filter-application step.
- **`ALL(table | column[s])`** — returns a table ignoring filters on the target; as a CALCULATE
  modifier it clears those filters. Reads as "all rows," so it doubles as a table function.
- **`REMOVEFILTERS(table | column[s])`** — clears filters with no return-value intent. Same effect
  as `ALL` inside CALCULATE but *clearer*: it says "remove these filters" and nothing else.
- **`ALLEXCEPT(table, keepCol[s])`** — clears all filters on a table *except* the listed columns —
  the safe way to "reset everything but keep what matters."

**Why it matters.** Most "running total / percent / grand total" measures hinge on clearing the
*right* filters and no more. Over-broad clearing is a top correctness bug; under-clearing leaves
stale filters.

**Deeper behavior.**
- Clearing a whole table (`ALL('Date')`) removes filters on **every** column of that table —
  including ones a slicer set. If you need to keep one (say Day of Week), use `ALLEXCEPT` or clear
  only the specific column: `REMOVEFILTERS('Date'[Date])`.
- `ALL` vs `ALLSELECTED`: `ALL` ignores *all* filters (grand total); `ALLSELECTED` respects what
  the user selected outside the visual (visible total). See CC-009 in the evaluation-context deep
  dive — choosing wrong is the classic percent-of-total bug.
- Prefer `REMOVEFILTERS` when you only intend to clear (intent is unambiguous); reserve `ALL` for
  when you actually want the returned table.

**Common mistake.** `CALCULATE([m], ALL('Date'))` to "ignore the date" while a Day-of-Week slicer
should still apply — it silently clears that slicer too.

**Retail example.**
```dax
% of Grand Total Sales :=
DIVIDE ( [Sales Amount], CALCULATE ( [Sales Amount], REMOVEFILTERS ( 'Product' ) ) )

Sales Ignoring Year Only :=
CALCULATE ( [Sales Amount], ALLEXCEPT ( 'Date', 'Date'[Day of Week] ) )  -- keep weekday, drop the rest
```

**Analyzer candidate.** ARC-ALL-01 — over-broad ALL clearing more than intended (extends
AR-ALL-001).

**Phases.** analyzer, generator, human guidance.

---

## The CALCULATE checklist (apply to every CALCULATE)

1. **Filter args:** evaluated in the *outer* context — is that what I want captured?
2. **Transition:** am I inside a row context? Will it convert a row into a filter here?
3. **Replace vs intersect:** does each filter replace the column (default), or do I need
   `KEEPFILTERS`?
4. **Clears:** are `ALL/REMOVEFILTERS/ALLEXCEPT` scoped to the right columns (CC-008 expanded
   tables: a table filter clears all of a table's columns)?
5. **Relationships:** correct active relationship? need `USERELATIONSHIP`/`CROSSFILTER`? config
   table applied via `TREATAS` with correct lineage (CC-010)?
6. **Single-value reads:** using `SELECTEDVALUE(col, default)` rather than fragile idioms (CC-011)?

---

## Agent reasoning questions (Slice 1 — CALCULATE)

Use these to train/verify reasoning. Each: prompt · expected reasoning · expected answer ·
concepts · analyzer candidates.

1. *"Does `CALCULATE([Sales Amount], 'Date'[Year]=2025)` honor a Year slicer set to 2024?"*
   → Predicate = `FILTER(ALL('Date'[Year]),…)`, replaces the column filter. **No — returns 2025.**
   Concepts CC-004, CC-005. Candidate ARC-CALC-01.
2. *"How do I restrict to Red while keeping the user's other Color choices?"*
   → Need intersection, not replace. **`KEEPFILTERS('Product'[Color]="Red")`.** CC-006. AR-CALC-001.
3. *"`CALCULATE([m], 'Product')` vs `CALCULATE([m], 'Product'[Color]="Red")` — what's the difference?"*
   → Table filter reapplies the whole expanded table (clears all Product columns); column predicate
   touches only Color. **Table form clears more; usually slower.** CC-005, CC-008. ARC-PERF-03.
4. *"A measure should ignore the date but keep the Day-of-Week slicer. `ALL('Date')` ok?"*
   → `ALL('Date')` clears every Date column incl. weekday. **Use `ALLEXCEPT('Date','Date'[Day of Week])`
   or `REMOVEFILTERS('Date'[Date])`.** CC-019. ARC-ALL-01.
5. *"Sales by delivery date returns order-date numbers. Why?"*
   → DeliveryDate relationship is inactive. **Wrap in `CALCULATE(…USERELATIONSHIP('Sales'[DeliveryDate],'Date'[Date]))`.**
   CC-016, CC-006. ARC-REL-01.
6. *"I have a disconnected bucket table; applying it as a filter does nothing. Why?"*
   → No lineage to a model column. **Apply via `TREATAS(VALUES('Bucket'[Category]),'Product'[Category])`.**
   CC-010. ARC-LINEAGE-01.

---

## Links — files to update in later slices (not now)

- `dax-function-semantics.md` (Slice 2) — exact return types/gotchas for `CALCULATE`, `FILTER`,
  the `ALL*` family, `VALUES/DISTINCT/FILTERS`, `SELECTEDVALUE`, `TREATAS`.
- `dax-performance-diagnostics.md` (Slice 3) — table-vs-column filter and context-transition cost
  feed the "slow measure" playbook.
- `patterns/analyzer-rules.json` — only `analyzer_v1` candidates promoted from
  `analyzer-rule-candidates.json` after review; nothing merged in this slice.
- `patterns/metric-contract-patterns.json` — add optional `concepts:[CC-xxx]` links once the card
  set stabilizes.
