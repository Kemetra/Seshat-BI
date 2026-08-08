# Fabric, Power BI, dbt, and Dagster integrations

Seshat does not run network installers as a side effect of `pipx install`,
`pip install`, or any other command. These integrations are opt-in and reached
through one verb:

```powershell
seshat integrations setup                       # local plan only; no network or writes
seshat integrations setup --refresh             # resolve exact coordinates; still no writes
seshat integrations setup --refresh --apply     # prompt, then install the resolved plan
seshat integrations setup --refresh --apply --yes  # pre-approved non-interactive install
```

A run with approval clones the Microsoft Fabric and dbt Labs agent skill bundles
and registers the read-only Power BI modeling and dbt MCP servers. Dagster
workflow skills ship with Seshat and are validated, not downloaded.

The setup validates required skills and runtime prerequisites and returns
categorical `planned`, `present`, `installed`, `unavailable`, or `failed`
results. `--refresh`, `--apply`, and `--yes` are independent gates: `--refresh`
permits upstream resolution, `--apply` requests writes, and `--yes` only confirms
an already-requested apply. A bare `--yes` never enables either network access or
writes. It never stores credentials, changes readiness, or grants approval.

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
- **It never modifies the active Python interpreter.** Python components are
  installed into the selected profile's isolated environment under
  `.seshat/integrations/env/<profile>/`. The dbt MCP server reaches dbt through
  `uvx` at an exact resolved version, so no ambient `dbt` is required.
- **It never overwrites an unparseable MCP config.** A config it cannot read is
  reported as `failed` and left exactly as the operator left it. A readable one
  is merged: unrelated server registrations survive.
- **It never clones over an existing directory.** A partially-populated bundle
  directory is reported as `failed` for a human to look at.

## Where the output lives

Everything the installer writes goes under `.seshat/integrations/` in the
resolved workspace:

- official skill checkouts under `skills/<component-id>/`;
- isolated Python environments under `env/<profile>/`;
- MCP installation markers under `node/<component-id>/`;
- temporary, fail-closed checkout work under `staging/<component-id>/`;
- the merged `mcp.json` and exact-coordinate `lock.json`.

That directory is git-ignored: it is machine-local integration state, not a
committed artifact. A checkout is activated only after the catalog-declared
required payload is present; incomplete staged content is rejected.

Non-interactive clients (CI, piped output, agent harnesses) have no prompt to
answer, so an install requires the full explicit
`--refresh --apply --yes` sequence. Otherwise they report a plan or fail closed
without changing integration state.

After a semantic-model readiness pass, run the existing read-only gate:

```powershell
seshat pbi-mcp preflight --repo .
```
