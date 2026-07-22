# User installation: Seshat BI public beta

> **Availability:** the current public release is `seshat-bi==0.6.0` on public
> PyPI (the version is single-sourced from `pyproject.toml`), externally
> verified by a clean-venv public-index install, first-success run, and
> uninstall-preservation check; see
> [the v0.3.1 public acceptance record](../releases/v0.3.1-public-acceptance.md)
> for the sanitized evidence. The `pipx`-lane evidence was captured at v0.2.0
> ([record](../releases/v0.2.0-public-acceptance.md)).

Seshat BI is installed as an isolated command-line application. A first run needs Python 3.13, `pipx`, and Git; it does not need a database or Power BI Desktop.

## Public install and first success

Windows is the validated release lane:

```powershell
pipx install seshat-bi
pipx ensurepath
seshat init-project my-bi
cd my-bi
git init
seshat status --format json      # {"tables": []}
seshat next --format agent       # Source Ready, not_started
seshat check                     # exit 0
```

On macOS/Linux, use the same commands in a POSIX shell; this lane is documented
best-effort beta support, not the release gate. Reopen the shell after
`pipx ensurepath` if the command is not found. A public user does not clone the
Seshat development repository.

A release reviewer validating a not-yet-published candidate may instead install the
exact validated wheel from the candidate handoff:

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

`dev` (pytest/ruff) and `livetest` (testcontainers) are contributor-only extras; users should not install them for a first run.

## Upgrade, remove, and recover

Upgrade with:

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
- **Install says no matching distribution:** confirm you are on Python 3.13 and
  using the public index (`--index-url https://pypi.org/simple`); if the problem
  persists, check [the support matrix](support-matrix.md) for the current status.
- **Upgrade fails:** the installed specification or index may be unavailable. The
  current project remains user-owned; record the failure and do not delete it.
- **Uninstall leaves a command:** reopen the shell, inspect `pipx list`, and remove
  only the stale pipx shim. Do not delete the project directory.

Credentials belong only in `.env`, never in a command line copied into documentation or a tracked file.
