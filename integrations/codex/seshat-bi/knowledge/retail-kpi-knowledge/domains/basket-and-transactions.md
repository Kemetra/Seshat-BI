# Basket and Transactions Domain

Customer purchase behaviour at the receipt level. The most grain-sensitive domain:
receipt vs line confusion breaks every metric here.

## KPIs in this domain

| KPI | Contract | Status |
|-----|----------|--------|
| Transactions Count | `contracts/transactions-count.md` | Seeded |
| Average Transaction Value | `contracts/average-transaction-value.md` | Seeded |
| Average Basket Size (Units) | `contracts/average-basket-size-units.md` | Seeded |

## Decision questions this domain answers

Enter from the business question; each routes to a seeded contract or an honest
planned marker. A question never implies a formula and never invents a contract.

| Decision question | Routes to | Status |
|-------------------|-----------|--------|
| How many transactions did we process in the period? | `contracts/transactions-count.md` | Seeded |
| What does the average customer spend per transaction? | `contracts/average-transaction-value.md` | Seeded |
| How many units are in a typical basket? | `contracts/average-basket-size-units.md` | Seeded |

## Key ambiguities (see knowledge/kpi-ambiguities.md)

- Grain: count distinct receipts (`transaction_id`), never transaction lines.
- A7 Exclude cancelled / void / test transactions.
- Returns-only receipts: usually excluded from transaction count and ATV — confirm.
- A1/A4 ATV uses **net sales** in the numerator; keep VAT and gross/net consistent.

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
| A7 | Which transactions should be excluded: cancelled, void, staff, or test? | Basket counts and averages include transactions that never happened | None -- exclusions are a business ruling | `data_exclusion` |
| A1 | Is basket value measured pre-tax or tax-inclusive? | Average basket value is not comparable across branches on mixed bases | Pre-tax unless you state otherwise | `kpi_definition` |

## Owner

Sales / Commercial (Operations for traffic-style metrics).

## Notes

Transaction count is effectively additive across days/branches when `transaction_id` is
unique and time-bounded. ATV and basket size are non-additive — recompute from net sales
÷ distinct receipts (or units ÷ receipts) at every level.
