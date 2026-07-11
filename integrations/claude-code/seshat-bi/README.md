# Seshat BI -- Claude Code plugin (verified draft, not released)

> **Status: locally verified draft, not publicly released.** The plugin
> manifest passes `claude plugin validate` and the local marketplace-add ->
> install -> component-load flow succeeds (Claude Code CLI v2.1.206,
> 2026-07; see [`../README.md`](../README.md) for the verified steps).
> Nothing here is published anywhere.

This plugin teaches Claude Code to drive the **Seshat BI** readiness system
safely through its existing CLI. It contains **no BI logic of its own** -- the
CLI (`seshat` / `python -m retail.cli`) remains the single source of truth;
the plugin only supplies the guarded operating procedure (skill) and four
thin slash commands.

## What it enforces

Seshat BI is a *guarded* BI readiness system, not a dashboard generator. The
skill instructs the agent to:

1. inspect the repo first (read-only),
2. read `AGENTS.md`,
3. run `seshat status --format json` and `seshat next --format agent` before
   editing anything,
4. perform ONLY the next allowed action,
5. never skip a readiness gate (no silver before Mapping Ready, no gold
   before Silver Ready, no dashboards before semantic readiness, no publish
   before handoff readiness),
6. run `seshat check` after changes,
7. stop before commit / push / PR unless explicitly requested -- and never
   use `git add -A` or stage unrelated files.

## Layout

| Path | Purpose |
|------|---------|
| `.claude-plugin/plugin.json` | Plugin manifest (draft; schema unverified). |
| `skills/seshat-bi/SKILL.md` | The guarded operating procedure the agent loads. |
| `commands/seshat-init.md` | `/seshat-init` -- verify the CLI, scaffold a fresh project. |
| `commands/seshat-next.md` | `/seshat-next` -- status + next; summarize stage, blockers, next action, stop point. |
| `commands/seshat-check.md` | `/seshat-check` -- run the governance gate; report findings honestly. |
| `commands/seshat-review.md` | `/seshat-review` -- read readiness evidence; recommend the next safe action; no edits. |

## Prerequisites

The Seshat BI CLI must be available in the working repo:

```bash
pip install -e ".[dev]"     # from a clone of Seshat_BI
seshat check                # proves the install
```

or, without installing, every command also runs as
`python -m retail.cli <verb>`.

## Trying the draft locally

The local flow is Claude Code's plugin/marketplace mechanism -- see
[`../README.md`](../README.md) (the marketplace root) for the verified
add/install/load steps. Publication is still pending the standalone-repo
decision; do not point users at this directory as a released install path.
