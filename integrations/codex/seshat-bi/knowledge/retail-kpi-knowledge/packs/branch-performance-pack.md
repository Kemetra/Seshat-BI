# Branch Performance KPI Pack

ID: KPI-PK-03

**Purpose**
Compare store productivity, growth, profitability, and stock/service levels across the
network.

**Included KPIs**

| KPI | Contract | State |
|-----|----------|-------|
| Net Sales (by branch) | `contracts/net-sales.md` (sliced by branch) | Live |
| Transactions Count (by branch) | `contracts/transactions-count.md` | Live |
| Average Transaction Value (by branch) | `contracts/average-transaction-value.md` | Live |
| Returns Rate % (Value) by branch | `contracts/returns-rate-value.md` | Live |
| Gross Margin % by branch | `contracts/gross-margin-percent.md` | Live |
| Net Sales per Branch (dedicated) | — | Planned |
| Same-Store Sales Growth % | — | Planned (Needs business definition: same-store rule) |
| Sales per Square Meter | — | Planned (needs floor-area field) |
| Inventory Turnover by branch | — | Planned (needs inventory snapshots) |
| Out-of-Stock Rate % by branch | — | Planned |
| Net Sales vs Target % by branch | — | Planned (needs target fact) |

**Required fields**
Sales fact + branch dimension (region, format, opening date). Planned additions: store
floor area, same-store flag, inventory snapshots, target fact.

**Blocked-by conditions**
Branch key (not name) used for aggregation (A9); same-store rule defined; store master
data and inventory snapshots available for the planned KPIs.

**Owner**
Operations and Finance.

**Recommended dashboard / page use**
Branch performance page; executive summary network view.

**Readiness notes**
Does not imply readiness.

**Handoff notes**
Five live KPIs (branch-sliced base contracts) ready for DAX handoff; six planned KPIs
require contracts and/or extra source data first.
