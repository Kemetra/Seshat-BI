# KPI Coverage Scorecard Template

A coverage scorecard answers one question for **one source table**: *which KPIs can
this table support today, and what blocks the rest?* It is a per-table view built by
crossing the table's available fields against each KPI's required fields
(`references/source-field-requirements.md`) and the KPI's contract status
(`knowledge/metric-contracts.md`).

## What this is not

- **Not a score.** Coverage is expressed as an explicit **status + blocker**, never a
  number or percentage. A "70% covered" figure hides which KPIs are blocked and why; it
  fabricates confidence (hard rule #9). If you are tempted to compute a percentage,
  stop — list the statuses and blockers instead.
- **Not readiness.** A scorecard grants no readiness stage and no dashboard/publish
  approval. Those remain human gates owned by the Readiness layer. "Covered" here means
  *the meaning is contracted and the required fields are present* — not *ready to ship*.
- **Not a guess from field presence.** A field merely existing does not make a KPI
  "covered"; and a required field being **absent is a blocker**, never silent coverage.

## Coverage statuses (use exactly these)

| Status | Meaning |
|--------|---------|
| **Covered** | The KPI's contract is **Seeded** *and* every required field is present in this table. Safe to hand off for implementation. |
| **Blocked — missing field** | The contract exists but a required field is absent (or only an unverified assumption). Name the field. |
| **Blocked — needs business definition** | A required policy (VAT, returns, cost method, same-store, snapshot date) is unresolved; the KPI is **Needs business definition** until the owner decides. |
| **Planned** | No seeded contract for this KPI yet; nothing to cover. Route to the planned/deferred note, do not fabricate. |
| **Out of scope** | The KPI belongs to a domain this table cannot serve (e.g. an inventory KPI against a sales-only fact). |

A KPI is **Covered** only when both halves hold: contract Seeded **and** fields present.
Either half failing produces a `Blocked …` or `Planned` status with the reason named.

## How to fill it

1. List the candidate KPIs (start from the relevant `domains/*.md` and its decision
   questions).
2. For each, read its contract status and its required fields
   (`references/source-field-requirements.md`).
3. Check each required field against the table's actual columns (confirm with the source
   owner — do not assume).
4. Assign one status above. If blocked, name the **specific** missing field or undecided
   policy in the Blocker column. Never write a number.

## Scorecard (clone this table per table)

> Table: `<schema.table>` — `<one-line description of grain>`

| KPI | Contract | Coverage status | Blocker (named field / undecided policy) |
|-----|----------|-----------------|------------------------------------------|
| <KPI name> | `contracts/<file>.md` or — | Covered / Blocked — missing field / Blocked — needs business definition / Planned / Out of scope | <the specific blocker, or — if Covered> |

## Worked example — `raw.sales` (line-grain sales fact, illustrative)

Illustrative only: assume `raw.sales` supplies transaction id, sale date key, branch
key, product key, quantity, gross sales amount, and a line discount amount, but has **no
cost field** and **no return flag**, and the VAT policy is undecided.

| KPI | Contract | Coverage status | Blocker (named field / undecided policy) |
|-----|----------|-----------------|------------------------------------------|
| Gross Sales | `contracts/gross-sales.md` | Blocked — needs business definition | VAT included vs excluded (A1) undecided |
| Quantity Sold | `contracts/quantity-sold.md` | Covered | — |
| Transactions Count | `contracts/transactions-count.md` | Covered | — |
| Average Transaction Value | `contracts/average-transaction-value.md` | Blocked — needs business definition | depends on Net Sales, which is VAT/returns-blocked |
| Discount Amount | `contracts/discount-amount.md` | Blocked — missing field | header discount amount absent (only line discount present) |
| Net Sales | `contracts/net-sales.md` | Blocked — missing field | return value / return flag absent; cannot net returns |
| Gross Margin (Value) | `contracts/gross-margin.md` | Blocked — missing field | cost amount (COGS) absent |
| Returns Rate % (Value) | `contracts/returns-rate-value.md` | Blocked — missing field | return value absent |
| Inventory Turnover | — | Out of scope | inventory snapshot fact, not this sales table |
| Net Sales Growth % | — | Planned | no seeded contract |

Reading the example: presence of `quantity` and `transaction id` makes two KPIs
**Covered**; everything else surfaces its **named blocker** — an absent field or an
undecided policy — rather than a coverage percentage. No KPI is marked covered because a
field "might" exist, and no status implies the table is ready to ship.
