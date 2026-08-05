# Fabric, Power BI, dbt, and Dagster integrations

Seshat does not run network installers as a side effect of `pipx install`,
`pip install`, or any other command. These integrations are opt-in and reached
through one verb:

```powershell
seshat integrations setup            # plan only -- writes nothing
seshat integrations setup --apply    # install, after you have decided
```

A run with approval clones the Microsoft Fabric and dbt Labs agent skill bundles
and registers the read-only Power BI modeling and dbt MCP servers. Dagster
workflow skills ship with Seshat and are validated, not downloaded.

The setup validates required skills and runtime prerequisites and returns
categorical `planned`, `present`, `installed`, `unavailable`, or `failed`
results. Use `--yes` only when an operator has already approved the install.
Non-interactive runs without `--apply` or `--yes` remain a dry run. It never
stores credentials, changes readiness, or grants approval.

## What it will not do

- **It never runs unprompted.** No other command reaches this installer: `seshat
  check` is a read-only governance verb and stays one. The CLI entry point does
  not import the installer at all, which is asserted by a test — a guard inside
  the installer would leave the call site in place for a later edit to widen. If
  a first-arrival offer is wanted, `first-hour-compass` is the verb whose
  contract covers first arrival.
- **It never writes outside a Seshat workspace.** `--repo` is validated the way
  `seshat mcp` validates it: a directory that is not a workspace is refused by
  name (exit 2) rather than seeded with a `.seshat/` tree.
- **It never modifies the active Python interpreter.** A missing `dbt` is
  reported as `unavailable` with the versions to install (`dbt-core==1.12.0`,
  `dbt-postgres==1.10.2`) rather than `pip install`-ed into whatever environment
  happens to be activated — that would silently reshape the operator's
  environment and hard-fails outright on a PEP 668 managed interpreter. The dbt
  MCP server reaches dbt through `uvx`, so no ambient `dbt` is required. The
  Dagster runtime is provisioned into `orchestration/dagster/.venv`, never into
  the ambient environment, and only with `uv` present.
- **It never overwrites an unparseable MCP config.** A config it cannot read is
  reported as `failed` and left exactly as the operator left it. A readable one
  is merged: unrelated server registrations survive.
- **It never clones over an existing directory.** A partially-populated bundle
  directory is reported as `failed` for a human to look at.

## Where the output lives

Everything the installer writes goes under `.seshat/integrations/` in the
resolved workspace — the two shallow clones and the generated `mcp.json`. That
directory is git-ignored: it is machine-local installer output, not a committed
artifact.

Non-interactive clients (CI, piped output, agent harnesses) have no prompt to
answer, so they report the plan and change nothing unless `--apply` or `--yes`
is passed explicitly.

After a semantic-model readiness pass, run the existing read-only gate:

```powershell
seshat pbi-mcp preflight --repo .
```
