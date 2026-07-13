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
