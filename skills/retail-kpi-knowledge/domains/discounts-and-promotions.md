# Discounts and Promotions Domain

Value given away to customers and the effectiveness of promotional activity.

## KPIs in this domain

| KPI | Contract | Status |
|-----|----------|--------|
| Discount Amount | `contracts/discount-amount.md` | Seeded |
| Discount Rate % | `contracts/discount-rate.md` | Seeded |
| Discounted Transaction Rate | `contracts/discounted-transaction-rate.md` | Seeded |
| Promotion Uplift % | — | Planned (needs promotion dimension + baseline rule) |

## Decision questions this domain answers

Enter from the business question; each routes to a seeded contract or an honest
planned marker. A question never implies a formula and never invents a contract.

| Decision question | Routes to | Status |
|-------------------|-----------|--------|
| How much value did we give away in discounts? | `contracts/discount-amount.md` | Seeded |
| What share of gross sales is discounted? | `contracts/discount-rate.md` | Seeded |
| How often do qualifying transactions carry a discount? | `contracts/discounted-transaction-rate.md` | Seeded |
| How much extra did a promotion drive vs baseline? | — | Planned (needs promotion dimension + baseline rule) |

## Key ambiguities (see knowledge/kpi-ambiguities.md)

- A5 Discount line vs header — state which fields exist and how they combine; avoid
  double-counting.
- A4 Gross vs net — discount rate uses **gross** sales in the denominator.
- Separate commercial discounts from accounting write-offs and loyalty-point redemptions.
- Retailer-funded vs supplier-funded discount — split only if the source supports it.

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
| writeoff | Which deduction types count as discount, and which are accounting write-offs or loyalty redemptions? | Discount rate absorbs unrelated accounting activity and misreports commercial performance | None -- the split is a business ruling | `policy_ruling` |
| funding | Which source field distinguishes a retailer-funded discount from a supplier-funded one? | Supplier-funded discount is charged against your own margin | None -- split only if the source supports it | `policy_ruling` |
| A5 | Are discounts recorded per line, or once on the whole transaction? | Line and header discounts double-count or vanish when summed together | None -- the storage level must be confirmed | `kpi_definition` |
| A4 | Is discount measured against gross or net sales? | Discount rate shifts with the base and cannot be compared | None -- gross and net are never interchangeable | `kpi_definition` |

## Owner

Commercial and Finance.

## Notes

Discount Rate % is non-additive (recompute as total discount ÷ total gross at each
level). Promotion Uplift % requires a robust promotion fact and an agreed baseline
period; it stays planned until both exist.
