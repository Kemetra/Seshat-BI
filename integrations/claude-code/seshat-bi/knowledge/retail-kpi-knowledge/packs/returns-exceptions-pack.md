# Returns and Exceptions KPI Pack

ID: KPI-PK-06

**Purpose**
Surface quality issues, fraud, and operational problems through returns and exception
analysis.

**Included KPIs**

| KPI | Contract | State |
|-----|----------|-------|
| Returns Rate % (Value) | `contracts/returns-rate-value.md` | Live |
| Returns Rate % (Units) | — | Planned |
| Net Sales Impact of Returns | — | Planned |
| Returns by Reason Code | — | Planned (needs reason-code field) |
| High-Return Product List (top N) | — | Planned |
| Branches with High Return Rates | — | Planned |

**Required fields**
Returns fact or transaction-type flag, return value, return/sale date, product and branch
keys. Planned additions: returned units, reason code.

**Blocked-by conditions**
- Returns modelling decided: negative lines vs separate fact (A2).
- Primary date axis decided: return date vs original sale date (A3).
- Exchange handling defined (A2) — Needs business definition.

**Owner**
Operations and Finance (Quality / Buying for unit and reason-code analysis).

**Recommended dashboard / page use**
Returns and exceptions page; executive exception tiles.

**Readiness notes**
Does not imply readiness; the live KPI still carries open policy dependencies.

**Handoff notes**
One live KPI ready for DAX handoff (with its open ambiguities flagged); the rest return to
this layer for contracting.
