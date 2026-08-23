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
| A6 | Which cost do you want margin measured against: standard, average, or last purchase cost? | Margin moves materially with the method; two reports disagree with no data change | None -- cost method is a business ruling | `policy_ruling` |
| A4 | Which net-sales definition is the revenue side of margin -- which deductions are already removed? | The net-sales basis is unstated, so margin is not comparable across reports | Net sales is the base -- fixed by this domain, never gross | `kpi_definition` |
| A2 | Do returns reduce the margin of the period they were sold in, or the period returned? | Margin is attributed to the wrong period and trends mislead | None -- the policy must be stated, not assumed | `policy_ruling` |
| A1 | Which VAT basis is cost recorded on, and which is sales recorded on? | A pre-tax cost against a tax-inclusive sale overstates margin | Pre-tax unless you state otherwise | `kpi_definition` |

## Owner

Finance (Commercial as stakeholder).

## Notes

Gross Margin value is additive; Gross Margin % is non-additive (recompute as total margin
÷ total net sales — never average the child percentages, KPI-AP-05).
