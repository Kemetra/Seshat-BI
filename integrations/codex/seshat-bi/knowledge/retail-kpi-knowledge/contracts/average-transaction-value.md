# Average Transaction Value — Metric Contract

ID: KPI-MC-05

**Business question**
On average, how much does a customer spend per transaction?

**Business definition**
Net sales divided by the number of distinct qualifying transactions in the selected
period. Also called average receipt value or average basket value (in currency).

**Formula in business terms**
ATV = Net Sales ÷ Transactions Count, both over the same qualifying scope.

**Derives from**
KPI-MC-02 (Net Sales), KPI-MC-04 (Transactions Count) -- transcribed from this contract's
formula "ATV = Net Sales / Transactions Count" and its required field "net sales amount
(from Net Sales contract)". (Reference IDs, never filenames. See
references/kpi-derivation-lineage.md for the full graph.)

**Required fields**
- net sales amount *(from Net Sales contract)*
- transaction id at header level *(confirmed concept)*
- sale date key, branch key, channel key *(confirmed concept)*

**Grain**
Derived KPI evaluated at aggregated levels: aggregated net sales ÷ distinct transactions
within each group. Not meaningful at a single transaction.

**Additivity**
**Non-additive.** Must be recomputed at every level; never sum or average ATV across
branches, days, or channels.

**Recommended dimensions**
Date, branch, region, channel, customer segment, promotion period.

**Filters / exclusions**
- Exclude cancelled / void transactions.
- Exclude return-only transactions (usual policy — confirm; must match Transactions Count).
- Numerator and denominator must share identical scope (e.g., do not pair POS-only
  transaction count with all-channel net sales).

**Interpretation**
Higher ATV means customers buy more, or pricier, items per visit. Used for upsell /
cross-sell and promotion effectiveness.

**Common mistakes**
- Summing ATV from detail rows instead of recomputing (non-additive — KPI-AP-05).
- Pairing a transaction count from a subset with total net sales.
- Counting returns / cancelled sales as transactions, deflating ATV.

**Validation checks**
- Recompute from raw export for a sample branch-month: net sales ÷ distinct receipts.
- Cross-check against any POS standard ATV report.
- Inspect transaction-level outliers for data errors.

**Implementation handoff notes (SQL / DAX / Python)**
Define as a ratio of the Net Sales base measure over a distinct count of the header key;
recomputed in filter context, never pre-aggregated. Flag the header-grain requirement for
the distinct count. No DAX authored here.

**Dashboard use**
Sales Performance, Basket and transaction analysis, Branch performance.

**Priority**
Core.

**Owner**
Sales and Commercial.

**Status**
Seeded.
