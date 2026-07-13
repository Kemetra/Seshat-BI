# Research Notes

This layer was seeded from an internal retail KPI catalog (raw source material). The
catalog was rewritten into original, repo-native contracts and knowledge; no raw catalog
text or external article wording is reproduced here.

## Provenance

The seed's KPI selection, additivity calls, grain definitions, and ambiguity list derive
from a consolidated retail KPI catalog supplied as project input. That catalog in turn
cited general retail-analytics references (industry KPI guides and Power BI modelling
best-practice articles). Those citations were used only to inform structure and are **not**
quoted.

## What was deliberately not carried over

- Power BI / DAX implementation snippets from the catalog — out of scope; this layer hands
  off to the DAX layer with business-terms formulas only.
- Any source-specific schema names — kept logical (see `source-map.md`).
- Shallow or generic phrasing — rewritten into concise contract language.
- Raw web excerpts — excluded.

## Open questions inherited from the catalog (for business owners)

- VAT: pre- or post-tax storage of sales amounts (A1).
- Returns modelling and sign convention; sale vs return date axis (A2, A3).
- Cancelled/void/test transaction definitions (A7).
- Cost-of-goods method and alignment with finance (A6).
- Promotion identifiers and supplier-funded discount availability.
- Inventory snapshot frequency and meaning (A10).
- Store master data (floor area, format, opening/closing dates).
- Same-store definition (A11).
- Customer identification reliability.

## Maintenance

When the catalog is expanded or owners resolve an open question, update the affected
contracts and the ambiguity checklist, and move candidate KPIs from
`patterns/metric-contract-candidates.json` into `contracts/` as they are contracted.
