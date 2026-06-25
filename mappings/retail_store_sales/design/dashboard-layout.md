# Dashboard layout plan -- retail_store_sales

Filled instance (the second worked example, after C086). Authored by the
`dashboard-design` verb from the 5 APPROVED metric contracts once
`semantic_model_ready` reached `pass`. AUTHORING ONLY -- no publish, no Power BI
Desktop / DB connection, no execution adapter (that is F016). ASCII, UTF-8 no BOM.

## Subject area

- subject_area: `RetailStoreSales` (gold star `gold.fct_sales_rss`)
- governed_model: `../../../powerbi/RetailStoreSales.SemanticModel`
- semantic_model_ready: `pass`   # gate cleared (mappings/retail_store_sales/readiness-status.yaml)

## Business questions (analyst-supplied -- Principle V input)

Owner asked for "all possible" -- the full set answerable from the 5 approved
contracts across the available dimensions (date, product/category, location,
payment_method, customer):

1. How are we doing overall right now? (headline volume + basket value + discount share)
2. How do sales move over time -- trend / seasonality?
3. Which product categories drive sales and units?
4. How do sales split by channel (location: in-store vs online) and payment method?
5. What is the basket value (avg transaction value) and how does it vary by channel?
6. Who are the highest-activity customers (transaction count)?

> Out of answerable scope with the current contracts (recorded, not invented):
> margin/profit (no cost data); returns (none in this source). NOTE: the approved
> DiscountedTransactionRate IS the known-status rate (50.37% = discounted / known
> status); carry the contract's floor (33.55%) and unknown-status (33.39%) figures as
> caveats on any discount visual.

## Page / section structure (one question per region, in reading order)

A single executive overview page; KPI strip + one main-insight trend, then diagnostic
breakdowns, then an exception/detail table. Detail-heavy cross-tabs are deliberately
kept to one table (F011A: reserve tables for diagnostic/exception, keep the executive
page from becoming a dense grid).

| Region | Purpose | Business question it serves |
|--------|---------|-----------------------------|
| Header | title + as-of context | (orientation) |
| Filter rail (compact) | date range, category, location, payment_method slicers | scopes every region |
| KPI strip | the 4 headline numbers at a glance | Q1 |
| Main insight | TotalSales over time (the trend) | Q2 |
| Diagnostic A | TotalSales by category; TotalQuantity by category | Q3 |
| Diagnostic B | TotalSales by location; AvgTransactionValue by payment_method | Q4, Q5 |
| Exception/detail | top customers by TransactionCount | Q6 |
| Footer-status | data-as-of + the discount caveat note | (honesty) |

## Notes

- One row per region maps to one or more visuals in `visual-list.md`; every visual
  binds to exactly one approved contract (see `visual-contract-binding-map.md`).
- Filter-rail slicers are dimension slicers (date/category/location/payment_method);
  they are NOT visuals bound to a measure contract, so they do not appear in the
  binding map (which governs measure-bearing visuals).
- The discount KPI + any discount visual shows the APPROVED DiscountedTransactionRate
  = 50.37% (discounted / known-status), and MUST surface the contract caveat: 33.39%
  of transactions have an UNKNOWN discount status (excluded from the rate), and the
  floor if unknowns were treated as not-discounted is 33.55%. See
  `mappings/retail_store_sales/metrics/DiscountedTransactionRate.yaml`.

## See also

- The binding map (the review sign-off artifact): `visual-contract-binding-map.md`.
- The visual list: `visual-list.md`. The contracts: `../metrics/*.yaml`.
- The stage: `../../../docs/readiness/dashboard-ready.md`; the design foundation:
  `../../../docs/powerbi/visual-design-system.md` (F011A).
