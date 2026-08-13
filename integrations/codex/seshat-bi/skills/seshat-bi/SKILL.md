---
name: seshat-bi
description: >-
  Route a BI project through Seshat BI's governed seven-stage readiness flow.
  Use when a user asks to inspect a retail source, initialize a Seshat project,
  find the truthful next action, validate readiness evidence, or stop at the
  correct human approval gate.
---

# Seshat BI

Read `../../portable-operating-contract.md` before acting. Inspect the current
workspace and use installed `seshat` commands when available. If the workspace
has no `AGENTS.md`, this skill's portable operating contract still applies.

For subject reasoning, load only the relevant bundled skill:

- SQL and source grain: `bi-sql-knowledge`
- DAX and semantic measures: `bi-dax-knowledge`
- Python/dataframe preparation: `bi-python-knowledge`
- distributed data: `bi-bigdata-knowledge`
- retail KPI meaning and contracts: `retail-kpi-knowledge`
- decision-questions, framing, and story order from approved metrics:
  `bi-analyst-knowledge`
- Power BI design, review, theme, formatting, and PBIP adoption:
  `powerbi-workflows`
- governed dbt prerequisite, plan, shadow build, and evidence review:
  `dbt-workflows`
- governed Dagster preflight, gated medallion runs, and run-evidence review:
  `dagster-workflows`
- read-only Power BI MCP doctor, surface recommendation, and preflight:
  `pbi-mcp-doctor`

The ten readiness verbs, in flow order. Each owns one stage transition and stops
at its own gate; none of them self-grants an approval:

- orient a new table on one card: `first-hour-compass`
- sequence a table end to end and self-heal against the gate:
  `retail-orchestrate`
- discover a database metadata-only and propose governed scope:
  `retail-discover-portfolio`
- take a raw table from Source Ready to Mapping Ready: `retail-onboard-table`
- interview the owner into the Decision Store: `business-knowledge-interview`
- drive a raw table through the mapping gate: `source-mapping`
- author an owner-ready metric contract: `kpi-contract-builder`
- author the silver and gold migration SQL, then stop: `retail-build-warehouse`
- run the static governance checker and read its findings: `retail-govern`
- run the live data checks on materialized rows: `retail-validate`

Not a readiness verb, but the surface a user asks for by name: to open the local
analyst console for one workspace in a browser -- readiness, tables, and the
approvals a human still owes -- load `seshat-studio`. It renders recorded state
and stops at the same gates; it grants no approval and advances no stage.

End with one next action or one blocked stop. Cite evidence and named blockers;
never invent a pass or score.

## Discovering the surface (no name memorization needed)

A user or agent only needs this skill's name; everything else self-describes:

- On Claude Code, `/seshat-bi:help` prints the full installed command map; on
  Codex, the routing list above IS the map (there are no Codex slash
  commands).
- `seshat --help` lists every installed CLI verb, and
  `seshat next --format agent` returns the one machine-readable governed next
  action -- always prefer it over guessing a verb or a stage.
- Use only the commands, verbs, and skill names those surfaces report; never
  invent a name, and if `seshat` is not installed, say so and point to
  `pipx install seshat-bi` instead of simulating output.

## Agent-driven loop (programmatic automation)

For fully programmatic automation, the optional read-only MCP governor
(`seshat mcp --repo <workspace>`, installed via `pipx install "seshat-bi[mcp]"`)
exposes six tools: `seshat_get_status`, `seshat_get_next_action`,
`seshat_explain_blockers`, `seshat_prepare_approval_request`,
`seshat_run_static_check`, and `seshat_export_evidence_pack`.

The governed loop is: get the next action, perform exactly that one action,
re-run the static check, and repeat. When the next action is a named-human
decision, call `seshat_prepare_approval_request` to package it and STOP -- no
tool in this loop grants an approval, advances a stage, or emits a score, and
the loop must never route around a blocked gate.

## Existing PBIP projects

For an existing Power BI Project, first use the installed read-only entry path:

```powershell
seshat adopt-pbip assess --project <PBIP-project-directory> --format text
```

Treat PBIP structure as candidate evidence only. The assessment must not create
or approve mappings, metrics, business meaning, or readiness passes. It returns
one governed next action and an assessment digest. A `.pbix` is a conversion
boundary: save it as PBIP in Power BI Desktop before continuing.

Only after a human reviews the exact digest, and only in a clean existing Git
worktree, may the agent run:

```powershell
seshat adopt-pbip scaffold --project <PBIP-project-directory> --accept-assessment <assessment-digest>
```

This writes at most `.seshat/adoption/pbip-adoption.yaml`; it never initializes
Git, overwrites existing files, grants approval, or advances readiness.

## Resetting / re-running a project

Use the native verb first: `seshat reset <table>` removes the complete derived
file-set for ONE table (its `mappings/<table>/` incl. `dbt-evidence/`, the
exact-token silver/gold migrations, the three nested `dbt/models/*/<table>/`
folders, only this table's rows in the shared dbt files, and the table-scoped
dagster run evidence under `.seshat/dagster/runs/`), preserves the bronze
landing, and STAGES the deletions so `seshat check` runs clean afterwards. It
never touches a live database.

```powershell
seshat reset <table> --dry-run   # print the exact plan first (writes nothing)
seshat reset <table>             # interactive confirm; --yes for automation
seshat next --table <table>      # should now report a fresh Source stage
```

Refusals exit non-zero with a named reason (an unsafe table name, a symlinked
path, a shared dbt file the surgical row-edit cannot verify -- hand-edit that
file, then retry). In a non-interactive shell, pass `--yes` or the verb refuses
rather than hanging.

The MANUAL checklist below is the fallback for when the verb refuses or is
unavailable.

**STOP first -- two cases neither the verb nor this manual reset covers; hand
them to the owner rather than deleting blindly:**

1. **Shared conformed dimension.** If this table OWNS a conformed dimension that
   another star reuses, the marts directory the dbt adapter generates for it holds
   the sole dbt model
   the reuser resolves via `ref()` (the kit emits no duplicate model for
   non-owners). Deleting the marts folder would break the other star's build.
   Check the conformed-dimension map, creating the file if absent: if this table is the OWNER
   of any dimension listed with other-star reusers, **do not run this manual
   reset** -- ownership transfer / dependent regeneration is an owner decision.
2. **Downstream Power BI artifacts.** If this table reached Semantic Model or
   Dashboard, committed `powerbi/*.SemanticModel` / report artifacts still point
   at the gold objects you are about to remove. This checklist does NOT rewrite
   or quarantine them -- leaving them would let Power BI keep reading stale gold
   while `seshat next` reports Source. If a `powerbi/` artifact references this
   table's gold entities, **stop and hand the PBIP teardown to the owner** (a
   shared semantic model especially must be handled explicitly, never bulk
   deleted).

If neither case applies (no conformed-dimension ownership, no downstream PBIP),
this table's artifacts are table-local and the reset is safe -- prefer
`seshat reset <table>` above; the manual fallback follows.

First LIST what you are about to remove and confirm every path is for THIS
table -- never delete by a bare `<table>*` wildcard. A prefix wildcard is
dangerous when one table id is a prefix of another (e.g. `orders` also matches
`orders_archive`): `*_create_silver_<table>*.sql` would sweep the other table's
migrations too, and a later broad `git add` would then stage that unrelated data
loss. Enumerate the exact migration files and eyeball them before removing:

```powershell
# 1. Enumerate the migration SQL for THIS table -- review the list first.
Get-ChildItem warehouse/migrations |
  Where-Object { $_.Name -match "_create_(silver|gold)_<table>(_|\.)" }
```

Once the list is confirmed to contain only this table's files, remove the
derived artifacts (exact per-table paths, not prefix globs):

```powershell
Remove-Item -Recurse -Force mappings/<table>
# remove ONLY the confirmed migration files from the list above, e.g.:
Remove-Item -Force warehouse/migrations/0003_create_silver_<table>.sql
Remove-Item -Force warehouse/migrations/0004_create_gold_<table>_star.sql
Remove-Item -Recurse -Force dbt/models/staging/<table>
Remove-Item -Recurse -Force dbt/models/marts/<table>
Remove-Item -Recurse -Force dbt/models/audit/<table>
```

This covers `mappings/<table>/` (including its nested `dbt-evidence/`
subfolder -- it lives under the mapping directory, not as a separate
top-level path), the silver and gold migration SQL for that table (plus any
generated `warehouse/gold/` or `warehouse/schema/` outputs), and the three
per-table dbt model folders. Do not touch the bronze landing. In a multi-table
workspace, also confirm the shared dbt files (`dbt/models/sources/_sources.yml`,
`dbt/selectors.yml`) no longer reference this table's gold entities -- edit out
only this table's rows, leaving other tables' rows intact.

The materialized dagster project under `orchestration/dagster/` is
regenerable rather than hand-edited; if it references the removed table,
regenerate it with `seshat dagster init`.

Stage the deletions before running `seshat check` -- an unstaged delete can
leave the static gate reading stale tracked content. Stage the SPECIFIC paths
you removed (and the shared-file edits), not a blanket `git add -A` -- a bare
`-A` would also stage any unrelated working-tree change, including a mistaken
deletion of another table's files:

```powershell
# stage exactly the paths reset above -- review `git status` first
git add mappings/<table> `
        warehouse/migrations/0003_create_silver_<table>.sql `
        warehouse/migrations/0004_create_gold_<table>_star.sql `
        dbt/models/staging/<table> dbt/models/marts/<table> `
        dbt/models/audit/<table> `
        dbt/models/sources/_sources.yml dbt/selectors.yml
seshat check
seshat next --format agent --table <table>
```

Then verify no residual state remains by inspecting the per-table and shared
artifacts directly -- do NOT rely on `.seshat/manifest.yaml`, which records the
kit's integrity fingerprint (kit-source / compass / integration receipts), not
onboarded tables, so it never mentions a table and would give a false
all-clear. A truthful reset means: `mappings/<table>/` is gone, no
`*_<table>*.sql` migration remains, the three `dbt/models/*/<table>/` folders
are gone, and the shared dbt files carry no rows for this table. Pass
`--table <table>` to `seshat next` so it reports THIS table's stage (without it,
`next` focuses the portfolio's most urgent OTHER table and cannot confirm the
reset) -- it should now report a fresh Source stage; if it does not, the reset
is incomplete.
