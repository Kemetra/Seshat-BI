# SQL Aggregation Correctness

> COUNT/SUM/AVG correctness and GROUP BY completeness (SC-005..008). Original retail examples only; no book datasets. See `../references/source-map.md`.

**The rule that governs this whole file:** *an aggregate is only correct relative to a known,
verified grain.* So the agent's order of operations is always **(1) state the grain -> (2) verify
the keys -> (3) aggregate -> (4) sanity-check the total**.

---

## 1. Declare the grain of a query (do this first, every time)

Before writing or trusting any aggregate, write one sentence: *"one row of this result is one
___."* If you can't, stop and profile.

```sql
-- Grain: one row per ORDER LINE (the base grain of `sales`)
SELECT order_line_id, order_id, product_key, quantity, net_price
FROM sales;
-- => one row = one order line. An order_id may appear on many rows.
```

## 2. Uniqueness check for `sales.order_line_id`

Never assume a key is unique -- prove it. The "is this column unique?" check returns zero rows when
the column truly is a key:

```sql
-- Returns any value that appears more than once. Empty result = unique.
SELECT order_line_id, COUNT(*) AS n
FROM sales
GROUP BY order_line_id
HAVING COUNT(*) > 1;
```

A compact one-number version (the two numbers should be equal):

```sql
SELECT COUNT(*) AS row_count, COUNT(DISTINCT order_line_id) AS distinct_keys
FROM sales;            -- row_count == distinct_keys means the key is unique
```

## 3. COUNT(*) vs COUNT(DISTINCT order_id)

These answer different business questions on the same table:

```sql
SELECT
  COUNT(*)                    AS order_lines,   -- rows: one per line
  COUNT(DISTINCT order_id)    AS orders,        -- distinct orders (many lines each)
  COUNT(customer_key)         AS lines_with_customer  -- excludes NULL customer (guest checkout)
FROM sales;
```

If a report says "orders" but the query used `COUNT(*)`, it is reporting **lines**, not orders --
a classic silent overstatement (see SQL-AP-004).

## 4. Detecting duplicate product keys

`product` is supposed to be one row per product. Verify before relying on it for joins:

```sql
SELECT product_key, COUNT(*) AS n
FROM product
GROUP BY product_key
HAVING COUNT(*) > 1;          -- any rows here = duplicate keys = join will fan out
```

If this returns rows, joining `sales` -> `product` on `product_key` will **multiply** sales rows
and inflate every downstream `SUM`.

## 5. Correct revenue aggregation at day/store grain

A clean aggregation that stays at a well-defined grain (no risky joins to the measure):

```sql
-- Grain of result: one row per (store, day)
SELECT
  store_key,
  order_date,
  SUM(quantity * net_price) AS revenue,
  COUNT(DISTINCT order_id)  AS orders
FROM sales
GROUP BY store_key, order_date;
```

Revenue is computed from `sales` columns at the line grain, then summed into the store/day grain.
No join changed the grain, so the SUM is trustworthy.

## 6. Wrong aggregation caused by fan-out (preview of Slice 2)

Now introduce a one-to-many join and watch revenue inflate:

```sql
-- product_tag has MANY tags per product (one-to-many to product, and thus to sales)
SELECT
  p.category,
  SUM(s.quantity * s.net_price) AS revenue   -- WRONG: inflated by number of tags per product
FROM sales s
JOIN product p       ON p.product_key = s.product_key
JOIN product_tag t   ON t.product_key = p.product_key   -- fan-out happens here
GROUP BY p.category;
```

Each `sales` row is duplicated once per tag, so `revenue` is multiplied by the tag count. The query
runs and looks plausible -- that's what makes fan-out dangerous. Fixes (detailed in Slice 2):
aggregate `sales` to its grain **before** joining, or join to a one-row-per-product tag summary,
not the raw many-row tag table. Using `DISTINCT` to paper over this is an anti-pattern (SQL-AP-009).

## 7. WHERE vs HAVING

`WHERE` filters rows before grouping; `HAVING` filters groups after:

```sql
-- "High-revenue stores in 2025": row filter on year, group filter on revenue
SELECT store_key, SUM(quantity * net_price) AS revenue
FROM sales
WHERE order_date >= DATE '2025-01-01' AND order_date < DATE '2026-01-01'  -- rows
GROUP BY store_key
HAVING SUM(quantity * net_price) > 100000;                                -- groups
```

Putting the revenue test in `WHERE` is invalid; putting the year test in `HAVING` would scan more
than needed and muddle intent.

## 8. NULL-sensitive aggregation

`AVG` silently drops nulls from its denominator -- be explicit about what you mean:

```sql
-- If most lines have NULL discount, this averages only the discounted lines:
SELECT AVG(discount) AS avg_discount_over_discounted_lines
FROM sales;

-- Treat "no discount" as zero across ALL lines (different, usually intended for BI):
SELECT AVG(COALESCE(discount, 0)) AS avg_discount_all_lines
FROM sales;
```

The two numbers can differ dramatically. The agent must decide which denominator the business
means -- and say so. The same care applies to `NOT IN` with a null-bearing subquery (returns
nothing) and to counts on nullable columns (SC-008).

---

## Sanity-check habit (step 4)

After any non-trivial aggregate, the agent should reconcile against a known anchor:

- Does `SUM(quantity * net_price)` over the whole table match the ungrouped total?
- Does the row count of the grouped result equal the number of distinct group keys?
- After a join, did `COUNT(*)` change versus the base table? If yes, suspect fan-out.

These cheap checks catch most Slice 1 errors before they reach silver/gold or DAX.

## Feeds

- Anti-patterns: SQL-AP-002, 004, 005, 006, 008, 009.
- Analyzer candidates: SARC-GRAIN-01, SARC-COUNT-01, SARC-NULL-01, SARC-AVG-01, SARC-DISTINCT-01.
- Concepts: SC-005, SC-006, SC-007, SC-008.
