# DAX Performance Notes

> How the engine actually runs DAX, and the levers that matter. The agent uses this to choose
> between equivalent-but-not-equal formulations and to explain *why* a rewrite is faster.

## The two engines

DAX queries run across two cooperating engines:

- **Storage Engine (SE / VertiPaq)** — columnar, compressed, multi-threaded, very fast. It
  scans columns and does simple aggregations and filters. It is cache-friendly.
- **Formula Engine (FE)** — single-threaded, row-by-row, handles everything the SE can't
  (complex logic, iteration that can't be pushed down, context transition orchestration).

**Goal:** push as much work as possible into the SE; minimize FE iteration and "callback"
round-trips (where the FE asks the SE for a value per row — visible as `CallbackDataID` in a
query plan / server timings).

## Cardinality is king

VertiPaq compresses each column independently; compression depends on the number of distinct
values. Levers:

- Split `datetime` into `date` + `time` (or drop time). A full-precision datetime is nearly
  unique — terrible compression.
- Reduce decimal precision when business allows.
- Remove unused columns entirely (they still cost memory).
- Relationship and filter columns should be as low-cardinality as feasible (integer surrogate
  keys beat long strings).

## Context transition cost

Context transition (triggered by calling a measure inside a row context, or `CALCULATE` in an
iterator) is correct and necessary — but each transition builds a filter context. Doing this
per row over a high-cardinality table is a classic slowdown.

- Good: `SUMX ( VALUES ( 'Product'[Category] ), [Sales Amount] )` — transitions per *category*.
- Bad: `SUMX ( 'Sales', [Sales Amount] )` — transitions per *fact row*.
- When you only need arithmetic, avoid the transition: `SUMX('Sales','Sales'[Quantity]*'Sales'[Net Price])`.

## Filter arguments: column vs. table

- `CALCULATE ( [m], 'D'[Col] = "x" )` → simple SE column filter. Prefer this.
- `CALCULATE ( [m], FILTER ( 'D', 'D'[Col] = "x" ) )` → FE materializes a filtered table.
  Only needed for measure-based or multi-column conditions. If you must, filter the smallest
  thing: `FILTER ( VALUES ( 'D'[Col] ), … )`.

## Variables and caching

- A `VAR` is computed once; reusing it avoids recomputation **within that evaluation**.
- The SE also caches scan results within a query; identical subqueries can hit the cache.
- Don't fight the engine with cleverness that defeats caching (e.g. needlessly varying filters).

## Iterators and fusion

- Multiple simple aggregations over the same table can be "fused" into one SE scan. Writing
  `SUMX` with a clean row expression helps; wrapping logic that forces callbacks hurts.
- `IF` inside an iterator that calls measures can force per-row FE work; hoist invariant parts
  into variables outside the iterator.

## Distinct count

`DISTINCTCOUNT` is heavier than `SUM`. For "related distinct count" across relationships, the
shape of the filter (and whether you use `TREATAS`/bridge) materially affects cost — test both.

## Time intelligence

Built-in TI functions are well-optimized **when used as `CALCULATE` filters on a marked Date
table**. Re-implementing them with hand-written `FILTER` over the Date table is usually slower
and bug-prone — only do it for non-Gregorian/custom calendars where you must.

## Practical workflow for the agent

1. Get it **correct** first (right grain, right filters).
2. Measure with realistic data volume — don't optimize on toy data.
3. Read server timings: is time in SE or FE? Are there `CallbackDataID`s?
4. Attack the biggest lever: cardinality → context transitions → table-vs-column filters →
   redundant recomputation (VAR).
5. Re-measure. Keep the simplest formulation that meets the SLA; don't micro-optimize cold paths.

## Rules of thumb summary

| Symptom | Likely cause | First fix |
|---|---|---|
| Slow measure over big fact | measure iterated at fact grain | iterate dimension / column math |
| High FE time, many callbacks | logic not pushed to SE | simplify filter, remove per-row IF |
| Huge model size | high-cardinality column(s) | split datetime, reduce precision |
| Slow distinct count | DISTINCTCOUNT + complex filter | test TREATAS vs bridge; reduce cardinality |
| Wrong-but-fast vs right-but-slow | over-aggressive ALL / missing KEEPFILTERS | fix correctness, then optimize |
