# Same-Store Sales Growth % — Metric Contract

ID: KPI-MC-12

**Business question**
How is sales revenue changing versus a comparison baseline, restricted to the set
of stores comparable across both periods?

**Business definition**
Net Sales Growth % computed over ONLY the comparable ("same") store set. **Both the
comparison baseline AND the definition of a comparable store are owner-pending** —
this contract does NOT decide either; see the two open ambiguities below.

**Formula in business terms**
Same-Store Sales Growth % =
(Net Sales[period, comparable stores] − Net Sales[baseline, comparable stores])
/ Net Sales[baseline, comparable stores].
A base-over-base ratio over the comparable-store subset — never a sum of a growth
figure. "[baseline]" and "comparable stores" both resolve to owner rulings (below).

**Derives from**
KPI-MC-11 (Net Sales Growth %), restricted to the comparable-store subset; i.e.
Net Sales / Net Sales over that subset. A base-over-base recompute of an additive
base metric (Net Sales), NOT a direct sum of a non-additive child. (Reference IDs,
never filenames.)

**Required fields**
- Net Sales (KPI-MC-02) at line grain, aggregable to period
- sale date key (period vs baseline placement)
- branch/store key (to apply the comparable-store filter)
- the comparable-store membership rule *(owner-pending — A11)*
- the comparison-baseline choice *(owner-pending — un-coded)*

**Grain**
Period rollup over the comparable-store set; NOT valid at transaction-line grain.

**Additivity**
Non-additive. A ratio over a store subset: recompute at each grain from the Net
Sales base restricted to comparable stores — never sum or average the growth %.

**Recommended dimensions**
Date (period), region, channel, category — within the comparable-store set.

**Filters / exclusions**
Inherits Net Sales's exclusions. Adds TWO open decisions:

**Open ambiguity 1 — comparable-store definition (OWNER-PENDING, A11)**
Which stores count as "same-store"/comparable? This is ambiguity **A11** in
`knowledge/kpi-ambiguities.md` (same-store definition) — a named human judgment call
depending on minimum-months-open, relocations, closures, refits, and ownership
changes. **The agent does not define it.** The owner rules A11 and records it; until
then this contract is structure-only and cannot go `Seeded`.

**Open ambiguity 2 — comparison baseline (OWNER-PENDING, un-coded)**
Same as KPI-MC-11: SPLY vs prior period. **Un-coded** (A3 is the DATE-axis ambiguity,
not this) — see `domains/time-intelligence.md`. **The agent does not choose it.**
*Recommended for owner consideration:* SPLY, applied to the comparable-store set.

**Interpretation**
The retail like-for-like KPI: isolates organic growth from store-count growth. Only
meaningful once A11 (comparable store) is ruled. Do not sum across cells.

**Common mistakes**
- Summing/averaging same-store growth (non-additive).
- Leaving "comparable store" undefined (A11 must be ruled).
- Mixing new/closed/relocated stores into the comparable set inconsistently.
- An unstated baseline, or partial-period distortion.

**Validation checks**
- Confirm the comparable-store set matches the owner-ruled A11 rule in BOTH periods.
- Recompute base-over-base from Net Sales over the subset; never a summed growth.

**Implementation handoff notes (SQL / DAX / Python)**
Implement as Net Sales Growth % with a comparable-store filter applied identically
to both periods; the filter encodes the owner's A11 ruling. Confirm A11 + the
baseline before coding. No DAX authored here.

**Dashboard use**
Executive summary, Branch/Region performance (like-for-like view).

**Priority**
Core for a multi-store retailer — pending A11 + the baseline ruling.

**Owner**
Retail Operations (owns the comparable-store rule) + Sales Analytics.

**Status**
Planned — structure only; the comparable-store definition (A11) and the comparison
baseline are both owner-pending (not yet ruled).
