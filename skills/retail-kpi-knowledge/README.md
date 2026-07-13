# Retail KPI Knowledge

This is an **initial seed** of a retail KPI / metric-contract knowledge layer for BI
agents. It makes retail KPIs contract-first and governed before any implementation work.

What it is not:

- It is **not** a full KPI encyclopedia. The registry distinguishes seeded knowledge
  contracts from planned metadata with concrete blockers.
- It is **not** DAX. No measures are implemented here.
- It is **not** SQL transformation or Python prep.
- It is **not** dashboard design.
- It does **not** grant readiness or pass/block status.

Why it exists: to force every retail KPI to have an agreed business definition, grain,
additivity call, required-field list, and ambiguity review *before* a measure or a
dashboard tile is built. This prevents duplicated DAX, ambiguous tiles, and KPIs that
silently mean different things in different reports.

## Relationship to the F009 metric-contract store and KPI catalog

This layer does **not** replace the existing F009 metric-contract feature; it sits
**upstream** of it. The three are distinct, sequential artifacts — they do not compete:

1. **Catalog (menu)** — `docs/metrics/retail-kpi-catalog.md`: the generic list of *which*
   retail KPIs exist (intent + typical binding). You copy a starting point from here.
2. **This layer (business meaning)** — the prose, governed *reasoning* artifact: what a KPI
   **means** (definition, additivity, grain, required fields, ambiguity, owner ruling),
   reviewed by `checklists/metric-contract-review-checklist.md`. This is the *upstream
   reasoning*, not a stored deliverable.
3. **F009 store (machine-readable, per-table)** — `templates/metric-contract.yaml` copied to
   `mappings/<table>/metrics/<MetricName>.yaml` (lifecycle in
   `docs/metrics/metric-contract-store.md`): the *downstream stored artifact* that binds the
   meaning to a real `gold` column and feeds the DAX generator.

Flow: **catalog → (this layer reasons out the business meaning) → F009 YAML stores it,
bound to a table → SQL/DAX/Python implement it.** This layer produces a business-meaning
contract and a handoff note; the F009 YAML is where that meaning is persisted per table.
A real filled F009 set lives at `mappings/retail_store_sales/metrics/`.

## Current seeded coverage

Live (seeded) metric contracts:

1. Gross Sales — `contracts/gross-sales.md`
2. Net Sales — `contracts/net-sales.md`
3. Quantity Sold — `contracts/quantity-sold.md`
4. Transactions Count — `contracts/transactions-count.md`
5. Average Transaction Value — `contracts/average-transaction-value.md`
6. Discount Amount — `contracts/discount-amount.md`
7. Discount Rate % — `contracts/discount-rate.md`
8. Returns Rate % (Value) — `contracts/returns-rate-value.md`
9. Gross Margin — `contracts/gross-margin.md`
10. Gross Margin % — `contracts/gross-margin-percent.md`
11. Net Sales Growth % - `contracts/net-sales-growth.md`
12. YTD Net Sales - `contracts/ytd.md`
13. Discounted Transaction Rate - `contracts/discounted-transaction-rate.md`
14. Average Basket Size (Units) - `contracts/average-basket-size-units.md`

Also seeded: router/shell files, five knowledge concept files, eleven domain
overviews, seven KPI packs, three review checklists, six reference files (incl. the
KPI coverage scorecard template), and three pattern JSON files.

## Planned / deferred coverage

The authoritative lifecycle and blockers live in `registry.yaml`. The following remain
planned and receive no seeded contract in this feature:

- Same-Store Sales Growth %, Inventory Turnover, Out-of-Stock Rate %, GMROI
- Customer Retention, Customer Lifetime Value, Net Sales vs Target %, Promotion Uplift
- Sales per Square Meter, Returns Rate % (Units), Net Sales per Branch, Net Sales by Product
- Sell-Through Rate %, Missing Key Dimensions Rate %, Late Data Arrival Count
- Missing Key Dimensions Rate %, Late Data Arrival Count
- Customer domain KPIs (e.g., Customer Retention Rate %)

Deferred items are tracked honestly: routes pointing to them return a planned/deferred
note rather than a fabricated contract.
