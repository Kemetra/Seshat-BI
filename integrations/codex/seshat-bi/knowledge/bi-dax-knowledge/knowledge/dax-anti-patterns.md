# DAX Anti-Patterns

> The mistakes that produce wrong numbers, slow models, or unmaintainable code. Each entry:
> the anti-pattern, why it's wrong, and the correct move. The agent should flag these on
> review and never emit them on generation. IDs map to `analyzer-rules.json`.

## Context & correctness

### AP-001 — Time-intelligence functions inside iterators
```dax
-- WRONG: DATESYTD used inside SUMX row context
SUMX ( 'Product', CALCULATE ( [Sales Amount], DATESYTD ( 'Date'[Date] ) ) )  -- often fine but costly
SUMX ( 'Sales', DATESYTD ( 'Date'[Date] ) )                                  -- WRONG: TI func as scalar
```
**Why:** TI table functions depend on filter context and fire implicit context transitions per
row; misused as scalars they error or mislead. **Fix:** put TI functions in `CALCULATE` filter
args or a `VAR`, and iterate dimensions only when you genuinely need per-row context transition.

### AP-002 — Confusing scalar and table date functions
Using `EOMONTH` as a `CALCULATE` filter, or `ENDOFMONTH` in a scalar expression; using
`DATEADD`/`PREVIOUSDAY` just to add/subtract a day. **Fix:** day math = `'Date'[Date] - 1`;
month-end scalar = `EOMONTH`; month-end *filter* = `ENDOFMONTH`. Check the return type: only
table functions are time-intelligence functions.

### AP-003 — Assuming CALCULATE filters intersect
Expecting `CALCULATE([Sales], 'Product'[Color]="Red")` to *narrow* an existing Color selection.
It **replaces** the Color filter. **Fix:** wrap in `KEEPFILTERS` when you mean "and also".

### AP-004 — Relying on row context to cross relationships
Writing a calculated column like `'Sales'[Qty] * RELATED('Product'[Price])` is fine, but
expecting a bare row context (no `RELATED`, no context transition) to filter another table is
wrong. **Fix:** use `RELATED`/`RELATEDTABLE`, or trigger context transition via a measure/`CALCULATE`.

### AP-005 — Measure totals that don't add up (non-additive measures shown additively)
Segmentation, distinct counts, and ranking are **non-additive**: the total row is not the sum
of the visible rows. Leaving the engine to "sum" them silently gives a wrong/odd total.
**Fix:** compute at the correct grain and aggregate explicitly (iterate years/segments and sum),
or accept and document the non-additive total. Decide intent on purpose.

### AP-006 — Forgetting to guard divide-by-zero / future dates
`[Margin] / [Sales]` errors on zero; a running total shows a flat line into the future.
**Fix:** `DIVIDE(...)`; compare `MIN('Date'[Date])` against the last date with data and return
`BLANK()` beyond it.

### AP-007 — Using a non–date-marked table for time intelligence
TI functions silently misbehave if the Date table isn't marked (or you don't add
`REMOVEFILTERS('Date')` manually). **Fix:** Mark as Date Table (BP-001), or add the modifier.

### AP-008 — Bi-directional relationships as a default
Turning on bi-di to "make filtering work" creates ambiguous paths, surprising totals, and
performance cliffs. **Fix:** keep single-direction; apply the cross-filter you actually need
per measure with `CROSSFILTER` or model with `TREATAS`.

## Performance

### AP-020 — Iterating measures over fact-grain tables
`SUMX('Sales', [Some Measure])` forces a context transition per fact row (millions).
**Fix:** iterate the dimension you actually group by, or convert to column arithmetic / a
single `CALCULATE`.

### AP-021 — `FILTER(WholeTable, …)` where a column predicate suffices
```dax
CALCULATE ( [Sales], FILTER ( 'Product', 'Product'[Color] = "Red" ) )   -- materializes table
CALCULATE ( [Sales], 'Product'[Color] = "Red" )                          -- column filter, faster
```
Use `FILTER` only when the condition involves a measure or multiple columns that can't be a
simple predicate. **Fix:** prefer column predicates; when you must `FILTER`, filter the
smallest column/table possible (e.g. `FILTER(VALUES('Product'[Color]), …)`).

### AP-022 — High-cardinality calculated columns
Storing a near-unique calculated column (e.g. a per-row concatenated key, or a full-precision
datetime) inflates the model and kills compression. **Fix:** split datetime, reduce precision,
push to the source/ETL, or compute as a measure.

### AP-023 — Repeating an expensive subexpression instead of using VAR
Calling `[Expensive Measure]` five times in one formula evaluates it up to five times.
**Fix:** `VAR x = [Expensive Measure]` once, reuse `x`.

### AP-024 — Nested/over-broad `ALL` clears more than intended
`CALCULATE([Sales], ALL('Sales'))` or `ALL('Date')` when you only meant to clear one column.
**Fix:** clear the specific column(s) with `REMOVEFILTERS('Date'[Day of Week])`, or use
`ALLEXCEPT` to keep what must survive.

## Maintainability

### AP-030 — Copy-pasted arithmetic across measures
Re-deriving `Quantity * Price` in many measures means inconsistent fixes later.
**Fix:** one base measure; compose.

### AP-031 — Unqualified column refs / qualified measure refs (the reverse of the convention)
`[Net Price]` (column) and `'Sales'[Sales Amount]` (measure) read backwards and invite the
"a measure and column share a name" ambiguity bug. **Fix:** `'Sales'[Net Price]` and `[Sales Amount]`.

### AP-032 — Giant single formula with no variables or comments
Unreadable, unreviewable, unteachable. **Fix:** decompose with named `VAR`s and intent comments.

### AP-033 — Implicit measures (drag a column into values to auto-aggregate)
Hidden, unnamed, inconsistent logic scattered across visuals. **Fix:** define explicit measures.
