# Visual -> contract binding map -- retail_store_sales

The artifact the DESIGN REVIEW signs off: proves every measure-bearing visual binds
to exactly ONE approved metric contract (no orphan visual) and that no approved
contract is silently dropped. Authored by `dashboard-design`; it NEVER invents a
metric and NEVER self-grants `dashboard_ready: pass`. ASCII, UTF-8 no BOM.

## Subject area

- subject_area: `RetailStoreSales` (`gold.fct_sales_rss`)
- governed_model: `../../../powerbi/RetailStoreSales.SemanticModel`
- semantic_model_ready: `pass`

## Binding map (every visual -> exactly one APPROVED contract)

All 5 approved contracts are bound; 10 measure-bearing visuals, zero orphans.

| visual_id | visual_type | business_question | bound_contract (approved) | semantic_model_field(s) |
|-----------|-------------|-------------------|---------------------------|-------------------------|
| v01 | card | Q1 headline revenue | TotalSales | `[TotalSales]` |
| v02 | card | Q1 transaction volume | TransactionCount | `[TransactionCount]` |
| v03 | card | Q1/Q5 basket value | AvgTransactionValue | `[AvgTransactionValue]` |
| v04 | card | Q1 discount share (caveated) | DiscountedTransactionRate | `[DiscountedTransactionRate]` |
| v05 | line | Q2 trend / seasonality | TotalSales | `[TotalSales]` by `dim_date_rss[full_date]` (month) |
| v06 | bar | Q3 revenue by category | TotalSales | `[TotalSales]` by `dim_product_rss[category]` |
| v07 | bar | Q3 units by category | TotalQuantity | `[TotalQuantity]` by `dim_product_rss[category]` |
| v08 | bar/donut | Q4 channel split | TotalSales | `[TotalSales]` by `dim_location_rss[location]` |
| v09 | column | Q5 basket value by payment method | AvgTransactionValue | `[AvgTransactionValue]` by `dim_payment_method_rss[payment_method]` |
| v10 | table | Q6 top customers by activity | TransactionCount | `[TransactionCount]` by `dim_customer_rss[customer_id]` (Top N) |

> Every row cites one APPROVED contract by name + the mapped model field(s). No visual
> lacks a backing approved contract (no orphan). A measure reused across visuals (e.g.
> TotalSales in v01/v05/v06/v08) is still ONE contract bound multiple ways -- allowed;
> what is forbidden is a visual with NO approved contract behind it.

## Contract coverage (all 5 approved contracts appear)

| approved_contract | on which visuals |
|-------------------|------------------|
| TotalSales | v01, v05, v06, v08 |
| TransactionCount | v02, v10 |
| AvgTransactionValue | v03, v09 |
| DiscountedTransactionRate | v04 |
| TotalQuantity | v07 |

## Dropped contracts (record each -- no silent omission)

None. All 5 approved contracts are bound to at least one visual on the page.

## Caveat carried to the page (not a binding issue, a data-honesty note)

- v04 (DiscountedTransactionRate): the approved contract is the KNOWN-STATUS rate
  (50.37% = discounted / known status); unknown-status transactions are EXCLUDED. The
  card must footnote that 33.39% of transactions have an unknown discount status, and
  that the floor (if unknowns were treated as not-discounted) is 33.55%. Source:
  `../metrics/DiscountedTransactionRate.yaml`.

## Review sign-off (Principle V -- the reviewer's action, NOT the skill's)

- reviewer (BI report owner): `data_owner` (the user, acting as BI report owner)
- decision: `approved`
- at: `2026-06-25`

> Sign-off recorded 2026-06-25: the BI report owner reviewed this binding map (10
> visuals, all bound 1:1 to approved contracts, zero orphans, the v04 discount caveat
> noted) and approved the design. `dashboard_ready` is promoted to `pass` with a
> matching `approvals[]` entry in `readiness-status.yaml`. (Recorded by the reviewer,
> not self-granted by the skill.)
