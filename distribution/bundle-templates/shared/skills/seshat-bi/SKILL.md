---
name: seshat-bi
description: >-
  Route a BI project through Seshat BI's governed seven-stage readiness flow.
  Use when a user asks to inspect a retail source, initialize a Seshat project,
  find the truthful next action, validate readiness evidence, or stop at the
  correct human approval gate.
---

# Seshat BI

Read `../../portable-operating-contract.md` before acting. Inspect the current
workspace and use installed `seshat` commands when available. If the workspace
has no `AGENTS.md`, this skill's portable operating contract still applies.

For subject reasoning, load only the relevant bundled skill:

- SQL and source grain: `bi-sql-knowledge`
- DAX and semantic measures: `bi-dax-knowledge`
- Python/dataframe preparation: `bi-python-knowledge`
- distributed data: `bi-bigdata-knowledge`
- retail KPI meaning and contracts: `retail-kpi-knowledge`

End with one next action or one blocked stop. Cite evidence and named blockers;
never invent a pass or score.

## Existing PBIP projects

For an existing Power BI Project, first use the installed read-only entry path:

```powershell
seshat adopt-pbip assess --project <PBIP-project-directory> --format text
```

Treat PBIP structure as candidate evidence only. The assessment must not create
or approve mappings, metrics, business meaning, or readiness passes. It returns
one governed next action and an assessment digest. A `.pbix` is a conversion
boundary: save it as PBIP in Power BI Desktop before continuing.

Only after a human reviews the exact digest, and only in a clean existing Git
worktree, may the agent run:

```powershell
seshat adopt-pbip scaffold --project <PBIP-project-directory> --accept-assessment <assessment-digest>
```

This writes at most `.seshat/adoption/pbip-adoption.yaml`; it never initializes
Git, overwrites existing files, grants approval, or advances readiness.
