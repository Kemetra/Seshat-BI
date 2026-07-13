# Sales Performance KPI Pack

ID: KPI-PK-02

**Purpose**
Executive and sales-management view focused on revenue generation, trend, discounting,
and progress vs target.

**Included KPIs**

| KPI | Contract | State |
|-----|----------|-------|
| Gross Sales | `contracts/gross-sales.md` | Live |
| Net Sales | `contracts/net-sales.md` | Live |
| Transactions Count | `contracts/transactions-count.md` | Live |
| Average Transaction Value | `contracts/average-transaction-value.md` | Live |
| Discount Amount | `contracts/discount-amount.md` | Live |
| Discount Rate % | `contracts/discount-rate.md` | Live |
| Discounted Transaction Rate | `contracts/discounted-transaction-rate.md` | Live |
| Returns Rate % (Value) | `contracts/returns-rate-value.md` | Live |
| Net Sales Growth % | `contracts/net-sales-growth.md` | Live |
| Average Basket Size (Units) | `contracts/average-basket-size-units.md` | Live |
| YTD Net Sales | `contracts/ytd.md` | Live |
| Net Sales vs Target % | — | Planned |

**Required fields**
Sales fact (gross, net/discount, transaction id), date dimension, and units sold. Planned
additions: target fact (vs target). Time and discount policy choices remain owner-rules.

**Blocked-by conditions**
VAT / returns policy confirmed for revenue KPIs; target fact and its alignment policy for
the planned item.

**Owner**
Finance and Sales.

**Recommended dashboard / page use**
Sales Performance page; executive summary trend tiles.

**Readiness notes**
Does not imply readiness; Readiness layer decides.

**Handoff notes**
Eleven live contracts are available for governed handoff; Net Sales vs Target returns to
this layer for contracting after its target evidence and policy are approved.
