# User installation: Seshat BI public beta

> **Availability:** repository implementation is present; public PyPI availability
> is not claimed until a public-install evidence record passes. The distribution
> name is `seshat-bi`. Commands labeled “after publication” are the supported public
> path, not evidence that an owner has already published a release.

Seshat BI is installed as an isolated command-line application. A first run needs Python 3.13, `pipx`, and Git; it does not need a database or Power BI Desktop.

## Public install and first success

Windows is the release-gated path:

```powershell
pipx install seshat-bi           # after public-install evidence says available
pipx ensurepath
seshat init-project my-bi
cd my-bi
git init
seshat status --format json      # {"tables": []}
seshat next --format agent       # Source Ready, not_started
seshat check                     # exit 0
```

On macOS/Linux, use the same commands in a POSIX shell. Reopen the shell after
`pipx ensurepath` if the command is not found. A public user does not clone the
Seshat development repository.

Before publication, a release reviewer may install the exact validated wheel from
the candidate handoff:

```powershell
pipx install .\seshat_bi-<version>-py3-none-any.whl
```

That is candidate validation, not a public-index install. Source/editable installs
belong only in the [developer guide](developer-install.md).

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

After publication, upgrade with:

```powershell
pipx upgrade seshat-bi
seshat --help
```

Seshat workspaces are ordinary user-owned directories, outside the pipx application
environment. Upgrade MUST leave them unchanged. If the resolver reports that no
newer version exists, verify the public version and configured index; never overwrite
an immutable published version.

Remove the application with:

```powershell
pipx uninstall seshat-bi
Get-Command seshat, retail -ErrorAction SilentlyContinue  # Windows: no result expected
```

On macOS/Linux, use `command -v seshat retail`; neither command should resolve.
Uninstall removes the isolated application and both command shims, but MUST preserve
every user project. The per-surface rollback process is documented in
[release rollback](../operations/release-rollback.md).

## Supported beta boundary

- Python 3.13 is required. On an older interpreter, pip should reject the package
  with a `Requires-Python` message; do not bypass that constraint.
- Windows with Python 3.13 is the blocking Public Beta lifecycle gate: build,
  install, both commands, first success, upgrade, uninstall, and preservation.
- Linux and macOS with Python 3.13 are documented and collect best-effort beta
  evidence. Their CI result is explicitly non-blocking until the owner changes the
  support policy from observed evidence.
- A normal install includes PyYAML only. Database, browser, file-reader, test, and
  build dependencies must not appear unless the user selects the matching extra.

## Troubleshooting

- **Python or pipx missing:** install Python 3.13 and `pipx` first.
- **`seshat` not found:** run `pipx ensurepath`, reopen the shell, or use `python -m seshat.cli <verb>`.
- **Git missing / workspace not a repo:** install Git if necessary and run `git init` in the workspace.
- **Install says no matching distribution:** confirm Python 3.13 and the actual
  availability table. If PyPI is still `not_published`/`unverified`, wait for an
  owner-approved release; contributors may use the separate developer guide.
- **Upgrade fails:** the installed specification or index may be unavailable. The
  current project remains user-owned; record the failure and do not delete it.
- **Uninstall leaves a command:** reopen the shell, inspect `pipx list`, and remove
  only the stale pipx shim. Do not delete the project directory.

Credentials belong only in `.env`, never in a command line copied into documentation or a tracked file.
