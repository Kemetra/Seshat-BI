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

## Owner

Commercial and Finance.

## Notes

Discount Rate % is non-additive (recompute as total discount ÷ total gross at each
level). Promotion Uplift % requires a robust promotion fact and an agreed baseline
period; it stays planned until both exist.
