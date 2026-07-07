# Implementation Plan: User workspace initializer (roadmap M3) — HELD

**Branch**: `107-user-workspace-init` | **Date**: 2026-07-07 | **Spec**: `spec.md`

**Status: HELD — plan only, not executed.** Awaiting owner review of the spec before any
code. No `tasks.md` until the spec is approved.

## Summary

Add a `seshat init-project <name>` CLI subcommand that scaffolds a fresh Retail-BI project
workspace, reusing the existing `retail init` `.seshat/` bootstrap internally, without
altering `retail init`.

## Proposed generated workspace shape

```text
<name>/
  mappings/                 # source→mapping evidence (empty; source-mapping gate populates)
  warehouse/
    bronze/  silver/  gold/ # medallion SQL homes (empty)
  powerbi/                  # PBIP project home (empty scaffold)
  reports/                  # dashboard-spec / blueprint homes (empty)
  evidence/                 # evidence-pack output home (empty)
  .seshat/                  # governance bootstrap (same as `retail init` writes)
  .env.example              # parameter names only, NO real values
  README.md                 # points at the readiness flow + `seshat check`
```

## Approach (TDD, when approved)

1. **Extract** the reusable `.seshat/` bootstrap from the current `retail init` handler into
   a shared helper (so M3 reuses it, not copies it) — behavior-preserving to `retail init`.
2. **New** `src/retail/workspace_init.py`: `init_project(name, force=False) -> list[Path]`
   (stdlib `pathlib`; in-repo path guard; refuse-non-empty-without-force; idempotent).
3. **Wire** the `init-project` subparser + dispatch in the CLI (note: coordinate with the
   proposed cli.py decomposition branch if that lands first — add the command in the new
   `cli/commands/` layout rather than the monolith).
4. **Tests**: fresh-scaffold shape, idempotent re-run, refuse-non-empty, traversal guard,
   generated workspace passes `retail check`.
5. **Gate**: full `pytest -m unit` + `retail check` + ruff green.

## Dependency note
Touches the CLI surface — if the cli.py God-Module split (proposed, unmerged branch
`worktree-agent-a4e311bc15516fdbe`) lands, rebase this onto it and add `init-project`
in the new command layout. See the morning summary.
