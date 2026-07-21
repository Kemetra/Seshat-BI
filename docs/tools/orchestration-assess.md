# Orchestration Assess -- usage and boundary

- **Status:** Runtime slice shipped: `seshat orchestration-assess`.
- **Authority category:** Product Module / `read-only`.
- **Issue:** #401.

## What it does

`seshat orchestration-assess` answers the prior question the two orchestration
adapters (`seshat dbt`, `seshat dagster`) never surfaced on their own: **does
this project actually need dbt and/or dagster, or is the direct medallion path
enough?** It mirrors the readiness spine's own gate pattern -- surface a
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
  (`orchestration/dagster/pyproject.toml`) is already present.

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

The command prints these as guidance. It never runs them.
