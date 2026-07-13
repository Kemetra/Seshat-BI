# DAX Measure Review Checklist

Run before trusting / merging a measure. Copy it, check each box, and state the filter context the
measure assumes. A failed box is a finding, not a nit. References point to the analyzer rules
(`AR-*`), best practices (`BP-*`), and anti-patterns (`AP-*`) behind each check.

## Context & intent
- [ ] **Filter context stated**: what filters are active when this evaluates, and what one result value means.
- [ ] Measure traces to a **metric contract** or explicit user intent — not invented (see `metric-contract-checklist.md`).
- [ ] Base-measure composition used; no re-aggregating raw columns that a base measure already defines (BP-020).

## Context transition & CALCULATE
- [ ] Row-context → filter-context transitions are intentional (iterators, calculated columns) — no accidental context transition.
- [ ] Computed `CALCULATE` filters use `KEEPFILTERS` where the user's selection must still apply (AR-CALC-001, BP-024).
- [ ] `REMOVEFILTERS`/`ALL`/`ALLEXCEPT` clear exactly what's intended — no over-broad `ALL` (AR-ALL-001, BP-025).

## Totals & additivity
- [ ] Non-additive / semi-additive measures do not show a silently additive total (AR-ADD-001).
- [ ] Total-row behavior checked (`HASONEVALUE` / `SELECTEDVALUE` with a default where a single value is assumed — AR-PARAM-001, AR-STYLE-004).

## Time intelligence (if used)
- [ ] A proper **marked Date table**, contiguous calendar (AR-TI-002, BP-001); Auto Date/Time off (AR-TI-003, BP-002).
- [ ] TI table functions sit inside `CALCULATE`/`VAR`, not loose (AR-TI-001).
- [ ] Role-playing dates activated with `USERELATIONSHIP` (AR-REL-001).

## Correctness hygiene
- [ ] Division uses `DIVIDE`, never `/` (AR-DIV-001, BP-021).
- [ ] Repeated subexpressions captured in `VAR`/`RETURN` (AR-PERF-003, BP-022).
- [ ] Columns fully qualified, measures unqualified (AR-STYLE-001, BP-023); formula formatted, not monolithic (AR-STYLE-002).
- [ ] No implicit measures (auto-aggregated columns dropped in a visual) (AR-STYLE-003).
- [ ] Segmentation config tables have no overlapping/gapped ranges (AR-SEG-001).

## Performance (after correctness)
- [ ] Not iterating over a fact-grain table where a column predicate suffices (AR-PERF-001/002).
- [ ] No high-cardinality calculated column where a measure would do (AR-PERF-004).
- [ ] Bi-directional relationships not used as a default crutch (AR-BIDI-001).

## Verdict
- [ ] Open issues recorded by `AR-*` / `AP-*` id with severity and fix direction (analyzer-style verdict).
- [ ] If a model prerequisite (date table, relationship, uniqueness, grain) can't be confirmed → **stop and request it**; do not fake it (DAX stop rules).
- [ ] Optimize only after correctness is proven.
