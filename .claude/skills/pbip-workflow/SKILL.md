---
name: pbip-workflow
description: >-
  The git-based workflow for Power BI Project (PBIP) files — saving reports as
  plain-text TMDL/PBIR, what to commit vs ignore, and the Windows gotchas.
  Use this whenever someone is putting Power BI under version control: saving a
  report to git, choosing PBIP vs .pbix, editing TMDL or DAX as text, reviewing
  a semantic-model change in a PR, or troubleshooting why a .pbi folder, cache,
  or localSettings is (or isn't) showing up in git. Also use when "Save as
  PBIP" is missing, when PBIP diffs look noisy (line endings / encoding), or
  when path-too-long errors appear saving a Power BI project on Windows.
---

# PBIP Workflow

Power BI's default `.pbix` is a binary zip — opaque to git, impossible to diff or
merge, and it bloats history. The **Power BI Project (PBIP)** format saves the
same work as folders of plain text, so your semantic model and report become
reviewable code. This skill is how to work with PBIP under git correctly.

> PBIP is a **preview feature** (per Microsoft docs as of 2025-12). It can change.
> Verify specifics against the current docs:
> https://learn.microsoft.com/power-bi/developer/projects/projects-overview

## When this matters

The whole reason to use PBIP is that **the semantic model becomes code**. Tables,
relationships, and especially **DAX measures** are saved as TMDL (Tabular Model
Definition Language) text — so "who changed the Gross Margin measure and why" is
answerable from `git log`, and a teammate can review a measure change in a pull
request the same way they'd review a function. Treat the model with the same care
as source code.

## Adopt an existing PBIP into Seshat BI

When the analyst already has a PBIP project, start with the governed,
read-only intake rather than treating its report pages or measures as readiness
evidence:

```powershell
seshat adopt-pbip assess --project <PBIP-project-directory> --format text
```

The assessment inventories only supported PBIP/TMDL/PBIR structure, redacts
unsafe literals, reuses existing governance/readiness findings, and returns one
next action. It does not create a source map, metric contract, approval, or
readiness pass. Review the digest and declared write plan before any mutation.

For a clean, existing Git worktree only, an analyst may explicitly accept the
current assessment to create exactly one new evidence seam:

```powershell
seshat adopt-pbip scaffold --project <PBIP-project-directory> `
  --accept-assessment <assessment-digest> --format text
```

This creates only `.seshat/adoption/pbip-adoption.yaml`; it never initializes
Git, overwrites a file, or edits PBIP/TMDL/PBIR/DAX/SQL/source artifacts.
Approvals remain empty and readiness must still be proven through the existing
seven-stage gates. For a `.pbix`, open it in Power BI Desktop and save it as a
PBIP first; the adoption command does not parse or extract PBIX binaries.

## Enabling PBIP

If "Save as Power BI Project" is missing, it's because the preview feature isn't on:

1. Power BI Desktop → **File > Options and settings > Options > Preview features**.
2. Check **Power BI Project (.pbip) save option**.
3. Save via **File > Save as > Power BI Project (.pbip)**.

A `.pbix` can be saved as PBIP and back again (via Desktop's Save As), so migrating
an existing report is low-risk.

## What a PBIP looks like

```
Project/
├── MyReport.Report/
│   └── definition/            ← report visuals/layout (PBIR)
│       └── ...
├── MyReport.SemanticModel/
│   └── definition/            ← TMDL: tables, relationships, MEASURES (your DAX)
│       └── ...
├── MyReport.pbip              ← pointer file that opens the report+model
└── .gitignore
```

The `definition/` folders are the valuable part — that's the model and report *as
code*. The `.pbip` file is just a shortcut to open them.

## Commit vs. ignore — the part that bites people

This is the highest-risk decision. Get it backwards and you either leak local
workspace context into git or — worse — drop the actual model definition from
version control.

**Commit these** (this is your reviewable source):
- Everything under `*.SemanticModel/definition/` (TMDL — tables, relationships, DAX)
- Everything under `*.Report/definition/`, plus `definition.pbir`
- `.platform`
- The `*.pbip` file

**Ignore these** — Microsoft's official PBIP `.gitignore` baseline is exactly:
```gitignore
**/.pbi/localSettings.json
**/.pbi/cache.abf
```
- `localSettings.json` holds local workspace settings and can carry connection context.
- `cache.abf` is the local data cache — large, machine-specific, not source.

Verify behavior rather than trusting the file is right:
```bash
# should print the path (ignored):
git check-ignore "MyReport.SemanticModel/.pbi/cache.abf"
# should print NOTHING (tracked) — if it prints, your model is being dropped from git:
git check-ignore "MyReport.SemanticModel/definition/model.tmdl"
```

## Windows & diff gotchas

These come straight from Microsoft's docs and quietly break teams:

| Gotcha | Why | What to do |
|--------|-----|------------|
| **260-char path limit** | PBIP nests folders + files; long table/object names overflow it and saves fail | Keep the repo at a short root path; keep project/table names short |
| **CRLF line endings** | Power BI Desktop writes CRLF; mixed endings make diffs noisy | `git config core.autocrlf true` and commit a `.gitattributes` |
| **UTF-8 *without* BOM** | Editing TMDL/JSON externally with a BOM can corrupt the file | Save external edits as UTF-8 without BOM |
| **Desktop is unaware of external edits** | It won't see changes made by VS Code/Tabular Editor while open | Restart Power BI Desktop after external edits |

## Editing the model as text

You can edit TMDL in VS Code or Tabular Editor, not only in Power BI Desktop — that's
the point of plain text. But Desktop owns some files it doesn't fully document during
preview (e.g. `report.json`, `diagramLayout.json`); changing those by hand can prevent
the project from opening. Edit measures and table definitions freely; leave the
layout/diagram files to Desktop unless you know what you're changing.

## Reviewing a PBIP change in a PR

Because measures are TMDL text, review them like code:
- Does the measure use `DIVIDE()` for ratios (not `/`) so zero/blank denominators are safe?
- Is logic duplicated across measures that should share a base measure?
- Did a relationship flip to bidirectional (a common source of wrong totals)?
- Is any connection string or secret accidentally committed instead of parameterized?

## Orchestration

When a table is being driven end-to-end, the `retail-orchestrate` conductor skill
sequences this verb with the others and runs the self-heal loop against the gate
exit code. This skill stays single-purpose: it does its job and STOPS. The loop
(run gate -> classify findings -> auto-fix mechanical / HARD-STOP judgment calls ->
re-run) lives ONLY in `retail-orchestrate`, never here.
