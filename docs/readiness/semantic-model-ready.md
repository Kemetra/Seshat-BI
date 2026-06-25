# Semantic Model Ready

Status note: Planning (docs/templates; no runtime code).

## Purpose

Stage 5. A governed Power BI semantic model whose measures each bind to an
APPROVED metric contract. "Ready" means: the PBIP model is committed and clean
(relationships set, date table marked, PascalCase measures in display folders,
parameterized connection with NO real host), `retail check` passes the DAX/TMDL
+ connection rules, and every measure traces to a metric contract owned by the
metric owner. Maps to playbook Phase 7 (the model half, before any dashboard).

## Required artifacts

| Artifact | Where | Must show |
|----------|-------|-----------|
| PBIP model | `powerbi/<Model>.SemanticModel/definition/` | relationships, date table marked, PascalCase measures in display folders |
| Connection params | model expressions/parameters | parameterized host -- NO real host string (G6) |
| Metric contracts | `templates/metric-contract.yaml` (filled per table under `mappings/<table>/metrics/`) | per measure: name, grain, formula intent, owner |

Note: the metric-contract TEMPLATE now exists (F009 -- `templates/metric-contract.yaml`,
grouped into reusable packs via `templates/kpi-pack.yaml`; authoring guide
`docs/metrics/metric-contract-store.md`). F009 DEFINES contracts; CHECKING a PBIP
model against them stays F010 (on-disk feature 011). A measure can now trace to a
filled contract; a new table is still `not_started` here until contracts are filled
and owner-approved (`pass` needs owner + date), and Gold Ready is `pass`. (C086 is
the first worked example / a filled instance, not the schema.)

## Required checks

| Gate | Scope | Pass condition |
|------|-------|----------------|
| `retail check` | D1-D8 (DAX/TMDL), C1 (connection params), R1 (relative ref), G6 (no real host) | exit 0 |
| Metric-contract review | every measure | each measure traces to an approved contract |

## Statuses

| Status | Meaning HERE |
|--------|--------------|
| `not_started` | Gold not `pass`, OR no FILLED, owner-approved metric contracts exist for this table yet (the F009 template + F010 checker are shipped; the per-table contracts under `mappings/<table>/metrics/` are not authored) -- default for new tables |
| `blocked` | a D/C/R/G6 finding, a measure with no contract, or a real host in PBIP params (G6) -- see Blocking reasons |
| `warning` | `retail check` clean but a non-fatal item recorded (e.g. an accepted display-folder deviation); never auto-promotes |
| `pass` | model committed + clean, `retail check` exit 0, every measure traces to an approved contract, owner signed off |

## Blocking reasons

- Prior stage `gold_ready` is not `pass` (gold star / live validation incomplete).
- A `retail check` D1-D8 DAX/TMDL finding.
- A C1 connection-parameter finding or R1 relative-reference finding.
- G6: a real connection host baked into PBIP params (must be parameterized).
- A measure with no corresponding metric contract.
- No FILLED, owner-approved metric contracts exist for this table's measures yet
  (the F009 template + F010 checker are shipped; per-table contracts under
  `mappings/<table>/metrics/` are unauthored) -> stays `not_started`/`blocked`.

## Required owner / approval

Metric owner approves the metric contracts. A `pass` records that approval as
evidence (contract name + owner + date). Mechanical checks (`retail check`) need
no human; the contract binding does.

## Next allowed action

When this stage is `pass`: proceed to Stage 6 -- design the dashboard against the
approved contracts (`dashboard-ready.md`).

## What the agent must NOT do

- Do NOT design dashboards or visuals yet (that is Stage 6).
- Do NOT author a measure that has no metric contract.
- Do NOT commit a real connection host -- keep PBIP params parameterized (G6).
- Do NOT write a `pass` without owner-approved contracts as evidence.
- Do NOT EXECUTE the model -- no live connection, refresh, publish, or deployment
  against the gold DB. That is the execution-only F016 adapter (official Power BI
  connection / MCP), gated on this stage being `pass`. NOTE (clarified 2026-06-25):
  AUTHORING the governed model as committed TMDL -- relationships, the marked date
  table, PascalCase measures binding to approved contracts -- IS this stage's work
  (Phase 7, model-as-code / `pbip-workflow` + `powerbi-analyst`); it is NOT F016.
  F016 owns only the LIVE connection/refresh/publish, never the semantic definition.

## See also

- The state model: `readiness-model.md`
- The stage sequence + hard gates: `readiness-pipeline.md`
- The committed model: `../../powerbi/Retailgold.SemanticModel/definition/model.tmdl`
- Playbook Phase 7 + conventions: `../conventions.md`
