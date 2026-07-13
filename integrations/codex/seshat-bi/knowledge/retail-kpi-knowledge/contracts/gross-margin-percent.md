# Gross Margin % — Metric Contract

ID: KPI-MC-10

**Business question**
What is gross margin as a percentage of net sales?

**Business definition**
Gross margin value divided by net sales, expressed as a percentage, over the same
qualifying scope.

**Formula in business terms**
Gross Margin % = Gross Margin ÷ Net Sales × 100.

**Required fields**
Same as Gross Margin and Net Sales contracts.

**Grain**
Aggregated (product-category-branch-period, etc.).

**Additivity**
**Non-additive.** Recompute as total margin ÷ total net sales at each level.

**Recommended dimensions**
Product, category, brand, supplier, branch, region, channel, promotion.

**Filters / exclusions**
Same as Gross Margin; numerator and denominator must apply identical filters.

**Interpretation**
Higher margin % indicates a more profitable mix or pricing. Used for category management
and pricing. The weighted average margin must equal total margin ÷ total net sales.

**Common mistakes**
- Averaging child margins instead of recomputing from totals (KPI-AP-05).
- Using gross sales or including VAT (A1 / A4).
- Comparing margins across channels with different cost allocations without context.

**Validation checks**
- Compare to finance margin reports at category and total level.
- Confirm weighted average margin = total gross margin ÷ total net sales.
- Confirm aggregated margin % is plausible (typically 0–100% for retail merchandise).

**Implementation handoff notes (SQL / DAX / Python)**
Derive from the existing Gross Margin and Net Sales base measures; do not duplicate the
margin logic per visual. Watch filter contexts where some costs may be missing (partial
periods, special channels). No DAX authored here.

**Dashboard use**
Margin pages, Product / Branch performance, Promotion analysis.

**Priority**
Core.

**Owner**
Finance and Commercial.

**Status**
Seeded — inherits the cost-method dependency from Gross Margin (A6).
