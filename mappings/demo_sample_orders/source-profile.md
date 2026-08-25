# Source Profile -- demo_sample_orders (spec 083 demo fixture)

> GENERIC, INVENTED sample for the local demo harness. Not client data, not C086,
> not a real source. Authored + reviewed as a fixture (Principle IV/VII).

## Identity

- Source: `tests/fixtures/demo/demo_sample_orders.csv` (a CSV file source).
- Rows: 24. Columns: 9.
- Grain candidate: `order_id` (one row per order line).

## Reporting-date coverage

| Fact | Value |
|---|---|
| Primary reporting-date column | `order_date` |
| Observed coverage start | 2026-01-02 |
| Observed coverage end | 2026-01-13 |
| Coverage evidence | Committed `tests/fixtures/demo/demo_sample_orders.csv`, rows 2-25 |

## Columns (as landed, faithful TEXT)

| Column | Kind | Notes |
|---|---|---|
| `order_id` | grain key | invented `ORD-000NNN` ids; measured UNIQUE (grain ratio 1.00 on 24 rows) |
| `order_date` | date | plain `YYYY-MM-DD` |
| `product_name` | dim attribute | invented product vocabulary (no real brand, no C086) |
| `product_category` | dim attribute | invented categories; near-1:1 with product_name |
| `quantity` | measure (int) | small positive integers |
| `unit_price` | measure (money) | small positive decimals, currency-neutral |
| `line_total` | measure (money) | `quantity * unit_price` -- identity holds on 24/24 rows (measured) |
| `store_location` | dim attribute | invented labels: North / South / Online |
| `payment_method` | dim attribute | invented set: card / cash / voucher |

## Measured facts

- Grain ratio on `order_id`: 1.00 (24 distinct / 24 rows) -- unique.
- `line_total == quantity * unit_price`: holds on 24/24 rows (100%).
- Missingness: none (no empty cells in the sample).
- No customer-identifying column present (no PII ruling to make -- deliberately
  excluded to keep the demo small; the worked example remains the reference for
  the richer PII/returns judgment calls).
