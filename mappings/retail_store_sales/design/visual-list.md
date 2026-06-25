# Visual list -- retail_store_sales

The proposed visuals for the single overview page (see `dashboard-layout.md`).
Professional and FOCUSED, not exhaustive: F011A discipline -- a compact KPI strip +
one main trend + a few diagnostics + one detail table. We do NOT emit every
measure x dimension combination (that is a wall, not a dashboard); each visual earns
its place by answering a distinct business question. Every visual binds to exactly
ONE approved contract (the binding map is the sign-off artifact).

| visual_id | region | type | answers | measure (approved contract) | sliced by |
|-----------|--------|------|---------|-----------------------------|-----------|
| v01 | KPI strip | card | Q1 headline revenue | TotalSales | (page filters) |
| v02 | KPI strip | card | Q1 volume | TransactionCount | (page filters) |
| v03 | KPI strip | card | Q1/Q5 basket value | AvgTransactionValue | (page filters) |
| v04 | KPI strip | card | Q1 discount share (caveated) | DiscountedTransactionRate | (page filters) |
| v05 | Main insight | line | Q2 trend / seasonality | TotalSales | by month (dim_date_rss) |
| v06 | Diagnostic A | bar (horizontal) | Q3 which categories drive revenue | TotalSales | by category (dim_product_rss) |
| v07 | Diagnostic A | bar (horizontal) | Q3 which categories drive units | TotalQuantity | by category (dim_product_rss) |
| v08 | Diagnostic B | bar / donut | Q4 channel split | TotalSales | by location (dim_location_rss) |
| v09 | Diagnostic B | column | Q5 basket value by payment method | AvgTransactionValue | by payment_method (dim_payment_method_rss) |
| v10 | Exception/detail | table | Q6 highest-activity customers | TransactionCount | by customer_id (dim_customer_rss), Top N |

## Design discipline (why this set, and what was deliberately left off)

- **10 visuals, single page** -- a professional executive overview, not a dense grid.
  Each business question (Q1-Q6) is served by the minimum visuals that answer it.
- **No redundant pairings.** Each measure appears where it best answers a question:
  TotalSales as KPI + trend + category + channel (its 3 most-asked cuts); TotalQuantity
  only where units differ from revenue (category mix, v07); AvgTransactionValue as KPI +
  the one cut that explains it (payment method, v09). We did NOT also chart every measure
  by every dim (e.g. TransactionCount by location, AvgTransactionValue by category) --
  those are drill-downs a user reaches via the filter rail, not standing visuals.
- **Visual type fits the contract grain** (F011A): additive measure at a point ->
  card; over time -> line; by a dimension -> bar/column; row-level/Top-N -> table.
- **v04 / DiscountedTransactionRate carries the caveat** (a footnote on the card):
  the APPROVED rate is known-status (50.37% = discounted / known status); 33.39% of
  transactions have unknown status (excluded), and the floor (unknowns as
  not-discounted) is 33.55%.

## See also

- The sign-off artifact: `visual-contract-binding-map.md`.
- The layout: `dashboard-layout.md`. The contracts: `../metrics/*.yaml`.
