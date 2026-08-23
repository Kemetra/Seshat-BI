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
| discontinued | Should discontinued items be included when analysing the active assortment? | Assortment performance mixes live and dead SKUs and misdirects buying | None -- exclusions are a business ruling | `data_exclusion` |
| A8 | Should products be grouped by product key, or by product name? | The same product under two names splits into two rows, or two products merge | None -- key vs name is an identity ruling | `kpi_definition` |
| A2 | Do returns reduce the selling product's performance? | Product ranking is computed on unreturned volume and misleads buying decisions | None -- the policy must be stated, not assumed | `policy_ruling` |

## Owner

Commercial and Buying (Supply Chain for sell-through / GMROI).

## Notes

Net Sales by Product and Gross Margin value are additive. Margin %, sell-through, and
GMROI are non-additive ratios — recompute per level.
