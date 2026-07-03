<!--
=============================================================================
 dbt-model-contract.md  --  the copy-me declaration EACH dbt model fills
=============================================================================
 Seshat BI  -  feature F029 (on-disk spec 023-dbt-transformation-adapter).
 Authority category (F024): Execution Adapter / DB-connected -- this is the
 per-MODEL companion to templates/dbt-adapter-contract.md (the feature-level one).
 See: docs/decisions/0009-dbt-is-transformation-adapter.md (the decision record),
      docs/architecture/product-modules.md (the category contract),
      templates/source-map.yaml (the map a model CITES -- it never authors it).

 WHAT THIS IS
   A GENERIC, copy-me declaration for a SINGLE dbt model (staging / intermediate /
   mart). It binds the model to the EXACT approved source-map rows that justify its
   columns, grain, and placement, names the grain it builds, and lists the tests it
   carries. The citation is the PROOF that dbt read truth and did not author it: a
   reviewer can follow each reference to a real, approved map entry.

 THE BOUNDARY  (verbatim from product-modules.md -- do not drift)
   An Execution Adapter is EXECUTION-ONLY. It MUST NOT define metrics, mappings,
   semantic logic, or dashboard design; the definition it executes MUST already exist
   in Core Authority. A dbt model CITES the approved map; it never authors a column
   meaning, a grain, a PK, a PII decision, or a placement the map does not already
   state. A model column with no approved map citation is a DEFECT.

 HOW TO USE
   Copy this file once per model, alongside the model .sql (or under the model's dir),
   fill every <ANGLE-BRACKET> field, delete this comment banner, and keep it committed
   with the model. GENERIC -- no retail_store_sales / C086 column or table names; the
   filled first-MVP instance is CITED in a filled worked example under
   docs/worked-examples/, never inlined here (Principle VII).
=============================================================================
-->

# dbt Model Contract -- <model_name>

- **Model:** `<model_name>`  *(the dbt model file, e.g. `stg_<table>` / `<table>_mart`)*
- **Layer:** `<staging | intermediate | mart>`
- **Materializes:** `<the table this model builds, e.g. silver.<table> or gold.<fact_or_dim>>`
- **Roadmap feature:** F029  **On-disk spec:** `specs/023-dbt-transformation-adapter`
- **Owner:** `<named human or role>`
- **Status:** `<Planned | Authored | Shipped>`

## What it does (one line)

> `<one sentence: which silver/gold object this model materializes, at what grain, from
> which upstream source -- all per the approved map>`

## Source-map citation (the proof -- REQUIRED for every model)

The model MUST cite the approved map. A reviewer follows each reference to a real,
approved map entry. A stale citation (after the map is re-approved at a new version) is a
defect (reconciles with the F008 mapping-diff review).

- **Approved map:** `<path to source-map.yaml>` @ `<git ref / commit of the approved version>`
- **Mapping Ready:** `pass` recorded in `mappings/<table>/readiness-status.yaml` (the entry gate).
- **Grain cited from the map:** `<the declared grain + the map row(s) that state it>`
- **PK cited from the map:** `<the declared PK + the map row(s) that state it>`

## Column citations (one row per column the model builds)

Every column the model builds MUST trace to an approved map row. A column with no
corresponding approved map row is a DEFECT that blocks the model.

| Model column | Approved map row (path:key) | Meaning (per the map -- NOT authored here) |
|--------------|-----------------------------|--------------------------------------------|
| `<column_a>` | `<source-map.yaml: columns[...].name>` | `<the map's stated meaning -- cited, not invented>` |
| `<column_b>` | `<...>` | `<...>` |

## Grain it builds

- **Grain:** `<one row = one ...>`  *(MUST equal the cited map grain; a model may NEVER
  change the declared grain without a re-approved map -- Principle V)*

## Tests it carries

dbt tests produce EVIDENCE; a green test never moves a stage to `pass` (Tower readiness +
a named human do). List the schema + data tests on this model.

- `<e.g. unique(<business_key>)>`
- `<e.g. not_null(<business_key>)>`
- `<e.g. relationships from each fact FK to its dimension>`  *(mart models)*
- `<e.g. the reconciliation parity test vs the migration-built gold fact>`  *(mart of a migration-built table)*

## Forbidden operations (the matrix says NO)

- MUST NOT introduce a column meaning, grain, PK, PII flag, or placement the approved map
  does not state (cite the map; the map is re-approved first if a meaning must change).
- MUST NOT define a metric formula, a business rollup, or a segment mapping (those are
  F009 metric contracts decided by the metric owner; dbt produces columns, F009 defines
  meaning over them).
- MUST NOT change the declared grain (e.g. collapse line items) without a re-approved map.
- MUST NOT resolve a Principle V judgment call (grain ambiguity, sentinel-vs-null, PII
  publish-safety, business rollup) -- stop-and-ask for a named human.
- MUST NOT emit a numeric / maturity / confidence score (hard rule #9).

## How it handles a missing citation

When a column has no approved map row, or the map was re-approved at a new version and a
citation is stale, the model SURFACES the gap as a defect / `blocking_reason` and is
blocked -- it never invents the missing meaning or proceeds past the missing citation
(Principle V; stop-and-ask).

## See also

- The feature-level contract: `templates/dbt-adapter-contract.md`.
- The map it cites: `templates/source-map.yaml` (filled per table under `mappings/<table>/`).
- The decision record: `docs/decisions/0009-dbt-is-transformation-adapter.md`.
- The category contract: `docs/architecture/product-modules.md`.
- The filled first-MVP instance is CITED, never inlined: a filled worked example under `docs/worked-examples/`.
