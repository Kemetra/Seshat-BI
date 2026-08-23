# Returns Domain

Customer returns by value and by units. Returns expose whether sales facts hide
reversals and which date axis is used.

## KPIs in this domain

| KPI | Contract | Status |
|-----|----------|--------|
| Returns Rate % (Value) | `contracts/returns-rate-value.md` | Seeded |
| Returns Rate % (Units) | — | Planned |
| Net Sales Impact of Returns | — | Planned |
| Returns by Reason Code | — | Planned (needs reason-code field) |

## Decision questions this domain answers

Enter from the business question; each routes to a seeded contract or an honest
planned marker. A question never implies a formula and never invents a contract.

| Decision question | Routes to | Status |
|-------------------|-----------|--------|
| What share of sales value is returned? | `contracts/returns-rate-value.md` | Seeded |
| What share of units sold is returned? | — | Planned (Returns Rate % (Units)) |
| How much do returns reduce net sales? | — | Planned (Net Sales Impact of Returns) |
| Why are customers returning items? | — | Planned (needs reason-code field) |

## Key ambiguities (see knowledge/kpi-ambiguities.md)

- A2 Returns as negative sales vs separate fact — prefer separate fact / explicit
  `transaction_type`; never let returns net invisibly into sales.
- A3 Return date vs original sale date — state the primary axis; they will not reconcile
  if mixed.
- Exchanges: treat as return + new sale, or netted? Needs business definition.
- Exclude non-customer returns (warehouse corrections, stock adjustments).

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
| exchange | Should an exchange be recorded as a return plus a new sale, or netted to nothing? | Return rate and gross sales both change materially with the choice | None -- needs a business definition | `policy_ruling` |
| noncustomer | Should warehouse corrections and stock adjustments count as customer returns? | Return rate is inflated by movements no customer ever made | None -- exclusions are a business ruling | `data_exclusion` |
| A2 | Are returns stored as negative sales lines or as a separate returns record? | Returns are netted invisibly and true return volume is hidden | None -- the policy must be stated, not assumed | `policy_ruling` |
| A3 | Should a return be counted on the date it was returned, or the date of the original sale? | Return rate is attributed to the wrong period | None -- each contract must name its primary date | `kpi_definition` |

## Owner

Operations and Finance (Quality / Buying for unit-based returns).

## Notes

Return value is additive; return rate is non-additive. High return rates flag quality,
sizing, mis-selling, or fraud — monitor by product and branch.
