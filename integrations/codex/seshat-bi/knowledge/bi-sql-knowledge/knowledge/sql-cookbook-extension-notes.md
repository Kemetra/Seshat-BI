# SQL Cookbook Extension Notes

> Book-2 analytical and reconciliation extensions that don't belong to the core foundation or the
> transformation file: set operations & table comparison (SC-039..043), advanced date recipes
> (SC-059..063), gaps & islands + hierarchical/recursive queries (SC-064..067), and metadata-driven
> profiling (SC-068..070). Original retail examples only; no book text, recipes (no EMP/DEPT), or
> datasets reproduced. See `../references/source-map.md` and `../references/copyright-safety.md`.

These extend the layer's reach without changing its spine. Set operations sharpen **reconciliation**
(row-level diffs, not just sum tie-outs); date recipes **operationalize** the date spine; gaps/islands
and recursion add two analytical shapes; metadata-driven profiling **scales** the validation gates
across many tables. Each card keeps the standard shape and links back to the foundation it builds on.

---

## A. Set operations & table comparison (SC-039..043)

### SC-039 -- Set operations and column compatibility
- **Definition.** `UNION`/`UNION ALL` (stack rows), `INTERSECT` (rows in both), `EXCEPT`/`MINUS` (rows
  in A not in B). All require **the same number of columns, in the same order, with compatible types**
  -- they match by position, not by name.
- **Why it matters.** Row-level comparison and stacking of conformed result sets (combining channels,
  diffing layers) without a join.
- **Common failure mode.** Mismatched/misordered column lists that "work" but compare the wrong columns;
  relying on column names (set ops ignore them).
- **Diagnostic question.** *"Do both sides project the same columns, same order, same types?"*
- **Retail example.** `SELECT product_key FROM gold.fact_sales EXCEPT SELECT product_key FROM
  source.sales` -> product keys present in gold but missing from source.
- **Feeds.** SQL-AP-039 - SARC-SETOP-COLS-01.

### SC-040 -- UNION vs UNION ALL
- **Definition.** `UNION` removes duplicate rows (an implicit distinct/sort); `UNION ALL` keeps all
  rows. `UNION ALL` is cheaper and is the default choice unless dedup is genuinely intended.
- **Why it matters.** `UNION` silently drops legitimate duplicate rows (two real orders with identical
  values) and adds a sort cost; in BI that can understate counts/totals.
- **Common failure mode.** Using `UNION` to "combine" facts and losing rows / paying a needless dedup.
- **Diagnostic question.** *"Do I actually want duplicates removed here -- or did I mean UNION ALL?"*
- **Retail example.** Combining this-year and last-year sales rows -> `UNION ALL` (every row is a real
  transaction); `UNION` would collapse identical-valued lines.
- **Feeds.** SQL-AP-038 - SARC-UNIONALL-01.

### SC-041 -- INTERSECT / EXCEPT for reconciliation
- **Definition.** `INTERSECT` = rows common to both; `EXCEPT` = rows in the first not in the second.
  They dedupe by default and compare whole projected rows.
- **Why it matters.** The cleanest **row-level reconciliation**: `source EXCEPT gold` = rows lost in
  transformation; `gold EXCEPT source` = rows invented. Far more precise than a sum tie-out alone.
- **Common failure mode.** Comparing only some columns (so genuinely different rows look equal); not
  realizing nulls compare as equal under set ops (unlike `=`).
- **Diagnostic question.** *"Which columns define 'the same row' for this diff, and am I projecting
  exactly those?"*
- **Retail example.** `SELECT order_line_id, order_id, product_key, quantity, net_price FROM
  source.sales EXCEPT SELECT ... FROM gold.fact_sales` -> lines changed or dropped by the pipeline.
- **Feeds.** VP-DIFF - SARC-SETOP-COLS-01.

### SC-042 -- Proving two tables hold the same data
- **Definition.** Two tables are equal only if **both** `A EXCEPT B` and `B EXCEPT A` return zero rows
  (and, with `UNION ALL` semantics, row counts match so duplicates aren't masked).
- **Why it matters.** A one-directional `EXCEPT` returning nothing does **not** prove equality (B could
  have extra rows). Reconciliation gates must check both directions.
- **Common failure mode.** Asserting equality from a single `EXCEPT`; ignoring duplicate-count
  differences that set-distinct hides.
- **Diagnostic question.** *"Did I check the diff both directions, and did I account for duplicate
  counts?"*
- **Retail example.** Equality gate: `A EXCEPT B` -> 0 rows **and** `B EXCEPT A` -> 0 rows **and**
  `COUNT(*)` equal.
- **Feeds.** VP-DIFF - SQL-AP-041 - PB-SQL-13.

### SC-043 -- Cartesian products: detect and avoid
- **Definition.** A join with no (or a non-restrictive) join condition pairs every left row with every
  right row -- a Cartesian product. Sometimes intended (`CROSS JOIN` against a tiny set), usually a bug.
- **Why it matters.** Row count explodes (|A|x|B|) and every aggregate is corrupted -- a severe form of
  fan-out (SC-011).
- **Common failure mode.** A missing/incomplete `ON`, or a comma-join, producing the product silently.
- **Diagnostic question.** *"Is every join condition present and selective? Does the row count look like
  |A|x|B|?"*
- **Retail example.** `FROM sales s, store st` with no condition -> every sale paired with every store.
  Fix: `JOIN store st ON st.store_key = s.store_key`.
- **Feeds.** SQL-AP-034 (cross join) - SC-011.

### Set ops -- original retail examples

**1. Row-level reconciliation with EXCEPT (both directions).**
```sql
-- Rows in source but missing from gold (lost in transformation):
SELECT order_line_id, order_id, product_key, quantity, net_price FROM source.sales
EXCEPT
SELECT order_line_id, order_id, product_key, quantity, net_price FROM gold.fact_sales;

-- Rows in gold but not in source (invented / changed):
SELECT order_line_id, order_id, product_key, quantity, net_price FROM gold.fact_sales
EXCEPT
SELECT order_line_id, order_id, product_key, quantity, net_price FROM source.sales;
-- PASS (tables equal) = both return 0 rows AND COUNT(*) matches.
```

**2. UNION ALL vs UNION.**
```sql
SELECT * FROM sales_2024 UNION ALL SELECT * FROM sales_2025;  -- keep every transaction row
-- UNION here would silently drop identical-valued lines and add a dedup/sort cost.
```

> Diagnostics: two tables should match but don't -> **PB-SQL-13**. Reconciliation gate: **VP-DIFF**.

---

## B. Advanced date recipes (SC-059..063)

### SC-059 -- Generating a calendar / date spine
- **Definition.** Produce a contiguous date series with a recursive CTE or a numbers/tally table, rather
  than hardcoding dates.
- **Why it matters.** A generated spine is the backbone of complete trends, rolling windows, and
  completeness gates (SC-023, SC-031) -- and it's reproducible for any range.
- **Common failure mode.** Hand-typing date lists; relying on dates that happen to exist in the fact.
- **Diagnostic question.** *"Is the calendar generated for the full range, or assumed from the data?"*
- **Retail example.** Recursive CTE from `'2025-01-01'` to `'2025-12-31'` to LEFT JOIN sales onto.
- **Feeds.** SQL-AP-053 - SARC-CALENDAR-GEN-01 - (SC-023).

### SC-060 -- Filling missing dates
- **Definition.** LEFT JOIN the spine to the fact so empty periods appear (with 0 / carried-forward
  values).
- **Why it matters.** Trends and `LAG`/rolling break on gaps (SC-019); filling makes "zero" periods
  explicit and series contiguous.
- **Common failure mode.** Trending off the fact so missing days vanish silently.
- **Diagnostic question.** *"Could a period have no rows -- and does the spine make it explicit?"*
- **Retail example.** `date d LEFT JOIN sales s ON s.order_date=d.date` -> every day present,
  `COALESCE(SUM(...),0)`.
- **Feeds.** (SC-023, SC-025).

### SC-061 -- Business-day / working-day arithmetic
- **Definition.** Count or add days excluding weekends and holidays (via a calendar table flagging
  working days), not raw calendar days.
- **Why it matters.** SLAs, fulfillment time, and "days to ship" are business-day metrics; raw day
  differences overstate them.
- **Common failure mode.** `end_date - start_date` reported as business days.
- **Diagnostic question.** *"Does this duration mean calendar days or working days -- and are holidays
  excluded?"*
- **Retail example.** Days-to-deliver = count of working days in the calendar between `order_date` and
  `delivery_date` (calendar flags weekends/holidays).
- **Feeds.** SQL-AP-054.

### SC-062 -- Overlapping date ranges
- **Definition.** Two intervals `[a_start, a_end)` and `[b_start, b_end)` overlap iff
  `a_start < b_end AND b_start < a_end`. The canonical overlap test.
- **Why it matters.** Promotions in effect, contracts active, double-booked resources, events in
  progress -- all are interval-overlap questions.
- **Common failure mode.** Wrong/over-inclusive boundary logic (using `<=` on both ends double-counts
  touching intervals); ad-hoc conditions that miss containment cases.
- **Diagnostic question.** *"Am I using the canonical half-open overlap test, with consistent
  boundaries?"*
- **Retail example.** Find promotions overlapping a campaign window:
  `promo.start_date < :window_end AND :window_start < promo.end_date`.
- **Feeds.** SQL-AP-055 - SARC-OVERLAP-01 - (SC-024 half-open).

### SC-063 -- Period boundaries
- **Definition.** Compute first/last day of month/quarter/year and week-of for bucketing and
  comparisons.
- **Why it matters.** Aligns aggregation and period-over-period to clean boundaries
  (`sql-date-time-analysis.md`).
- **Common failure mode.** Approximating month-end (e.g. always day 30) instead of true end-of-month.
- **Diagnostic question.** *"Am I deriving true period boundaries, or approximating them?"*
- **Retail example.** Quarter buckets via `DATE_TRUNC('quarter', order_date)`; true month-end for
  closing-balance dates.
- **Feeds.** (SC-021, SC-024).

### Date recipes -- original retail examples

**1. Generate a calendar spine (recursive CTE) and fill missing days.**
```sql
WITH RECURSIVE cal AS (
  SELECT DATE '2025-01-01' AS d
  UNION ALL
  SELECT d + 1 FROM cal WHERE d + 1 < DATE '2026-01-01'   -- termination guard
)
SELECT c.d AS date, COALESCE(SUM(s.quantity * s.net_price), 0) AS revenue
FROM cal c
LEFT JOIN sales s ON s.order_date = c.d
GROUP BY c.d;   -- every day present, empty days = 0
```

**2. Overlapping ranges (canonical half-open test).**
```sql
SELECT promotion_key
FROM promotion
WHERE start_date < DATE '2025-07-01'     -- a_start < b_end
  AND DATE '2025-06-01' < end_date;      -- b_start < a_end
```

> Diagnostics: missing dates / business-day / overlap wrong -> **PB-SQL-17**.

---

## C. Gaps & islands + hierarchical / recursive queries (SC-064..067)

### SC-064 -- Islands (grouping consecutive values)
- **Definition.** An "island" is a run of consecutive values (consecutive integers, dates with no gap,
  an unbroken status streak). The classic technique: `value - ROW_NUMBER()` (or date minus a row index)
  is **constant within an island**, so group by that constant.
- **Why it matters.** Streak/run analytics (consecutive active days, contiguous in-stock periods) and
  collapsing adjacent ranges -- set-based, no loops.
- **Common failure mode.** Row-by-row/cursor logic; forgetting a partition (islands bleed across
  entities); non-deterministic ordering (SC-016).
- **Diagnostic question.** *"What defines 'consecutive' here, and what partitions the islands?"*
- **Retail example.** Longest run of consecutive days a store had sales: group by
  `order_date - ROW_NUMBER() OVER (PARTITION BY store_key ORDER BY order_date)`.
- **Feeds.** SQL-AP-056 - (SC-016 deterministic order).

### SC-065 -- Gaps (detecting missing values in a sequence)
- **Definition.** A gap is a break in an expected sequence (missing IDs, missing dates). Detect by
  comparing each value to the next (`LEAD`) or by anti-joining against a complete spine.
- **Why it matters.** Completeness and integrity (missing invoice numbers, missing days) -- ties to the
  validation layer (SC-031).
- **Common failure mode.** Looking for gaps only among values that exist (can't see a fully missing
  stretch) instead of against a complete sequence/spine.
- **Diagnostic question.** *"Am I detecting gaps against the complete expected sequence, not just
  present rows?"*
- **Retail example.** Missing order numbers: `LEAD(order_id) OVER (ORDER BY order_id) - order_id > 1`,
  or anti-join against a generated sequence.
- **Feeds.** SQL-AP-058 - (SC-023, SC-031).

### SC-066 -- Recursive CTE mechanics
- **Definition.** A recursive CTE = an **anchor** member, a **recursive** member that references the
  CTE, and a **termination** condition (recursion stops when the recursive member returns no rows).
  Optionally a depth counter / cycle guard.
- **Why it matters.** The standard way to traverse hierarchies and generate sequences (calendars,
  SC-059).
- **Common failure mode.** No termination/cycle guard -> infinite recursion (or hitting the engine's
  recursion limit); anchor selecting the wrong roots.
- **Diagnostic question.** *"What stops this recursion, and can the data contain a cycle?"*
- **Retail example.** Walk a category tree from roots down, carrying a `depth` and a path to guard
  cycles.
- **Feeds.** SQL-AP-057 - SARC-RECURSE-GUARD-01.

### SC-067 -- Tree traversal: path, depth, and cycles
- **Definition.** While recursing a parent-child tree, accumulate a **path** (root->node) and **depth**;
  use the path to **detect cycles** (stop if a node reappears).
- **Why it matters.** Produces browsable levels (like the DAX parent-child flattening) and protects
  against malformed data with loops.
- **Common failure mode.** No cycle detection on data that isn't a strict tree; assuming a fixed depth.
- **Diagnostic question.** *"Is the hierarchy guaranteed acyclic? If not, am I detecting cycles via the
  path?"*
- **Retail example.** Product category hierarchy -> emit `(node, depth, path)`; stop a branch if its key
  already appears in the accumulated path.
- **Feeds.** SQL-AP-057 - SARC-RECURSE-GUARD-01.

### Gaps/islands & recursion -- original retail examples

**1. Islands -- consecutive sales days per store (collapse to ranges).**
```sql
WITH d AS (
  SELECT DISTINCT store_key, order_date FROM sales
),
grp AS (
  SELECT store_key, order_date,
         order_date - (ROW_NUMBER() OVER (PARTITION BY store_key ORDER BY order_date)) * INTERVAL '1 day' AS island_key
  FROM d
)
SELECT store_key, MIN(order_date) AS run_start, MAX(order_date) AS run_end, COUNT(*) AS days
FROM grp GROUP BY store_key, island_key;   -- one row per consecutive run
```

**2. Recursive category tree with depth + cycle guard.**
```sql
WITH RECURSIVE tree AS (
  SELECT category_key, parent_key, category_name,
         1 AS depth, CAST(category_key AS VARCHAR) AS path
  FROM product_category WHERE parent_key IS NULL          -- anchor: roots
  UNION ALL
  SELECT c.category_key, c.parent_key, c.category_name,
         t.depth + 1, t.path || '>' || c.category_key
  FROM product_category c
  JOIN tree t ON c.parent_key = t.category_key
  WHERE POSITION(CAST(c.category_key AS VARCHAR) IN t.path) = 0   -- cycle guard
    AND t.depth < 20                                             -- depth guard
)
SELECT category_key, depth, path FROM tree;
```

> Diagnostics: recursive runs forever / islands wrong / gaps missed -> **PB-SQL-18**.

---

## D. Metadata-driven profiling (SC-068..070)

### SC-068 -- The information schema / data dictionary
- **Definition.** Standard catalog views (`information_schema.tables`/`.columns`, key/constraint views)
  describe the live schema: tables, columns, types, nullability, keys.
- **Why it matters.** It's the source of truth for what *actually* exists -- the basis for
  metadata-driven profiling and for detecting schema drift versus assumptions.
- **Common failure mode.** Assuming a hardcoded column list still matches reality (drift); trusting
  documentation over the catalog.
- **Diagnostic question.** *"Did I read the live catalog, or assume the schema?"*
- **Retail example.** List every column + type + nullability for `gold.fact_sales` from
  `information_schema.columns` before generating checks.
- **Feeds.** SQL-AP-060 - SARC-METADATA-DRIFT-01.

### SC-069 -- SQL that generates SQL
- **Definition.** Query the catalog and emit SQL text (one statement per table/column) to run -- a
  template instantiated over metadata.
- **Why it matters.** Turns "write 200 null-checks by hand" into "generate them from the catalog" --
  scalable, consistent validation/profiling (operationalizing VP-NOTNULL / VP-UNIQUE / VP-RANGE).
- **Common failure mode.** Concatenating identifiers/values without quoting/escaping (broken or
  injectable SQL); generating against a stale column list.
- **Diagnostic question.** *"Is generated identifier/literal text safely quoted, and sourced from the
  live catalog?"*
- **Retail example.** From `information_schema.columns` for a table, generate one
  `SELECT COUNT(*) ... WHERE col IS NULL` per column, then run the batch.
- **Feeds.** SQL-AP-059 - SARC-GENSQL-INJECTION-01 - VP-PROFILE.

### SC-070 -- Programmatic profiling at scale
- **Definition.** For each column, compute a standard profile: row count, null %, distinct count,
  min/max, sample values -- generated from metadata and stored as a profiling result.
- **Why it matters.** A repeatable profile across all source/silver/gold columns is the foundation of
  validation and drift monitoring; it feeds the reconciliation gates.
- **Common failure mode.** Profiling a hand-picked subset (blind spots); recomputing ad hoc instead of a
  standard, comparable profile.
- **Diagnostic question.** *"Is every column profiled with the same metrics, generated from the
  catalog?"*
- **Retail example.** Generate a per-column profile for all `gold.*` tables; compare runs to flag
  null-rate spikes or distinct-count drops (anomaly/absence -- SC-031).
- **Feeds.** VP-PROFILE - (SC-031, VP-RANGE).

### Metadata -- original retail examples

**1. Read the catalog (what actually exists).**
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'gold' AND table_name = 'fact_sales'
ORDER BY ordinal_position;   -- ground every check in the live schema
```

**2. Generate not-null checks for every column (SQL that writes SQL).**
```sql
SELECT
  'SELECT ' || quote_literal(table_name||'.'||column_name) || ' AS col, '
  || 'COUNT(*) AS nulls FROM ' || quote_ident(table_schema) || '.' || quote_ident(table_name)
  || ' WHERE ' || quote_ident(column_name) || ' IS NULL;' AS check_sql
FROM information_schema.columns
WHERE table_schema = 'gold' AND table_name = 'fact_sales';
-- identifiers quoted (quote_ident) and literals escaped (quote_literal) to stay safe
```

> Diagnostics: validation doesn't scale / schema drifted -> **PB-SQL-19**. Gate: **VP-PROFILE**.

---

## Feeds (this file)

- Concepts SC-039..043, SC-059..070 - Anti-patterns SQL-AP-038..041, SQL-AP-053..060 -
  Playbooks PB-SQL-13, 17, 18, 19 - Validation VP-DIFF, VP-PROFILE -
  Candidates SARC-UNIONALL-01, SARC-SETOP-COLS-01, SARC-CALENDAR-GEN-01, SARC-OVERLAP-01,
  SARC-RECURSE-GUARD-01, SARC-METADATA-DRIFT-01, SARC-GENSQL-INJECTION-01.
- Set ops sharpen reconciliation (SC-030); date recipes operationalize the spine (SC-023, SC-031);
  metadata profiling scales the validation gates (Slice 5).
