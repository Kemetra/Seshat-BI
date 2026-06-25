# Dashboard Ready

Planning (docs/templates; no runtime code). The stage verb is BUILT: the
`dashboard-design` skill (feature F011/012) runs this gated stage, and the
`powerbi-dashboard-design` design FOUNDATION (F011A) backs it. The stage remains
gated -- it is entered only when `semantic_model_ready` is `pass`.

## Purpose

Stage 6. A report/dashboard is designed AGAINST approved metric contracts --
never before them. Every visual binds to a metric contract that already exists in
the metric-contract store; the report references the governed PBIP model with a
relative path. Maps to playbook Phase 7 (the BI half).

This stage cannot begin until `semantic_model_ready` is `pass`: no metric
contracts, no dashboard design (roadmap rule 5).

## Required artifacts

| Artifact | What it is |
|----------|------------|
| `<report>/definition/` (PBIR) | the report, referencing the model by relative path -- not an absolute/remote ref |
| approved metric contracts (F009/F010) | the metric-contract store entries every visual maps to -- already committed at `semantic_model_ready` |
| visual -> contract map | a committed note showing each visual binds to one approved metric contract (no orphan visuals) |

## Required checks

| Gate | What it confirms |
|------|------------------|
| `retail check` (R1) | the PBIR references the model with a relative path (no baked-in/remote ref) |
| design review | every visual maps to an approved metric contract; no metric invented at design time |

## Statuses

| Status | Meaning HERE |
|--------|--------------|
| `not_started` | `semantic_model_ready` is not `pass` yet, or no report exists |
| `blocked` | a required artifact/check failed -- see Blocking reasons |
| `warning` | report exists and binds to contracts, but a non-fatal design note is recorded (e.g. an accepted layout deviation); never auto-promotes to `pass` |
| `pass` | R1 passes, design review confirms every visual maps to an approved contract, and the review approval is recorded in `evidence[]` |

## Blocking reasons

- `semantic_model_ready` is not `pass` (the hard gate -- contracts must exist first).
- A visual has no backing metric contract (orphan visual).
- A metric is invented at design time instead of reusing an approved contract.
- The PBIR references the model by absolute/remote path (R1 fails).

## Required owner / approval

BI / report owner signs off the design review (visual -> contract binding).
Recorded in `approvals[]` as `{stage: dashboard_ready, owner: <bi-report-owner>, at: <date>}`.

## Next allowed action

When this stage is `pass`: assemble the BI handoff pack (Stage 7,
`publish-ready.md`).

## What the agent must NOT do

- Do NOT invent metrics at design time -- only bind to approved contracts.
- Do NOT design any visual before its metric contract exists (rule 5).
- Do NOT call the Power BI execution adapter (official Power BI MCP / connection;
  `pbi-cli` no longer the preferred path) -- that is feature 016, the last and gated,
  EXECUTION-ONLY adapter (it cannot define metrics or design); not part of this stage.

## Design foundation that backs this stage

Pointer only -- not a gate. The generic design FOUNDATION the F011/012 design
verb reasons with (no gate, status, blocking reason, required check, or
design-review responsibility is changed here): the `powerbi-dashboard-design`
skill + `docs/powerbi/` + `templates/` + `design/` + `themes/` +
`reports/blueprints/` (feature 017 = F011A).

## See also

- `readiness-model.md` -- the state model (status + evidence + blockers).
- `readiness-pipeline.md` -- the stage sequence and hard gates.
- `semantic-model-ready.md` -- the prior stage (must be `pass` first).
- `publish-ready.md` -- the next stage.
- `../../docs/medallion-playbook.md` -- Phase 7 (BI half).
- `../../docs/roadmap/roadmap.md` -- features 011/016 and hard rules 5/6.
