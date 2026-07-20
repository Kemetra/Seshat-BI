# Client quickstart: install Seshat BI

The current public release is **`seshat-bi==0.5.2`** on public PyPI. Seshat BI
ships as two things you can download independently:

1. the **command-line package** (the `seshat` CLI + governance engine), and
2. the **agent plugin** (the `seshat-bi:*` skills and workflows) for Claude Code
   or Codex, served from this GitHub repository as a marketplace.

You do **not** need to clone this repository. You do not need a database or Power
BI Desktop for a first run — only Python 3.13, `pipx`, and Git.

---

## 1. Install the CLI package

```powershell
pipx install seshat-bi
pipx ensurepath
```

Reopen your shell after `pipx ensurepath` if `seshat` is not found. Verify:

```powershell
seshat init-project my-bi
cd my-bi
git init
seshat status --format json      # {"tables": []}
seshat check                     # exit 0
```

Windows is the validated release lane; macOS/Linux use the same commands in a
POSIX shell (best-effort beta support). Full detail, upgrade, and removal:
[user install guide](user-install.md).

### Optional database extras

The base install only needs the static gate's runtime dependency. Add a
capability only when you need live validation:

| Extra | Use | Install |
|---|---|---|
| `db` | PostgreSQL live validation | `pipx install "seshat-bi[db]"` |
| `mssql` | SQL Server profile/validate | `pipx install "seshat-bi[mssql]"` |
| `mysql` | MySQL profile/validate | `pipx install "seshat-bi[mysql]"` |
| `snowflake` | Snowflake profile/validate | `pipx install "seshat-bi[snowflake]"` |
| `files` | Excel file profiling | `pipx install "seshat-bi[files]"` |

---

## 2. Add the agent plugin (skills + workflows)

Pick your agent. This is separate from the CLI package above — it gives your
agent the `seshat-bi:*` skills and the governed retail workflows.

### Claude Code

```
/plugin marketplace add Kemetra/Seshat-BI
/plugin install seshat-bi@seshat-bi-marketplace
```

Later, to update or remove:

```
/plugin marketplace update seshat-bi-marketplace
/plugin update seshat-bi@seshat-bi-marketplace
/plugin uninstall seshat-bi@seshat-bi-marketplace
```

### Codex CLI

```bash
codex plugin marketplace add https://github.com/Kemetra/Seshat-BI
codex plugin add seshat-bi@seshat-bi-repository
codex plugin list
```

Full agent-install detail, verification, and the support matrix:
[agent install guide](agent-install.md) · [support matrix](support-matrix.md).

---

## What you get

- **9 governed skills/workflows** per agent bundle (Claude and Codex),
  version-matched to the CLI release.
- The seven-stage readiness flow, static + live governance gates, source
  mapping, metric contracts, and the `seshat dashboard` static readiness view
  (new in v0.5.2 — see [CHANGELOG](../../CHANGELOG.md)).

Repository marketplace availability is a distinct thing from a public catalog
listing; Seshat BI is not (yet) submitted to a public Claude or OpenAI catalog,
so add the repository marketplace directly as shown above.
