# Margin / Profitability Domain

Profit after cost of goods. Depends entirely on the cost method aligning with finance.

## KPIs in this domain

| KPI | Contract | Status |
|-----|----------|--------|
| Gross Margin (Value) | `contracts/gross-margin.md` | Seeded |
| Gross Margin % | `contracts/gross-margin-percent.md` | Seeded |
| GMROI | — | Planned (needs inventory cost snapshots) |

## Decision questions this domain answers

Enter from the business question; each routes to a seeded contract or an honest
planned marker. A question never implies a formula and never invents a contract.

| Decision question | Routes to | Status |
|-------------------|-----------|--------|
| How much profit did we make after cost of goods? | `contracts/gross-margin.md` | Seeded |
| What share of net sales is gross profit? | `contracts/gross-margin-percent.md` | Seeded |
| What return are we earning on inventory investment? | — | Planned (GMROI — needs inventory cost snapshots) |

## Key ambiguities (see knowledge/kpi-ambiguities.md)

- A6 Cost method (FIFO / average / standard) — must match finance; else margin is
  **Needs business definition**.
- A4 Use **net sales**, never gross, as the revenue side of margin.
- A2 Align returns handling (COGS reversals) with the Net Sales policy.
- A1 Exclude VAT consistently from both sales and cost.

## Owner

Finance (Commercial as stakeholder).

## Notes

Gross Margin value is additive; Gross Margin % is non-additive (recompute as total margin
÷ total net sales — never average the child percentages, KPI-AP-05).
