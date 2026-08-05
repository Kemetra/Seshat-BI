# Fabric, Power BI, dbt, and Dagster integrations

Seshat does not run network installers as a side effect of `pipx install` or
`pip install`. On the first interactive Seshat launch, it automatically shows
the integration plan and asks for approval; the client does not need to know
any command names. A `yes` clones Microsoft Fabric and dbt Labs agent skills,
registers the Power BI and dbt MCPs, and prepares the pinned dbt and Dagster
runtimes. Dagster workflow skills are shipped with Seshat and are validated.

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

After a semantic-model readiness pass, run the existing read-only gate:

```powershell
seshat pbi-mcp preflight --repo .
```