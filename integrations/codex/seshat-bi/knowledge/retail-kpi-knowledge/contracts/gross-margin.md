# Gross Margin (Value) — Metric Contract

ID: KPI-MC-09

**Business question**
How much gross profit is generated after subtracting cost of goods sold from net sales?

**Business definition**
Net sales minus cost of goods sold (COGS) for the same qualifying transactions in the
selected period.

**Formula in business terms**
Gross Margin = Net Sales − COGS.

**Required fields**
- net sales amount *(from Net Sales contract)*
- cost amount (COGS) per line *(assumption — must align with finance cost method, A6)*
- sale date key, branch key, product key *(confirmed concept)*

**Grain**
Transaction line; aggregable to product, branch, period.

**Additivity**
Fully additive across time, branches, and products (value, not percentage).

**Recommended dimensions**
Product, category, brand, supplier, branch, region, channel, promotion.

**Filters / exclusions**
- Exclude non-merchandise revenue not associated with a COGS.
- Align returns handling (COGS reversals) with the Net Sales policy (A2).
- Exclude VAT from both sales and cost consistently (A1).

**Interpretation**
Value available to cover operating expenses and profit after paying for inventory. The
core retail profitability measure.

**Common mistakes**
- Using gross sales instead of net sales (A4).
- Using a cost approximation that does not match the accounting method (A6).
- Ignoring returns and discounts when computing COGS.

**Validation checks**
- Reconcile total gross margin to finance P&L for a sample period.
- Check margin by category for expected patterns (high in accessories, low in commodities).
- Confirm COGS is captured at the same grain as net sales.

**Implementation handoff notes (SQL / DAX / Python)**
Define base Net Sales and COGS measures, then Gross Margin = Net Sales − COGS. Confirm the
cost method with finance before coding; if unknown, this KPI is Needs business definition.
No DAX authored here.

**Dashboard use**
Margin pages, Product / Branch performance, Executive summary.

**Priority**
Core, MVP.

**Owner**
Finance.

**Status**
Seeded — depends on a confirmed cost method (A6); becomes Needs business definition if the
method is undefined.
