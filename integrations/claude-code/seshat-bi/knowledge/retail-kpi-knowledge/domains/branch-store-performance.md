# Branch / Store Performance Domain

Performance compared across the store network. Needs store master data and a same-store
rule to be meaningful.

## KPIs in this domain

| KPI | Contract | Status |
|-----|----------|--------|
| Net Sales per Branch | — | Planned (reuses Net Sales sliced by branch) |
| Same-Store Sales Growth % | — | Planned (Needs business definition: same-store rule) |
| Sales per Square Meter | — | Planned (needs floor-area field) |

Branch-level cuts of seeded KPIs (Net Sales, Transactions Count, ATV, Discount Rate %,
Returns Rate %, Gross Margin %) are available now by slicing those contracts on the
branch key.

## Decision questions this domain answers

Enter from the business question; each routes to a seeded contract (sliced on the
branch key) or an honest planned marker. A question never implies a formula and
never invents a contract.

| Decision question | Routes to | Status |
|-------------------|-----------|--------|
| How much does each branch sell? | `contracts/net-sales.md` (sliced by branch key) | Seeded (base) |
| How do comparable stores grow year on year? | — | Planned (Needs business definition: same-store rule) |
| How productive is each branch per square meter? | — | Planned (needs floor-area field) |
| How does each branch compare on ATV? | `contracts/average-transaction-value.md` (sliced by branch key) | Seeded (base) |
| How does each branch compare on discount rate? | `contracts/discount-rate.md` (sliced by branch key) | Seeded (base) |
| How does each branch compare on returns rate? | `contracts/returns-rate-value.md` (sliced by branch key) | Seeded (base) |
| How does each branch compare on gross margin %? | `contracts/gross-margin-percent.md` (sliced by branch key) | Seeded (base) |

## Key ambiguities (see knowledge/kpi-ambiguities.md)

- A9 Branch name vs branch key — aggregate on the key only.
- A11 Same-store definition — minimum months open, relocations, refurb, closures.
- Treatment of click-and-collect / e-commerce sales attributed to a store.
- Exclude head-office / warehouse pseudo-branches.

## Owner

Operations and Finance.

## Notes

Net Sales per Branch is additive across branches and time. Same-store growth and sales
per sqm are non-additive ratios and stay planned until the same-store rule and store
master data are confirmed.
