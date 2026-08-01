---
name: pbip-xray
description: >-
  Audit a committed PBIP semantic model as text (unused fields, relationship
  risks, measure-graph findings) and explain a TMDL change in business terms
  for PR review. Read-only: it parses committed TMDL/PBIR and git history,
  opens no database, never launches Power BI, and edits nothing.
---

# pbip-xray

- **Capability id:** `pbip-xray` (`docs/capabilities/capabilities.yaml`).
- **Authority:** advisory. Findings NEVER block, never move a readiness
  stage, and never carry a numeric health/quality score (hard principle:
  never fabricate a confidence score). Counts and findings only.
- **Design spec:** `docs/superpowers/specs/2026-08-01-pbip-xray-design.md`.

## When to invoke

- "Audit the Power BI model" / "what is dead weight in this model?"
- "What changed in the semantic model in this PR, in business terms?"
- "Is this column used anywhere?" / "why does this measure exist?" (pair
  with `cross-table-lineage` for the cross-artifact chain).
- Reviewing any PR that touches `*.SemanticModel/definition/**.tmdl`.

## The two verbs

```bash
seshat xray --format json                 # full-model audit
seshat model-diff --base origin/main --format json   # PR-scoped semantic diff
```

Exit 0 = ran to completion (however many findings). Exit 3 = could not run;
the payload carries `{code, message, recovery}` blockers (XR001 no committed
model; XR002 unresolvable base ref).

## Finding families (audit)

| id | meaning |
|----|---------|
| X0 | a table file the parser could not read (excluded, never guessed) |
| X1 | column/measure unreferenced in scanned surfaces |
| X2 | relationship risks: many-to-many, dead inactive, string keys, snowflake chains |
| X3 | measure-graph: circular references, depth >= 5, cross-table duplicate logic |
| X4 | hygiene: unmarked date table, default summarizeBy feeding nothing |

## Diff buckets (model-diff)

`semantic` (measure logic, column type, relationship behavior),
`cosmetic` (format/description/folder/sort), `additive`, `removed`.
Relationships match by ENDPOINTS, so TMDL GUID-name churn never reports.
Formatting-only DAX churn classifies cosmetic (normalized-body comparison).

## The conservative core (read before trusting a finding)

- **Absence of evidence never becomes a finding.** No parseable report JSON
  -> X1 wording downgrades to `(no report scanned -- visual usage unknown)`
  and severity drops to info.
- Unresolved DAX tokens EXCLUDE a column from every "unused" determination.
- Enforcement stays with `seshat check`: D6 owns bi-directional
  relationships (X-Ray skips them entirely), D3 owns duplicate bodies,
  D7 owns the date-table marker -- X-Ray findings cite them.

## What this skill never does

- Never edits TMDL/PBIR, never auto-fixes (findings carry fix hints only).
- Never opens a DB connection or the Power BI execution adapter (F016).
- Never grants an approval or moves a readiness stage.
