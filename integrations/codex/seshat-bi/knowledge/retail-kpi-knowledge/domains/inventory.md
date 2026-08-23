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

## Owner questions

Ask these before this domain's contracts are handed off. Each card is the owner-facing
form of an ambiguity listed above: it names the question in business language, the
silent breakage if it goes unanswered, and the `decision_type` under which the answer is
recorded in the Decision Store. The **layer default** is context shown to the owner, never
a recorded ruling -- an unanswered card stays `pending` and this domain stays blocked
(`knowledge/kpi-ambiguities.md`, Resolution rule: this layer never invents a policy to
make a number appear).

Every ambiguity listed above has a card here UNLESS it is already marked **RULED** (a
settled decision -- re-asking invites a contradicting answer) or states a grain/handling
instruction rather than a question only the owner can answer. Those exclusions are named
in the row list below rather than left silent.

| # | Ask the owner | If unanswered | Layer default (context only) | Records as |
|---|---------------|---------------|------------------------------|------------|
| oos | Which stock location defines out-of-stock, and which source indicator separates a genuine zero from a data-error zero? | Availability is measured on the wrong location, or data-error zeros are counted as genuine stockouts | None -- name the location AND the rule that separates the two zero populations | `missing_value_rule` |
| A10 | How often is stock captured, and does a snapshot mean on-hand, on-shelf, or warehouse stock? | Inventory value, turnover and GMROI are computed on a snapshot whose cadence and scope are unknown | None -- both the cadence and the meaning must be stated | `kpi_definition` |
| A6 | Which cost should inventory be valued at? | Stock value changes materially with the method | None -- cost method is a business ruling | `policy_ruling` |

## Owner

Supply Chain and Finance.

## Notes

This whole domain is planned in the seed because it requires an inventory snapshot fact
that is not yet confirmed. Every KPI here is non-additive (ratios) or semi-additive
(snapshots) — none may be naively summed over time.
