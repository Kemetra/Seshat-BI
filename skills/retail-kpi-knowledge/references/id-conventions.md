# ID Conventions

Stable IDs let routes, packs, patterns, and checklists reference each other without
relying on filenames. Use these prefixes; number sequentially within each prefix.

| Prefix | Meaning | Lives in |
|--------|---------|----------|
| `KPI-CN-*` | Concept | `knowledge/kpi-core-concepts.md` |
| `KPI-MC-*` | Metric contract | `contracts/*.md` |
| `KPI-PK-*` | KPI pack | `packs/*.md` |
| `KPI-AP-*` | Anti-pattern | `patterns/metric-anti-patterns.json` |
| `KPI-PAT-*` | Pattern | `patterns/metric-patterns.json` |
| `KPI-CHK-*` | Checklist | `checklists/*.md` |
| `KPI-CAND-*` | Candidate KPI | `patterns/metric-contract-candidates.json` |

## Assigned in this seed

Metric contracts (`KPI-MC-*`):

| ID | KPI |
|----|-----|
| KPI-MC-01 | Gross Sales |
| KPI-MC-02 | Net Sales |
| KPI-MC-03 | Quantity Sold |
| KPI-MC-04 | Transactions Count |
| KPI-MC-05 | Average Transaction Value |
| KPI-MC-06 | Discount Amount |
| KPI-MC-07 | Discount Rate % |
| KPI-MC-08 | Returns Rate % (Value) |
| KPI-MC-09 | Gross Margin (Value) |
| KPI-MC-10 | Gross Margin % |
| KPI-MC-11 | Net Sales Growth % |
| KPI-MC-12 | Same-Store Sales Growth % (planned) |
| KPI-MC-13 | YTD Net Sales |
| KPI-MC-14 | Discounted Transaction Rate |
| KPI-MC-15 | Average Basket Size (Units) |
| KPI-MC-16 | Inventory Turnover (planned) |
| KPI-MC-17 | GMROI (planned) |
| KPI-MC-18 | Out-of-Stock Rate (planned) |
| KPI-MC-19 | Customer Retention (planned) |
| KPI-MC-20 | Customer Lifetime Value (planned) |
| KPI-MC-21 | Net Sales vs Target (planned) |
| KPI-MC-22 | Promotion Uplift (planned) |

Packs: KPI-PK-01 … KPI-PK-07. Concepts: KPI-CN-01 … KPI-CN-08. Checklists: KPI-CHK-01 …
KPI-CHK-03. Patterns, anti-patterns, and candidates are numbered inside their JSON files.

## Rules

- IDs are permanent. Reusing an ID for a different KPI is forbidden.
- Cross-references use the ID, never the filename, so files can move.
- New contracts continue from KPI-MC-23. The registry owns lifecycle and aliases;
  this table is an ID-only consumer projection.
- Ambiguity codes (`A1`…`A11`) are local to `knowledge/kpi-ambiguities.md` and are not in
  the `KPI-*` namespace.
