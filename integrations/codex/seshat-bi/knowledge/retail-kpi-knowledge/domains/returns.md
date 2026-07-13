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

## Owner

Operations and Finance (Quality / Buying for unit-based returns).

## Notes

Return value is additive; return rate is non-additive. High return rates flag quality,
sizing, mis-selling, or fraud — monitor by product and branch.
