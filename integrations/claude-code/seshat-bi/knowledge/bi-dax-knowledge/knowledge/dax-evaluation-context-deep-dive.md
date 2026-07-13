# DAX Evaluation Context — Deep Dive

> The reasoning core. Almost every "wrong number" in DAX is an evaluation-context error, not a
> syntax error. This file teaches the agent to *name the context* at any point in a formula and
> predict the result. Concise on-ramp lives in `dax-core-concepts.md`; this is the depth behind it.
> Examples use the reference retail schema (`references/retail-schema.md`). Original teaching
> material — no book text/examples reproduced.

Concept cards in this file: **CC-001, CC-002, CC-003, CC-007, CC-008, CC-009, CC-018.**

---

## CC-001 — Filter context

**What it is.** The set of filters active on the model when an expression is evaluated. It
restricts which rows of each table are *visible*. Sources: visual rows/columns, slicers, page/
report filters, and `CALCULATE` filter arguments.

**Mental model.** A measure result is always the answer to: *"this expression, given these
filters."* Before predicting any measure value, the agent should be able to state the filter
context in one sentence.

**Why it matters.** It is the first diagnostic question for any incorrect result. If you can't
name the context, you can't explain the number.

**Deeper behavior.**
- Filter context flows across relationships from the one-side to the many-side (default
  single-direction). Filtering `'Product'` filters `'Sales'`; not the reverse, by default.
- Multiple filters on different columns combine by intersection.
- A filter on a column is a *set of allowed values* for that column.

**Common mistake.** Believing a measure "just sums the column," ignoring that the visual's row/
column/slicer context is silently filtering it.

**Retail example.** In a matrix with `'Product'[Category]` on rows, `[Sales Amount]` on the
"Audio" row evaluates `SUMX('Sales', Quantity*Net Price)` over only the Sales rows whose product
is in Audio — because the row contributes a filter `'Product'[Category] = "Audio"`.

**Analyzer candidate.** ARC-CTX-01 — measure correctness depends on an unstated filter-context
assumption (human_review; high FP risk).

**Phases.** analyzer (assist), human guidance.

---

## CC-002 — Row context

**What it is.** A "current row" cursor. It exists in (a) calculated columns and (b) iterators
(`SUMX`, `FILTER`, `ADDCOLUMNS`, `AVERAGEX`, …). It lets you read column values for the current
row. It does **not**, by itself, filter the model.

**Why it matters.** Explains why `SUMX('Sales', 'Sales'[Quantity] * 'Sales'[Net Price])` works,
and why a bare row context does *not* reach across a relationship to filter another table.

**Deeper behavior.**
- Row context does not automatically follow relationships. To read a related one-side value use
  `RELATED`; to read many-side rows use `RELATEDTABLE` (which is `CALCULATETABLE` + transition).
- Nested row contexts: an iterator inside an iterator creates two row contexts. To reference an
  outer row's value from an inner iterator, **capture it in a `VAR`** (the modern replacement for
  the old `EARLIER` function — see CC card note below).

**Common mistake.** Expecting a row context to filter a different table (e.g. assuming iterating
`'Sales'` will "see" a filtered `'Product'`), or reaching for `EARLIER` instead of a `VAR`.

**Retail example.**
```dax
-- For each product, count products with higher sales (calculated column)
Product[Higher Selling Count] =
VAR CurrentSales = [Sales Amount]                       -- captured in this row's context
RETURN
    COUNTROWS ( FILTER ( ALL ( 'Product' ), [Sales Amount] > CurrentSales ) )
```
`CurrentSales` is the outer row's value; inside `FILTER`'s row context we compare against it
without `EARLIER`.

**Analyzer candidate.** ARC-CTX-02 — row-context reference assumed to cross-filter another table.

**Phases.** analyzer (assist), human guidance.

---

## CC-003 — Context transition

**What it is.** When `CALCULATE` runs inside a row context (explicitly, or implicitly because you
referenced a *measure*), it converts the current row context into an equivalent filter context.
Every measure is wrapped in an implicit `CALCULATE`, so **calling a measure inside an iterator
triggers a transition.**

**Why it matters.** It is *the* concept that explains "why does iterating a measure give per-row
results?" — and it is the most common hidden performance cost.

**Deeper behavior.**
- Transition applies the *entire* current row as a filter, including all columns. On a table with
  a unique key, it filters down to that one entity.
- Transition cost is paid *per iteration*. Over a high-cardinality table (the fact), this is
  millions of filter-context constructions.
- Transition can also re-introduce filters you thought you removed — be deliberate.

**Common mistake.** `SUMX('Sales', [Sales Amount])` — transitions per fact line (slow and usually
not what's meant). Compare with `SUMX(VALUES('Customer'[CustomerKey]), [Sales Amount])` which
transitions once per customer (intended granularity).

**Retail example.**
```dax
-- Average sales per customer: transition per customer, not per fact row
Avg Sales per Customer :=
AVERAGEX ( VALUES ( 'Customer'[CustomerKey] ), [Sales Amount] )
```

**Analyzer candidate.** ARC-PERF-01 — measure iterated at fact grain (extends AR-PERF-001).

**Phases.** analyzer, generator, human guidance.

---

## CC-007 — Variables are constants + lazy evaluation

**What it is.** A `VAR` is evaluated **once**, at the point of declaration, in the filter/row
context that exists *there* — then reused as an immutable constant. Unused variables are not
evaluated at all (lazy).

**Why it matters.** Variables are the idiomatic, reliable way to **capture an outer-context value
before a later `CALCULATE` changes the context** (the modern replacement for `EARLIER` in nested
row contexts), and a primary performance lever (compute an expensive subexpression once).

**Deeper behavior.**
- A variable does **not** re-evaluate under a later context change — that's the whole point when
  you want the "before" value, and a trap if you expected the "after" value.
- Capturing `MAX('Date'[Date])` in a `VAR` *outside* a `CALCULATE` freezes the last visible date
  for use *inside* the modified context.
- Reusing a `VAR` avoids recomputation within that evaluation (pairs with the SE/FE story in
  `dax-engine-internals.md`).

**Common mistake.** Referencing an expensive measure several times in one formula instead of a
`VAR`; or expecting a variable to reflect a context that changes after its declaration.

**Retail example.**
```dax
Sales RT :=
VAR LastVisibleDate = MAX ( 'Date'[Date] )      -- captured in the OUTER context
RETURN
    CALCULATE ( [Sales Amount], 'Date'[Date] <= LastVisibleDate )
```

**Analyzer candidate.** ARC-PERF-02 / AR-PERF-003 — repeated expensive subexpression not captured
in a VAR.

**Phases.** analyzer, generator, human guidance.

---

## CC-008 — Expanded tables

**What it is.** A conceptual model: a base table "expands" to include the columns of all tables on
the one-side of its relationships. Filtering any expanded column filters the base table. This is
the engine's actual mental model of relationships (more accurate than "runtime join").

**Why it matters.** Explains *why* filtering a dimension filters the fact, why table filters behave
as they do, and how context transition interacts with related tables.

**Deeper behavior.**
- `'Sales'` expands to include `'Product'[*]`, `'Customer'[*]`, `'Store'[*]`, `'Date'[*]` (the
  one-sides). A filter on `'Product'[Category]` is, in expanded terms, a filter on `'Sales'`.
- A table filter like `CALCULATE([m], 'Product')` applies the expanded `'Product'` as a filter —
  which is broader than a single-column filter and replaces filters on *all* of Product's columns.
- This is why "table filters vs column filters" (CC-012, in the CALCULATE deep-dive) matters for
  both correctness and performance.

**Common mistake.** Reasoning about relationships as SQL joins and being surprised when a table
filter clears more than expected.

**Retail example.** `CALCULATE ( [Sales Amount], 'Product' )` removes any existing filter on every
`'Product'` column (because the whole expanded table is reapplied), unlike
`CALCULATE ( [Sales Amount], 'Product'[Color] = "Red" )` which touches only Color.

**Analyzer candidate.** — (human guidance; hard to detect statically).

**Phases.** human guidance.

---

## CC-009 — Shadow filter context & ALLSELECTED

**What it is.** Iterators leave behind a "shadow" filter context that records the rows they
iterated. `ALLSELECTED` reads that shadow: it returns values as filtered *outside* the current
visual — honoring slicers and report filters, but ignoring the filters the current visual's own
rows/columns impose.

**Why it matters.** It is the backbone of "percentage of the visible total" and "running total
within what the user selected." It is also the **most error-prone** filter function, because its
result depends on the surrounding iteration/visual in subtle ways.

**Deeper behavior.**
- `ALL(col)` → grand total across *everything*. `ALLSELECTED(col)` → total across *what the user
  currently sees*. Choosing the wrong one is the classic percent-of-total bug.
- Without parameters, `ALLSELECTED()` restores the shadow context for the whole visual.
- Because it depends on shadow contexts created by enclosing iterators, test it in the actual
  visual; don't assume.

**Common mistake.** Using `ALLSELECTED` like `ALL` (or vice versa), producing a denominator that
ignores or over-includes the user's selection.

**Retail example.**
```dax
% of Visible Category Sales :=
DIVIDE (
    [Sales Amount],
    CALCULATE ( [Sales Amount], ALLSELECTED ( 'Product'[Category] ) )   -- visible categories only
)
```
Swap `ALLSELECTED` for `ALL` and the denominator becomes *all* categories regardless of slicers.

**Analyzer candidate.** ARC-CTX-03 — ALL vs ALLSELECTED scope mismatch.

**Phases.** analyzer (assist), generator, human guidance.

---

## CC-018 — Circular dependency & auto-exist

**What it is.** Two related runtime behaviors:
- **Circular dependency** — calculated columns/measures whose definitions reference each other (or
  themselves through relationships) can fail to refresh; DAX detects and rejects cycles.
- **Auto-exist** — when a query filters multiple columns *of the same table*, the engine
  intersects only the combinations that actually exist in the data, rather than the full Cartesian
  product.

**Why it matters.** Auto-exist explains "missing combinations" results that look like a bug but
aren't; circular-dependency understanding prevents unrefreshable models.

**Deeper behavior.**
- Auto-exist applies within a single table's columns; cross-table behavior differs. It is usually
  helpful (no empty Category×Color cells) but can surprise when you *expected* all combinations.
- Circular dependencies often arise from calculated columns that use `CALCULATE`/measures whose
  filter context loops back to the same column.

**Common mistake.** Assuming a matrix will show every `Category × Color` pair; auto-exist drops
pairs with no rows. Or: building a calculated column with a measure that depends on that column.

**Retail example.** A `Category × Color` matrix of `[Sales Amount]` shows only pairs that occur in
`'Sales'` (e.g. no "Audio × Pink" row if none sold) — auto-exist at work, not a filter mistake.

**Analyzer candidate.** — (human guidance; subtle).

**Phases.** human guidance.

---

## Diagnostic drill — "name the context"

When reviewing any measure, the agent should answer, in order:
1. **Filter context?** What do the visual rows/columns, slicers, and outer `CALCULATE`s filter?
2. **Row context?** Are we in a calculated column or iterator? Whose row?
3. **Transition?** Does a measure call / `CALCULATE` convert a row into a filter here?
4. **Clears?** Do `ALL/REMOVEFILTERS/ALLSELECTED` change the context — and is the scope right?
5. **Propagation?** Which tables get filtered via relationships / expanded tables?

If those five are answered correctly, the result is predictable — and most bugs reveal themselves
at one specific step. The diagnostic playbooks in `dax-performance-diagnostics.md` (Slice 3) will
build on this.

---

## Agent reasoning questions (Slice 1 — evaluation context)

Each: prompt · expected reasoning · expected answer · concepts · analyzer candidates.

1. *"Matrix with Category on rows. What does `[Sales Amount]` see on the Audio row?"*
   → The row contributes a filter `'Product'[Category]="Audio"`. **Audio-only sales.** CC-001.
2. *"Why does `SUMX('Sales',[Sales Amount])` differ from `SUM` and run slowly?"*
   → Calling a measure inside the iterator triggers context transition per fact row. **Per-line
   transitions; expensive and usually unintended.** CC-003. Candidate ARC-PERF-01.
3. *"In a calculated column on Product, can I reference `'Sales'` rows directly with a row context?"*
   → A bare row context doesn't cross relationships. **Use `RELATEDTABLE`/a measure (transition) —
   not the row context alone.** CC-002, CC-008.
4. *"Why does a Category × Color matrix omit some pairs?"*
   → Auto-exist intersects only existing combinations. **It's expected, not a filter bug.** CC-018.
5. *"For 'percent of the categories the user selected', do I use `ALL` or `ALLSELECTED` in the
   denominator?"*
   → Visible total honors the selection. **`ALLSELECTED('Product'[Category])`.** CC-009. ARC-CTX-03.
6. *"I want each product's rank vs all products inside a calculated column without `EARLIER`."*
   → Capture the current row's value in a `VAR`, then iterate `ALL`. **Use a `VAR` for the outer
   row value.** CC-002.

---

## Links — files to update in later slices (not now)

- `dax-core-concepts.md` — keep as the concise on-ramp; it now points here (updated this slice).
- `dax-engine-internals.md` (Slice 3) — will explain *why* context transition over a fact table is
  costly (storage vs formula engine).
- `dax-performance-diagnostics.md` (Slice 3) — hosts the playbooks that operationalize the
  "name the context" drill.
- `patterns/analyzer-rule-candidates.json` — staged candidates referenced above (created this
  slice; not merged into the live rules file).
