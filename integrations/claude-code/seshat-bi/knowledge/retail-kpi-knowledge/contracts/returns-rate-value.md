# Returns Rate % (by Value) — Metric Contract

ID: KPI-MC-08

**Business question**
What percentage of sales value is being returned by customers?

**Business definition**
Total value of customer returns in a period divided by total net sales for the same
period, expressed as a percentage. Return value is the absolute value of refunded /
reversed sales, pre-tax unless policy differs.

**Formula in business terms**
Returns Rate % = Return Value ÷ Net Sales × 100.

**Required fields**
- return value — from a returns fact, or net sales amount carrying a negative sign
  *(assumption — depends on returns modelling, A2)*
- return flag / transaction type *(assumption)*
- sale date key and/or return date key *(confirmed concept — primary axis must be chosen)*
- branch key, product key, transaction id *(confirmed concept)*

**Grain**
Return line (and matching sales line); aggregable to branch-period, product-period, etc.

**Additivity**
Return value is additive; the **rate is non-additive** and must be recomputed per level.

**Recommended dimensions**
Date (return date and/or original sale date), branch, region, channel, product, category,
brand, supplier, reason code *(if available)*, customer segment.

**Filters / exclusions**
- Exclude internal write-offs and stock adjustments not tied to customer returns.
- Decide exchange handling: return + new sale, or netted — **Needs business definition**
  (A2).
- Exclude test / training returns.
- Choose and state the primary date axis (return date vs original sale date — A3).

**Interpretation**
High return rates flag quality, sizing, mis-selling, or fraud. Monitor by category and
branch. Compare with unit-based return rate (planned) to detect price-mix effects.

**Common mistakes**
- Treating returns as negative sales with no separate visibility, hiding their extent
  (A2 / KPI-AP-07).
- Mixing sale date and return date across reports (A3).
- Counting inventory adjustments as returns, inflating the rate.

**Validation checks**
- Reconcile total return value to finance / ERP for a sample period.
- Flag branches / products with implausibly high or low return rates.
- Confirm returns link to original sales where possible.

**Implementation handoff notes (SQL / DAX / Python)**
Prefer a separate returns fact or an explicit transaction-type flag; define Net Sales and
Return Value as separate measures and derive the rate from them. Manage sign conventions
carefully. Flag the returns-modelling and date-axis decisions as prerequisites. No DAX
authored here.

**Dashboard use**
Returns and exceptions analysis, Product / Branch performance, Executive exception tiles.

**Priority**
Core.

**Owner**
Operations and Finance.

**Status**
Seeded — with an open dependency: exchange handling and primary date axis are Needs
business definition until the owner confirms.
