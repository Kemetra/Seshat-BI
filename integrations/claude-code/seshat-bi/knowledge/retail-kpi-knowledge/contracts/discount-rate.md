# Discount Rate % — Metric Contract

ID: KPI-MC-07

**Business question**
What proportion of gross sales value is being discounted?

**Business definition**
Total discount amount as a percentage of gross sales over a period.

**Formula in business terms**
Discount Rate % = Discount Amount ÷ Gross Sales × 100, with both over the same qualifying
scope. (Gross — not net — in the denominator.)

**Required fields**
Same as Discount Amount and Gross Sales contracts.

**Grain**
Aggregated (branch-period, category-period, channel-period). Not meaningful at a single
transaction except for investigation.

**Additivity**
**Non-additive.** Recompute as total discount ÷ total gross at each level.

**Recommended dimensions**
Date, branch, region, channel, product, category, brand, promotion, customer segment.

**Filters / exclusions**
Same filters as Discount Amount and Gross Sales; numerator and denominator must apply
identical filters.

**Interpretation**
Higher rate = heavier discounting. A healthy range is category-specific. Extreme rates
suggest pricing problems or data issues; aggregated values should sit between 0% and 100%.

**Common mistakes**
- Using net sales instead of gross in the denominator (A4).
- Including zero-gross transactions (e.g., warranty replacements) that distort the ratio.
- Summing or averaging discount rates across levels (KPI-AP-04).

**Validation checks**
- Compare by branch and category; investigate outliers.
- Cross-check with promotion analytics / finance.
- Confirm aggregated rate stays within 0–100%.

**Implementation handoff notes (SQL / DAX / Python)**
Ratio measure referencing the Discount Amount and Gross Sales base measures; recomputed in
filter context. Watch filter context when promo vs non-promo dimensions are combined. No
DAX authored here.

**Dashboard use**
Promotion analysis, Margin pages, Executive summary.

**Priority**
Core.

**Owner**
Commercial and Finance.

**Status**
Seeded.
