# Net Sales Growth % — Metric Contract

ID: KPI-MC-11

**Business question**
How is realized sales revenue changing versus a comparison baseline?

**Business definition**
The percentage change in Net Sales between the selected period and a comparison
baseline period. **The baseline is RULED** (H9-time-intel D3 = C): SPLY primary,
prior-period secondary — see the comparison-baseline section below.

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
- sale date key (to place a row in the selected period vs the baseline period;
  sale date is the ruled primary axis — H9 D2 = A)
- the comparison-baseline *(RULED — SPLY primary, prior-period secondary; H9 D3 = C)*

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
VAT handling). Adds one decision, now ruled:

**Comparison baseline — RULED (metric owner, 2026-07-05; H9-time-intel D3=C)**
The baseline was owner-pending; the named metric owner (Ahmed Shaaban, metric_owner)
ruled it in decision `H9-time-intel` (D3 = C): **both baselines, year-over-year /
same-period-last-year (SPLY) as the PRIMARY comparison and the immediately prior
period as a NAMED SECONDARY**. Each visual states which baseline it uses. So
"[baseline]" defaults to SPLY (the primary), with prior-period available as the
declared secondary. The ruling is recorded in
`mappings/retail_store_sales/approval-decision-H9-time-intel.md` and the
`semantic_model_ready` `approvals[]` entry; see `domains/time-intelligence.md`,
"Comparison baseline". (A3 in `knowledge/kpi-ambiguities.md` is the sale-vs-posting
DATE-axis ambiguity, a different thing.) The primary-date axis is also ruled: sale
date (H9 D2 = A).

**Interpretation**
The headline growth KPI. Explaining a move belongs to the driver-decomposition
(is it volume or basket?) — see templates/driver-decomposition.md. Do not sum
growth across cells.

**Common mistakes**
- Summing or averaging growth % across periods/branches (it is non-additive).
- Comparing against an unstated baseline (the ruling is SPLY primary / prior-period
  secondary — H9 D3=C; state which one each visual uses).
- Partial-period distortion (a to-date period vs a full baseline period).

**Validation checks**
- Recompute from the Net Sales base at each grain; confirm it never equals a summed
  growth figure.
- Confirm the baseline period is the owner-ruled one (SPLY primary / prior-period
  secondary — H9 D3=C), applied consistently.

**Implementation handoff notes (SQL / DAX / Python)**
Implement as a base-over-base ratio on the Net Sales measure with a time-intelligence
baseline shift on the sale-date axis (H9 D2=A); the baseline is SPLY primary with
prior-period as a declared secondary (H9 D3=C). Do not materialize per-cell growth and
sum it. No DAX authored here.

**Dashboard use**
Executive summary (the `<period-comparison-contract>` reference target), Sales
Performance, Branch/Region performance.

**Priority**
Core, MVP.

**Owner**
Sales Analytics (primary) and Finance.

**Status**
Seeded — the comparison-baseline (SPLY primary / prior-period secondary) and the
primary-date axis (sale date) are both owner-ruled (H9-time-intel D3=C, D2=A,
2026-07-05). No remaining owner-pending decision. Structure/intent only; the DAX/SQL
implementation is a downstream handoff (no measure authored here).
