# Data Quality Control Room KPI Pack

ID: KPI-PK-07

**Purpose**
Support BI operations and trust in the semantic model. These are **internal** metrics for
the BI team — never external business performance.

**Included KPIs**

| KPI | Contract | State |
|-----|----------|-------|
| Missing Key Dimensions Rate % | — | Planned |
| Late Data Arrival Count | — | Planned |
| Unknown Member Usage | — | Planned |
| Daily Row Count vs Historical Average | — | Planned |
| Null / Outlier Rate for Critical Measures | — | Planned (Needs business definition) |
| Failed ETL Jobs Count | — | Planned (needs ETL monitoring source) |

This pack is **planned/deferred** in the current seed; it depends on load/quality
metadata and ETL monitoring sources not yet confirmed.

**Required fields**
Fact keys for null/unknown checks, load timestamp, source-system identifier, SLA rules,
ETL job status. Mostly unconfirmed.

**Blocked-by conditions**
- Allowed-null vs defect distinction defined.
- SLA thresholds and time zones defined for lateness.
- ETL monitoring source available.

**Owner**
BI / Data.

**Recommended dashboard / page use**
Data quality control room; BI operational monitoring (separate from business pages).

**Readiness notes**
Detecting issues here is in scope; fixing them (SQL/ETL/Python) and declaring the model
fit to ship (Readiness) are not. Does not imply readiness.

**Handoff notes**
No DAX handoff yet. First confirm load/quality metadata, then contract these KPIs.
