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

## Owner questions

Ask these before this domain's contracts are handed off. Each card is the owner-facing
form of an ambiguity listed above: it names the question in business language, the
silent breakage if it goes unanswered, and the `decision_type` under which the answer is
recorded in the Decision Store. The **layer default** is context shown to the owner, never
a recorded ruling -- an unanswered card stays `pending` and this domain stays blocked
(`knowledge/kpi-ambiguities.md`, Resolution rule: this layer never invents a policy to
make a number appear).

Every ambiguity listed above has a card here UNLESS it is already marked **RULED** (a
settled decision -- re-asking invites a contradicting answer) or states a grain/handling
instruction rather than a question only the owner can answer. Those exclusions are named
in the row list below rather than left silent.

| # | Ask the owner | If unanswered | Layer default (context only) | Records as |
|---|---------------|---------------|------------------------------|------------|
| unknown | Should an "Unknown" member be treated as a data-quality signal rather than a real category? | "Unknown" is analysed as a genuine product or branch and hides the underlying defect | None -- must be recognised, not analysed as valid | `policy_ruling` |
| nulls | Which blank values are legitimate (for example a walk-in customer), and which are defects? | Real defects are dismissed as expected, or valid rows are flagged as broken | None -- only you can separate allowed from defective | `missing_value_rule` |
| late | How late may data arrive before it counts as late, and in which time zone? | Late-arrival alerts fire on healthy loads or stay silent on broken ones | None -- the SLA is owner-supplied | `policy_ruling` |
| backdated | Are back-dated corrections allowed by policy, or do they indicate a problem? | Genuine corrections are reported as data quality failures | None -- the policy must be stated, not assumed | `policy_ruling` |

## Owner

BI / Data.

## Notes

Counts here are additive; rates are non-additive. These KPIs belong on a control-room
dashboard for the BI team, and must never be mixed into business-performance pages.
Boundary reminder: detecting data-quality issues is in scope here; *fixing* them via SQL
or ETL is owned by the SQL / Python layers, and declaring the model fit to ship is owned
by Readiness.
