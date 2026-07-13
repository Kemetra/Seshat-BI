# Average Basket Size Units - Metric Contract

ID: KPI-MC-15

**Business question**
How many units does a qualifying customer basket contain on average?

**Business definition**
The average number of units sold per qualifying transaction within an approved scope.
This is a unit measure, not a currency measure.

**Formula in business terms**
Relate units sold to qualifying transactions in the same scope. The relationship is
recomputed at every reporting level rather than rolled up from lower-level averages.

**Derives from**
KPI-MC-03 (Units Sold) and KPI-MC-04 (Transactions Count). The registry owns these
derivation edges; this contract does not duplicate their underlying calculations.

**Required fields**
- units sold at the sale-line grain *(confirmed concept)*
- transaction identifier at receipt grain *(confirmed concept)*
- qualifying transaction status and business date *(assumption)*

**Grain**
An aggregated transaction population for a reporting slice; not a single sale line.

**Additivity**
Non-additive. Recompute from total units and qualifying transactions for every rollup.

**Filters / exclusions**
- The owner rules treatment of returns, cancellations, and non-merchandise activity.
- Numerator and denominator use the identical approved transaction population.

**Validation checks**
- Confirm receipt grain is distinct from sale-line grain.
- Confirm both sides use the same filters and period.
- Confirm the result is recomputed rather than summed or averaged across slices.

**Implementation handoff notes (SQL / DAX / Python)**
Ratio intent only. Keep units and transaction populations explicit; no implementation
code is authored here.

**Priority**
Expansion wave.

**Owner**
Sales and Commercial.

**Status**
Seeded generic knowledge contract. Project use still requires approved decisions and
mapped source evidence.
