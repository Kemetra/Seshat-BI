# Discount Amount — Metric Contract

ID: KPI-MC-06

**Business question**
How much value has been given away as discounts over a period?

**Business definition**
Sum of commercial discounts granted to customers (line- and header-level) on completed
qualifying transactions in the selected period, excluding tax adjustments and accounting
write-offs.

**Formula in business terms**
Discount Amount = sum of (line discount + header discount) over qualifying sales lines,
counting header discount once per transaction, not once per line.

**Required fields**
- line discount amount, header discount amount *(assumption)*
- sale date key, branch key, product key, transaction id *(confirmed concept)*
- promotion identifiers *(assumption — optional)*

**Grain**
Transaction line for line discounts; transaction (header) for header discounts.
Aggregable to higher levels.

**Additivity**
Fully additive across time and dimensions — once the header-vs-line double-count is
avoided.

**Recommended dimensions**
Date, branch, region, channel, product, category, brand, supplier, promotion / campaign,
customer segment.

**Filters / exclusions**
- Exclude cancelled transactions and test data.
- Decide treatment of discounts on returns (A2).
- Separate commercial discounts from accounting write-offs and loyalty-point redemptions
  — **Needs business definition** where the source mixes them.
- Do not count tax adjustments as discounts.

**Interpretation**
Total price reductions. Compared against gross sales it gives Discount Rate %. Rising
discount value with flat volume signals margin erosion.

**Common mistakes**
- Double-counting when header discount is spread onto each line (A5).
- Mixing loyalty redemptions or write-offs with cash discounts.
- Counting tax adjustments as discounts.

**Validation checks**
- Reconcile to POS discount summary / promo settlement reports.
- Flag negative discounts or discounts exceeding gross sales at transaction level.
- Compare promo vs non-promo discount distribution.

**Implementation handoff notes (SQL / DAX / Python)**
Sum of line + header discount; consider separate promo-funded vs retailer-funded measures
only if the source supports the split. Flag the header double-count risk so the measure
aggregates header discount at header grain. No DAX authored here.

**Dashboard use**
Sales Performance, Promotion effectiveness, Margin pages, Executive summary.

**Priority**
Core.

**Owner**
Commercial and Finance.

**Status**
Seeded.
