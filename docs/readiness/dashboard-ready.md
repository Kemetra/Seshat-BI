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
| `seshat check` (R1) | the PBIR references the model with a relative path (no baked-in/remote ref) |
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

## Evidence item: "design approved" vs "page implemented"

> Added by feature F034 (on-disk spec `specs/039-visual-implementation-mvp`; roadmap
> F-number wins). This is an EVIDENCE ITEM only -- it adds NO new status, NO new gate, NO
> new `seshat check` rule, and does NOT change the gate, statuses, blocking reasons, owner,
> required checks, or the design-review responsibility above.

A `pass` here is granted on the DESIGN (the approved visual -> contract binding map plus the
recorded design-review sign-off) -- it can be `pass` while no report page has yet been built.
A separate evidence item records that the approved design was REALIZED as visuals on a real
PBIR page, built by a human in Power BI Desktop and reviewed in git like code:

- A `pass` MAY record `evidence: built-page traces to the approved binding map; R1 passes`
  once a human-built PBIR page is committed and verified 1:1 against the approved binding map
  (every measure-bearing visual -> exactly one approved contract + a mapped model field; no
  orphan visual; no unmapped field).
- This evidence is recorded under the EXISTING owner; it never self-grants `dashboard_ready:
  pass` and never DOWNGRADES a legitimately approved design. A build-time divergence is a new
  `warning` / `blocked` finding on the page, not a retraction of the design approval.
- The build is a HUMAN Desktop save committed as plain text -- NOT automation. Any generation
  / publish step is the deferred, gated F016 adapter (rule 6); F034 is independent of it.

The reviewable evidence artifact is the implementation trace
(`templates/visual-implementation-trace.md`, filled per subject area under
`mappings/<subject>/design/`). The procedure that fills it ships alongside `powerbi-handoff.md`
(`.claude/skills/powerbi-dashboard-design/workflows/visual-implementation-review.md`).

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
