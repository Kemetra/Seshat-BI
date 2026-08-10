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
and registers only catalog-declared MCP surfaces. Dagster workflow skills ship
with Seshat and are validated, not downloaded. Installation is not activation:
the closed-world discovery check must prove the exact harness capability before
any route may use it.

For Power BI, Microsoft owns `powerbi-report-design` and
`powerbi-report-authoring`; Seshat owns business semantics, readiness gates,
named-human approvals, and post-authoring validation. The current full Claude
`powerbi-authoring` plugin is incompatible because it also activates planning,
management, semantic-model authoring, and a default-write moving Modeling MCP
coordinate. The firewall blocks that whole plugin surface rather than ignoring
extras. Exact Codex skill projections may be discoverable when their locked
provenance passes. F016 remains parked, so no modeling MCP is run.

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

To inspect a candidate native-report route without execution, run the read-only
doctor with an exact table and harness:

```powershell
seshat pbi-mcp doctor --repo . --intent report-authoring --target <table> --harness <claude-code|codex>
```

For Seshat's temporary bounded PBIR patch gap, each mutator additionally
requires `--repo . --table <table>` and reads only committed, clean exact-table
semantic and named-human design-approval evidence before touching a payload.
