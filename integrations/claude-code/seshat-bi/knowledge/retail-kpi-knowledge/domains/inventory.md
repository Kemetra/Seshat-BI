# Inventory Domain

Stock efficiency, service level, and working-capital performance. Built on **semi-additive
inventory snapshots** — the defining constraint of this domain.

## KPIs in this domain

| KPI | Contract | Status |
|-----|----------|--------|
| Inventory Turnover | — | Planned (needs COGS + average inventory cost) |
| Out-of-Stock Rate % | — | Planned (needs stock status + assortment list) |
| Sell-Through Rate % | — | Planned (needs beginning inventory) |
| GMROI | — | Planned (needs inventory cost snapshots) |
| On-Hand Qty / On-Hand Cost (base) | — | Planned |

## Decision questions this domain answers

Enter from the business question; each routes to a seeded contract or an honest
planned marker. This whole domain is planned in the seed (it needs an inventory
snapshot fact), so every question is a deferred note — never a fabricated contract.

| Decision question | Routes to | Status |
|-------------------|-----------|--------|
| How many times did we sell through our stock? | — | Planned (Inventory Turnover — needs COGS + average inventory cost) |
| How often is an item out of stock? | — | Planned (needs stock status + assortment list) |
| How much of received stock has sold? | — | Planned (needs beginning inventory) |
| What return are we earning on inventory investment? | — | Planned (GMROI — needs inventory cost snapshots) |
| How much stock (qty / cost) is on hand right now? | — | Planned (On-Hand Qty / Cost) |

## Key ambiguities (see knowledge/kpi-ambiguities.md)

- A10 Inventory snapshot date — frequency and meaning (on-hand vs on-shelf vs warehouse);
  **Needs business definition**. Never sum snapshots across dates.
- A6 Cost method — turnover and GMROI depend on the valuation method matching finance.
- Out-of-stock: shelf stock vs warehouse stock; treat data-error zeros separately from
  true stockouts.

## Owner

Supply Chain and Finance.

## Notes

This whole domain is planned in the seed because it requires an inventory snapshot fact
that is not yet confirmed. Every KPI here is non-additive (ratios) or semi-additive
(snapshots) — none may be naively summed over time.
