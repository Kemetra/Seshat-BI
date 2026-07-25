# KPI Implementation Handoff Template

Use only after sufficiency is `answerable`. Populate the shared
`../../../contracts/knowledge/knowledge-layer-handoff.yaml` contract and attach these KPI-specific
fields. This template contains business semantics, never SQL, DAX, Python, or job code.

```yaml
kpi:
  contract_id: ""
  contract_revision: ""
  canonical_name: ""
  formula_business_terms: ""
  input_grain: ""
  output_grain: ""
  additivity:
    classification: ""
    dimensions: []
  time_behavior:
    date_role: ""
    period_policy: ""
    snapshot_policy: ""
  filters: []
  exclusions: []
  required_source_fields: []
  null_and_sentinel_policy: []
  validation_and_reconciliation: []
  unresolved_policy: []
  approval_receipts: []
```

## Rules

- `unresolved_policy` must be empty for an `answerable` implementation handoff.
- Cite approval receipts; never manufacture or infer them.
- Use logical source roles/fields here. Physical bindings belong in the SQL/Python/BigData
  destination evidence.
- State additivity per relevant dimension and preserve non-additive/semi-additive behavior.
- The shared handoff's `authority` remains all false.
- If any required field lacks evidence, return `blocked_by_source`.
- If any number-moving policy lacks an eligible human receipt, return `blocked_by_policy` and use
  the policy-decision checklist instead.
