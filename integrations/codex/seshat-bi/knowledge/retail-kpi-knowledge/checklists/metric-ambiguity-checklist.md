# Metric Ambiguity Checklist

ID: KPI-CHK-03

Run this whenever numbers disagree between reports, or before sealing any contract that
touches revenue, discount, returns, margin, targets, or inventory. Each item maps to an
ambiguity in `knowledge/kpi-ambiguities.md`. Mark every item Resolved (with the deciding
owner) or **Needs business definition**.

## Required checks

- [ ] **VAT policy** (A1) — amounts pre-tax or tax-inclusive, applied consistently.
- [ ] **Returns policy** (A2) — negative lines vs separate fact; netted vs separate KPI;
      exchange handling.
- [ ] **Date policy** (A3) — primary axis: sale date vs posting date vs return date.
- [ ] **Cost policy** (A6) — cost method (FIFO / average / standard) aligned with finance.
- [ ] **Discount policy** (A5) — line vs header; no double-count.
- [ ] **Cancelled / void / test transaction policy** (A7) — definition and exclusion rule.
- [ ] **Target / budget grain** — target grain matches the actuals grain it is compared to.
- [ ] **Inventory snapshot policy** (A10) — frequency and meaning; never summed over dates.

## Supporting checks

- [ ] Gross vs net not mixed (A4).
- [ ] Aggregation uses product key and branch key, not names (A8, A9).
- [ ] Same-store rule defined where relevant (A11).

## Verdict

Record per item: Resolved (owner) / Needs business definition. Any unresolved required
item blocks the contract from reaching **Seeded**.
