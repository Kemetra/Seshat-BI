# SQL Date / Time Analysis

> Truncation, the date spine, half-open ranges, rolling windows, period-over-period (SC-021..026). Original retail examples only. See `../references/source-map.md`.

## Slice 4 overview -- why this matters for Seshat BI

Time is the primary axis of BI: nearly every dashboard trends something over dates. Date/time logic
is also where silent errors hide -- a timestamp `BETWEEN` that drops the last day's afternoon, a
period-over-period comparison thrown off by a missing month, a daily count that shifts because two
sources used different time zones. For Seshat BI this slice supports **analytics** (trends, YoY/MoM,
indexing) and **reconciliation** (period totals must tie out and be comparable across time). It also
resolves the Slice 3 sparse-data trap by introducing the **date spine**.

---

## Concept cards (continuing SC-001...020)

### SC-021 -- Date vs timestamp, and truncation to a grain
- **Definition.** A `date` is a day; a `timestamp` carries time-of-day. **Truncating** (e.g.
  `DATE_TRUNC('month', ts)`) buckets a timestamp to the period you analyze.
- **Why it matters.** You analyze at a grain (day, month); raw timestamps are near-unique
  (cardinality, SC-014/profiling) and won't group meaningfully. Truncate to the reporting grain.
- **Common failure mode.** `GROUP BY order_ts` (one group per instant) instead of grouping by a
  truncated/derived day or month.
- **Diagnostic question.** *"At what time grain am I reporting, and have I truncated to it?"*
- **Retail example.** Monthly revenue: `GROUP BY DATE_TRUNC('month', order_date)` (or join to the
  `date` dimension's month), not by the raw order timestamp.
- **Feeds.** SQL-AP-023 - SARC-DATE-TRUNC-01.

### SC-022 -- Time zones
- **Definition.** A timestamp without a zone is ambiguous. Best practice: **store UTC**, convert to
  a business/local zone only when bucketing or displaying.
- **Why it matters.** Daily/period boundaries depend on the zone; mixing zones (or ignoring them)
  shifts events across midnight and corrupts daily counts and day-level reconciliation.
- **Common failure mode.** Grouping UTC timestamps into "days" that don't match the business's local
  day; joining two sources stored in different zones.
- **Diagnostic question.** *"What zone are these timestamps in, and what zone defines a 'day' for the
  business?"*
- **Retail example.** Convert `order_ts` to the store's local zone before truncating to day, so a
  23:30-local sale counts on the correct local date.
- **Feeds.** SQL-AP-024 - SARC-DATE-TZ-01.

### SC-023 -- The date spine (calendar table)
- **Definition.** A complete, gap-free series of dates (our `date` dimension is exactly this). You
  **LEFT JOIN** facts onto the spine so every period appears, even those with no rows.
- **Why it matters.** Trends, rolling windows, and period-over-period (`LAG`/`LEAD`) break on sparse
  data (Slice 3, SC-019). A spine guarantees contiguous periods and makes "zero" periods explicit
  rather than missing.
- **Common failure mode.** Trending directly off `sales` so empty days/months vanish, making rolling
  and offset calculations silently wrong.
- **Diagnostic question.** *"Could a period have zero rows? Then anchor on the date spine, not on the
  fact."*
- **Retail example.** `date d LEFT JOIN sales s ON s.order_date = d.date` -> every calendar day
  present; days with no sales show `COALESCE(SUM(...),0)`.
- **Feeds.** SQL-AP-025 - SARC-DATE-SPINE-01.

### SC-024 -- Date math and half-open ranges
- **Definition.** A period is best expressed as a **half-open interval** `[start, end)` --
  `>= start AND < next_start`. This is exact regardless of time-of-day and avoids boundary
  double-counting.
- **Why it matters.** `BETWEEN start AND end` on a timestamp is inclusive of `end` (a single
  instant) and silently drops the rest of the end day; half-open ranges are unambiguous.
- **Common failure mode.** `WHERE order_ts BETWEEN '2025-01-01' AND '2025-01-31'` -- misses
  Jan-31 after midnight.
- **Diagnostic question.** *"Is my date filter a half-open range, and does it handle time-of-day?"*
- **Retail example.** January 2025: `WHERE order_date >= DATE '2025-01-01' AND order_date < DATE
  '2025-02-01'`.
- **Feeds.** SQL-AP-022, SQL-AP-027 - SARC-DATE-BETWEEN-01, SARC-DATE-SARG-01.

### SC-025 -- Period-over-period (YoY / MoM)
- **Definition.** Compare a period to a comparable earlier one. Two idioms: `LAG` over an ordered,
  **spine-backed** series, or a self-join aligning the shifted period (e.g. this month vs same month
  last year).
- **Why it matters.** The most-requested BI comparison -- and a common source of wrong numbers when
  periods are sparse (SC-023) or when a partial period is compared to a full one (SC-026).
- **Common failure mode.** `LAG` on sparse months (compares non-adjacent months); comparing
  month-to-date against a full prior month.
- **Diagnostic question.** *"Are the two periods truly comparable (same length, contiguous series)?"*
- **Retail example.** MoM over a spine: `revenue - LAG(revenue) OVER (PARTITION BY store_key ORDER BY
  month)`, where `month` comes from the date spine so every month is present.
- **Feeds.** SQL-AP-025, SQL-AP-026 - SARC-DATE-SPINE-01.

### SC-026 -- Percent-of-total and indexing over time
- **Definition.** **Percent-of-total**: a value over a window/period total (window denominator,
  SC-015). **Indexing**: rebase a series to a base period = `value / base_value * 100`, so series of
  different magnitudes are comparable.
- **Why it matters.** These turn raw trends into comparable, interpretable views -- core analytics
  output. Both depend on a correct denominator/base (right grain, guarded division).
- **Common failure mode.** Dividing by a total computed at the wrong grain; division by zero/blank
  base.
- **Diagnostic question.** *"What is the denominator/base, at what grain, and is the division
  guarded?"*
- **Retail example.** Index monthly revenue to Jan 2025:
  `revenue / FIRST_VALUE(revenue) OVER (PARTITION BY store_key ORDER BY month) * 100` (guard with
  `NULLIF`).
- **Feeds.** (links to SC-008 null/division, SC-015 window denominator).

---

## The picture: anchor on the date spine

```mermaid
flowchart LR
  D["date spine (every day/month)"] -->|LEFT JOIN| F["sales (sparse: some periods empty)"]
  F --> S["complete contiguous series (zeros explicit)"]
  S --> W["safe rolling / LAG / YoY-MoM"]
```

## Original retail examples

**1. Monthly revenue (truncate to grain, half-open year filter).**
```sql
SELECT DATE_TRUNC('month', order_date) AS month,
       SUM(quantity * net_price)       AS revenue
FROM sales
WHERE order_date >= DATE '2025-01-01' AND order_date < DATE '2026-01-01'   -- half-open
GROUP BY DATE_TRUNC('month', order_date);
```

**2. Complete daily series via the date spine (no missing days).**
```sql
SELECT d.date,
       COALESCE(SUM(s.quantity * s.net_price), 0) AS revenue
FROM date d
LEFT JOIN sales s ON s.order_date = d.date
WHERE d.date >= DATE '2025-01-01' AND d.date < DATE '2025-02-01'
GROUP BY d.date;            -- every calendar day appears; empty days show 0
```

**3. MoM change over a spine-backed monthly series.**
```sql
WITH monthly AS (
  SELECT d.month, s.store_key,
         COALESCE(SUM(s.quantity * s.net_price), 0) AS revenue
  FROM date d
  LEFT JOIN sales s ON s.order_date = d.date
  GROUP BY d.month, s.store_key
)
SELECT store_key, month,
       revenue - LAG(revenue) OVER (PARTITION BY store_key ORDER BY month) AS mom_change
FROM monthly;             -- contiguous months guarantee 'previous row' = 'previous month'
```

**4. Indexing a series to a base period.**
```sql
SELECT store_key, month,
       revenue
         / NULLIF(FIRST_VALUE(revenue) OVER (PARTITION BY store_key ORDER BY month), 0) * 100
         AS revenue_index
FROM monthly_store_revenue;   -- base month = 100; later months relative to it
```

**5. The BETWEEN-on-timestamp trap and its fix.**
```sql
-- BUG: misses transactions after midnight on Jan 31 (end is a single instant)
SELECT SUM(quantity * net_price) FROM sales
WHERE order_ts BETWEEN TIMESTAMP '2025-01-01 00:00' AND TIMESTAMP '2025-01-31 00:00';

-- FIX: half-open range covers the whole month regardless of time-of-day
SELECT SUM(quantity * net_price) FROM sales
WHERE order_ts >= TIMESTAMP '2025-01-01 00:00' AND order_ts < TIMESTAMP '2025-02-01 00:00';
```

---

## Slice 4 diagnostic mini-playbook

- **"A trend is missing some days/months"** -> trending off the fact, not a spine (SC-023). LEFT JOIN
  the `date` dimension; COALESCE zeros.
- **"Monthly total is short / boundary looks off"** -> `BETWEEN` on a timestamp dropped the end day
  (SC-024). Use a half-open `>= start AND < next_start`.
- **"Daily counts don't match the business day"** -> time-zone mismatch (SC-022). Convert to the
  business zone before truncating.
- **"YoY/MoM is wrong for some rows"** -> sparse periods or partial-vs-full comparison (SC-025,
  SC-026). Anchor on a spine; compare like-for-like period lengths.
- **"GROUP BY date returns thousands of groups"** -> grouping a raw timestamp (SC-021). Truncate to
  the reporting grain.
- **Stop & request metadata when** the time zone of a source or the business "day" definition is
  unknown -- confirm before bucketing.

## Feeds

- Concepts: SC-021...SC-026 (extend SC-008 nulls/division, SC-015 windows, SC-019 LAG/LEAD).
- Anti-patterns: SQL-AP-022...SQL-AP-027.
- Analyzer candidates: SARC-DATE-BETWEEN-01, SARC-DATE-TRUNC-01, SARC-DATE-TZ-01, SARC-DATE-SPINE-01,
  SARC-DATE-SARG-01, SARC-DATE-PARTIAL-01.
