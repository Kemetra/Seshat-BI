# Retail KPI Knowledge Router

Route first. Each route opens the fewest files and ends on a checklist, a contract,
a verdict, or a handoff. Do not scan the whole knowledge base.

Status legend: **[seeded]** file exists in this seed · **[planned]** route named but
target deferred · resolve **[planned]** routes by returning a planned/deferred note.

## 1. Task routes

| Task | Open | End on |
|------|------|--------|
| Define Net Sales | `contracts/net-sales.md` | metric-contract-review-checklist |
| Define Gross Sales | `contracts/gross-sales.md` | metric-contract-review-checklist |
| Define Gross Margin / Margin % | `contracts/gross-margin.md`, `contracts/gross-margin-percent.md` | metric-contract-review-checklist |
| Define ATV | `contracts/average-transaction-value.md` | metric-contract-review-checklist |
| Choose MVP dashboard KPIs | `packs/mvp-retail-kpi-pack.md` | kpi-pack-review-checklist |
| Decide if a KPI can be summed | `knowledge/kpi-additivity-and-grain.md` | metric-contract-review-checklist |
| Resolve VAT / returns / cost ambiguity | `knowledge/kpi-ambiguities.md` | metric-ambiguity-checklist |
| Write a brand-new KPI contract | `references/metric-contract-template.md` | metric-contract-review-checklist |
| See which KPIs are base vs derived (and the base each derived KPI depends on) | `references/kpi-derivation-lineage.md` | the derivation graph (no readiness, no score) |
| Prepare DAX handoff (measure) | relevant `contracts/*.md` + `references/metric-contract-template.md` | handoff note to DAX (formula, additivity, filters — not DAX code) |
| Prepare SQL handoff (required fields, grain, transform, reconciliation) | relevant `contracts/*.md` + `references/source-field-requirements.md` | handoff note to SQL (fields, grain, exclusions, validation — not SQL code) |
| Prepare Python handoff (single-node source-prep) | relevant `contracts/*.md` + `references/source-field-requirements.md` | handoff note to Python (required fields + dtype/quality assumptions — not Python code) |
| Prepare Big-data handoff (distributed / at-scale aggregation & reconciliation) | relevant `contracts/*.md` + `references/source-field-requirements.md` | handoff note to Big-data (required fields, grain + additivity for distributed aggregation, scale reconciliation checks — not job code; only when too large for single-node) |
| Confirm required source fields | `references/source-field-requirements.md` | metric-contract-review-checklist |
| Check if one KPI's contract is complete enough to build | `../../templates/kpi-sufficiency-card.md` | per-KPI sufficiency card (`ready`/`blocked` + named blockers, never a score; grants no readiness) |
| Assess which KPIs a source table can support | `references/kpi-coverage-scorecard-template.md` + `references/source-field-requirements.md` | per-table coverage scorecard (statuses + named blockers, never a score; grants no readiness) |

## 2. Symptom routes

| Symptom | Open | End on |
|---------|------|--------|
| "Gross and net sales are mixed" | `knowledge/kpi-ambiguities.md` | metric-ambiguity-checklist |
| "Average was summed across branches" | `knowledge/kpi-additivity-and-grain.md` | metric-contract-review-checklist |
| "Return rate differs by report" | `contracts/returns-rate-value.md` + `knowledge/kpi-ambiguities.md` | metric-ambiguity-checklist |
| "ATV total row is wrong" | `contracts/average-transaction-value.md` + `knowledge/kpi-additivity-and-grain.md` | metric-contract-review-checklist |
| "Dashboard has a KPI with no definition" | `knowledge/metric-contracts.md` | metric-contract-review-checklist |
| "Discount looks double-counted" | `contracts/discount-amount.md` + `knowledge/kpi-ambiguities.md` | metric-ambiguity-checklist |
| "Inventory KPI uses wrong date grain" | `domains/inventory.md` (overview) + `knowledge/kpi-additivity-and-grain.md` | metric-contract-review-checklist (per-KPI inventory contracts **[planned]**) |
| "Same-store numbers don't reconcile" | `knowledge/kpi-ambiguities.md` | metric-ambiguity-checklist (same-store **[planned]**) |

## 3. Domain routes

All domain overviews are **[seeded]** as summaries; deep per-KPI contracts beyond the
10 core seeds are **[planned]**.

| Domain | File |
|--------|------|
| Sales & revenue | `domains/sales-and-revenue.md` |
| Discounts & promotions | `domains/discounts-and-promotions.md` |
| Returns | `domains/returns.md` |
| Basket & transactions | `domains/basket-and-transactions.md` |
| Branch / store performance | `domains/branch-store-performance.md` |
| Product / category performance | `domains/product-category-performance.md` |
| Inventory | `domains/inventory.md` |
| Margin / profitability | `domains/margin-profitability.md` |
| Targets & budgets | `domains/targets-and-budgets.md` |
| Time intelligence | `domains/time-intelligence.md` |
| Data quality / control room | `domains/data-quality-control.md` |
| Customer | `domains/customer.md` -- **[seeded]** overview; per-KPI contracts [planned] |

## 4. KPI pack routes

| Pack | File | End on |
|------|------|--------|
| MVP first dashboard | `packs/mvp-retail-kpi-pack.md` | kpi-pack-review-checklist |
| Sales performance | `packs/sales-performance-pack.md` | kpi-pack-review-checklist |
| Branch performance | `packs/branch-performance-pack.md` | kpi-pack-review-checklist |
| Product performance | `packs/product-performance-pack.md` | kpi-pack-review-checklist |
| Inventory control | `packs/inventory-control-pack.md` | kpi-pack-review-checklist |
| Returns & exceptions | `packs/returns-exceptions-pack.md` | kpi-pack-review-checklist |
| Data quality control room | `packs/data-quality-control-room-pack.md` | kpi-pack-review-checklist |

## 5. File map

```
skills/retail-kpi-knowledge/
  SKILL.md            scope, workflow, boundaries, stop rules
  INDEX.md            this router
  README.md           seed scope and disclaimers
  knowledge/          cross-cutting reasoning (concepts, contracts, additivity, ambiguity, domains)
  domains/            per-domain KPI overviews (12 files)
  contracts/          10 seeded metric contracts
  packs/              7 KPI pack definitions
  checklists/         contract review, pack review, ambiguity
  references/         template, field requirements, id conventions, derivation lineage, source map, research notes
  patterns/           metric patterns, anti-patterns, candidate KPIs (JSON)
```

Seeded contracts (10): gross-sales, net-sales, quantity-sold, transactions-count,
average-transaction-value, discount-amount, discount-rate, returns-rate-value,
gross-margin, gross-margin-percent.

## 6. Stop rules

- A route ending in "DAX code", "SQL", "Python", "readiness pass", or "dashboard
  visual" is **out of scope** → emit a handoff note, do not produce the artifact.
- A **[planned]** route returns a planned/deferred note, never a fabricated contract.
- If no route matches, return to `SKILL.md` boundaries; do not free-scan the base.
- Never grant readiness or dashboard-readiness from this layer.
