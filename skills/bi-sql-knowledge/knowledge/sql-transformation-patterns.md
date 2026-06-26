# SQL Transformation Patterns (silver / gold)

> The write side that builds silver and gold: DML and idempotent loads (SC-044..048), reporting /
> reshaping (SC-049..053), and string / data cleaning (SC-054..058). Original retail examples only on
> the fictional schema; no book text, recipes, or datasets reproduced. See `../references/source-map.md`.

Silver/gold tables are *produced* by transformations, not just queried. This file covers the three
families that build them safely: the **DML** that loads them (and makes a reload idempotent), the
**reshaping** that produces report-grade gold, and the **cleaning** that canonicalizes messy source
text before it becomes a key. Each card: definition - why it matters - common failure - diagnostic
question - original retail example - feeds.

---

## A. DML & idempotent loads (SC-044..048)

### SC-044 -- INSERT shapes (and copying tables)
- **Definition.** Single-row, multi-row, and `INSERT ... SELECT` (load from a query);
  `CREATE TABLE ... AS SELECT` (CTAS) / copy-definition for staging.
- **Why it matters.** `INSERT ... SELECT` is the backbone of layer-to-layer loads; CTAS builds
  staging/silver tables from transformations.
- **Common failure mode.** Column-list/position mismatches; relying on default values silently.
- **Diagnostic question.** *"Are the INSERT target columns explicitly listed and aligned to the SELECT?"*
- **Retail example.** `INSERT INTO silver.sales (order_line_id, order_id, product_key, quantity,
  net_price) SELECT ... FROM bronze.sales WHERE ...`.
- **Feeds.** (links SC-036 explicit columns).

### SC-045 -- UPDATE correctly (and update-from-another-table)
- **Definition.** `UPDATE` with a precise `WHERE`; updating a target from a related table requires a
  correlated subquery or an `UPDATE ... FROM`/`MERGE` that matches **one** source row per target.
- **Why it matters.** A missing `WHERE` updates every row; a multi-match source makes the result
  ambiguous/nondeterministic.
- **Common failure mode.** `UPDATE` with no/incorrect `WHERE`; update-from where the source returns
  many rows per target key.
- **Diagnostic question.** *"Does my WHERE scope the rows precisely, and does the source match at most
  one row per target?"*
- **Retail example.** Backfill `silver.sales.unit_cost` from `product`: ensure `product_key` is unique
  in `product` (SC-010) so each sales row matches exactly one cost.
- **Feeds.** SQL-AP-042, SQL-AP-045 - SARC-DML-NOFILTER-01, SARC-DML-MULTIMATCH-01.

### SC-046 -- DELETE patterns (dedupe, RI violations)
- **Definition.** Delete specific rows, delete-duplicates-keeping-one (deterministically), delete
  referential-integrity violations (orphans), delete rows referenced elsewhere.
- **Why it matters.** Cleaning silver/gold safely; dedup-delete must choose a deterministic survivor
  (SC-013).
- **Common failure mode.** Deleting duplicates without a keep rule (random survivor / over-delete);
  deleting parents still referenced by children.
- **Diagnostic question.** *"Which row survives, by what deterministic rule, and what references it?"*
- **Retail example.** Keep the latest line per `order_line_id` via `ROW_NUMBER()` and delete `rn>1`.
- **Feeds.** SQL-AP-044 - (SARC-DEDUP-01).

### SC-047 -- MERGE / upsert (idempotent loads)
- **Definition.** `MERGE` matches a source against a target and inserts new keys / updates changed
  ones / (optionally) deletes -- in one statement. The standard idempotent-load primitive.
- **Why it matters.** Re-running a `MERGE` keyed on the business key yields the **same** result -- no
  duplication on reload (SC-032). Append-only `INSERT` does not.
- **Common failure mode.** Loading with plain `INSERT` (append) so reloads double rows; `MERGE` on a
  non-unique key (matches many -> inflates).
- **Diagnostic question.** *"Is this load idempotent -- does re-running keep row count and totals
  identical? Is the merge key unique?"*
- **Retail example.** `MERGE gold.fact_sales t USING staging.sales s ON t.order_line_id =
  s.order_line_id WHEN MATCHED THEN UPDATE ... WHEN NOT MATCHED THEN INSERT ...`.
- **Feeds.** SQL-AP-043 - SARC-DML-IDEMPOTENT-01 - VP-DEDUP.

### SC-048 -- Set-based DML vs row-by-row
- **Definition.** Express a change as one set-based statement over all affected rows, not a loop/cursor
  over individual rows.
- **Why it matters.** Set-based DML is correct, far faster, and transactionally clean; row-by-row loops
  are slow and error-prone.
- **Common failure mode.** Procedural loops doing per-row `UPDATE`/`INSERT`.
- **Diagnostic question.** *"Can this be one statement over the whole set?"*
- **Retail example.** One `UPDATE ... WHERE` over all matching sales rows, not a per-row loop.
- **Feeds.** (perf reasoning, `sql-performance-notes.md`).

### DML -- original retail examples

**1. Idempotent load with MERGE (upsert).**
```sql
MERGE INTO gold.fact_sales t
USING staging.sales s
  ON t.order_line_id = s.order_line_id           -- unique merge key (verify! SC-010)
WHEN MATCHED THEN UPDATE SET quantity = s.quantity, net_price = s.net_price
WHEN NOT MATCHED THEN INSERT (order_line_id, order_id, product_key, quantity, net_price)
                      VALUES (s.order_line_id, s.order_id, s.product_key, s.quantity, s.net_price);
-- Re-running yields identical rows/totals (idempotent). PASS gate: VP-DEDUP.
```

**2. Deterministic dedup-delete (keep latest per key).**
```sql
DELETE FROM silver.sales
WHERE order_line_id IN (
  SELECT order_line_id FROM (
    SELECT order_line_id,
           ROW_NUMBER() OVER (PARTITION BY order_line_id ORDER BY loaded_at DESC) AS rn
    FROM silver.sales
  ) d WHERE rn > 1
);   -- survivor chosen by an explicit ORDER BY (SC-013)
```

**3. Update-from with a verified single-match source.**
```sql
-- product_key must be unique in product (one cost per product) or this is ambiguous
UPDATE silver.sales s
SET unit_cost = (SELECT p.standard_cost FROM product p WHERE p.product_key = s.product_key)
WHERE EXISTS (SELECT 1 FROM product p WHERE p.product_key = s.product_key);
```

> Diagnostics: a reload that changes counts / an upsert that duplicates -> **PB-SQL-14**.

---

## B. Reporting & reshaping for gold (SC-049..053)

### SC-049 -- Pivot (rows -> columns)
- **Definition.** Turn row categories into columns, usually via `CASE`-inside-aggregate (or a vendor
  `PIVOT`). Requires a **known, fixed** set of target columns.
- **Why it matters.** Cross-tab report extracts (e.g. revenue by category across columns) for
  gold/presentation.
- **Common failure mode.** Pivoting on an unknown/changing value set (needs fragile dynamic SQL);
  forgetting the aggregate so non-pivoted columns explode the grain.
- **Diagnostic question.** *"Is the set of pivot columns fixed and known at write time?"*
- **Retail example.** `SUM(CASE WHEN channel='Online' THEN revenue END) AS online, ... GROUP BY
  store_key` -- one row per store, channels as columns.
- **Feeds.** SQL-AP-046.

### SC-050 -- Unpivot (columns -> rows)
- **Definition.** Normalize wide data into tall key/value rows via `UNION ALL` (or vendor `UNPIVOT`).
- **Why it matters.** Wide source extracts (a column per month/metric) must be unpivoted to a tidy
  grain before modeling/aggregation.
- **Common failure mode.** Leaving data wide and writing per-column logic; losing the column's identity
  when unpivoting.
- **Diagnostic question.** *"What is the tidy grain (one row per entity x attribute), and does unpivot
  produce it?"*
- **Retail example.** Turn `jan_qty, feb_qty, ...` columns into `(month, qty)` rows via `UNION ALL`.
- **Feeds.** (links SC-003 grain).

### SC-051 -- GROUPING SETS / ROLLUP / CUBE
- **Definition.** Compute **multiple aggregation levels in one query**: `ROLLUP` (hierarchical
  subtotals + grand total), `CUBE` (all combinations), `GROUPING SETS` (an explicit chosen set).
- **Why it matters.** The correct, single-pass way to produce subtotals/grand totals -- replacing
  brittle `UNION`-of-aggregations and guaranteeing consistent grain.
- **Common failure mode.** Hand-`UNION`-ing several `GROUP BY` queries (slow, inconsistent, easy to
  desync); using `CUBE` when only a few subtotal levels are wanted.
- **Diagnostic question.** *"Which subtotal levels do I need -- and can one ROLLUP/GROUPING SETS produce
  them?"*
- **Retail example.** `GROUP BY ROLLUP (region, store_key)` -> per store, per region subtotal, and a
  grand total in one result.
- **Feeds.** SQL-AP-047 - SARC-ROLLUP-01.

### SC-052 -- GROUPING() to identify subtotal rows
- **Definition.** With ROLLUP/CUBE/GROUPING SETS, `GROUPING(col)` returns 1 on rows where `col` is
  aggregated away (a subtotal/total), letting you label and distinguish them from real NULLs.
- **Why it matters.** Subtotal rows have NULL in the rolled-up column -- indistinguishable from a
  genuine NULL category unless you use `GROUPING()`. Misreading them corrupts the report.
- **Common failure mode.** Treating subtotal NULLs as a real category; double-counting subtotals when
  the result is consumed downstream.
- **Diagnostic question.** *"Which rows are subtotals vs real categories -- am I using GROUPING() to
  tell them apart?"*
- **Retail example.** `CASE WHEN GROUPING(region)=1 THEN 'All regions' ELSE region END`.
- **Feeds.** SQL-AP-048 - SARC-GROUPINGFLAG-01.

### SC-053 -- Bucketing, NTILE & histograms
- **Definition.** Group continuous values into buckets: fixed-width (by arithmetic), or equal-count via
  `NTILE(n)`; histograms count rows per bucket.
- **Why it matters.** Distributions and banded reports (price bands, basket-size bands). Equal-width and
  equal-count buckets answer different questions.
- **Common failure mode.** Assuming equal-width buckets are equal-population (skew makes one bucket
  huge); off-by-one bucket boundaries.
- **Diagnostic question.** *"Do I want equal-width ranges or equal-count groups (NTILE)? Are bucket
  boundaries half-open and consistent?"*
- **Retail example.** `NTILE(4) OVER (ORDER BY net_price)` for price quartiles; or
  `FLOOR(net_price/10)*10` for fixed bands.
- **Feeds.** SQL-AP-049.

### Reshaping -- original retail examples

**1. Multi-level subtotals in one pass (ROLLUP + GROUPING()).**
```sql
SELECT
  CASE WHEN GROUPING(region)=1 THEN 'All regions' ELSE region END     AS region,
  CASE WHEN GROUPING(store_key)=1 THEN 'All stores' ELSE CAST(store_key AS VARCHAR) END AS store,
  SUM(quantity * net_price) AS revenue
FROM sales s JOIN store st ON st.store_key = s.store_key
GROUP BY ROLLUP (region, store_key);   -- store rows + region subtotals + grand total
```

**2. Pivot channels into columns (fixed set).**
```sql
SELECT store_key,
       SUM(CASE WHEN st.channel='Online'   THEN s.quantity*s.net_price END) AS online,
       SUM(CASE WHEN st.channel='Retail'   THEN s.quantity*s.net_price END) AS retail,
       SUM(CASE WHEN st.channel='Reseller' THEN s.quantity*s.net_price END) AS reseller
FROM sales s JOIN store st ON st.store_key=s.store_key
GROUP BY store_key;   -- channel set is fixed/known
```

**3. Price quartiles (equal-count buckets).**
```sql
SELECT product_key, net_price,
       NTILE(4) OVER (ORDER BY net_price) AS price_quartile
FROM product;   -- equal-count groups, not equal-width
```

> Diagnostics: subtotals/grand totals wrong or duplicated -> **PB-SQL-15**.

---

## C. String & data cleaning for silver (SC-054..058)

### SC-054 -- Canonicalize before grouping/joining
- **Definition.** Normalize text to a single canonical form before it's used as a key: trim whitespace,
  fold case, strip/normalize accents and punctuation.
- **Why it matters.** Grouping/joining on raw text treats `"Acme "`, `"acme"`, and `"ACME"` as
  different -- splitting groups and breaking joins (a silent grain/aggregation error).
- **Common failure mode.** `GROUP BY customer_name` or joining on a raw text key without normalization.
- **Diagnostic question.** *"Is every text key canonicalized (trim/upper/unaccent) before it's grouped
  or joined?"*
- **Retail example.** `GROUP BY UPPER(TRIM(customer_name))` (or store a normalized key column); better
  still, join on a surrogate key, not text.
- **Feeds.** SQL-AP-050 - SARC-STR-NORMALIZE-01 - (SC-008 group variants).

### SC-055 -- Split delimited -> rows / build delimited list
- **Definition.** Convert a delimited blob (`"A,B,C"`) into rows (split), and the reverse -- aggregate
  rows into a delimited list (`STRING_AGG`/`LISTAGG`).
- **Why it matters.** Source feeds often pack multi-values into one field; splitting to rows reaches a
  tidy grain (one value per row) before modeling. Building lists is for compact display only.
- **Common failure mode.** Keeping multi-valued fields and matching with `LIKE '%X%'` (false hits);
  splitting with brittle nested `SUBSTRING` instead of a split function/recursive CTE.
- **Diagnostic question.** *"Should this multi-valued field be exploded to one-value-per-row first?"*
- **Retail example.** Split `product.tags = 'sale,clearance'` into one row per tag before any per-tag
  aggregation (and beware fan-out, SC-011).
- **Feeds.** SQL-AP-051 - (SC-003 grain).

### SC-056 -- Pattern matching & regex
- **Definition.** `LIKE`/`SIMILAR TO`/regex to extract, validate, or find non-matching text; anchored
  vs wildcard patterns.
- **Why it matters.** Validation (does this look like an email/postcode?), extraction (pull a code), and
  finding dirty values that *don't* match an expected pattern.
- **Common failure mode.** Leading-wildcard `LIKE '%x'` (non-sargable, SC-033); over-broad patterns that
  match too much.
- **Diagnostic question.** *"Is the pattern anchored and specific? Am I validating or extracting?"*
- **Retail example.** Find malformed postal codes: rows where `postal_code` does **not** match the
  expected pattern -> a data-quality gate.
- **Feeds.** (SC-033 sargability).

### SC-057 -- Fuzzy / sound matching (use with caution)
- **Definition.** `SOUNDEX`/phonetic or edit-distance matching to link near-duplicate spellings.
- **Why it matters.** Helps *surface* likely duplicates (customer name variants) for review -- but is
  approximate.
- **Common failure mode.** Auto-merging on fuzzy match (false merges); using it as a join key.
- **Diagnostic question.** *"Is fuzzy matching surfacing candidates for review, or silently merging
  records?"*
- **Retail example.** Flag customer names that are phonetically equal but spelled differently as
  *candidate* duplicates -- never auto-merge without confirmation.
- **Feeds.** (links SC-013 dedup, human review).

### SC-058 -- Type-safe parsing (is-numeric, safe cast)
- **Definition.** Before casting text to number/date, verify it's parseable (pattern/`TRY_CAST`), and
  decide what an unparseable value becomes (null vs reject).
- **Why it matters.** A single garbage value can error a hard `CAST` (aborting the load) or silently
  mis-convert; explicit handling keeps loads robust and honest.
- **Common failure mode.** `CAST(text AS INT)` over a column with stray non-numeric values.
- **Diagnostic question.** *"Could any value fail this cast, and what should happen if it does?"*
- **Retail example.** `TRY_CAST(raw_qty AS INT)` (or a numeric-pattern check) -> route unparseable rows
  to a quarantine instead of aborting.
- **Feeds.** SQL-AP-052 - SARC-CAST-UNSAFE-01 - (SC-008 nulls).

### Cleaning -- original retail examples

**1. Canonicalize a text key before grouping.**
```sql
SELECT UPPER(TRIM(customer_name)) AS customer_norm, COUNT(*) AS rows
FROM bronze.customer
GROUP BY UPPER(TRIM(customer_name));   -- "Acme ", "acme", "ACME" collapse to one group
```

**2. Data-quality gate via pattern (find non-matching).**
```sql
SELECT customer_key, postal_code
FROM bronze.customer
WHERE postal_code IS NOT NULL
  AND postal_code !~ '^[0-9]{5}$';     -- rows that don't match the expected format (0 = clean)
```

**3. Safe numeric parse with quarantine.**
```sql
SELECT order_line_id,
       TRY_CAST(raw_qty AS INT) AS qty,
       CASE WHEN TRY_CAST(raw_qty AS INT) IS NULL AND raw_qty IS NOT NULL
            THEN 'unparseable' END AS quality_flag
FROM bronze.sales;   -- unparseable values flagged, not silently dropped or error-aborting
```

> Diagnostics: groups split by case/whitespace, or a join misses obvious matches -> **PB-SQL-16**.

---

## Feeds (this file)

- Concepts SC-044..058 - Anti-patterns SQL-AP-042..052 - Playbooks PB-SQL-14, 15, 16 -
  Validation VP-DEDUP, VP-CONTROLTOTAL - Candidates SARC-DML-*, SARC-ROLLUP-01, SARC-GROUPINGFLAG-01,
  SARC-STR-NORMALIZE-01, SARC-CAST-UNSAFE-01.
- Idempotency closes the loop on SC-032 (`sql-reconciliation-playbook.md`); cleaning feeds key
  uniqueness (SC-004) and grouping correctness (SC-005).
