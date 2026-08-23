# Targets / Budgets Domain

Actual performance against plan. Requires a target/budget fact aligned to the same grain
as actuals.

## KPIs in this domain

| KPI | Contract | Status |
|-----|----------|--------|
| Net Sales vs Target % | — | Planned (needs target fact) |

## Decision questions this domain answers

Enter from the business question; each routes to a seeded contract or an honest
planned marker. This domain needs a target/budget fact, so its question is a
deferred note — never a fabricated contract.

| Decision question | Routes to | Status |
|-------------------|-----------|--------|
| Are we hitting our sales target? | — | Planned (Net Sales vs Target % — needs target fact) |

## Key ambiguities (see knowledge/kpi-ambiguities.md)

- Grain match: compare actuals and targets at the **same** grain; mismatched grain is a
  core anti-pattern (KPI-AP-09).
- Calendar alignment between target periods and actual periods.
- Missing targets (e.g., new stores) must be flagged, not shown as 0%.
- Same filter scope (channels, branches) on actuals and targets.

## Owner questions

Ask these before this domain's contracts are handed off. Each card is the owner-facing
form of an ambiguity listed above: it names the question in business language, the
silent breakage if it goes unanswered, and the `decision_type` under which the answer is
recorded in the Decision Store. The **layer default** is context shown to the owner, never
a recorded ruling -- an unanswered card stays `pending` and this domain stays blocked
(`knowledge/kpi-ambiguities.md`, Resolution rule: this layer never invents a policy to
make a number appear).

| # | Ask the owner | If unanswered | Layer default (context only) | Records as |
|---|---------------|---------------|------------------------------|------------|
| grain | At what level are targets set: month by store, by category, or another grain? | Actuals and targets are compared at mismatched grain (KPI-AP-09) | None -- the target grain is owner-supplied | `table_grain` |
| missing | How should a store or product with no target be shown? | A missing target is displayed as 0% achievement and reads as total failure | None -- must be flagged, never shown as 0% | `policy_ruling` |
| scope | Do targets cover the same channels and branches as the actuals they are compared to? | A partial-scope target is compared to full-scope actuals and always looks missed | None -- the scope must be confirmed | `policy_ruling` |

## Owner

Finance and Sales.

## Notes

Net Sales vs Target % is non-additive: aggregate actuals and targets separately, then
recompute the percentage. Planned until a target fact exists.
