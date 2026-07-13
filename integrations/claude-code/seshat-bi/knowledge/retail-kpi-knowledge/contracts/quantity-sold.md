# Quantity Sold — Metric Contract

ID: KPI-MC-03

**Business question**
How many units were sold in a given period?

**Business definition**
Sum of unit quantities on completed, qualifying sales lines within the selected period,
excluding cancelled / void / test transactions. Returned units are not netted here unless
policy states otherwise; returns are reported separately.

**Formula in business terms**
Quantity Sold = sum of quantity sold over qualifying sales lines.

**Required fields**
- quantity sold per line *(confirmed concept)*
- sale date key, branch key, product key, transaction id *(confirmed concept)*
- cancellation / test flags, return flag / transaction type *(assumption)*

**Grain**
Transaction line; aggregable to product-day, branch-day, product-period, etc.

**Additivity**
Fully additive across all dimensions and time, provided lines are not double-counted and
returns are not silently netted.

**Recommended dimensions**
Date, branch, region, channel, product, category, brand, supplier.

**Filters / exclusions**
- Exclude cancelled / void / test lines.
- Decide whether returned units are excluded, netted, or separate (A2).
- Exclude zero-quantity service lines if policy requires.

**Interpretation**
Volume base for unit-based KPIs (basket size, unit return rate, sell-through). Distinct
from revenue: volume can rise while value falls under heavy discounting.

**Common mistakes**
- Netting returns into units sold without disclosure (A2).
- Counting transaction lines as units (a line may carry quantity > 1).
- Mixing sale and return signs in one naive sum.

**Validation checks**
- Reconcile period units to POS quantity reports for a sample branch.
- Check for negative quantities (returns leaking into the measure).
- Confirm units sold ≥ 0 at every aggregation level.

**Implementation handoff notes (SQL / DAX / Python)**
Base additive count → SUM measure on the sales fact. If returns are stored as negative
quantities in the same fact, define separate Units Sold and Units Returned measures
filtered on transaction type rather than a naive SUM. No DAX authored here.

**Dashboard use**
Sales Performance, Basket analysis, Product performance, Inventory (as the sales side).

**Priority**
Core, MVP.

**Owner**
Sales / Commercial (Supply Chain as stakeholder).

**Status**
Seeded.
