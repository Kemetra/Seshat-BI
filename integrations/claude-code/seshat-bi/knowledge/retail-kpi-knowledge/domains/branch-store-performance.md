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
| channel | Should click-and-collect and e-commerce sales be attributed to a store? | Store performance either double-counts online sales or misses them entirely | None -- attribution is a business ruling | `policy_ruling` |
| pseudo | Which branches are not real stores (head office, warehouse) and should be excluded? | Pseudo-branches appear in store rankings and distort every per-store average | None -- exclusions are a business ruling | `data_exclusion` |
| A9 | Should branches be grouped by branch key, or by branch name? | A renamed or re-coded branch splits into two, breaking every trend | None -- key vs name is an identity ruling | `kpi_definition` |
| A11 | Which stores count as "same-store", and after how long does a new store join? | Like-for-like growth silently includes new stores and overstates performance | None -- same-store is a business definition | `policy_ruling` |

## Owner

Operations and Finance.

## Notes

Net Sales per Branch is additive across branches and time. Same-store growth and sales
per sqm are non-additive ratios and stay planned until the same-store rule and store
master data are confirmed.
