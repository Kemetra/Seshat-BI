# Net Sales Growth % — Metric Contract

ID: KPI-MC-11

**Business question**
How is realized sales revenue changing versus a comparison baseline?

**Business definition**
The percentage change in Net Sales between the selected period and a comparison
baseline period. **The baseline is owner-pending** — see the comparison-baseline
ambiguity below; this contract does NOT decide it.

**Formula in business terms**
Net Sales Growth % = (Net Sales[period] − Net Sales[baseline]) / Net Sales[baseline].
A base-over-base ratio recomputed at each grain — never a sum of a growth figure.
"[baseline]" resolves to the owner-ruled comparison baseline (see below).

**Derives from**
KPI-MC-02 (Net Sales), taken as a ratio of current-period Net Sales over
baseline-period Net Sales: (Net Sales / Net Sales) − 1. This is a base-over-base
recompute of an additive base metric; it is NOT a direct sum of a non-additive
child. (Reference IDs, never filenames. See references/kpi-derivation-lineage.md.)

**Required fields**
- Net Sales (KPI-MC-02) at the transaction-line grain, aggregable to the period
- sale date key (to place a row in the selected period vs the baseline period)
- the comparison-baseline choice *(owner-pending — see ambiguity below)*

**Grain**
Reported at a period rollup (e.g. month, quarter, year) per branch/region/etc.;
NOT valid at transaction-line grain (a growth % has no meaning on one line).

**Additivity**
Non-additive. A growth percentage is a ratio: recompute it at each grain from the
underlying Net Sales base — never sum or average growth percentages across periods,
branches, or products.

**Recommended dimensions**
Date (period), branch, region, channel, product, category — the same rollups Net
Sales supports.

**Filters / exclusions**
Inherits Net Sales's exclusions (cancelled/test transactions, returns treatment,
VAT handling). Adds one open decision:

**Open ambiguity — comparison baseline (OWNER-PENDING, un-coded)**
Which baseline does "[baseline]" mean: same period last year (SPLY) or the
immediately prior period? This is a named human judgment call. It is **un-coded** in
`knowledge/kpi-ambiguities.md` (A3 there is the sale-vs-posting DATE-axis ambiguity,
a different thing) — see `domains/time-intelligence.md`, "Comparison baseline: same
period last year vs previous period — state it." **The agent does not choose it.**
*Recommended option for the owner to consider:* SPLY for seasonal retail. The owner
DECIDES and records the ruling; until then this contract is structure-only.

**Interpretation**
The headline growth KPI. Explaining a move belongs to the driver-decomposition
(is it volume or basket?) — see templates/driver-decomposition.md. Do not sum
growth across cells.

**Common mistakes**
- Summing or averaging growth % across periods/branches (it is non-additive).
- Comparing against an unstated baseline (state SPLY vs prior period — owner ruling).
- Partial-period distortion (a to-date period vs a full baseline period).

**Validation checks**
- Recompute from the Net Sales base at each grain; confirm it never equals a summed
  growth figure.
- Confirm the baseline period is the owner-ruled one, applied consistently.

**Implementation handoff notes (SQL / DAX / Python)**
Implement as a base-over-base ratio on the Net Sales measure with a time-intelligence
baseline shift; do not materialize per-cell growth and sum it. Confirm the baseline
ruling before coding. No DAX authored here.

**Dashboard use**
Executive summary (the `<period-comparison-contract>` reference target), Sales
Performance, Branch/Region performance.

**Priority**
Core, MVP — pending the baseline ruling.

**Owner**
Sales Analytics (primary) and Finance.

**Status**
Planned — structure only; the comparison-baseline is owner-pending (not yet ruled).
