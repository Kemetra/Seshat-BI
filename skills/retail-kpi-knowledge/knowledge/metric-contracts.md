# Metric Contracts

A metric contract is the governed, reviewable definition of one KPI. It is the artifact
this layer produces and the input every downstream layer consumes.

## Why contracts exist

Without contracts, each report author re-derives a KPI from memory. The result is
duplicated DAX (three measures that all claim to be "net sales"), and ambiguous
dashboards (two tiles labelled the same that disagree). A contract fixes the meaning
once, names an owner, and forces ambiguities to be resolved before code is written.

A contract does three jobs:

1. **Pins meaning** — one agreed business definition and formula.
2. **Pins shape** — grain, additivity, required fields, dimensions, filters.
3. **Pins handoff** — what the DAX/semantic layer must implement and what it must not
   assume.

## Required sections

Every contract in `contracts/` uses this fixed structure:

- Business question
- Business definition
- Formula in business terms
- Required fields
- Grain
- Additivity
- Recommended dimensions
- Filters / exclusions
- Interpretation
- Common mistakes
- Validation checks
- Implementation handoff notes (SQL / DAX / Python / Big-data)
- Dashboard use
- Priority
- Owner
- Status — one of **Seeded**, **Planned**, **Needs business definition**

The canonical blank is `references/metric-contract-template.md`.

## Status meaning

- **Seeded** — contract is complete and live in this seed; safe to hand off.
- **Planned** — KPI is recognised and scheduled but not yet contracted; do not hand off.
- **Needs business definition** — a required policy (VAT, returns, cost method,
  same-store, snapshot date) is unresolved; the KPI is blocked until the owner decides.

## Handoff to implementation (SQL / DAX / Python / Big-data)

A contract does not feed only DAX. The same governed contract hands off to **all four**
implementation layers, each consuming the slice it owns. This layer provides the meaning;
it never writes the code.

| Receiving layer | Slice of the contract it consumes | What it owns (this layer never does) |
|---|---|---|
| **SQL knowledge** (`skills/bi-sql-knowledge/`) | required fields, grain, filters/exclusions, validation/reconciliation checks | the physical source binding, silver/gold transform logic, reconciliation queries |
| **DAX knowledge** (`skills/bi-dax-knowledge/`) | business-terms formula, additivity call, filter/exclusion rules, recommended dimensions | the measure, filter context, relationships, semantic-model prerequisites |
| **Python knowledge** (`skills/bi-python-knowledge/`) | required fields + their dtypes/quality assumptions, grain for any pre-aggregation | dataframe source-prep, cleaning/standardization, dtype decisions |
| **Big-data knowledge** (`skills/bi-bigdata-knowledge/`) | required fields, grain + additivity (for distributed aggregation), validation/reconciliation checks (run at scale) | engine selection, partitioning/shuffle, skew, distributed aggregation, scale reconciliation — *only when the data is too large for single-node Python* |

Every handoff carries the same core payload:

- the business-terms formula (never DAX/SQL/Python code from this layer),
- the required fields and which are confirmed / assumption / derived,
- the grain and additivity call (so each layer aggregates / models correctly),
- filter/exclusion rules,
- known ambiguities still open (so they are not silently coded around).

The implementation layers own the code; this layer owns only the contract. The SQL layer
in particular owns the **logical → physical field binding** (see `references/source-map.md`);
this layer references logical fields only. A contract that fails the
metric-contract-review-checklist is **not** ready for handoff, and no contract grants
dashboard-readiness — that is the Readiness layer's decision.
