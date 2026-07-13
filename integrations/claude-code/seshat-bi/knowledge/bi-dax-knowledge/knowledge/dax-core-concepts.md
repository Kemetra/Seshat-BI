# DAX Core Concepts

> Purpose: give the BI agent the mental model it must hold *before* applying any pattern.
> Patterns are surface; these concepts are why the patterns work. If the agent reasons
> from these concepts, it can adapt a pattern safely instead of pasting it blindly.
>
> **This file is the concise on-ramp.** For the deep reasoning layer, follow the pointers below.

## Deep dives (read when you need depth)

This page gives the short version. Two deep-dive files carry the full reasoning layer, with
concept cards (`CC-xxx`), worked retail examples, common mistakes, checklists, agent reasoning
questions, and links to staged analyzer-rule candidates (`patterns/analyzer-rule-candidates.json`):

- **`dax-evaluation-context-deep-dive.md`** — filter context, row context, context transition,
  expanded tables, shadow filter contexts & `ALLSELECTED`, auto-exist. *(CC-001…003, 008, 009, 018)*
- **`dax-calculate-deep-dive.md`** — CALCULATE evaluation order, predicate-vs-table filters,
  replace-vs-intersect, `KEEPFILTERS`, `REMOVEFILTERS`/`ALL`/`ALLEXCEPT`, modifiers
  (`USERELATIONSHIP`, `CROSSFILTER`), data lineage & `TREATAS`, `VALUES`/`SELECTEDVALUE`, active vs
  inactive relationships. *(CC-004…006, 010, 011, 016, 019)*
- **`dax-function-semantics.md`** — per-function reference: return type (scalar vs table), blank
  handling, key rule, and gotcha for `CALCULATE`/`FILTER`, the `ALL*` family,
  `VALUES`/`DISTINCT`/`FILTERS`, `SELECTEDVALUE`/`ISFILTERED`/`ISINSCOPE`, `TREATAS`, iterators,
  `RANKX`, `DIVIDE`, `SUMMARIZECOLUMNS`/`SUMMARIZE`/`ADDCOLUMNS`, and the TI scalar-vs-table split.
- **`dax-engine-internals.md`** — Storage Engine vs Formula Engine, CallbackDataID, VertiPaq
  compression & cardinality, `DISTINCTCOUNT` internals. *(CC-013, CC-014)* The "why" behind
  performance.
- **`dax-performance-diagnostics.md`** — the SE/FE triage workflow plus 8 step-by-step diagnostic
  playbooks (wrong total, ignores slicer, slow measure, TI wrong, blank vs zero, propagation,
  context transition, percent-of-total).

Graded Q&A bank for teaching/eval: `references/agent-training-set.md` (+ machine-gradeable
`references/agent-training-set.json`).

## 1. The two evaluation contexts

Every DAX expression is evaluated inside a combination of two contexts. Confusing them is
the single most common source of wrong numbers.

**Filter context** — the set of filters currently applied to the model (from slicers, rows,
columns, visual filters, and `CALCULATE`). It restricts *which rows of each table are visible*.
Measures live and breathe in filter context.

**Row context** — a "current row" pointer. It exists inside calculated columns and inside
iterators (`SUMX`, `AVERAGEX`, `FILTER`, `ADDCOLUMNS`, …). A row context does **not** filter
the model by itself; it just lets you reference column values for the current row.

Key consequence: a row context alone does **not** propagate across relationships or filter
other tables. Only filter context filters the model.

## 2. Context transition (the concept that explains CALCULATE)

> → Deep dive: `dax-evaluation-context-deep-dive.md` (CC-003), incl. the per-row cost and the
> "iterate the dimension, not the fact" rule.

When `CALCULATE` (or an implicit context transition) runs inside a row context, it converts
the current row context into an equivalent filter context. This is **context transition**.

- Referencing a *measure* inside an iterator triggers an automatic context transition,
  because every measure is wrapped in an implicit `CALCULATE`.
- This is why `SUMX ( Customer, [Sales Amount] )` gives per-customer sales summed up — each
  iteration transitions the current customer row into a filter on that customer.
- Context transition is powerful but expensive at high cardinality. Iterating a measure over
  millions of rows forces millions of transitions.

**Rule of thumb:** want a per-entity calculation? Iterate the entity dimension and call a
measure. Want raw arithmetic over fact rows? Iterate the fact with column references only
(no measure, no transition).

## 3. CALCULATE — the only function that changes filter context

> → Deep dive: `dax-calculate-deep-dive.md` (CC-004…006, 019) — evaluation order, predicate sugar,
> replace-vs-intersect, modifiers, and the CALCULATE checklist.

`CALCULATE ( <expression>, <filter1>, <filter2>, … )` evaluates the expression in a filter
context modified by the filter arguments. Mechanics, in order:

1. Filter arguments are evaluated (in the *outer* filter context).
2. Context transition happens (if inside a row context).
3. Filter arguments are applied — by default they **replace** existing filters on the same
   columns (not intersect).
4. The expression is evaluated.

Two filter-argument forms:
- **Predicate form**: `CALCULATE ( [Sales], 'Product'[Color] = "Red" )` — syntax sugar for
  `FILTER ( ALL ( 'Product'[Color] ), 'Product'[Color] = "Red" )`. Note it uses `ALL` on that
  column, so it *overrides* an existing Color filter.
- **Table form**: `CALCULATE ( [Sales], <table expression> )` — the table becomes the filter.

### KEEPFILTERS — intersect instead of replace
Wrap a filter argument in `KEEPFILTERS` to **intersect** with the existing filter rather than
replacing it. Essential whenever a pattern must respect the user's current selection (e.g.
dynamic segmentation, restricting to a computed customer set while honoring slicers).

### REMOVEFILTERS / ALL — clear filters
`REMOVEFILTERS ( <table or column> )` (modern, clearer name) and `ALL(…)` remove filters.
`ALLEXCEPT` removes all filters on a table except the listed columns. `ALLSELECTED` is special
(see §6).

## 4. Variables (VAR / RETURN)

Variables are evaluated **once**, at the point of declaration, in the context where they are
declared — then reused as constants.

Why they matter:
- **Performance**: compute an expensive sub-result once, reference it many times.
- **Readability**: name intermediate steps.
- **Context safety**: a variable captures a value *before* later context changes. This is the
  idiomatic fix for the classic "I wanted the value from the outer context but CALCULATE
  changed it" problem.

```dax
VAR LastVisibleDate = MAX ( 'Date'[Date] )      -- captured in outer context
VAR Result =
    CALCULATE ( [Sales Amount], 'Date'[Date] <= LastVisibleDate )
RETURN Result
```

A variable is immutable; you cannot reassign it. Build a new variable instead.

## 5. Iterators and the X-functions

`SUMX`, `AVERAGEX`, `MAXX`, `MINX`, `RANKX`, `CONCATENATEX`, `FILTER`, `ADDCOLUMNS`, etc.
iterate a table row by row in a row context, then aggregate.

- Use the X-aggregators when the quantity is a row-level expression: `SUMX(Sales, qty*price)`.
- `SUM(col)` is just `SUMX(table, col)` with a single column.
- Remember context transition fires if you call a measure inside the iterator.

## 6. ALLSELECTED and "what the user sees"

> → Deep dive: `dax-evaluation-context-deep-dive.md` (CC-009, shadow filter contexts) and the
> `ALL` vs `ALLSELECTED` note in `dax-calculate-deep-dive.md` (CC-019).

`ALLSELECTED` returns the filter context as defined by the **outside** of the current visual —
i.e. it ignores filters coming from inside the visual (rows/columns) but honors slicers and
report/page filters. It is the backbone of "percentage of visible total" and "running total
within the visual" calculations. Treat it as approximate/context-sensitive and test it; it is
the most subtle of the filter functions.

## 7. Relationships, data lineage, and TREATAS

> → Deep dive: `dax-calculate-deep-dive.md` (CC-010 lineage/TREATAS, CC-016 active vs inactive
> relationships, CC-006 USERELATIONSHIP/CROSSFILTER).

- Filters propagate along relationships from the **one** side to the **many** side by default
  (single-direction). The fact table is filtered by its dimensions.
- **Data lineage**: a column value "remembers" which model column it came from. A table
  produced by `VALUES('Product'[ProductKey])` still filters the model on ProductKey.
- `TREATAS ( <table>, <column> )` re-stamps the lineage of an arbitrary table onto a model
  column — the clean way to apply a configuration/disconnected table as a filter, and to
  activate "virtual relationships."
- `USERELATIONSHIP` activates an inactive relationship inside a `CALCULATE` (e.g. analyze by
  DeliveryDate instead of OrderDate).

## 8. DIVIDE and safe arithmetic

Always use `DIVIDE ( numerator, denominator [, alternate] )` instead of `/`. It returns blank
(or the alternate) on divide-by-zero instead of an error, and is engine-optimized.

## 9. Blank handling

`BLANK()` is not zero. Aggregations ignore blanks; blanks are filtered out of many operations;
`BLANK() = 0` is TRUE in comparisons but blank still displays as empty. Patterns deliberately
return `BLANK()` to hide rows (e.g. future dates in a running total) — preserve that intent.

## 10. The golden mental checklist (apply to every measure)

1. What filter context will this run in (rows, columns, slicers)?
2. Is there a row context? Will a measure reference trigger context transition?
3. Do my `CALCULATE` filters **replace** or should they **intersect** (`KEEPFILTERS`)?
4. Am I clearing the right filters (`REMOVEFILTERS`/`ALL`) and re-applying what must stay?
5. Is the result additive across the rows/total of the target visual? If not, compute at the
   right grain and aggregate explicitly.
6. Could a denominator be zero or a date be in the "future"? Guard it.
