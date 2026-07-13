# SQL Core Concepts

> Mental model, grain, keys, COUNT, and NULL semantics (SC-001..008). Distilled, original explanations; all examples use the fictional Seshat retail schema. No book text or datasets reproduced -- see `../references/source-map.md` and `../references/copyright-safety.md`.

## Schema used by every example (fictional, original)

| Table | Grain (one row per...) | Key columns (assumed) |
|---|---|---|
| `sales` | **one order line** | `order_line_id` (PK), `order_id`, `order_date`, `product_key`, `customer_key`, `store_key`, `quantity`, `net_price`, `unit_cost` |
| `product` | one product | `product_key` (PK), `category`, `brand` |
| `customer` | one customer | `customer_key` (PK), `region` |
| `store` | one store | `store_key` (PK), `store_name`, `region` |
| `date` | one calendar date | `date` (PK), `year`, `month` |

---

## Slice 1 overview -- why this matters for Seshat BI

Slice 1 is the **foundation of trustworthy numbers**. Before an agent writes a transformation, a
validation query, or a DAX measure, it must be able to answer one question with certainty: *"what
does one row of this result mean, and is my aggregation honest about it?"* Almost every wrong BI
number traces back to a broken answer here.

Concretely, Slice 1 supports:

- **Source profiling.** You can't profile what you can't describe. Grain, keys, and null behavior
  are the vocabulary of profiling -- "is this column unique?", "how many rows per order?", "what
  fraction is null?"
- **Validation.** The earliest, cheapest gates -- uniqueness, not-null, row-count, grain -- are
  pure Slice 1 reasoning. They catch problems before they propagate.
- **Aggregation correctness.** SUM/COUNT/AVG are only correct *relative to a known grain*. This
  slice is where the agent learns to verify grain before trusting a total.
- **Preventing wrong BI numbers.** Duplicate amplification (fan-out), `COUNT` vs `COUNT DISTINCT`
  confusion, and AVG-of-averages are silent and common. Catching them here stops them reaching
  dashboards.
- **Trustworthy silver/gold.** A silver/gold table is only safe to publish if its grain is
  declared, its keys are unique, and its aggregations are provably correct. Slice 1 is the
  pre-flight checklist for promotion.

The mental analogy to `bi-dax-knowledge`: filter context is the foundation of DAX correctness;
**grain + aggregation correctness is the foundation of SQL correctness.**

---

## Concept cards

Each card: **definition - why it matters for Seshat BI - common failure mode - diagnostic question
- original retail example - feeds (future artifact/rule)**.

### SC-001 -- SQL is set-based and declarative
- **Definition.** SQL describes *what* result set you want, not *how* to compute it row by row.
  You operate on sets of rows; the engine plans execution. There is no inherent row order unless
  you impose one with `ORDER BY`.
- **Why it matters.** Agents must reason about *sets and grain*, not loops. "For each row I'll..."
  thinking leads to correlated-subquery sprawl and grain mistakes. Set thinking leads to clean
  joins and aggregations.
- **Common failure mode.** Assuming rows come back in a stable order without `ORDER BY`; thinking
  procedurally and reaching for row-by-row logic where a set operation is correct and clearer.
- **Diagnostic question.** *"Am I describing a set of rows and its grain, or am I imagining a
  loop?"*
- **Retail example.** "Total revenue by store" is one set operation --
  `SELECT store_key, SUM(quantity * net_price) AS revenue FROM sales GROUP BY store_key` -- not a
  per-store loop.
- **Feeds.** `sql-core-concepts.md` framing; underpins every later rule.

### SC-002 -- Logical query processing order
- **Definition.** SQL clauses are *evaluated* in a logical order that differs from how they're
  written: **FROM/JOIN -> WHERE -> GROUP BY -> HAVING -> SELECT -> DISTINCT -> ORDER BY -> LIMIT**.
- **Why it matters.** It explains the rules that trip agents up: you can't reference a `SELECT`
  alias in `WHERE`; `HAVING` filters groups while `WHERE` filters rows; window functions (computed
  at `SELECT`) can't be used in `WHERE`. Getting this right prevents whole classes of bugs.
- **Common failure mode.** Filtering an aggregate in `WHERE`; expecting a column alias to exist in
  `WHERE`/`GROUP BY`; trying to filter on a window function in `WHERE`.
- **Diagnostic question.** *"At which step does the value I'm filtering on actually exist?"*
- **Retail example.** "Stores with more than 1,000 orders" must filter the **group**:
  `... GROUP BY store_key HAVING COUNT(DISTINCT order_id) > 1000` -- not `WHERE`.
- **Feeds.** `sql-logical-query-processing.md`; rules `SARC-HAVING-01`.

### SC-003 -- Table grain
- **Definition.** The **grain** of a table or query is what a single row represents. `sales` is
  "one order line"; a query that groups by store/day has grain "one store per day." Every dataset
  has a grain, stated or not.
- **Why it matters.** Grain is the unit every aggregation is relative to. You cannot judge whether
  a `SUM` is correct, whether a join is safe, or whether a silver/gold table is publishable without
  knowing the grain. It is the SQL counterpart of "what does this row mean."
- **Common failure mode.** Aggregating before the grain is declared; assuming "one row = one
  transaction" when `sales` is actually one row per *line* (several per order).
- **Diagnostic question.** *"One row of this result is one **what**? Can I name it in a sentence?"*
- **Retail example.** `sales` grain = one order line, so one `order_id` can span many rows;
  counting rows is **not** counting orders.
- **Feeds.** `sql-grain-and-joins.md` (Slice 2); rules `SARC-GRAIN-01`, `SARC-KEY-01`.

### SC-004 -- Keys and uniqueness assumptions
- **Definition.** A key (primary or business) is a column (or set) that uniquely identifies a row.
  "This column is unique" is an **assumption that must be verified**, not a belief.
- **Why it matters.** Joins, counts, and dedup all rest on uniqueness. An unverified key is the
  root cause of fan-out, double-counting, and broken reconciliation.
- **Common failure mode.** Joining on a column presumed unique on the "one" side that actually has
  duplicates; trusting a "key" column name without a check.
- **Diagnostic question.** *"Which columns am I assuming are unique here -- and have I run a
  uniqueness check?"*
- **Retail example.** Before joining `sales` to `product` on `product_key`, verify `product_key`
  is unique in `product` (one row per product). If not, revenue will inflate.
- **Feeds.** `sql-grain-and-joins.md`; rule `SARC-KEY-01`; a future validation pattern.

### SC-005 -- GROUP BY semantics and result grain
- **Definition.** `GROUP BY` collapses rows into one row per distinct combination of the grouped
  columns; that combination **is the new grain**. Every selected non-aggregated column must appear
  in `GROUP BY`.
- **Why it matters.** Grouping deliberately changes grain. Agents must know the output grain to
  reason about downstream joins and aggregations, and to avoid re-inflating it.
- **Common failure mode.** Grouping, then joining back to a finer table and silently restoring the
  old grain; selecting a non-grouped, non-aggregated column.
- **Diagnostic question.** *"After this GROUP BY, what is the new grain, and does anything
  downstream change it again?"*
- **Retail example.** `SELECT store_key, order_date, SUM(quantity*net_price) revenue FROM sales
  GROUP BY store_key, order_date` -> new grain = one store per day.
- **Feeds.** `sql-aggregation-correctness.md`; rules `SARC-GRAIN-01`.

### SC-006 -- COUNT(*) vs COUNT(column) vs COUNT(DISTINCT column)
- **Definition.** `COUNT(*)` counts rows; `COUNT(col)` counts rows where `col` is **not null**;
  `COUNT(DISTINCT col)` counts distinct non-null values. Three different questions.
- **Why it matters.** These diverge exactly when data has nulls or duplicates -- i.e. the cases
  that matter most for validation. Picking the wrong one silently mis-measures.
- **Common failure mode.** Using `COUNT(column)` expecting `COUNT(*)` and under-counting because of
  nulls; counting rows when you meant distinct orders.
- **Diagnostic question.** *"Am I counting rows, non-null values, or distinct entities -- and which
  do I actually want?"*
- **Retail example.** `COUNT(*)` on `sales` = order lines; `COUNT(DISTINCT order_id)` = orders;
  `COUNT(customer_key)` excludes lines with a null customer (guest checkout).
- **Feeds.** `sql-aggregation-correctness.md`; rule `SARC-COUNT-01`.

### SC-007 -- Aggregation correctness and fan-out preview
- **Definition.** An aggregate (`SUM`, `COUNT`) is only correct at the grain it runs on. A
  one-to-many join multiplies rows on the "many" side, so aggregating afterward **double-counts**
  -- "fan-out" (full treatment in Slice 2).
- **Why it matters.** Fan-out is the most dangerous silent bug in BI SQL: the query runs, returns a
  plausible-looking-but-too-large number, and no error is raised.
- **Common failure mode.** `SUM(quantity * net_price)` after joining `sales` to a table that has
  more than one row per `sales` row; "fixing" it with `DISTINCT` instead of fixing the grain.
- **Diagnostic question.** *"Did any join change my grain before this SUM? Could a row be repeated?"*
- **Retail example.** Joining `sales` to a `product_tag` table (many tags per product) inflates
  revenue by the number of tags -- the SUM is now meaningless.
- **Feeds.** `sql-aggregation-correctness.md`, `sql-grain-and-joins.md`; rules `SARC-GRAIN-01`,
  `SARC-DISTINCT-01`.

### SC-008 -- NULLs in aggregation and grouping
- **Definition.** SQL uses three-valued logic (TRUE/FALSE/UNKNOWN). Aggregates **ignore** nulls;
  `GROUP BY` puts all nulls in **one group**; `NULL = NULL` is *unknown* (not true).
- **Why it matters.** Nulls silently change denominators, drop rows from filters, and break
  `NOT IN`. For validation and reconciliation, null behavior must be explicit, not accidental.
- **Common failure mode.** `AVG(col)` quietly excluding null rows from the denominator; a
  `customer_key NOT IN (subquery)` returning nothing because the subquery contains a null.
- **Diagnostic question.** *"Could nulls in this column change my count, my average, or my filter --
  and is that intended?"*
- **Retail example.** `AVG(discount)` over `sales` averages only rows where `discount` is not
  null; if most lines have null discount, the average describes a small subset, not all sales.
- **Feeds.** `sql-aggregation-correctness.md`; rule `SARC-NULL-01`.

---

## Card -> artifact map (Slice 1)

| Concept | Deep-dive file | Anti-patterns | Analyzer candidates |
|---|---|---|---|
| SC-001, SC-003, SC-004 | this file / `sql-grain-and-joins.md` (Slice 2) | SQL-AP-001, 003 | SARC-GRAIN-01, SARC-KEY-01 |
| SC-002 | `sql-logical-query-processing.md` | SQL-AP-007 | SARC-HAVING-01 |
| SC-005, SC-007 | `sql-aggregation-correctness.md` | SQL-AP-002, 005, 008, 009 | SARC-GRAIN-01, SARC-DISTINCT-01 |
| SC-006 | `sql-aggregation-correctness.md` | SQL-AP-004 | SARC-COUNT-01 |
| SC-008 | `sql-aggregation-correctness.md` | SQL-AP-006 | SARC-NULL-01, SARC-AVG-01 |
