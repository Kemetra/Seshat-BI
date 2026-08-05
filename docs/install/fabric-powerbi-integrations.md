# Fabric, Power BI, dbt, and Dagster integrations

Seshat does not run network installers as a side effect of `pipx install` or
`pip install`. On the first interactive Seshat launch in a workspace, it shows
the integration plan once and asks for approval; the client does not need to
know any command names. A `yes` clones the Microsoft Fabric and dbt Labs agent
skill bundles and registers the read-only Power BI modeling and dbt MCP servers.
Dagster workflow skills ship with Seshat and are validated, not downloaded.

For operators who want an explicit flow:

```powershell
seshat integrations setup
seshat integrations setup --apply
```

The setup validates required skills and runtime prerequisites and returns
categorical `planned`, `present`, `installed`, `unavailable`, or `failed`
results. Use `--yes` only when an operator has already approved the install.
Non-interactive runs without `--apply` or `--yes` remain a dry run. It never
stores credentials, changes readiness, or grants approval.

## What it will not do

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

Everything the installer writes goes under `.seshat/integrations/` — the two
shallow clones, the generated `mcp.json`, and the first-run offer marker. That
directory is git-ignored: it is machine-local installer output, not a committed
artifact.

The first-run offer resolves the workspace root by discovery, so launching from
a subdirectory still writes the one true `.seshat/integrations/`. Outside a
Seshat workspace no offer is made at all.

To suppress the offer entirely:

```powershell
$env:SESHAT_NO_AUTO_INTEGRATIONS = "1"
```

Non-interactive clients (CI, piped output, agent harnesses) are never prompted.

After a semantic-model readiness pass, run the existing read-only gate:

```powershell
seshat pbi-mcp preflight --repo .
```
