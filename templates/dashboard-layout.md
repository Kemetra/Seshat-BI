# Dashboard layout plan -- <subject-area>

<!--
  GENERIC TEMPLATE (roadmap rule 7). Copy this blank into a per-subject-area
  working set and fill the placeholders. The dashboard-design skill authors it
  from APPROVED metric contracts (F009) once semantic_model_ready is `pass`.

  C086 IS AN EXAMPLE, NEVER INLINED HERE. Do NOT copy any C086/pharmacy specifics
  (billing codes, segment rollups, insurance/PII columns, pharmacy grain keys,
  real metric names) into this file. Worked values live only in the filled
  instance. ASCII, UTF-8 no BOM. No real connection host or secret.

  This is DESIGN AUTHORING ONLY -- it never edits PBIR, publishes, opens Power BI
  Desktop, or connects to a DB. Native report implementation routes to Microsoft's
  official report-authoring skill after the gate; F016 owns only parked live
  semantic-model connection/refresh/query/publish execution.
-->

## Subject area

- subject_area: `<schema.table or model name>`
- governed_model: `<powerbi/<Model>.SemanticModel/ relative path>`
- semantic_model_ready: `pass`   # gate -- design only when this is pass

## Business questions (analyst-supplied -- Principle V input)

1. `<the question this page answers, in plain language>`
2. `<...>`

## Page / section structure (one question per region, in reading order)

| Region | Purpose | Business question it serves |
|--------|---------|-----------------------------|
| header | title + period + filter context | `<...>` |
| kpi_strip | the headline measures at a glance | `<...>` |
| main_insight | the primary chart answering the lead question | `<...>` |
| diagnostic | the "why" breakdown behind the headline | `<...>` |
| exception_detail | rows/items needing attention (detail, not insight) | `<...>` |
| filter_rail | slicers (kept compact -- must not dominate) | `<...>` |
| footer_status | data-as-of / source / readiness note | `<...>` |

## Design notes

- `<accessibility / contrast, consistent category colors, number-format notes -- see docs/powerbi/visual-design-system.md>`
- `<any grain-mismatch or readability deviation recorded as a warning-class note>`

## Readiness

- dashboard_ready: `warning`   # highest this design records; pass needs the review sign-off
- evidence: ["<this layout plan>", "<the visual list>", "<the binding map>"]
- blocking_reasons: []
- next_action: "get the design review (visual->contract binding) signed off by the BI report owner"
