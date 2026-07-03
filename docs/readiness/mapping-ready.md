# Mapping Ready

Planning (docs/templates; no runtime code).

Stage 2 of 7. THE source-mapping gate (constitution Principle IV). Enter only
when Stage 1 (Source Ready) is `pass`.

## Purpose

Grain, primary key, PII, and gold placement for `<schema>.<table>` are mapped
into committed, reviewed artifacts BEFORE any silver SQL exists. This is the
hard gate: no `silver.*` is written until the map is reviewed and APPROVED. The
agent profiles and proposes; a human resolves the judgment calls (Principle V).

## Required artifacts

All committed under `mappings/<table>/`:

| Artifact | Must contain |
|----------|--------------|
| `source-map.yaml` | grain statement, PK column(s), every column with `pii:` flag, gold placement (which star: fact vs dim, conformed dims) |
| `assumptions.md` | RC1-RC16 (ADR 0002) each marked adopted or deviated; every deviation cites a concrete data fact |
| `unresolved-questions.md` | `Gate status: CLEARED` and ZERO open rows |

Source for blanks: `../../templates/`. Profile input from Stage 1:
`mappings/<table>/source-profile.md`.

## Required checks

| Check | What it asserts |
|-------|-----------------|
| source-mapping gate | the three artifacts above exist, are filled, and are reviewed and APPROVED as a unit (playbook Phase-4 review gate) |

Approval is a human action recorded in the readiness status `approvals[]`. The
agent CANNOT self-grant it. There is no runtime validator for this gate; the
evidence is the committed artifacts plus the recorded approval.

## Statuses

| Status | Meaning HERE |
|--------|--------------|
| `not_started` | Source Ready not yet `pass`, or no `mappings/<table>/` artifacts begun |
| `blocked` | a required artifact is missing/incomplete, an open question remains, OR approval not recorded -- see Blocking reasons |
| `warning` | a deviation from RC1-RC16 is recorded and data-justified, but otherwise complete; never auto-promotes to `pass` |
| `pass` | three artifacts committed and filled, `Gate status: CLEARED`, zero open rows, human approval recorded in `approvals[]` |

## Blocking reasons

- `unresolved-questions.md` shows `Gate status: OPEN`.
- Any open (unresolved) row remains in `unresolved-questions.md`.
- Grain is not confirmed unique on the data (PK does not hold).
- A `pii:true` column is not dropped or otherwise handled in the map.
- A business rollup / segmentation is agent-invented rather than analyst-supplied.
- `source-map.yaml`, `assumptions.md`, or required gold placement is missing.
- Map is filled but not yet reviewed/APPROVED (no `approvals[]` entry).

## Required owner / approval

Analyst / governance approves (Principle V judgment calls: grain, PII handling,
business rollups). Recorded as an `approvals[]` entry
(`{stage: mapping_ready, owner: "<Person Name> (analyst)", at: <YYYY-MM-DD>}` -- the NAMED decider + authority class; RS1 rejects a role-only owner). Not mechanical --
human sign-off is mandatory.

## Next allowed action

When `pass`: begin Silver Ready (Stage 3) -- write
`warehouse/migrations/NNNN_create_silver_<table>.sql` driven strictly by the
approved `source-map.yaml`.

## What the agent must NOT do

- Write ANY `silver.*` SQL or migration before this stage is `pass`.
- Self-grant or fabricate the gate approval / `Gate status: CLEARED`.
- Invent grain, PK, PII classification, or business rollup decisions -- propose
  and STOP at the human seam.
- Resolve an open question on the analyst's behalf to clear the gate.
- Emit a confidence number in place of an explicit status.

## See also

- The state model: `readiness-model.md`.
- The stage sequence + hard gate: `readiness-pipeline.md`.
- Mapping artifacts + layout: `../../mappings/README.md`.
- Mapping decision: `../../docs/decisions/0003-mapping-artifact-location.md`.
- RC1-RC16 assumptions (ADR 0002): `../../docs/decisions/0002-retail-cleaning-defaults.md`.
- Filled instance: a worked example under `../../docs/worked-examples/`.
