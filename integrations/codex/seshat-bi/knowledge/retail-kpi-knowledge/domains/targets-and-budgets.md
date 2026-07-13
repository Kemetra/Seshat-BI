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

## Owner

Finance and Sales.

## Notes

Net Sales vs Target % is non-additive: aggregate actuals and targets separately, then
recompute the percentage. Planned until a target fact exists.
