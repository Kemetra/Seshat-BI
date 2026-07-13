# Gross Sales — Metric Contract

ID: KPI-MC-01

**Business question**
How much sales value did the business generate at list price, before discounts and
returns, in a given period?

**Business definition**
Sum of sales value at list price (before any discount) for completed, qualifying sales
within the selected period, excluding cancelled, void, and test transactions. Returns are
handled separately (see filters), so this reflects gross sales outflow at list value.

**Formula in business terms**
Gross Sales = sum of gross sales amount (unit list price × quantity, before discount) over
qualifying sales lines.

**Required fields**
- gross sales amount per line *(assumption — confirm it is pre-discount and pre-VAT)*
- sale date key *(confirmed concept — FK to date dimension)*
- branch/store key, product key, transaction id *(confirmed concept)*
- cancellation / void / test flags *(assumption)*
- return flag or transaction type *(assumption — needed if returns excluded)*

**Grain**
Computed from transaction-line grain; aggregable to any higher grain (branch-day,
product-month, etc.).

**Additivity**
Fully additive across all dimensions and time, provided lines are not double-counted.

**Recommended dimensions**
Date, branch, region, channel, product, category, brand, supplier, customer segment.

**Filters / exclusions**
- Exclude cancelled / void transactions.
- Exclude test / training stores and internal transfers (policy).
- Exclude pure return transactions if returns are a separate KPI.
- VAT treatment must match the gross sales amount definition (assume pre-tax — A1).

**Interpretation**
Total commercial value of goods at list price. The gap between gross and net sales shows
discount intensity. A large or rising gap signals aggressive discounting.

**Common mistakes**
- Mixing gross and net amounts in one measure or visual (A4).
- Including cancelled / test transactions.
- Treating returns as negative gross sales without an agreed policy (A2).
- Inconsistent VAT treatment across branches / channels (A1).

**Validation checks**
- Reconcile period total against POS/ERP sales summary.
- Spot-check receipts: line qty × list price = stored gross value.
- Confirm pre-go-live periods show zero, not blank or noise.

**Implementation handoff notes (SQL / DAX / Python)**
Base additive amount → implement as a SUM measure on the sales fact, sliced by a proper
date dimension with single-direction relationships. Confirm the gross amount field is
pre-discount and pre-VAT before coding. No DAX is authored in this layer.

**Dashboard use**
Executive summary, Sales Performance, Branch and Product performance pages.

**Priority**
Core, MVP.

**Owner**
Finance (primary); Sales / Commercial stakeholders.

**Status**
Seeded.
