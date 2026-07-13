# Data Quality / Control Room Domain

Trust metrics for the semantic model itself. These are **internal BI operations** KPIs,
never external business performance.

## KPIs in this domain

| KPI | Contract | Status |
|-----|----------|--------|
| Missing Key Dimensions Rate % | — | Planned |
| Late Data Arrival Count | — | Planned |
| Unknown Member Usage | — | Planned |
| Daily Row Count vs Historical Average | — | Planned |

## Decision questions this domain answers

Enter from the business question; each routes to a seeded contract or an honest
planned marker. These are internal BI-operations questions (never business
performance); all are deferred notes — never a fabricated contract.

| Decision question | Routes to | Status |
|-------------------|-----------|--------|
| How often are key dimensions missing? | — | Planned (Missing Key Dimensions Rate %) |
| How much data arrived late? | — | Planned (Late Data Arrival Count) |
| How often is the "Unknown" member used? | — | Planned (Unknown Member Usage) |
| Is today's row count abnormal vs history? | — | Planned (Daily Row Count vs Historical Average) |

## Key ambiguities (see knowledge/kpi-ambiguities.md)

- Distinguish allowed nulls (walk-in customer) from genuine data defects.
- "Unknown" member must be recognised as a quality signal, not a valid analysis member.
- SLA thresholds and time zones for late-arrival logic.
- Back-dated corrections allowed by policy vs true lateness.

## Owner

BI / Data.

## Notes

Counts here are additive; rates are non-additive. These KPIs belong on a control-room
dashboard for the BI team, and must never be mixed into business-performance pages.
Boundary reminder: detecting data-quality issues is in scope here; *fixing* them via SQL
or ETL is owned by the SQL / Python layers, and declaring the model fit to ship is owned
by Readiness.
