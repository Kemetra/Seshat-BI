# Visual -> contract binding map -- <subject-area>

<!--
  GENERIC TEMPLATE (roadmap rule 7). Copy this blank into a per-subject-area
  working set and fill the placeholders. This is the artifact the DESIGN REVIEW
  signs off: it proves every visual binds to exactly ONE approved metric contract
  (no orphan visual) and that no approved contract is silently dropped.

  C086 IS AN EXAMPLE, NEVER INLINED HERE. Do NOT copy any C086/pharmacy specifics
  into this file. ASCII, UTF-8 no BOM. No real connection host or secret.

  The dashboard-design skill authors this; it NEVER invents a metric (binds only
  to approved F009 contracts) and NEVER self-grants dashboard_ready: pass.
-->

## Machine-readable three-way front section (spec 021, Phase B)

`seshat narrative-check --table <table> --binding-map` reads this fenced `yaml`
block. It proves the THREE-way binding (visual -> contract -> decision-question):
every visual answers >=1 brief decision-question (no orphan, FR-005), every
declared page serves >=1 decision (coverage), and every headline visual answers
an `overview` question (no bare-total headline, FR-006). Fill the placeholders;
keep it in sync with the human table below. ASCII, UTF-8 no BOM.

```yaml
schema: seshat.binding-map/v1
table: <table>                              # matches mappings/<table>/
brief: mappings/<table>/narrative-brief.md  # the brief whose Q-ids this map references
pages:
  - id: <page id>                           # a page may be a bare id or {id, regions}
    regions: [<region>, ...]
visuals:
  - visual_id: v01
    page: <page id>
    region: <region>
    visual_type: <card|bar|line|table>
    contract: <approved-contract-name>      # the F011 leg (unchanged)
    decision_questions: [<Qn>, ...]         # a LIST: >=1 brief question id (the NEW leg)
    headline: <true|false>                  # true = KPI-card class -> must answer an overview Q
```

## Subject area

- subject_area: `<schema.table or model name>`
- governed_model: `<relative path>`
- semantic_model_ready: `pass`

## Binding map (every visual -> exactly one APPROVED contract + decision-question)

| visual_id | visual_type | decision_question(s) | bound_contract (approved) | semantic_model_field(s) |
|-----------|-------------|----------------------|---------------------------|-------------------------|
| `v01` | `<card/bar/line/table>` | `<Qn[, Qm]>` | `<approved-contract-name>` | `<mapped field(s)>` |
| `v02` | `<...>` | `<Qn>` | `<approved-contract-name>` | `<...>` |

> Every row MUST cite one APPROVED contract by name, the mapped model field(s), AND
> >=1 brief decision-question id. A visual with no backing approved contract is an
> unbound ORPHAN; a visual answering no decision-question is a narrative ORPHAN
> (FR-005) -> do not emit it -> STOP.

## Dropped contracts (more approved contracts than visuals -- record each, no silent omission)

| dropped_contract | reason it is not on this page |
|------------------|-------------------------------|
| `<approved-contract-name>` | `<e.g. covered by the Stage 7 handoff pack, not the dashboard>` |

## Review sign-off (Principle V -- the reviewer's action, NOT the skill's)

- reviewer (BI report owner): `<name>`
- decision: `<pending | approved>`
- approvals entry (added by the reviewer on approval):
  `{stage: dashboard_ready, owner: <bi-report-owner>, at: <YYYY-MM-DD>}`

## Readiness

- dashboard_ready: `warning`   # the skill records at most warning; pass requires the approvals entry above
- evidence: ["<layout plan>", "<visual list>", "<this binding map>"]
- next_action: "get the design review (visual->contract binding) signed off by the BI report owner"
