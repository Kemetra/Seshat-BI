# Source Field Requirements

Representative fields the seeded contracts reference. This is a **logical** field list,
not a schema. Every field is marked by confidence; nothing here asserts that a specific
source actually contains it. Confirm with source owners before implementation.

Confidence legend: **confirmed-concept** (a field of this meaning is expected in any retail
sales model) · **assumption** (likely present but must be verified) · **derived**
(computed during modelling).

## Sales fact (logical)

| Field (logical) | Confidence | Used by |
|-----------------|-----------|---------|
| transaction id (header-level) | confirmed-concept | transactions-count, ATV, all |
| transaction line id | assumption | line-grain measures |
| sale date key | confirmed-concept | all |
| posting date key | assumption | date-policy alternative (A3) |
| branch / store key | confirmed-concept | all |
| product key | confirmed-concept | most |
| category key (via product) | assumption | product/category cuts |
| channel key | assumption | channel cuts |
| customer key | assumption | customer KPIs (planned) |
| quantity sold | confirmed-concept | quantity-sold, average-basket-size-units |
| gross sales amount (pre-discount, pre-VAT) | assumption | gross-sales |
| line discount amount | assumption | discount-amount |
| header discount amount | assumption | discount-amount |
| discount qualification indicator | assumption | discounted-transaction-rate |
| net sales amount (pre-tax) | assumption (or derived) | net-sales |
| tax / VAT amount | assumption | VAT policy (A1) |
| cost amount (COGS) | assumption | gross-margin |
| return flag / transaction type | assumption | returns, exclusions |
| return value | assumption | returns-rate-value |
| cancellation / void / test flags | assumption | exclusions (A7) |

## Dimensions (logical)

| Field | Confidence | Used by |
|-------|-----------|---------|
| date dimension (with fiscal attributes) | confirmed-concept | time intelligence (planned) |
| branch attributes (region, format, opening date) | assumption | branch KPIs |
| store floor area (sqm) | assumption | sales-per-sqm (planned) |
| product attributes (category, brand, supplier) | assumption | product KPIs |

## Planned-only sources (not confirmed)

- target / budget fact (target amount, aligned grain) — for vs-target (planned)
- inventory snapshot fact (on-hand qty, on-hand cost, snapshot date) — for inventory
  (planned)
- promotion dimension / fact (promo id, start/end) — for uplift (planned)
- load timestamp, source-system id, SLA rules — for data-quality KPIs (planned)

## Rule

If a contract needs a field marked **assumption**, the contract must flag it; the DAX/SQL
layers verify existence. This layer never upgrades an assumption to a fact on its own.
