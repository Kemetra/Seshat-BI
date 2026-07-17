---
description: Show the installed Seshat BI command map and how each surface is used
---

Report the installed Seshat BI surface truthfully; never advertise anything
absent from this list.

Slash commands (Claude Code namespaces them by plugin, so invoke as
`/seshat-bi:<name>`, e.g. `/seshat-bi:next`):

- `help` -- this command map.
- `init` -- initialize or inspect a fresh project safely.
- `check` -- run and interpret the static governance check.
- `status` -- report the truthful per-table readiness status.
- `next` -- return the one truthful next readiness action.
- `doctor` -- run and interpret the workspace health check.
- `review` -- review readiness evidence and stop at the human gate.
- `auto` -- run the governed autonomous loop until the next human gate.
- `dbt-doctor` -- check governed dbt prerequisites without a database query.
- `dbt-plan` -- validate Mapping Ready and prepare an immutable execution plan.
- `dbt-build` -- execute the fixed shadow graph under an accepted plan digest.
- `dbt-review` -- review normalized dbt evidence and stop at the human gate.
- `powerbi-design` -- guarded dashboard/page design from approved metric contracts.
- `powerbi-review` -- screenshot review, dashboard QA, blueprint validation, PBIR review.
- `powerbi-theme` -- theme JSON, palette, typography, filter-pane defaults, backgrounds, canvas.
- `powerbi-format` -- formatting plans and governed PBIR formatting/geometry.
- `powerbi-adopt` -- adopt an existing PBIP project through assess/scaffold.
- `dagster-doctor` -- read-only orchestration preflight (environment, pinned dagster, gates).
- `dagster-run` -- execute one governed orchestration job, fail-closed behind every gate.
- `dagster-evidence` -- list runs or render a run's committed derived evidence.

The former names `seshat-init`, `seshat-check`, `seshat-next`, and
`seshat-review` remain as deprecated aliases for one release cycle and behave
identically to their bare forms.

Bundled skills: `seshat-bi` (readiness router), `dbt-workflows` (governed dbt
routing), `powerbi-workflows` (guarded Power BI routing), and the knowledge
skills `bi-sql-knowledge`,
`bi-dax-knowledge`, `bi-python-knowledge`, `bi-bigdata-knowledge`, and
`retail-kpi-knowledge`.

Slash commands and terminal CLI verbs are different surfaces: a slash command
is a reviewed prompt inside this agent session, while `seshat` is a separately
installed Python package (`pipx install seshat-bi`). If `seshat` is not
installed, say so instead of simulating its output. Useful CLI-only verbs with
no slash wrapper include `validate`, `drift`, `semantic-check`, `generate`,
`value-check`, `evidence-pack`, `approvals`, `pack`, and `watch`; list
everything with `seshat --help`.
