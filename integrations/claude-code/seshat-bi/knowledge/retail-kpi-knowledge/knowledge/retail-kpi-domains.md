# Retail KPI Domains

The domains this layer organises KPIs into. Each has a one-file overview in `domains/`.
Use this page to pick the right domain, then open that domain file. Per-KPI contracts
live in `contracts/` (14 seeded and one planned); `registry.yaml` owns the full
machine-readable lifecycle inventory.

## Sales and revenue

Top-line value: gross sales, net sales, growth, ATV, sales per sqm. Owns the gross-vs-net
and VAT distinctions that everything else inherits. → `domains/sales-and-revenue.md`

## Discounts and promotions

Value given away and promotion effectiveness: discount amount, discount rate %,
promotion uplift. Depends on line-vs-header discount clarity. →
`domains/discounts-and-promotions.md`

## Returns

Refunded/reversed sales by value and by units. Depends on the returns-modelling and
return-date policies. → `domains/returns.md`

## Basket and transactions

Customer purchase behaviour: transaction count, average basket size. Grain-sensitive
(receipt vs line). → `domains/basket-and-transactions.md`

## Branch / store performance

Per-branch revenue, same-store growth, sales per sqm. Needs store master data and a
same-store rule. → `domains/branch-store-performance.md`

## Product / category performance

Revenue, returns, margin, and sell-through by SKU/category. Needs stable product keys
and one category hierarchy. → `domains/product-category-performance.md`

## Customer

Retention, frequency, and lifetime value. Requires reliable customer identification;
**planned** — no domain file in this seed, summarised here.

## Inventory

Stock efficiency and service level: turnover, out-of-stock, sell-through, GMROI. Built on
semi-additive snapshots. → `domains/inventory.md`

## Margin / profitability

Gross margin value and %, GMROI. Depends on cost method alignment with finance. →
`domains/margin-profitability.md`

## Targets / budgets

Actual vs plan: net sales vs target %. Needs a target fact aligned to the same grain as
actuals. → `domains/targets-and-budgets.md`

## Time intelligence

Cumulative and comparison views: YTD, period-over-period. Needs a marked date table and
careful additivity (YTD is semi-additive). → `domains/time-intelligence.md`

## Data quality / control room

Trust metrics for the model itself: missing key dimensions, late data arrival. Internal
BI operations, never external performance. → `domains/data-quality-control.md`
