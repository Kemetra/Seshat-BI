# Publish Ready

Status: Planning (docs/templates; no runtime code).

Stage 7 of 7. The BI handoff pack is complete, reviewed, and approved to publish.
Maps to post-Phase-7. Power BI EXECUTION (publishing via the official Power BI MCP /
connection adapter; `pbi-cli` no longer the preferred path) and Fabric deployment are a
SEPARATE, LAST step (feature 016) gated on every prior stage -- it is NOT this stage.
The execution adapter is execution-only; it cannot define metrics, mappings, semantic
logic, or dashboard design.

## Purpose

Confirm the handoff pack (feature 013, PLANNED) is complete and approved so the
table/report can be released to consumers. "Ready" here means: every prior stage
is `pass`, the pack documents the deployed schema honestly (caveats included),
reconciliation evidence is attached, and the data-owner/governance has signed off
to publish. This stage authorizes a release; it does not perform it.

## Required artifacts

The BI handoff pack (feature 013) -- a committed set, not runtime code. The generic
templates now exist: `templates/handoff/bi-handoff-pack.md` (the bundle index, copied
per table to `mappings/<table>/handoff/`) and `templates/handoff/handoff-review-checklist.md`
(the completeness gate a human walks before publish):

| Artifact | What it carries |
|----------|-----------------|
| Data dictionary | column-by-column doc against the DEPLOYED `<schema>.<table>` (gold star + model) |
| Caveats note | PII excluded, returns/refunds handling, out-of-scope items, known gaps |
| Metric contracts | the approved measure definitions carried from stage 5 (F009/F010) |
| Reconciliation evidence | the filled `reconciliation-report.md` (totals tie to source) |
| Publish approval | recorded data-owner/governance sign-off (see Required owner) |

## Required checks

| Gate | Requirement |
|------|-------------|
| All prior stages | stages 1-6 each `pass` in the readiness status file |
| Handoff review | a human review of the pack (completeness + caveats + reconciliation) |

No new validator is introduced here. `retail check` / `retail validate` evidence
is inherited from stages 3-5; this stage adds the handoff review on top.

## Statuses

| Status | Meaning HERE |
|--------|--------------|
| `not_started` | stage 6 (Dashboard Ready) is not yet `pass`; pack not begun |
| `blocked` | a required pack artifact, reconciliation evidence, or publish approval is missing -- see Blocking reasons |
| `warning` | pack assembled but a non-fatal gap is recorded (e.g. a caveat noted as TBD); does NOT auto-promote to `pass` |
| `pass` | full pack committed, handoff review done, publish approval recorded; evidence[] cites the pack files + approval |

## Blocking reasons

- Any prior stage (1-6) is not `pass`.
- Missing caveats note, or caveats do not state PII exclusion / returns handling / out-of-scope.
- Missing or unfilled reconciliation evidence (totals do not tie to source).
- Data dictionary does not match the deployed schema.
- No recorded publish approval from the data-owner/governance.

## Required owner / approval

Data-owner / governance approves publish. The sign-off is recorded in the
readiness status `approvals[]` (stage `publish_ready`, owner, date). Not
mechanical -- a human authorizes release.

## Next allowed action

When `pass`: publish via the approved path -- the Power BI execution adapter
(feature 016; official Power BI MCP / connection preferred, `pbi-cli` no longer
preferred), and ONLY once that adapter exists and is itself gated on every prior
stage. Until feature 016 is built, the next action is to record the approved pack
and STOP; there is no automated publish today.

## What the agent must NOT do

- Publish, or trigger any deployment, without the recorded publish approval.
- Run the Power BI execution adapter (official Power BI MCP / connection; `pbi-cli`
  no longer preferred) before feature 016 is built and gated.
- Deploy to Microsoft Fabric (out of scope for this kit).
- Mark `pass` while any prior stage is not `pass`, or with caveats/reconciliation missing.
- Edit the deployed schema or metric contracts to make the pack "tie" -- escalate instead.

## See also

- The state model: `readiness-model.md`
- The stage sequence + hard gates: `readiness-pipeline.md`
- Prior stage: `dashboard-ready.md`
- The handoff pack + review checklist: `../../templates/handoff/bi-handoff-pack.md`, `../../templates/handoff/handoff-review-checklist.md`
- Optional executive/sponsor companion to the handoff pack (NOT a required Stage 7 artifact, not a gate): `../../templates/handoff/answerability-summary.md`
- The concrete record-and-STOP record of this stage's action (non-gating evidence): the "Publish approval" section of `../../templates/handoff/bi-handoff-pack.md`
- Status + approvals template: `../../templates/readiness-status.yaml`
- A filled instance (first worked example): `../worked-examples/c086-pharmacy.md`
