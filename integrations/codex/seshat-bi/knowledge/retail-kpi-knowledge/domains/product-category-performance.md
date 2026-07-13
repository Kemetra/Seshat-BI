# Product / Category Performance Domain

Revenue, returns, margin, and stock movement by SKU and category. Drives assortment and
pricing decisions.

## KPIs in this domain

| KPI | Contract | Status |
|-----|----------|--------|
| Net Sales by Product | — | Planned (reuses Net Sales sliced by product) |
| Returns Rate % (Units) by Product | — | Planned |
| Gross Margin % by Product/Category | `contracts/gross-margin-percent.md` (sliced) | Seeded (base) |
| Sell-Through Rate % | — | Planned (needs beginning-inventory field) |
| GMROI by Category | — | Planned (needs inventory cost snapshots) |

## Decision questions this domain answers

Enter from the business question; each routes to a seeded contract (sliced on the
product/category key) or an honest planned marker. A question never implies a
formula and never invents a contract.

| Decision question | Routes to | Status |
|-------------------|-----------|--------|
| Which products / categories sell the most? | `contracts/net-sales.md` (sliced by product key) | Seeded (base) |
| Which products / categories are most profitable? | `contracts/gross-margin-percent.md` (sliced by product/category) | Seeded (base) |
| Which products are returned most? | — | Planned (Returns Rate % (Units) by Product) |
| How much of bought stock has sold? | — | Planned (needs beginning-inventory field) |
| What return on inventory does each category earn? | — | Planned (GMROI — needs inventory cost snapshots) |

## Key ambiguities (see knowledge/kpi-ambiguities.md)

- A8 Product name vs product key — group on the key; one product → one category path.
- A2 Returns handling for high-return SKUs (overstatement if ignored).
- Discontinued items: include or exclude when analysing active assortment.

## Owner

Commercial and Buying (Supply Chain for sell-through / GMROI).

## Notes

Net Sales by Product and Gross Margin value are additive. Margin %, sell-through, and
GMROI are non-additive ratios — recompute per level.
