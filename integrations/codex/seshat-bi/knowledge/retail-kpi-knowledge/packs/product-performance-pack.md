# Product Performance KPI Pack

ID: KPI-PK-04

**Purpose**
Support buying and merchandising decisions: assortment optimisation, pricing, and stock
movement by SKU / category.

**Included KPIs**

| KPI | Contract | State |
|-----|----------|-------|
| Net Sales by Product/Category | `contracts/net-sales.md` (sliced by product) | Live |
| Quantity Sold by Product | `contracts/quantity-sold.md` | Live |
| Gross Margin % by Product/Category | `contracts/gross-margin-percent.md` | Live |
| Discount Rate % by Product/Category | `contracts/discount-rate.md` | Live |
| Returns Rate % (Units) by Product | — | Planned |
| Inventory Turnover by Product/Category | — | Planned (needs inventory snapshots) |
| Sell-Through Rate % | — | Planned (needs beginning inventory) |
| GMROI by Category | — | Planned (needs inventory cost snapshots) |
| Promotion Uplift % | — | Planned (needs promotion fact + baseline rule) |

**Required fields**
Sales fact + product dimension (category, brand, supplier). Planned additions: inventory
snapshots, beginning-inventory, promotion fact.

**Blocked-by conditions**
Product key (not name) used for grouping; one product → one category path (A8). Inventory
and promotion facts required for the planned KPIs.

**Owner**
Commercial and Buying (Supply Chain for inventory-linked KPIs).

**Recommended dashboard / page use**
Product performance / assortment page; category management views.

**Readiness notes**
Does not imply readiness.

**Handoff notes**
Four live KPIs (product-sliced base contracts) ready for DAX handoff; five planned KPIs
require contracts and extra data.
