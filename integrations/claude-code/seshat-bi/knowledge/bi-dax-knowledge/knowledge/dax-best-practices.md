# DAX Best Practices

> A ruleset the BI agent should treat as defaults. Each rule has a *why* so the agent can
> decide when a justified exception applies. Rules are grouped by theme. Many of these map
> directly to `analyzer-rules.json` for automated checking.

## Modeling foundations (these make DAX simpler)

- **BP-001 — Build a proper Date table and Mark as Date Table.** It must be contiguous
  (Jan 1 → Dec 31, every day, covering all referenced years) with a unique Date column.
  Marking it makes time-intelligence functions auto-apply `REMOVEFILTERS('Date')`, which is
  what makes them behave correctly. *Why:* almost every time-intelligence bug traces back to
  a malformed or unmarked date table.
- **BP-002 — Disable Auto Date/Time.** Power BI's automatic per-column date tables bloat the
  model and fragment time intelligence. Use one explicit Date table. *Why:* control and size.
- **BP-003 — Prefer a star schema.** Push attributes into dimensions; keep the fact narrow.
  *Why:* DAX patterns assume dimensions filter facts via single-direction relationships.
- **BP-004 — Hide helper columns and key columns** used only for sorting/relationships
  (e.g. `Year Month Number`, `DateWithSales`). *Why:* keeps the model usable and intent clear.

## Measures vs. calculated columns

- **BP-010 — Default to measures, not calculated columns.** Measures are evaluated in filter
  context at query time and don't cost storage. *Why:* flexibility and model size.
- **BP-011 — Use a calculated column only when the value is row-fixed and needed as a
  grouping/filter/sort axis** (e.g. static ABC class, static rank, age band). *Why:* you can
  only slice/group by a physical column, not a measure.
- **BP-012 — Never store a measure's result in a calculated column to "freeze" it** unless a
  snapshot is explicitly desired; snapshots belong in snapshot tables.

## Writing measures

- **BP-020 — Build on base measures.** Define `Sales Amount`, `Margin`, `# Customers` once and
  compose everything from them. *Why:* one place to fix logic; consistent results.
- **BP-021 — Always use `DIVIDE` for division.** Handles divide-by-zero, engine-optimized.
- **BP-022 — Use `VAR`/`RETURN` liberally** for any subexpression used more than once or any
  value that must be captured before the context changes. *Why:* performance + correctness.
- **BP-023 — Fully qualify column references (`'Table'[Column]`) and use unqualified measure
  references (`[Measure]`).** *Why:* this convention makes columns vs. measures readable at a
  glance and avoids ambiguity bugs.
- **BP-024 — Use `KEEPFILTERS` when a computed filter must respect the user's selection.**
  *Why:* default `CALCULATE` filters replace; users expect their slicer choices to still apply.
- **BP-025 — Use `REMOVEFILTERS`/`ALLEXCEPT` deliberately and re-apply filters that must
  survive.** A running total clears the Date filter; if you must keep Day-of-Week, re-add it.
- **BP-026 — Prefer `REMOVEFILTERS` over `ALL` when you only need to clear filters** (not to
  return a table). *Why:* clearer intent; `ALL` reads as "return all rows."
- **BP-027 — Use `SELECTEDVALUE(col, alternate)` instead of `IF(HASONEVALUE(...), VALUES(...))`.**
  *Why:* concise and safe when more than one value is in context.
- **BP-028 — Use `TREATAS` to apply disconnected/config tables as filters** rather than
  bi-directional relationships or `INTERSECT`. *Why:* explicit, fast, lineage-correct.

## Time intelligence

- **BP-030 — Use built-in time-intelligence functions only on a standard Gregorian calendar.**
  Weeks, 4-4-5, custom fiscal starts → use the custom/week patterns instead.
- **BP-031 — Time-intelligence *table* functions (`DATESYTD`, `DATEADD`, `SAMEPERIODLASTYEAR`,
  `ENDOFMONTH`…) belong only in `CALCULATE` filter arguments or assigned to a variable.**
  Do not use them in iterators or scalar expressions. *Why:* they rely on the filter context;
  in an iterator they fire costly implicit context transitions and often return wrong results.
- **BP-032 — Use scalar date functions (`EDATE`, `EOMONTH`, `DATE`, date arithmetic) in
  row-context/scalar expressions; never as `CALCULATE` filters.** Mirror image of BP-031.
- **BP-033 — Guard "future" periods.** YTD/running totals will happily show flat values past
  the last real transaction; compare against the last date with data (e.g. `DateWithSales`).

## Performance defaults (see dax-performance-notes.md for depth)

- **BP-040 — Minimize context transitions at scale**; don't iterate measures over fact-grain
  tables when you can iterate a dimension or do column arithmetic.
- **BP-041 — Filter columns, not tables.** `CALCULATE([m], Dim[Col]="x")` beats
  `CALCULATE([m], FILTER(Dim, Dim[Col]="x"))` when a simple predicate suffices. *Why:* the
  former is a storage-engine-friendly column filter; `FILTER(table)` materializes more.
- **BP-042 — Reduce cardinality** of columns used in filters/relationships; split
  date+time; avoid high-cardinality calculated columns.
- **BP-043 — Prefer set-based logic over row-by-row** where possible; lean on the storage
  engine, not the formula engine.

## Readability & maintainability

- **BP-050 — Format code (DAX Formatter style): one filter argument per line, capitalize
  functions, indent.** *Why:* reviewable, diff-able, teachable.
- **BP-051 — Name variables for meaning** (`LastVisibleDate`, `CustomersInSegment`), not
  `tmp1`. *Why:* a measure should read like its explanation.
- **BP-052 — Comment the *intent* and the *non-obvious filter moves*, not the syntax.**
- **BP-053 — Keep one definition per concept.** If two measures must agree, one references the
  other; never copy-paste arithmetic.
