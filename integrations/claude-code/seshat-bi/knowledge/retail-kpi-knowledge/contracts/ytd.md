# Year-to-Date Net Sales — Metric Contract

ID: KPI-MC-13

**Business question**
How much Net Sales has accumulated from the start of the year through the selected
date?

**Business definition**
The running accumulation of Net Sales from the year's start boundary to the selected
date. **The year-start boundary is the CALENDAR year (1 January)** and partial-period
comparisons are made **both** to-date-vs-to-date (primary) and against the full prior
year (secondary) — both ruled by the metric owner (H9/YTD-year-start, 2026-07-05); see
the resolved section below.

**Formula in business terms**
YTD Net Sales = accumulation of Net Sales over all dates from the calendar year-start
(1 January of the selected date's year) through the selected date. An accumulation of
an additive base (Net Sales) along the date axis — computed from the base, never from
a summed YTD figure.

**Derives from**
KPI-MC-02 (Net Sales), accumulated along the marked date dimension from the
year-start boundary to the current date. This is a running accumulation of an
additive base metric over the date axis, recomputed from the base — NOT a direct
sum of a non-additive child. (Reference IDs, never filenames.)

**Required fields**
- Net Sales (KPI-MC-02) at line grain, aggregable to day
- a marked, contiguous date dimension (rule S8; time-intelligence needs a date-table
  marker, rule D7)
- the calendar year-start boundary (1 January) *(RULED — E1=A; no fiscal calendar)*

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
Inherits Net Sales's exclusions. Its two prior open decisions are now ruled:

**Year-start boundary + partial period — RULED (metric owner, 2026-07-05; YTD-year-start E1=A, E2=C)**
- **E1 = A (calendar year).** "Year" means the CALENDAR year; the year-start boundary
  is 1 January. No fiscal calendar is declared. (If the organization later declares a
  fiscal year, Finance owns that boundary and this is revisited.)
- **E2 = C (both partial-period comparisons).** A partial current YTD is compared BOTH
  to-date-vs-to-date against the prior year's same to-date point (PRIMARY, like-for-like)
  AND against the full prior-year YTD (SECONDARY, explicitly labelled); each visual
  states which it uses. This mirrors Net Sales Growth %'s ruled both-baselines shape
  (H9 D3=C). The ruling is recorded in
  `mappings/retail_store_sales/approval-decision-YTD-year-start.md`. (A3 in
  `knowledge/kpi-ambiguities.md` is the sale-vs-posting DATE-axis ambiguity, distinct —
  the sale-date axis is separately ruled by H9 D2=A.)

**Interpretation**
Cumulative performance tracking; pairs with Net Sales Growth % for a to-date-vs-SPLY
view. Semi-additive: safe to add across branches at a fixed date, never across dates.

**Common mistakes**
- Summing YTD across dates (it is a to-date accumulation, non-additive on the date
  axis).
- Using a fiscal year-start: the ruling is the CALENDAR year (1 January, E1=A) unless
  a fiscal year is later declared and Finance re-rules the boundary.
- Comparing a partial current YTD to a full prior-year YTD WITHOUT labelling it: the
  primary comparison is to-date-vs-to-date; the full-prior-year view is a labelled
  secondary (E2=C), never an unlabelled substitute.

**Validation checks**
- Recompute to-date from the Net Sales base; confirm it is never a summed YTD.
- Confirm the year-start boundary is the calendar 1 January (the ruled E1=A boundary).

**Implementation handoff notes (SQL / DAX / Python)**
Implement with a time-intelligence to-date accumulation over the marked date table,
anchored at the calendar year-start (1 January); do not materialize per-cell YTD and
sum it. Expose both the to-date-vs-to-date (primary) and full-prior-year (secondary,
labelled) comparisons (E2=C). No DAX authored here.

**Dashboard use**
Executive summary, Sales Performance (cumulative view).

**Priority**
Core, MVP.

**Owner**
Sales Analytics (primary). Finance owns the year-start boundary and has, for now, the
calendar year in force (E1=A); a future fiscal-year declaration is Finance's to re-rule.

**Status**
Seeded — the year-start boundary (calendar, 1 January) and partial-period handling
(both, to-date primary) are owner-ruled (YTD-year-start E1=A, E2=C, 2026-07-05). No
remaining owner-pending decision. Structure/intent only; the DAX/SQL implementation is
a downstream handoff (no measure authored here).
