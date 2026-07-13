# DAX Function Semantics — Deep Dive

> Precise behavior of the functions the agent emits and reviews most. For each: **return type**
> (scalar vs table — the single most clarifying property), what it actually does, blank handling,
> the key rule, and the gotcha. This is the function the future **generator** consults before
> emitting code and the **analyzer** consults to judge it. Concise concepts live in
> `dax-core-concepts.md`; the CALCULATE/context mechanics live in the Slice 1 deep dives — this
> file is the per-function reference layer. Examples use the reference retail schema. Original
> teaching material — no book text or examples reproduced. For an exhaustive per-function
> reference (every argument, every version), defer to https://dax.guide.

Concept cards referenced: **CC-004, CC-005, CC-006, CC-010, CC-011, CC-019** (Slice 1) and the
return-type/blank notes below. Slice 2 adds focused function semantics; deeper engine cost lands
in `dax-engine-internals.md` (Slice 3, planned).

---

## 0. The two properties that disambiguate every function

**Return type — scalar or table.** A function returns either a single value (scalar) or a table.
This one fact resolves most confusion:
- Scalar functions can appear where a value is expected (measure body, `IF`, comparisons).
- Table functions appear as `CALCULATE` filter arguments, as arguments to other table functions,
  or in `CALCULATETABLE`/queries.
- **Time intelligence split (recap of BP-031/032):** `DATESYTD`, `DATEADD`, `SAMEPERIODLASTYEAR`,
  `ENDOFMONTH`, `DATESBETWEEN` are **table** functions → only inside `CALCULATE` filters or a VAR.
  `EDATE`, `EOMONTH`, `DATE`, date arithmetic are **scalar** → for row/scalar expressions.

**Blank behavior.** `BLANK()` is not zero but compares equal to zero; aggregations ignore blanks;
many functions add or drop a blank row. Knowing whether a function includes the blank row changes
counts and totals (see `VALUES` vs `DISTINCT`).

---

## CC-017 — Blank semantics (blank vs zero, and the blank row)

**What it is.** DAX has a first-class `BLANK()` that is distinct from zero and from an empty
string, plus a *blank row* the engine adds to a dimension for unmatched (invalid-relationship)
fact rows. Two separate ideas share the word "blank": the **scalar** `BLANK()` value, and the
**blank row** in a table.

**Why it matters.**
- `BLANK()` **compares equal to zero** (`BLANK() = 0` is `TRUE`) but is **not** zero: aggregations
  and `COUNT`/`AVERAGE` *ignore* blanks, so totals and counts differ from treating them as `0`.
- Whether a function **includes or drops the blank row** changes counts and totals. `ALL` keeps
  it; `ALLNOBLANKROW` and `VALUES`/`DISTINCT` differ on whether the blank row appears (see the
  ALL* family and `VALUES` vs `DISTINCT` notes below).
- A measure returning `BLANK()` is **hidden** in a visual (rows/columns collapse), which is often
  desired (suppress empty) but can also hide a bug.

**Key rule.** Decide deliberately: return `BLANK()` to suppress empties; coalesce to `0` (e.g.
`<expr> + 0` or an explicit `IF`) only when a visible zero is intended. Choose `ALL` vs
`ALLNOBLANKROW` based on whether the blank row should participate.

**Common mistake.** Assuming a blank measure is `0` in arithmetic that should show zero; or using
`ALL` where `ALLNOBLANKROW` is needed (or vice-versa) and getting an off-by-the-blank-row count.

**Phases.** analyzer, generator, human guidance.

---

## 1. CALCULATE / CALCULATETABLE

- **Returns:** scalar (`CALCULATE`) / table (`CALCULATETABLE`).
- **Does:** evaluates its expression in a filter context modified by the filter arguments;
  performs context transition if in a row context. Full mechanics in `dax-calculate-deep-dive.md`
  (CC-004).
- **Blank:** returns whatever the expression yields, including `BLANK()`.
- **Key rule:** filter args are evaluated in the *outer* context and **replace** same-column
  filters unless wrapped in `KEEPFILTERS`.
- **Gotcha:** a boolean predicate silently does `FILTER(ALL(column), …)` (CC-005) — it clears that
  column's existing filter. `CALCULATETABLE` is the table-returning sibling; prefer it over
  `FILTER(CALCULATE…)` constructions when you want a filtered table.
- **Retail one-liner:** `CALCULATE ( [Sales Amount], KEEPFILTERS ( 'Product'[Color] = "Red" ) )`.

## 2. FILTER

- **Returns:** table.
- **Does:** iterates a table in a row context and keeps rows satisfying a predicate.
- **Blank:** preserves the blank row only if present in the input table.
- **Key rule:** use `FILTER` only when the condition needs a measure or multiple columns; for a
  simple column constant, use a predicate filter instead (CC-005).
- **Gotcha:** `FILTER('Sales', …)` over the whole fact materializes a large table in the formula
  engine — filter the smallest column set instead, e.g. `FILTER ( VALUES ( 'Product'[Color] ), … )`.
  Nesting `FILTER` over a fact table is a classic slowdown (→ ARC-PERF-03).
- **Retail one-liner:** `CALCULATE ( [Sales Amount], FILTER ( VALUES ( 'Product'[Brand] ), [Margin %] > 0.3 ) )`.

## 3. The ALL* family — ALL / ALLEXCEPT / ALLNOBLANKROW / ALLSELECTED / REMOVEFILTERS

All are **table** functions (except as CALCULATE modifiers, where they act as filter removers).
- **`ALL(table|col[s])`** — ignores filters on the target; returns all distinct rows/values
  (including the blank row for a full table). Doubles as "clear filter" inside `CALCULATE`.
- **`REMOVEFILTERS(table|col[s])`** — clear-only intent; same effect as `ALL` inside `CALCULATE`
  but reads unambiguously (CC-019). Prefer it when you don't need a returned table.
- **`ALLEXCEPT(table, keepCol[s])`** — clears all filters on a table *except* the kept columns.
- **`ALLNOBLANKROW`** — like `ALL` but excludes the blank row added for invalid relationships.
- **`ALLSELECTED(col?)`** — returns values as filtered *outside* the current visual (shadow filter
  context, CC-009): the "visible total." The subtle one — test it.
- **Key rule:** clear the *narrowest* thing that achieves the intent; a table filter clears every
  column of that (expanded) table (CC-008).
- **Gotcha:** `ALL('Date')` wipes a Day-of-Week slicer too; use `ALLEXCEPT('Date','Date'[Day of Week])`
  or `REMOVEFILTERS('Date'[Date])`. `ALL` ≠ `ALLSELECTED` (grand vs visible total) → ARC-CTX-03.
- **Retail one-liner:** `DIVIDE ( [Sales Amount], CALCULATE ( [Sales Amount], ALLSELECTED ( 'Product'[Category] ) ) )`.

## 4. VALUES / DISTINCT / FILTERS

- **Returns:** single-column table (or scalar when one row, via implicit conversion).
- **`VALUES(col)`** — distinct values in the current context, **including** the blank row added for
  invalid/missing relationship keys.
- **`DISTINCT(col)`** — same, but **excludes** that blank row.
- **`FILTERS(col)`** — the values actually being *filtered* on the column (what's applied), which
  can differ from what's visible.
- **Key rule:** pick based on whether the blank row should count; `VALUES` is the usual choice for
  "what's in context," `DISTINCT` when a stray blank would distort a count.
- **Gotcha:** a single-row `VALUES`/`DISTINCT` auto-converts to a scalar; more than one row throws.
  Guard with `HASONEVALUE`/`SELECTEDVALUE`.
- **Retail one-liner:** `CONCATENATEX ( VALUES ( 'Store'[Channel] ), 'Store'[Channel], ", " )`.

## 5. HASONEVALUE / SELECTEDVALUE / ISFILTERED / ISCROSSFILTERED / ISINSCOPE

- **Returns:** boolean (most) / scalar (`SELECTEDVALUE`).
- **`SELECTEDVALUE(col, alternate)`** — single value in context, else `alternate`. Replaces
  `IF(HASONEVALUE(col), VALUES(col), alternate)` (CC-011 → ARC-STYLE-01).
- **`HASONEVALUE(col)`** — exactly one value in context (e.g. guard a total row).
- **`ISFILTERED(col)`** — col is *directly* filtered. **`ISCROSSFILTERED(col)`** — col is filtered
  directly or via another table. **`ISINSCOPE(col)`** — col is used as a grouping level in the
  current visual (best for hierarchy-aware logic).
- **Key rule:** use `SELECTEDVALUE` with a default for labels/parameter reads; use `HASONEVALUE`/
  `ISINSCOPE` to guard totals and hierarchy levels.
- **Gotcha:** `ISFILTERED` ≠ `ISCROSSFILTERED`; a column can be cross-filtered without being
  directly filtered. For "are we on a subtotal row?", prefer `ISINSCOPE` over `HASONEVALUE`.
- **Retail one-liner:** `SELECTEDVALUE ( 'Store'[Channel], "All Channels" )`.

## 6. TREATAS

- **Returns:** table (with re-stamped data lineage).
- **Does:** applies an arbitrary table as a filter on chosen model column(s) — a virtual
  relationship (CC-010).
- **Key rule:** source columns must match target columns in number and order; the result then
  propagates like a real filter.
- **Gotcha:** without correct lineage a disconnected table filters nothing; `TREATAS` is the fix
  (cleaner/faster than `INTERSECT`/`CONTAINS`). → ARC-LINEAGE-01.
- **Retail one-liner:** `CALCULATE ( [Sales Amount], TREATAS ( VALUES ( 'Category Bucket'[Category] ), 'Product'[Category] ) )`.

## 7. Iterators — SUMX / AVERAGEX / MAXX / MINX / RANKX / CONCATENATEX / COUNTX

- **Returns:** scalar (aggregate of a row-level expression).
- **Does:** iterate a table in a row context, evaluate the expression per row, aggregate.
- **Blank:** blanks are skipped by `AVERAGEX` (affects denominator) and ignored by `SUMX`.
- **Key rule:** iterate at the **right grain**. Calling a *measure* inside triggers context
  transition per row (CC-003) — fine over a dimension, costly over the fact.
- **Gotcha:** `SUMX('Sales', [Some Measure])` (transition per line) vs
  `SUMX('Sales', 'Sales'[Quantity]*'Sales'[Net Price])` (pure column math, no transition).
  → ARC-PERF-01.
- **Retail one-liner:** `AVERAGEX ( VALUES ( 'Customer'[CustomerKey] ), [Sales Amount] )`.

## 8. RANKX (focused)

- **Returns:** scalar (the rank).
- **Does:** ranks the current value against an iterated table of values.
- **Key rule:** static rank → calculated column over `ALL`; dynamic rank → measure over
  `ALLSELECTED`; guard the total row with `HASONEVALUE`/`ISINSCOPE`.
- **Gotcha:** default ties are `SKIP` (1,1,3); pass `DENSE` for 1,1,2. The expression argument is
  evaluated in a context transition — ensure it's the measure you intend.
- **Retail one-liner:** `IF ( HASONEVALUE ( 'Product'[ProductKey] ), RANKX ( ALLSELECTED ( 'Product'[Product Name] ), [Sales Amount],, DESC, DENSE ) )`.

## 9. DIVIDE

- **Returns:** scalar.
- **Does:** safe division; returns `alternate` (default `BLANK()`) on divide-by-zero.
- **Key rule:** always prefer over `/` for measure ratios (BP-021).
- **Gotcha:** the third argument lets you return 0 instead of blank when a zero row should still
  display — choose deliberately (interacts with blank-row hiding, CC-017 in Slice 3).
- **Retail one-liner:** `DIVIDE ( [Margin], [Sales Amount] )`.

## 10. Grouping table functions — SUMMARIZECOLUMNS / SUMMARIZE / ADDCOLUMNS / SELECTCOLUMNS

- **Returns:** table.
- **`SUMMARIZECOLUMNS(groupCols, [filters], "Name", expr, …)`** — the modern, efficient grouping
  function for queries; computes grouped expressions in one pass and drops empty combinations.
- **`SUMMARIZE`** — older grouping; **use it only for grouping**, not for adding computed columns
  (computing measures inside `SUMMARIZE` has subtle context pitfalls).
- **`ADDCOLUMNS(table, "Name", expr)`** — extends a table with columns evaluated in the row
  context of `table` (with context transition when calling measures).
- **`SELECTCOLUMNS`** — projects/renames columns; can preserve or drop lineage depending on
  expressions.
- **Key rule:** prefer `SUMMARIZECOLUMNS` for query-style grouping; use `SUMMARIZE` purely to
  group, then `ADDCOLUMNS` to compute.
- **Gotcha:** computing expressions directly inside `SUMMARIZE` can give wrong results due to the
  way it sets context — the "`SUMMARIZE` + `ADDCOLUMNS`" split avoids this. → ARC-FUNC-02.
- **Retail one-liner:**
  `ADDCOLUMNS ( SUMMARIZE ( 'Sales', 'Product'[Category] ), "Sales", [Sales Amount] )`.

## 11. Time-intelligence functions (return-type recap)

- **Table TI** (`DATESYTD`, `DATESQTD`, `DATESMTD`, `DATESBETWEEN`, `DATEADD`,
  `SAMEPERIODLASTYEAR`, `PARALLELPERIOD`, `ENDOFMONTH`, `STARTOFYEAR`, …) → **only** as `CALCULATE`
  filter arguments or assigned to a VAR used as a filter.
- **Scalar date** (`EDATE`, `EOMONTH`, `DATE`, `YEAR`/`MONTH`/`DAY`, date arithmetic) → for
  row/scalar expressions; never as a `CALCULATE` filter.
- **Key rule / gotcha:** check the return type before placing the function. `EOMONTH` (scalar) as a
  filter, or `ENDOFMONTH` (table) in a scalar slot, are the canonical mistakes. → AR-TI-001,
  ARC-FUNC-01.
- Full TI patterns live in the pattern catalog (`patterns/dax-patterns.json`: ti-ytd, ti-py-yoy,
  ti-rolling-12) and `knowledge/dax-retail-examples.md`.

---

## Return-type quick table

| Function | Returns | Lives where |
|---|---|---|
| CALCULATE | scalar | measure body / inside iterators (transition) |
| CALCULATETABLE | table | filter arg, query, table var |
| FILTER | table | filter arg, table var |
| ALL / REMOVEFILTERS / ALLEXCEPT / ALLNOBLANKROW | table (or modifier) | filter arg / CALCULATE modifier |
| ALLSELECTED | table (or modifier) | filter arg (visible total) |
| VALUES / DISTINCT / FILTERS | table (1 col) | filter arg, scalar via 1-row conversion |
| HASONEVALUE / ISFILTERED / ISINSCOPE | boolean | scalar expressions |
| SELECTEDVALUE | scalar | measure body, labels, params |
| TREATAS | table (lineage) | filter arg |
| SUMX / AVERAGEX / RANKX / … | scalar | measure body |
| DIVIDE | scalar | measure body |
| SUMMARIZECOLUMNS / SUMMARIZE / ADDCOLUMNS / SELECTCOLUMNS | table | queries, table vars, filter args |
| DATESYTD / DATEADD / SAMEPERIODLASTYEAR / ENDOFMONTH | table | CALCULATE filter arg / VAR |
| EDATE / EOMONTH / DATE | scalar | row/scalar expressions |

---

## Agent reasoning questions (Slice 2 — function semantics)

1. *"Is `ENDOFMONTH` valid as the last argument of `EOMONTH(...)`-style scalar math?"*
   → `ENDOFMONTH` is a **table** TI function; scalar math needs a scalar. **No — use `EOMONTH`.**
   Concepts §0/§11. Candidate ARC-FUNC-01.
2. *"My distinct count is one higher than expected. `VALUES` or `DISTINCT`?"*
   → `VALUES` includes the blank row for invalid keys. **Use `DISTINCT`, or fix the key.** §4.
3. *"`SUMMARIZE` with a measure column gives odd subtotals. Fix?"*
   → Compute measures with `ADDCOLUMNS` over a `SUMMARIZE` grouping, not inside `SUMMARIZE`. §10.
   Candidate ARC-FUNC-02.
4. *"Why does `SELECTEDVALUE('Store'[Channel])` return blank on the total row?"*
   → Multiple values in context → returns the alternate (blank if none given). **Provide a default.**
   §5. Candidate ARC-STYLE-01.
5. *"Disconnected `'Category Bucket'` filter does nothing. Why?"*
   → No lineage to a model column. **Apply via `TREATAS(..., 'Product'[Category])`.** §6. ARC-LINEAGE-01.
6. *"`ISFILTERED` returns FALSE but the column clearly affects results. Bug?"*
   → It may be cross-filtered, not directly filtered. **Check `ISCROSSFILTERED`.** §5.

---

## Links — files to update in later slices (not now)

- `dax-engine-internals.md` (Slice 3) — *why* `FILTER(table)` and per-row transitions cost (SE vs
  FE, callbacks); `DISTINCTCOUNT` internals.
- `dax-performance-diagnostics.md` (Slice 3) — playbooks that use these return-type/cost facts.
- `patterns/analyzer-rule-candidates.json` — new Slice 2 candidates ARC-FUNC-01/02 staged there.
- `patterns/metric-contract-patterns.json` — add `concepts:[CC-xxx]` links once cards stabilize.
