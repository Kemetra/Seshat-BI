# KPI Derivation Lineage

A static map of which seeded retail KPIs are BASE (computed directly from fact fields)
and which are DERIVED (computed from other KPIs), plus the exact base each derived KPI
depends on. Every edge below is transcribed from the cited contract's own committed
"Formula in business terms" prose -- this map computes no value, ranks nothing, and
carries no score. It maps DERIVATION only; it is NOT a statement about additivity (each
contract's own "Additivity" section and knowledge/kpi-additivity-and-grain.md own that,
and the two axes are orthogonal -- a base KPI may be non-additive and a derived KPI may be
additive).

**Scope**: the 10 existing KPI-MC contracts only (see references/id-conventions.md for the
ID-to-KPI table). Edges reference stable KPI-MC IDs, never filenames.

## Base KPIs (no derives-from edge)

These are computed directly from fact-table fields (a SUM or distinct COUNT over sales
lines or receipts), so they have no parent KPI.

| ID | KPI | Why base (cited prose) |
|----|-----|------------------------|
| KPI-MC-01 | Gross Sales | "sum of gross sales amount (unit list price x quantity, before discount) over qualifying sales lines" -- a direct SUM over a fact field. (The "x quantity" is a line-level field computation, NOT a derivation from KPI-MC-03 Quantity Sold; no edge.) |
| KPI-MC-03 | Quantity Sold | "sum of quantity sold over qualifying sales lines" -- a direct SUM over a fact field. |
| KPI-MC-04 | Transactions Count | "count of distinct transaction id over qualifying transactions" -- a direct distinct COUNT over a fact key. |
| KPI-MC-06 | Discount Amount | "sum of (line discount + header discount) over qualifying sales lines" -- a direct SUM over fact fields. |

## Derived KPIs (derives-from edges)

Each row lists the parent KPI-MC IDs and the contract prose the edge was transcribed from.

| ID | KPI | Derives from | Cited prose |
|----|-----|--------------|-------------|
| KPI-MC-02 | Net Sales | KPI-MC-01, KPI-MC-06 | "Net Sales = Gross Sales - total discount (line + header), pre-tax". |
| KPI-MC-05 | Average Transaction Value | KPI-MC-02, KPI-MC-04 | "ATV = Net Sales / Transactions Count, both over the same qualifying scope". |
| KPI-MC-07 | Discount Rate % | KPI-MC-06, KPI-MC-01 | "Discount Rate % = Discount Amount / Gross Sales * 100". |
| KPI-MC-08 | Returns Rate % (Value) | KPI-MC-02 | "Returns Rate % = Return Value / Net Sales * 100". (Return Value is a field, not a contract node -- no edge to it.) |
| KPI-MC-09 | Gross Margin (Value) | KPI-MC-02 | "Gross Margin = Net Sales - COGS". (COGS is a field, not a contract node -- no edge to it.) |
| KPI-MC-10 | Gross Margin % | KPI-MC-09, KPI-MC-02 | "Gross Margin % = Gross Margin / Net Sales * 100". |

Note: KPI-MC-02 Net Sales is itself derived (from KPI-MC-01 and KPI-MC-06) AND is the base
for four downstream KPIs (KPI-MC-05, KPI-MC-08, KPI-MC-09, KPI-MC-10). A node can be both
an intermediate and a parent.

## Not nodes

These names appear in contract prose but are NOT KPI-MC contracts, so no edge points at
them:

- **Named downstream USES** of Net Sales -- "growth, sales per sqm, vs-target" (from the
  Net Sales Interpretation prose). These are uses, not defined contracts.
- **FIELDS** referenced inside derived formulas -- "Return Value" (KPI-MC-08) and "COGS"
  (KPI-MC-09). These are fact/cost fields, not KPIs with a contract.

Drawing an edge to any of the above would be an invented derivation relationship, which
this doc does not do.

## Blast radius

Because derivation flows downward, a change to a base KPI's definition propagates to its
descendants. Example: a Gross Sales ruling (e.g. the pre-tax VAT decision, A1) changes
KPI-MC-01, which flows to KPI-MC-02 (Net Sales) and KPI-MC-07 (Discount Rate %), and then
on through Net Sales to KPI-MC-05 (ATV), KPI-MC-08 (Returns Rate %), KPI-MC-09 (Gross
Margin), and KPI-MC-10 (Gross Margin %) -- one base ruling, six downstream KPIs touched.
A change to an intermediate node has a smaller blast radius: a Net Sales (KPI-MC-02) ruling
reaches its four dependents KPI-MC-05, KPI-MC-08, KPI-MC-09, and KPI-MC-10. Surfacing the
graph makes this leverage visible instead of implicit.

## Provenance

Every edge above was transcribed from committed contract "Formula in business terms" prose;
no edge was invented. Declaring a NEW derivation relationship that is not stated in a
committed contract is a metric-owner ruling (Principle V) and is out of scope for this
document. This doc grants no readiness or dashboard-readiness stage (Principle I); it is a
DEFINE-layer navigation/reasoning aid over the existing contracts.
