# Inventory Control KPI Pack

ID: KPI-PK-05

**Purpose**
Stock efficiency, service level, and working-capital performance for supply-chain and
finance.

**Included KPIs**

| KPI | Contract | State |
|-----|----------|-------|
| Inventory Turnover | — | Planned (needs COGS + average inventory cost) |
| Out-of-Stock Rate % | — | Planned (needs stock status + assortment) |
| Sell-Through Rate % | — | Planned (needs beginning inventory) |
| GMROI | — | Planned (needs inventory cost snapshots) |
| On-Hand Qty / On-Hand Cost (base) | — | Planned |

This pack is **entirely planned/deferred** in the current seed: it depends on an
inventory snapshot fact that is not yet confirmed.

**Required fields**
Inventory snapshot fact (on-hand qty, on-hand cost, snapshot date, product/branch keys),
COGS from the sales fact, assortment list per store. All currently unconfirmed.

**Blocked-by conditions**
- Inventory snapshot frequency and meaning defined (A10) — Needs business definition.
- Cost method aligned with finance (A6).
- Assortment list available for out-of-stock.

**Owner**
Supply Chain and Finance.

**Recommended dashboard / page use**
Inventory control room; supply-chain page (after data and contracts exist).

**Readiness notes**
Not ready; no live KPI in this pack. Does not imply readiness.

**Handoff notes**
No DAX handoff from this pack yet. First step is confirming the inventory snapshot fact,
then writing contracts in this layer.
