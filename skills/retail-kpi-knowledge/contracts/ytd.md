# Year-to-Date Net Sales — Metric Contract

ID: KPI-MC-13

**Business question**
How much Net Sales has accumulated from the start of the year through the selected
date?

**Business definition**
The running accumulation of Net Sales from the year's start boundary to the selected
date. **The year-start boundary and the partial-period handling are owner-pending**
— see the open ambiguity below; this contract does NOT decide them.

**Formula in business terms**
YTD Net Sales = accumulation of Net Sales over all dates from the year-start
boundary through the selected date. An accumulation of an additive base (Net Sales)
along the date axis — computed from the base, never from a summed YTD figure.

**Derives from**
KPI-MC-02 (Net Sales), accumulated along the marked date dimension from the
year-start boundary to the current date. This is a running accumulation of an
additive base metric over the date axis, recomputed from the base — NOT a direct
sum of a non-additive child. (Reference IDs, never filenames.)

**Required fields**
- Net Sales (KPI-MC-02) at line grain, aggregable to day
- a marked, contiguous date dimension (rule S8; time-intelligence needs a date-table
  marker, rule D7)
- the fiscal-vs-calendar year-start boundary *(owner-pending — see below)*

**Grain**
Reported at any date point as the accumulation to that date; per branch/region/etc.

**Additivity**
Semi-additive. YTD Net Sales is additive across non-date dimensions (branch,
product) but NON-additive along the date axis — it is an accumulation, so it must be
recomputed to-date rather than summed across dates. Never sum YTD values across
periods.

**Recommended dimensions**
Date (to-date), branch, region, channel, product, category.

**Filters / exclusions**
Inherits Net Sales's exclusions. Adds one open decision:

**Open ambiguity — year-start boundary + partial period (OWNER-PENDING, un-coded)**
Does "year" mean the fiscal year or the calendar year, and how is a partial current
period normalized when comparing YTD across years? This is a named human judgment
call, **un-coded** in `knowledge/kpi-ambiguities.md` (A3 there is the sale-vs-posting
DATE-axis ambiguity, distinct) — see `domains/time-intelligence.md` on period
boundaries. **The agent does not choose the boundary.** *Recommended for owner
consideration:* the organization's fiscal year if one is declared, else calendar.

**Interpretation**
Cumulative performance tracking; pairs with Net Sales Growth % for a to-date-vs-SPLY
view. Semi-additive: safe to add across branches at a fixed date, never across dates.

**Common mistakes**
- Summing YTD across dates (it is a to-date accumulation, non-additive on the date
  axis).
- Assuming calendar year when a fiscal year is declared (owner ruling).
- Comparing a partial current YTD to a full prior-year YTD without normalization.

**Validation checks**
- Recompute to-date from the Net Sales base; confirm it is never a summed YTD.
- Confirm the year-start boundary matches the owner's fiscal/calendar ruling.

**Implementation handoff notes (SQL / DAX / Python)**
Implement with a time-intelligence to-date accumulation over the marked date table;
do not materialize per-cell YTD and sum it. Confirm the fiscal/calendar boundary
before coding. No DAX authored here.

**Dashboard use**
Executive summary, Sales Performance (cumulative view).

**Priority**
Core, MVP — pending the year-boundary ruling.

**Owner**
Finance (owns the fiscal-year boundary) + Sales Analytics.

**Status**
Planned — structure only; the year-start boundary and partial-period handling are
owner-pending (not yet ruled).
