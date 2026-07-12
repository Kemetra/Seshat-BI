# Visual -> contract binding map -- demo_report_area (spec 123 US2 fixture)

The artifact the design review signs off: every measure-bearing visual binds to
exactly ONE approved metric contract (no orphan visual), and each visual's
business_question traces to a question declared in the committed Report Intent
(FR-002a). ASCII, UTF-8 no BOM.

## Subject area

- subject_area: `DemoReportArea` (`gold.fct_demo`)
- governed_model: `../../../powerbi/DemoReportArea.SemanticModel`
- semantic_model_ready: `pass`

## Binding map (every visual -> exactly one APPROVED contract)

| visual_id | visual_type | business_question | bound_contract (approved) | semantic_model_field(s) |
|-----------|-------------|-------------------|---------------------------|-------------------------|
| v01 | card | q1 headline sales | DemoSales | `[DemoSales]` |
| v02 | card | q2 transaction volume | DemoCount | `[DemoCount]` |
| v03 | bar | q1 sales by category | DemoSales | `[DemoSales]` by `dim_product_demo[category]` |

> Every row cites one APPROVED contract by name + the mapped model field(s). No
> visual lacks a backing approved contract (no orphan). Each business_question
> (q1, q2) traces to a question in the committed report-intent.yaml (FR-002a).

## Contract coverage (all approved contracts appear)

| approved_contract | on which visuals |
|-------------------|------------------|
| DemoSales | v01, v03 |
| DemoCount | v02 |

## Dropped contracts (record each -- no silent omission)

None. Both approved contracts are bound to at least one visual.

## Review sign-off (Principle V -- the reviewer's action, NOT the skill's)

- reviewer (BI report owner): pending -- the coordinator STOPS at this human seam
  and never self-grants dashboard_ready: pass.
