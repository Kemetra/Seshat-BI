# MVP Retail KPI Pack

ID: KPI-PK-01

**Purpose**
The first governed dashboard's KPI set — a balanced view across sales, basket behaviour,
discounting, returns, branch/product performance, margin, inventory, plan-vs-actual, and
data reliability. Use this pack to scope an MVP without over-building.

**Included KPIs**
First 20 recommended KPIs. Thirteen have seeded generic knowledge contracts; the other
seven are **planned/deferred** and must not be treated as ready.

| # | KPI | Contract | State |
|---|-----|----------|-------|
| 1 | Gross Sales | `contracts/gross-sales.md` | Live |
| 2 | Net Sales | `contracts/net-sales.md` | Live |
| 3 | Quantity Sold | `contracts/quantity-sold.md` | Live |
| 4 | Transactions Count | `contracts/transactions-count.md` | Live |
| 5 | Average Transaction Value | `contracts/average-transaction-value.md` | Live |
| 6 | Discount Amount | `contracts/discount-amount.md` | Live |
| 7 | Discount Rate % | `contracts/discount-rate.md` | Live |
| 8 | Returns Rate % (Value) | `contracts/returns-rate-value.md` | Live |
| 9 | Gross Margin (Value) | `contracts/gross-margin.md` | Live |
| 10 | Gross Margin % | `contracts/gross-margin-percent.md` | Live |
| 11 | Net Sales Growth % | `contracts/net-sales-growth.md` | Live |
| 12 | Average Basket Size (Units) | `contracts/average-basket-size-units.md` | Live |
| 13 | Net Sales by Branch | — | Planned/deferred |
| 14 | Net Sales by Product | — | Planned/deferred |
| 15 | Inventory Turnover | — | Planned/deferred |
| 16 | Out-of-Stock Rate % | — | Planned/deferred |
| 17 | Net Sales vs Target % | — | Planned/deferred |
| 18 | YTD Net Sales | `contracts/ytd.md` | Live |
| 19 | Missing Key Dimensions Rate % | — | Planned/deferred |
| 20 | Late Data Arrival Count | — | Planned/deferred |

**Required fields**
Sales fact (gross amount, net amount or discount components, quantity, transaction id,
cost amount), date dimension, branch and product dimensions. Planned KPIs additionally
need: a target fact (17), inventory snapshots (15, 16), and load/quality metadata
(19, 20). Time policy choices remain owner-rules.

**Blocked-by conditions**
- VAT, returns, and cost-method policies confirmed (A1, A2, A6) for the live revenue and
  margin KPIs.
- Cost method confirmed before #9/#10 leave Needs business definition.
- Planned KPIs blocked until their extra source facts exist and contracts are written.

**Owner**
BI lead, coordinating Finance (revenue/margin), Commercial (discount), Operations
(transactions/returns).

**Recommended dashboard / page use**
Executive summary tiles + a Sales Performance page. Show only the 13 live KPIs on the
first release; reserve placeholders for planned KPIs.

**Readiness notes**
This pack does **not** imply dashboard readiness. Contract completeness is necessary but
not sufficient; the Readiness layer owns the pass/block decision.

**Handoff notes**
Hand the 13 live contracts to the DAX/semantic layer with their business-terms formulas,
grain, additivity, and open ambiguities. Hand planned KPIs back to this layer for
contracting before any DAX work.
