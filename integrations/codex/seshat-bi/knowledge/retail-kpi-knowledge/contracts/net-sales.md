# Net Sales — Metric Contract

ID: KPI-MC-02

**Business question**
How much sales revenue did the business actually realize after discounts, before returns
and tax?

**Business definition**
Sum of sales value after deducting all discounts (line- and header-level), excluding tax,
for completed qualifying sales in the selected period. Returns are reported separately
unless policy states otherwise.

**Formula in business terms**
Net Sales = Gross Sales − total discount (line + header), pre-tax. Equivalently, sum of
net sales amount per qualifying line where net = gross − discounts.

**Derives from**
KPI-MC-01 (Gross Sales), KPI-MC-06 (Discount Amount) -- transcribed from this contract's
formula "Net Sales = Gross Sales - total discount (line + header), pre-tax". Net Sales is
itself a derived KPI and is in turn the base for KPI-MC-05, KPI-MC-08, KPI-MC-09,
KPI-MC-10. (Reference IDs, never filenames. See references/kpi-derivation-lineage.md for
the full graph.)

**Required fields**
- net sales amount per line *(assumption)* — or gross + line discount + header discount to
  derive
- sale date key, branch key, product key, transaction id *(confirmed concept)*
- cancellation / test flags, return flag / transaction type *(assumption)*

**Grain**
Transaction line; aggregable to branch-day, product-day, customer-period, etc.

**Additivity**
Fully additive across dates, branches, products, customers, provided returns are handled
consistently.

**Recommended dimensions**
Date, branch, region, channel, product, category, brand, supplier, customer segment,
promotion, sales rep.

**Filters / exclusions**
- Exclude cancelled / test transactions.
- Decide and document returns treatment: excluded, netted, or separate measure (A2).
- Exclude internal consumption / staff sales if policy requires.
- VAT handling explicit: this contract assumes **pre-tax** net sales (A1).

**Interpretation**
Primary realized-revenue KPI. Base for growth, margin, ATV, sales per sqm, and vs-target.
Define once and reuse rather than re-deriving.

**Common mistakes**
- Mixing pre-tax and post-tax net sales (A1).
- Including returns as negative net sales without disclosing policy (A2).
- Subtracting header discount twice (A5).
- Using posting date instead of sale date without agreement (A3).

**Validation checks**
- Reconcile a sample month to P&L / management reports.
- Compare gross vs net and inspect discount ratio by branch for anomalies.
- Confirm net sales never exceeds gross sales for any transaction.

**Implementation handoff notes (SQL / DAX / Python)**
Implement as a base SUM measure, with separate Gross Sales and Discount measures for
transparency; build derived KPIs on top of this base rather than re-deriving the logic.
Confirm VAT treatment and the discount fields before coding. No DAX authored here.

**Dashboard use**
Executive summary, Sales Performance, Branch / Product performance, Margin pages.

**Priority**
Core, MVP.

**Owner**
Finance (primary) and Sales.

**Status**
Seeded.
