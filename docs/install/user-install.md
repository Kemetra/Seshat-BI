# User installation: Seshat BI public beta

> **Status: draft public-beta path.** The distribution name is `seshat-bi`, but no package has been published yet. Do not treat the commands below as currently available until the owner publishes a release.

Seshat BI is installed as an isolated command-line application. A first run needs Python 3.13, `pipx`, and Git; it does not need a database or Power BI Desktop.

## First success

Windows is the release-gated path:

```powershell
pipx install seshat-bi           # target — not yet published
pipx ensurepath
seshat init-project my-bi
cd my-bi
git init
seshat status --format json      # {"tables": []}
seshat next --format agent       # Source Ready, not_started
seshat check                     # exit 0
```

On macOS/Linux, use the same commands in a POSIX shell. Reopen the shell after `pipx ensurepath` if the command is not found.

## Optional capabilities

A normal install contains only the runtime dependency needed by the static gate. Add one optional capability only when you need it:

| Extra | Use | User path |
|---|---|---|
| `db` | PostgreSQL live validation | `pipx install "seshat-bi[db]"` |
| `mssql` | SQL Server profile/validate | `pipx install "seshat-bi[mssql]"` |
| `mysql` | MySQL profile/validate | `pipx install "seshat-bi[mysql]"` |
| `snowflake` | Snowflake profile/validate | `pipx install "seshat-bi[snowflake]"` |
| `files` | Excel file profiling | `pipx install "seshat-bi[files]"` |

All commands above are targets until publication. `dev` (pytest/ruff) and `livetest` (testcontainers) are contributor-only extras; users should not install them for a first run.

## Upgrade, remove, and recover

After publication, upgrade with `pipx upgrade seshat-bi` and remove it with `pipx uninstall seshat-bi`. The rollback process is documented in [release rollback](../operations/release-rollback.md).

## Troubleshooting

- **Python or pipx missing:** install Python 3.13 and `pipx` first.
- **`seshat` not found:** run `pipx ensurepath`, reopen the shell, or use `python -m seshat.cli <verb>`.
- **Git missing / workspace not a repo:** install Git if necessary and run `git init` in the workspace.
- **Install fails:** no published package may exist yet; use the contributor instructions for a source checkout.

Credentials belong only in `.env`, never in a command line copied into documentation or a tracked file.