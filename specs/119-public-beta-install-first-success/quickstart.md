# Quickstart: Seshat BI — Install to First Success

> **Status: BETA (planning artifact).** This is the *design* of the user-facing quickstart
> that will land in the top-level `README.md` and `docs/install/user-install.md`. It shows
> the exact copy-pasteable path a new user follows. **`pipx install seshat-bi` is the
> target command and is NOT published yet** — no line here may be presented as working
> before a real artifact exists (SC-008).

Seshat BI is an agent-controlled Retail BI readiness tool: it tells your AI agent the one
truthful next step to turn a raw retail source into a governed Power BI model — one gated
stage at a time. **The first run needs no database and no Power BI Desktop.**

---

## Three-step quickstart

```text
1. pipx install seshat-bi          # install (target — not yet published)
2. seshat init-project my-bi       # create a clean workspace
3. cd my-bi && git init && seshat check   # prove it works (exit 0)
```

Then open Claude Code in `my-bi` and say:
> Use Seshat BI for this project and perform only the next allowed action.

---

## Try without a database (the full first success)

### Windows (gate-verified path)

```powershell
pipx install seshat-bi           # target — not yet published
pipx ensurepath                  # if `seshat` is not found afterwards, then reopen shell
seshat --help                    # confirms the command is available
seshat init-project my-bi
cd my-bi
git init                         # required: Seshat reads committed evidence
seshat status --format json      # expected: {"tables": []}
seshat next --format agent       # expected: a truthful SOURCE READY onboarding action
seshat check                     # expected: exit 0 (governance-clean)
```

### macOS / Linux (documented; best-effort tested)

```bash
pipx install seshat-bi           # target — not yet published
pipx ensurepath                  # then reopen your shell if `seshat` is not found
seshat --help
seshat init-project my-bi
cd my-bi
git init
seshat status --format json      # {"tables": []}
seshat next --format agent       # truthful Source Ready onboarding action
seshat check                     # exit 0
```

**Expected signal that install succeeded**: `seshat --help` prints usage listing
`init-project`, `status`, `next`, `check`; and `seshat check` on the fresh workspace exits
`0`. `seshat next` never invents readiness — it reports `not_started` and the evidence-first
onboarding action, with no numeric score.

---

## Use with Claude Code

Install the Seshat BI plugin (verified public syntax):

```text
/plugin marketplace add <owner>/<repo>        # the hosted Seshat marketplace
/plugin install seshat-bi@seshat-bi-marketplace
/plugin marketplace update                    # later, to refresh
```

This exposes the Seshat skill and the `/seshat-*` commands. Open Claude Code in your
workspace and issue one instruction:

> Use Seshat BI for this project and perform only the next allowed action.

Claude reads the recorded readiness state and returns the truthful next allowed action —
a Source Ready onboarding step — with no fabricated readiness and no database prompt.

> **Note**: while the plugin is a draft/beta, its status label says so. The dev-only local
> command `claude plugin marketplace add ./integrations/claude-code` is **not** the public
> command — use the `<owner>/<repo>` form above once the marketplace is published.

---

## Connect your database (optional, later step)

Only when you want live validation:

```bash
pipx inject seshat-bi psycopg2-binary     # or: pipx install "seshat-bi[db]"
# put your DSN in .env  (git-ignored — NEVER a tracked file):
#   ANALYTICS_DB_URL=postgresql://...
seshat validate --source-map mappings/<table>/source-map.yaml
```

Other engines: `seshat-bi[mssql]`, `seshat-bi[mysql]`, `seshat-bi[snowflake]`. File
profiling: `seshat-bi[files]`. A normal first install pulls **none** of these.

---

## Troubleshooting (most likely first-run failures)

| Symptom | Fix |
|---------|-----|
| `seshat: command not found` after install | run `pipx ensurepath`, reopen the shell; or use `python -m seshat.cli <verb>` |
| `python`/`pipx` not found | install Python 3.13 and `pipx`; re-run the quickstart |
| `check`/`next` complain the repo is not git | run `git init` in the workspace first |
| plugin won't install | confirm the marketplace `<owner>/<repo>` and that the plugin is published (draft/beta may be local-only) |

*The user-facing quickstart deliberately requires no reading of `AGENTS.md`, the
constitution, the roadmap, or internal specs before first success — those stay contributor
and agent references.*
