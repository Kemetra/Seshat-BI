# SQL Anti-Patterns

> The mistakes that produce wrong numbers, slow queries, or unmaintainable SQL (SQL-AP-001..060). Each entry: the mistake, why it's wrong, the fix, and links. Flag these on review; never emit them on generation. See `../references/source-map.md`.

## Slice 1 entries (grain, counts, aggregation, logical order)

### SQL-AP-001 -- Assuming one row equals one transaction without proof
- **Mistake.** Treating `sales` as "one row per order" and counting rows as orders.
- **Why wrong.** `sales` grain is one *order line*; an order spans many lines. Row counts overstate orders.
- **Fix.** State the grain (SC-003); use `COUNT(DISTINCT order_id)` for orders; verify rows-per-order.
- **Links.** SC-003, SC-006 - SARC-GRAIN-01.

### SQL-AP-002 -- Aggregating before grain is declared
- **Mistake.** Writing `SUM(...)`/`COUNT(...)` without naming what one row represents.
- **Why wrong.** An aggregate is only correct relative to a grain; skipping it hides fan-out.
- **Fix.** Declare grain in a one-sentence comment before any aggregate (SC-005, SC-007).
- **Links.** SC-005, SC-007 - SARC-GRAIN-01.

### SQL-AP-003 -- Trusting uniqueness without checking
- **Mistake.** Joining or counting on a column *assumed* unique (e.g. `product_key` in `product`).
- **Why wrong.** A duplicate on the "one" side silently fans out the join and inflates totals.
- **Fix.** Run a uniqueness check (`GROUP BY key HAVING COUNT(*)>1`) before relying on it (SC-004).
- **Links.** SC-004 - SARC-KEY-01.

### SQL-AP-004 -- Using COUNT(column) when COUNT(*) or COUNT(DISTINCT) is intended
- **Mistake.** `COUNT(customer_key)` expecting all rows, or `COUNT(*)` when distinct entities are meant.
- **Why wrong.** `COUNT(col)` skips nulls; `COUNT(*)` counts rows not entities -- both silently mis-measure.
- **Fix.** Choose deliberately: rows -> `COUNT(*)`; distinct entities -> `COUNT(DISTINCT col)`; non-null -> `COUNT(col)` (SC-006).
- **Links.** SC-006 - SARC-COUNT-01.

### SQL-AP-005 -- SUM after an inflated (fan-out) join
- **Mistake.** `SUM(quantity * net_price)` after a one-to-many join (e.g. to `product_tag`).
- **Why wrong.** Rows are duplicated, so the SUM is multiplied -- a plausible but wrong number, no error.
- **Fix.** Aggregate to grain before joining, or join to a one-row-per-key summary; verify `COUNT(*)` unchanged (SC-007).
- **Links.** SC-007 - SARC-GRAIN-01, SARC-DISTINCT-01.

### SQL-AP-006 -- AVG of averages
- **Mistake.** Averaging pre-aggregated averages (e.g. per-store averages -> company average).
- **Why wrong.** Unweighted averages of averages ignore group sizes and give the wrong overall number.
- **Fix.** Average from the base grain (`SUM(x)/SUM(n)`) or weight by group size (SC-008).
- **Links.** SC-008 - SARC-AVG-01.

### SQL-AP-007 -- Filtering aggregates in WHERE instead of HAVING
- **Mistake.** `WHERE SUM(...) > 100` or `WHERE COUNT(*) > 5`.
- **Why wrong.** Aggregates/groups don't exist at the `WHERE` step (logical order); errors or wrong intent.
- **Fix.** Filter groups in `HAVING`; keep row filters in `WHERE` (SC-002).
- **Links.** SC-002 - SARC-HAVING-01.

### SQL-AP-008 -- GROUP BY hiding duplicated source rows
- **Mistake.** Relying on `GROUP BY` to "collapse" upstream duplicates, treating the result as clean.
- **Why wrong.** Grouping hides row duplication, but additive aggregates alongside are still inflated.
- **Fix.** Remove duplication at its source (dedup by key) before grouping (SC-005, SC-007).
- **Links.** SC-005, SC-007 - SARC-GRAIN-01.

### SQL-AP-009 -- Using DISTINCT as a band-aid without explaining grain
- **Mistake.** Wrapping a query in `SELECT DISTINCT` to make duplicates "go away."
- **Why wrong.** `DISTINCT` runs last (SC-002); it hides a grain/fan-out problem and can still leave additive aggregates wrong.
- **Fix.** Identify why duplicates exist (which join fanned out), fix the grain; use `DISTINCT` only when distinctness is the genuine intent, with grain stated.
- **Links.** SC-007 - SARC-DISTINCT-01.

---

## Slice 2 entries (joins, cardinality, fan-out, nulls)

### SQL-AP-010 -- Many-to-many join without a bridge or pre-aggregation
- **Mistake.** Joining two tables that each have multiple rows per key directly (e.g. `sales` -> `product_tag`).
- **Why wrong.** Rows multiply combinatorially; additive aggregates inflate and the result grain is undefined.
- **Fix.** Pre-aggregate one side to one row per key, or introduce a bridge; verify cardinality first (SC-010, SC-011).
- **Links.** SC-010, SC-011 - SARC-M2M-01, SARC-FANOUT-01.

### SQL-AP-011 -- NOT IN against a nullable subquery
- **Mistake.** `WHERE key NOT IN (SELECT key FROM other)` where `other.key` can be null.
- **Why wrong.** A single null makes the whole `NOT IN` UNKNOWN for every row -> **zero rows returned**, silently.
- **Fix.** Use `NOT EXISTS` (null-safe) or `LEFT JOIN ... WHERE b.key IS NULL`; filter nulls if `IN` is required (SC-012, SC-014).
- **Links.** SC-012, SC-014 - SARC-NOTIN-01.

### SQL-AP-012 -- Filtering the right table of a LEFT JOIN in WHERE
- **Mistake.** `LEFT JOIN store st ... WHERE st.region = 'West'`.
- **Why wrong.** Unmatched left rows have null `st.region`, which fails the `WHERE` test, so they're dropped -- silently turning the LEFT JOIN into an INNER JOIN.
- **Fix.** Move the right-table condition into the `ON` clause to preserve unmatched rows (SC-009).
- **Links.** SC-009 - SARC-LEFTFILTER-01.

### SQL-AP-013 -- Joining on a non-unique key and then aggregating
- **Mistake.** Treating a join key as unique on the "one" side without checking, then `SUM`/`COUNT`.
- **Why wrong.** A duplicate on that side fans out rows; the aggregate is multiplied -- the general form of SQL-AP-005.
- **Fix.** Verify uniqueness (`GROUP BY key HAVING COUNT(*)>1`) before the join; dedup or change grain (SC-010, SC-004).
- **Links.** SC-004, SC-010, SC-011 - SARC-FANOUT-01.

### SQL-AP-014 -- DISTINCT as a dedup without choosing a survivor
- **Mistake.** `SELECT DISTINCT *` (or distinct on a key) to remove duplicates created upstream.
- **Why wrong.** Non-deterministic about *which* row survives, can still leave additive aggregates wrong, and hides the fan-out cause (compounds SQL-AP-009).
- **Fix.** Dedup with `ROW_NUMBER()` + explicit `ORDER BY` tiebreak to choose a deterministic survivor per key (SC-013).
- **Links.** SC-013 - SARC-DEDUP-01.

### SQL-AP-015 -- Assuming a LEFT JOIN preserves row count
- **Mistake.** Believing `LEFT JOIN` can only keep or drop rows, never multiply.
- **Why wrong.** If the right side has duplicate keys, a LEFT JOIN still fans out (preserves *and* multiplies); row count rises.
- **Fix.** Verify right-side key uniqueness even for LEFT joins; compare `COUNT(*)` before/after (SC-010, SC-011).
- **Links.** SC-010, SC-011 - SARC-FANOUT-01.

---

## Slice 3 entries (window functions)

### SQL-AP-016 -- Ordered window without a deterministic tiebreak
- **Mistake.** `ROW_NUMBER()/RANK() OVER (PARTITION BY k ORDER BY col)` where `col` has ties.
- **Why wrong.** Tied rows get an arbitrary order, so the row number / chosen survivor is
  nondeterministic and changes between runs.
- **Fix.** Add a tiebreak column to `ORDER BY` (e.g. a key) so the order is total (SC-016, SC-018).
- **Links.** SC-016, SC-018 - SARC-WINDOW-ORDER-01.

### SQL-AP-017 -- Relying on the default frame for a running total
- **Mistake.** `SUM(x) OVER (ORDER BY d)` with a non-unique `d`, expecting strict row-by-row
  accumulation.
- **Why wrong.** The default frame is `RANGE`, which groups all peer rows with equal `d` together,
  so the running total jumps at ties rather than accumulating one row at a time.
- **Fix.** Specify `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` for predictable accumulation
  (SC-017).
- **Links.** SC-017 - SARC-WINDOW-FRAME-01.

### SQL-AP-018 -- LAST_VALUE / FIRST_VALUE without an explicit frame
- **Mistake.** `LAST_VALUE(x) OVER (PARTITION BY k ORDER BY d)` expecting the partition's last value.
- **Why wrong.** The default frame ends at the current row, so `LAST_VALUE` returns the current
  row's value, not the partition's last.
- **Fix.** Add `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING` (SC-017).
- **Links.** SC-017, SC-019 - SARC-WINDOW-LASTVAL-01.

### SQL-AP-019 -- Filtering on a window result in WHERE/HAVING
- **Mistake.** `WHERE ROW_NUMBER() OVER (...) = 1`.
- **Why wrong.** Window functions are computed at `SELECT`, after `WHERE`/`HAVING` (logical order),
  so they can't be referenced there.
- **Fix.** Compute the window in a subquery/CTE and filter in an outer query (SC-020, SC-002).
- **Links.** SC-020, SC-002 - SARC-WINDOW-WHERE-01.

### SQL-AP-020 -- Confusing window grain with GROUP BY grain
- **Mistake.** Expecting a window function to collapse rows like `GROUP BY`, or mixing the two
  without knowing which grain each operates on.
- **Why wrong.** Windows preserve row count (annotate each row); `GROUP BY` reduces it. Mixing them
  carelessly double-reports or mis-grains the result.
- **Fix.** Decide the grain explicitly: aggregate with `GROUP BY` to change grain, or use a window
  to keep detail; don't conflate (SC-015, SC-005).
- **Links.** SC-015, SC-005 - (heuristic; human review).

### SQL-AP-021 -- LAG/LEAD across sparse periods without a date spine
- **Mistake.** `LAG(revenue) OVER (ORDER BY month)` for "previous month" when some months have no
  rows.
- **Why wrong.** `LAG` reads the previous *row*, not the previous *calendar period*; with gaps it
  silently compares non-adjacent months, breaking MoM/YoY.
- **Fix.** Join to a complete date spine so the series is contiguous before applying offset
  functions (SC-019; full treatment in Slice 4).
- **Links.** SC-019 - SARC-WINDOW-SPARSE-01.

---

## Slice 4 entries (date/time & time-series)

### SQL-AP-022 -- BETWEEN on a timestamp column
- **Mistake.** `WHERE ts BETWEEN '2025-01-01' AND '2025-01-31'`.
- **Why wrong.** `BETWEEN` is inclusive of the end *instant*, so it drops everything after midnight
  on the end day; on timestamps this silently undercounts the last day.
- **Fix.** Use a half-open range: `>= start AND < next_start` (SC-024).
- **Links.** SC-024 - SARC-DATE-BETWEEN-01.

### SQL-AP-023 -- Grouping by a raw timestamp instead of truncating
- **Mistake.** `GROUP BY order_ts` (or selecting a raw timestamp as the time axis).
- **Why wrong.** Near-unique timestamps produce one group per instant -- no real aggregation, and
  huge result sets.
- **Fix.** Truncate to the reporting grain (`DATE_TRUNC('month', ...)`) or join to the date
  dimension's period column (SC-021).
- **Links.** SC-021 - SARC-DATE-TRUNC-01.

### SQL-AP-024 -- Ignoring or mixing time zones
- **Mistake.** Bucketing UTC timestamps into "days" without converting to the business zone, or
  joining two sources stored in different zones.
- **Why wrong.** Period boundaries depend on the zone; events near midnight land on the wrong day,
  corrupting daily counts and day-level reconciliation.
- **Fix.** Store UTC; convert to the business/local zone before truncating or bucketing (SC-022).
- **Links.** SC-022 - SARC-DATE-TZ-01.

### SQL-AP-025 -- Period-over-period without a date spine
- **Mistake.** `LAG`/`LEAD` (or self-join) for YoY/MoM directly off a sparse fact.
- **Why wrong.** Missing periods make "previous row" != "previous period", silently comparing
  non-adjacent months.
- **Fix.** Anchor the series on a complete date spine (LEFT JOIN) so periods are contiguous (SC-023,
  SC-025).
- **Links.** SC-023, SC-025 - SARC-DATE-SPINE-01.

### SQL-AP-026 -- Comparing a partial period to a full one
- **Mistake.** Comparing month-to-date to a full prior month (or YTD to a full prior year) without
  guarding.
- **Why wrong.** Unequal period lengths make the comparison misleading (current looks worse than it
  is).
- **Fix.** Compare like-for-like (same-length windows), or explicitly label/compute a partial-period
  comparison (SC-026).
- **Links.** SC-025, SC-026 - SARC-DATE-PARTIAL-01.

### SQL-AP-027 -- Wrapping a date column in a function in WHERE (non-sargable)
- **Mistake.** `WHERE YEAR(order_date) = 2025` or `WHERE DATE_TRUNC('day', order_ts) = '...'`.
- **Why wrong.** Applying a function to the column prevents index use (non-sargable) and is
  error-prone for boundaries.
- **Fix.** Use a range predicate on the bare column: `>= start AND < next_start` (SC-024; perf
  reasoning expanded in a later slice).
- **Links.** SC-024 - SARC-DATE-SARG-01.

---

## Slice 5 entries (validation & reconciliation)

### SQL-AP-028 -- Eyeballing instead of a zero-row gate
- **Mistake.** "I looked at the data and it seems fine" as the validation step.
- **Why wrong.** Not repeatable, not automatable, misses violations outside the rows you happened to
  view.
- **Fix.** Write a deterministic gate with a precise pass condition (returns 0 rows / totals equal)
  (SC-027).
- **Links.** SC-027 - SARC-VAL-GATE-01.

### SQL-AP-029 -- Reconciling row counts only (no value control total)
- **Mistake.** Confirming source and gold have the same row count and declaring success.
- **Why wrong.** A fan-out can keep counts plausible while sums drift, or values can change with
  counts unchanged; counts alone don't prove correctness.
- **Fix.** Pair row counts with a value control total (revenue, quantity) and distinct-entity counts
  (SC-030).
- **Links.** SC-030 - SARC-VAL-COUNTONLY-01.

### SQL-AP-030 -- Reconciling layers at different grains
- **Mistake.** Comparing a total from a line-grain source to a total from an order-grain gold table.
- **Why wrong.** The totals were never meant to match; the "mismatch" is a grain artifact, not a
  data error (or worse, hides a real one).
- **Fix.** Align both sides to a shared grain before comparing control totals (SC-005, SC-030).
- **Links.** SC-005, SC-030 - SARC-RECON-GRAIN-01.

### SQL-AP-031 -- Trusting a transform without idempotency/dedup verification
- **Mistake.** Assuming a reload/backfill is safe; assuming a dedup step worked.
- **Why wrong.** Non-idempotent loads double data on reload; dedup logic may not yield one row per
  key.
- **Fix.** Verify row count = distinct-key count after dedup, and that re-running keeps row count and
  control totals identical (SC-032).
- **Links.** SC-032 - (SARC-DEDUP-01).

### SQL-AP-032 -- Completeness checked off the fact instead of a spine
- **Mistake.** Checking "are there rows?" on the fact to judge completeness.
- **Why wrong.** Missing periods/segments are invisible when you only look at rows that exist; a
  whole missing day or store feed passes unnoticed.
- **Fix.** Check completeness against the date spine (and an expected-segment list); flag periods
  with zero rows (SC-031, SC-023).
- **Links.** SC-031, SC-023 - SARC-VAL-FRESH-01.

---

## Slice 6 entries (performance & maintainability)

### SQL-AP-033 -- SELECT * in a transformation or view
- **Mistake.** `CREATE VIEW ... AS SELECT * FROM ...` or `SELECT *` feeding a downstream step.
- **Why wrong.** Reads/stores unneeded columns (cost, worse on column-stores), breaks on upstream
  schema changes, and hides the step's output grain/contract.
- **Fix.** List the exact columns the step outputs; declare its grain (SC-035, SC-036).
- **Links.** SC-035, SC-036 - SARC-SELECTSTAR-01.

### SQL-AP-034 -- Implicit cross join (missing join condition)
- **Mistake.** Comma-style join (`FROM a, b`) or a `JOIN` with no/incorrect `ON`, producing every
  combination.
- **Why wrong.** A Cartesian product explodes row count and corrupts every aggregate; often
  unintended.
- **Fix.** Always specify an explicit, correct `ON` condition; if a cross join is truly intended,
  use `CROSS JOIN` to make it deliberate (SC-009, SC-037).
- **Links.** SC-009, SC-037 - SARC-CROSSJOIN-01.

### SQL-AP-035 -- Non-sargable predicate
- **Mistake.** Wrapping the filtered column in a function (`YEAR(col)`, `UPPER(col)`) or a
  leading-wildcard `LIKE '%x'`.
- **Why wrong.** Prevents index/zone-map use, forcing a full scan even when an index exists.
- **Fix.** Keep the column bare; use range predicates and avoid leading wildcards (SC-033).
- **Links.** SC-033 - SARC-SARG-01 (general; SARC-DATE-SARG-01 for dates).

### SQL-AP-036 -- Ambiguous grain across a CTE stack
- **Mistake.** A stack of CTEs (`step1`, `step2`, ...) with no stated grain, where joins/aggregates
  silently change grain between steps.
- **Why wrong.** Fan-out and double-counting hide in the middle of the stack; nobody can say what a
  row means, making review and debugging unreliable.
- **Fix.** Comment each CTE with its grain in one sentence; make every grain transition explicit
  (SC-038).
- **Links.** SC-038, SC-005 - SARC-CTE-GRAIN-01.

### SQL-AP-037 -- Filtering/aggregating late instead of early
- **Mistake.** Joining large tables in full (or aggregating everything) and only then applying the
  selective filter.
- **Why wrong.** Every intermediate step processes far more rows than necessary; slow and
  memory-heavy.
- **Fix.** Push the most selective filters before joins/aggregations; let the smallest set drive the
  work (SC-034, SC-037).
- **Links.** SC-034, SC-037 - SARC-FILTER-LATE-01.


---

## Slice C1 entries (set operations & table comparison -- SQL Cookbook)

### SQL-AP-038 -- UNION where UNION ALL was intended
- **Mistake.** Using `UNION` to combine result sets that should keep all rows.
- **Why wrong.** `UNION` removes duplicate rows (silently dropping legitimate identical transactions) and adds a dedup/sort cost.
- **Fix.** Use `UNION ALL` unless removing duplicates is the genuine intent (SC-040).
- **Links.** SC-040 - SARC-UNIONALL-01.

### SQL-AP-039 -- Set operation with mismatched/misordered columns
- **Mistake.** `UNION`/`INTERSECT`/`EXCEPT` whose two sides project different columns, order, or types.
- **Why wrong.** Set ops match by position, not name; the query may run but compare/stack the wrong columns.
- **Fix.** Project identical columns in the same order and compatible types on both sides (SC-039).
- **Links.** SC-039 - SARC-SETOP-COLS-01.

### SQL-AP-040 -- Using a join to compare tables where a set op is correct
- **Mistake.** Hand-rolling a multi-column join with IS-NULL gymnastics to find row differences.
- **Why wrong.** Error-prone with nulls and duplicates; `EXCEPT`/`INTERSECT` express row-level diff directly and handle null-equality.
- **Fix.** Use `EXCEPT`/`INTERSECT` for row-level comparison; reserve joins for combining columns (SC-041).
- **Links.** SC-041 - SARC-SETOP-COLS-01.

### SQL-AP-041 -- One-directional EXCEPT assumed to prove equality
- **Mistake.** Concluding two tables are equal because `A EXCEPT B` returns no rows.
- **Why wrong.** B may contain extra rows; set-distinct also hides duplicate-count differences.
- **Fix.** Check `A EXCEPT B` AND `B EXCEPT A` both return 0 rows, and compare `COUNT(*)` (SC-042).
- **Links.** SC-042 - VP-DIFF.


---

## Slice C2 entries (DML & transformation logic -- SQL Cookbook)

### SQL-AP-042 -- UPDATE/DELETE without a (correct) WHERE
- **Mistake.** Running an `UPDATE`/`DELETE` with no `WHERE`, or a `WHERE` that doesn't scope the intended rows.
- **Why wrong.** Mutates every row -- silent, large-scale data corruption.
- **Fix.** Always scope with a precise `WHERE`; preview with a matching `SELECT` first (SC-045, SC-046).
- **Links.** SC-045, SC-046 - SARC-DML-NOFILTER-01.

### SQL-AP-043 -- Non-idempotent load (append INSERT on reload)
- **Mistake.** Loading a layer with plain `INSERT` so a re-run/backfill appends duplicates.
- **Why wrong.** Row counts and totals double on reload; breaks reconciliation.
- **Fix.** Use `MERGE`/upsert (or replace) keyed on a unique business key so reloads are idempotent (SC-047, SC-032).
- **Links.** SC-047, SC-032 - SARC-DML-IDEMPOTENT-01 - VP-DEDUP.

### SQL-AP-044 -- Deleting duplicates without a deterministic keep rule
- **Mistake.** Deleting "duplicates" without specifying which row survives.
- **Why wrong.** Nondeterministic survivor (or over-deletion); results vary between runs.
- **Fix.** Use `ROW_NUMBER()` with an explicit `ORDER BY` to choose the survivor, delete `rn>1` (SC-046, SC-013).
- **Links.** SC-046, SC-013 - SARC-DEDUP-01.

### SQL-AP-045 -- Update-from a source that matches multiple rows per target
- **Mistake.** `UPDATE ... FROM`/correlated update where the source returns many rows per target key.
- **Why wrong.** Ambiguous/nondeterministic result (engine picks an arbitrary match or errors).
- **Fix.** Ensure the source is unique per target key (verify, SC-010) or pre-aggregate it first (SC-045).
- **Links.** SC-045, SC-010 - SARC-DML-MULTIMATCH-01.


---

## Slice C3 entries (reporting & reshaping -- SQL Cookbook)

### SQL-AP-046 -- Pivoting on an unknown / changing column set
- **Mistake.** Building a pivot whose target columns depend on data values not known at write time.
- **Why wrong.** Requires fragile dynamic SQL; columns silently appear/disappear as data changes.
- **Fix.** Pivot only on a fixed, known set; for variable sets keep data tall (unpivoted) and pivot in the presentation tool (SC-049, SC-050).
- **Links.** SC-049 - (dynamic-SQL caution).

### SQL-AP-047 -- UNION of separate aggregations instead of GROUPING SETS/ROLLUP
- **Mistake.** Hand-`UNION`-ing several `GROUP BY` queries to get subtotals + totals.
- **Why wrong.** Slow, easy to desync between levels, and verbose; grain can drift between the unioned parts.
- **Fix.** Use one `ROLLUP`/`CUBE`/`GROUPING SETS` query (SC-051).
- **Links.** SC-051 - SARC-ROLLUP-01.

### SQL-AP-048 -- Subtotal rows mistaken for real categories
- **Mistake.** Reading ROLLUP/CUBE subtotal rows (NULL in the rolled-up column) as a genuine category, or re-summing a result that contains subtotals.
- **Why wrong.** Subtotal NULLs are indistinguishable from real NULLs without GROUPING(); re-summing double-counts.
- **Fix.** Use `GROUPING(col)` to label subtotal/total rows; filter them out before any downstream aggregation (SC-052).
- **Links.** SC-052 - SARC-GROUPINGFLAG-01.

### SQL-AP-049 -- Equal-width buckets assumed to be equal-population
- **Mistake.** Treating fixed-width buckets as if each holds a similar number of rows.
- **Why wrong.** Skewed data piles into one bucket; the distribution is misread.
- **Fix.** Use `NTILE(n)` for equal-count groups, or state that buckets are equal-width; keep boundaries half-open (SC-053).
- **Links.** SC-053 - (SC-024 half-open).


---

## Slice C4 entries (string & data cleaning -- SQL Cookbook)

### SQL-AP-050 -- Grouping/joining on un-normalized text
- **Mistake.** `GROUP BY`/join on raw text with case, whitespace, or accent variants.
- **Why wrong.** Identical entities split into different groups and obvious matches are missed -- a silent grain/aggregation/reconciliation error.
- **Fix.** Canonicalize (TRIM/UPPER/unaccent) before grouping/joining, or key on a surrogate (SC-054).
- **Links.** SC-054, SC-008 - SARC-STR-NORMALIZE-01.

### SQL-AP-051 -- Brittle string ops on structured/multi-valued data
- **Mistake.** Matching a multi-valued field with `LIKE '%X%'`, or parsing structured text with nested SUBSTRING/INSTR.
- **Why wrong.** `LIKE '%X%'` gives false hits (substring of another value); hand-parsing is fragile and breaks on format drift.
- **Fix.** Split delimited fields to rows (one value per row) and match exactly; use a split function/recursive CTE (SC-055).
- **Links.** SC-055 - (SC-003 grain).

### SQL-AP-052 -- CAST without guarding non-parseable values
- **Mistake.** `CAST(text AS INT/DATE)` over a column that may contain garbage.
- **Why wrong.** A single bad value errors the cast (aborting the load) or silently mis-converts.
- **Fix.** Use `TRY_CAST`/a pattern check; route unparseable rows to a quarantine with a quality flag (SC-058).
- **Links.** SC-058, SC-008 - SARC-CAST-UNSAFE-01.


---

## Slice C5 entries (advanced date recipes -- SQL Cookbook)

### SQL-AP-053 -- Hardcoded date list instead of a generated calendar
- **Mistake.** Hand-typing dates (or relying on dates that happen to exist in the fact) instead of generating a spine.
- **Why wrong.** Brittle, incomplete, and unreproducible; missing periods vanish.
- **Fix.** Generate a contiguous calendar (recursive CTE / numbers table) and LEFT JOIN facts to it (SC-059, SC-060).
- **Links.** SC-059, SC-023 - SARC-CALENDAR-GEN-01.

### SQL-AP-054 -- Counting elapsed calendar days as business days
- **Mistake.** Reporting `end_date - start_date` as a business/working-day duration.
- **Why wrong.** Includes weekends/holidays, overstating SLA/fulfillment metrics.
- **Fix.** Count working days via a calendar that flags weekends/holidays (SC-061).
- **Links.** SC-061 - (no rule yet; human review).

### SQL-AP-055 -- Incorrect overlap boundary logic
- **Mistake.** Ad-hoc interval-overlap conditions, or `<=` on both ends, that double-count touching intervals or miss containment.
- **Why wrong.** Wrong rows flagged as overlapping/active; miscounts promotions/contracts in effect.
- **Fix.** Use the canonical half-open test `a_start < b_end AND b_start < a_end` (SC-062, SC-024).
- **Links.** SC-062, SC-024 - SARC-OVERLAP-01.


---

## Slice C6 entries (gaps & islands + hierarchical/recursive -- SQL Cookbook)

### SQL-AP-056 -- Row-by-row/cursor logic for islands or runs
- **Mistake.** Looping row by row to find consecutive runs/streaks.
- **Why wrong.** Slow and error-prone; the set-based `value - ROW_NUMBER()` island technique is correct and fast.
- **Fix.** Group by the island key (`value - row_number`), partitioned by entity, deterministically ordered (SC-064).
- **Links.** SC-064, SC-016 - (perf, Slice 6).

### SQL-AP-057 -- Recursive CTE without a termination / cycle guard
- **Mistake.** A recursive CTE with no stopping condition or cycle/depth guard.
- **Why wrong.** Infinite recursion (or hitting the engine limit) on deep or cyclic data.
- **Fix.** Ensure the recursive member terminates; add a path-based cycle guard and a depth cap (SC-066, SC-067).
- **Links.** SC-066, SC-067 - SARC-RECURSE-GUARD-01.

### SQL-AP-058 -- Detecting gaps only among present rows
- **Mistake.** Looking for missing values among the rows that exist, rather than against the complete expected sequence.
- **Why wrong.** A fully missing stretch (no rows at all) is invisible.
- **Fix.** Compare against a generated complete sequence/spine (anti-join), or use LEAD to spot breaks (SC-065, SC-023).
- **Links.** SC-065, SC-023, SC-031 - (SARC-CALENDAR-GEN-01 adjacent).


---

## Slice C7 entries (metadata-driven profiling -- SQL Cookbook)

### SQL-AP-059 -- Hand-writing per-column checks instead of generating from metadata
- **Mistake.** Manually authoring null/uniqueness/profile checks for each column.
- **Why wrong.** Doesn't scale to hundreds of columns and goes stale as the schema evolves; coverage gaps.
- **Fix.** Generate checks from `information_schema` (SQL that writes SQL) so coverage is complete and current (SC-069, SC-070).
- **Links.** SC-069, SC-070 - SARC-METADATA-DRIFT-01.

### SQL-AP-060 -- Trusting an assumed schema instead of querying the catalog
- **Mistake.** Hardcoding a column/table list and assuming it still matches the database.
- **Why wrong.** Schema drift (added/renamed/dropped columns) silently breaks checks or leaves blind spots.
- **Fix.** Read the live catalog (`information_schema`) and reconcile against expected schema; flag drift (SC-068).
- **Links.** SC-068 - SARC-METADATA-DRIFT-01.
