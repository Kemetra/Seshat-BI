# Orchestration Assess -- usage and boundary

- **Status:** Runtime slice shipped: `seshat orchestration-assess`.
- **Authority category:** Product Module / `read-only`.
- **Issue:** #401.

## What it does

`seshat orchestration-assess` answers the prior question the adapters
(`seshat dbt`, `seshat dagster`, `seshat pbi-mcp`) never surfaced on their own:
**does this project actually need dbt, dagster, and/or the Power BI MCP read-only
diagnostics family -- or is core-only (the direct medallion path) enough?** It mirrors the readiness spine's own gate pattern -- surface a
recommendation plus the evidence, then let the human decide -- so a customer with
one direct-built table isn't pushed into ceremony they don't need, and a customer
who would benefit gets a signal.

```bash
seshat orchestration-assess
seshat orchestration-assess --format json
```

The command is read-only. It does not install a package, run an adapter, run
`seshat dbt` / `seshat dagster`, edit any committed file, or record an adoption
decision. It **recommends; the human decides** (`decision_owner: human`).

## What it reads (and what it deliberately cannot)

Derivable offline, from committed state only:

- how many tables are onboarded (`mappings/*/readiness-status.yaml`);
- whether every onboarded table has already reached `gold_ready`;
- whether a dbt project (`dbt/dbt_project.yml`) or a dagster project
  (`orchestration/dagster/pyproject.toml`) is already present;
- whether a PBIP semantic model (`*.SemanticModel/`) is committed -- i.e. whether
  the Power BI MCP read-only diagnostics would have anything to inspect;
- whether a machine-local `.mcp.json` already exists (the offline
  already-adopted signal; its deeper classification belongs to
  `seshat pbi-mcp doctor`, which is the authority).

`core_only_sufficient` is DERIVED from the three per-adapter blocks -- true when
none of them is worth weighing -- so it can never disagree with them.

NOT derivable -- these are intentions, surfaced as `open_questions` for the
human, never as a fabricated verdict:

- whether scheduled / unattended runs are needed;
- whether there are cross-table run dependencies;
- whether the team already speaks dbt.

## Recommendation vocabulary

Per adapter, one categorical verdict (no numeric score, Principle V):

- `consider` -- a signal to weigh, not an approval; the highest tier a
  state-derived signal ever reaches;
- `not_recommended` -- e.g. a single governed table, direct build already
  Gold-validated (the C086 case): orchestration NOT required; revisit when a 2nd
  table is added or scheduled runs are needed;
- `already_adopted` -- the adapter's project is already present in the workspace.

There is deliberately no `recommended` tier. An adapter's value driver (dbt's
multi-model lineage, dagster's scheduled / unattended runs) always turns on an
intention the tool cannot read from committed state, so a state-derived signal is
capped at `consider` with the deciding question left open in `open_questions` --
it never asserts that the customer must adopt.

## Opt-in commands (only if you decide)

- dbt: `pip install 'seshat-bi[dbt]'`, then `seshat dbt init` (materialize the
  governed project), then `seshat dbt doctor`. Running `doctor` before `init`
  reports missing `dbt_project.yml` / `selectors.yml`.
- dagster: `seshat dagster init` then `seshat dagster doctor`.
- Power BI MCP: `seshat pbi-mcp doctor`, then `pbi-mcp generate-config` and
  `pbi-mcp preflight`. **This command advertises the read-only family only.**
  ADR 0018 is RATIFIED (2026-08-18) and slice 5 IS now built (spec 149, PR #659):
  `seshat pbi-mcp plan-write` and `seshat pbi-mcp apply` exist. They are deliberately
  NOT advertised here, because they are approval-gated -- a write requires committed
  passing readiness, a shape-valid named-human `publish_ready` approval naming the
  target, an allowlisted target, a resolved operation and a clean-or-backed-up tree.
  Advertising them as guidance would invite an unapproved attempt, and a successful
  write advances no readiness stage. (Updated 2026-08-21; the earlier text said no
  write path existed, which was true only before PR #659.)

The command prints these as guidance. It never runs them.
