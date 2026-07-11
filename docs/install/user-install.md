# Installing Seshat BI

Seshat BI is an agent-controlled Retail BI readiness tool. This page covers
what works **today** (a source / editable install from GitHub) and where
distribution is headed. Sections are labeled explicitly: anything under
"Future distribution path" is **not** a current capability.

## The `seshat` command

The tool exposes a `seshat` console command (an alias of the canonical
`retail` command; both dispatch the same entry point -- roadmap M1, shipped).
Once installed, `seshat` and `retail` are interchangeable; `seshat` is the
product-facing brand name.

## Supported today: development install

```bash
git clone https://github.com/ahmed-shaaban-94/Seshat_BI.git
cd Seshat_BI
python -m venv .venv
.venv/Scripts/activate       # Windows; on macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"      # exposes both `seshat` and `retail` commands
seshat check                 # proves the install: exit 0 == governance-clean
```

Requirements:

- Python 3.13
- Git (Seshat reads committed evidence; several checks are git-aware)
- For live DB validation only: the `db` extra and a DSN
  (`pip install -e ".[db]"`) -- see `docs/powerbi-connection.md`. Static
  `check` needs no database.

## Supported today: direct source execution (no console script)

With the package installed (the editable install above is enough), every verb
also runs as a module, no `seshat`/`retail` script needed:

```bash
python -m retail.cli check --repo .
python -m retail.cli status --repo . --format json
python -m retail.cli next --repo . --format agent
```

From a **bare clone with no install at all**, the package lives under `src/`
and is not on Python's import path -- prefix the same commands with
`PYTHONPATH=src` (PowerShell: `$env:PYTHONPATH="src"`) and have `pyyaml`
available, or just use the editable install:

```bash
PYTHONPATH=src python -m retail.cli check --repo .
```

## Supported today: fresh project test

Prove the installed tool end-to-end on a brand-new workspace:

```bash
seshat init-project my-retail-bi
cd my-retail-bi
git init                       # required before `seshat check`: git-aware rules read the repo
seshat status --format json    # empty projection: {"tables": []}
seshat next --format agent     # conservative first action: start at Source Ready
seshat check                   # static gate over the fresh workspace (exit 0)
```

`seshat next` on a fresh project never invents readiness: it reports
`not_started` and points at the evidence-first onboarding action.

## Future distribution path

The ladder below is the plan, in order. Only the first rung exists today; do
not treat the later rungs as available.

| Rung | State |
|------|-------|
| **GitHub source / editable install** (this page) | **Current -- supported today.** |
| **Claude Code local plugin skeleton** | Verified draft at `integrations/claude-code/seshat-bi/` -- manifest schema and local install flow verified with the Claude Code CLI (v2.1.206); not published. |
| **Plugin marketplace repo** | Later. Verified draft manifest at `integrations/claude-code/.claude-plugin/`; would likely move to a standalone repository before publication. |
| **PyPI / pipx / uv tool install** (`pipx install seshat-bi`) | Later (roadmap M2). Not published to any package index yet -- `pipx install seshat-bi` does not work today. |
| **MCP server** | Later. Not designed in this slice. |

Roadmap detail: `docs/roadmap/seshat-bi-agent-controlled-user-tool-roadmap.md`.

## What `seshat` does

It is a **gate the agent calls**, not a dashboard generator. It profiles a
retail source, governs the source-to-mapping decisions a human must approve,
gates silver/gold warehouse work, validates the warehouse live, defines
metric contracts, protects Power BI semantic meaning, and prepares the PBIP
handoff -- advancing one **readiness stage** at a time, always with evidence
and blocking reasons, never a fabricated confidence score. Publishing /
execution stays gated behind semantic-model readiness and a named-human
approval.

See the [seven-star readiness spine](../readiness/readiness-model.md), the
[medallion playbook](../medallion-playbook.md), and
[Agent Mode](../agent-mode.md) for how an agent drives the tool.

## Configuration

Credentials live only in `.env` (git-ignored) and reach Power BI via
parameters, never baked-in connection strings. See the top-level `README.md`
and `docs/powerbi-connection.md`.
