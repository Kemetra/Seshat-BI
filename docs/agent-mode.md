# Seshat Agent Mode

How an AI agent (Claude Code or any other coding agent) drives Seshat BI
safely. Agent Mode is not a separate runtime or flag -- it is the guarded way
of working this repo already enforces: the agent inspects evidence, reads the
recorded readiness state, performs ONLY the next allowed action, validates,
and stops at the gate.

## What Seshat Agent Mode is

Seshat BI is agent-first: the agent is the interface, and the CLI surfaces
(`seshat check`, `seshat status`, `seshat next`, `seshat validate`) are
helpers the agent calls. Agent Mode means the agent never decides what to do
from intuition or from the user's excitement -- it decides from the committed
readiness state, one table at a time, one stage at a time.

Readiness is always `status + evidence + blocking_reasons` across the seven
stages (Source -> Mapping -> Silver -> Gold -> Semantic Model -> Dashboard ->
Publish). It is never a fabricated number.

## Why Seshat is guarded, not free-form

A free-form agent pointed at retail data will happily jump to the fun part:
gold models, DAX, dashboards. Every one of those jumps bakes an unreviewed
assumption (grain, PII, business rollups, metric definitions) into a surface a
human will trust. The gates exist so that every judgment call is made by a
named human BEFORE the work that depends on it, and so that every `pass` cites
evidence a reviewer can open. The agent's job is to prepare that evidence and
stop -- not to grant its own approvals.

## The correct agent loop

1. Inspect the repo (read-only): what tables exist under `mappings/`, what
   artifacts are committed?
2. Read `AGENTS.md` -- the operating contract (hard stops, approval rules).
3. Run `seshat status --format json` -- the recorded per-table readiness state.
4. Run `seshat next --format agent` -- the computed next allowed action,
   blockers, forbidden scope, and stop point.
5. Perform ONLY the next allowed action (author the artifact that stage
   needs; nothing downstream of it).
6. Run `seshat check` -- the static governance gate; exit 0 is necessary,
   not sufficient.
7. Stop at the review gate. Report what was produced, what is blocked, and
   which named human must decide next. Never self-grant an approval.

`seshat next` also emits `--format json` with stable keys for a host or
harness to consume: `current_stage`, `readiness_state`, `evidence`,
`blocking_reasons`, `next_allowed_action`, `forbidden_scope`,
`validation_commands`, `stop_point`.

## Forbidden jumps

These orderings are the product; an agent must refuse to shortcut them:

- No source goes directly to silver: profile + map first.
- No silver work before Mapping Ready passes (the reviewed, approved
  `source-map.yaml`).
- No gold work before Silver Ready passes.
- No dashboard work before metric contracts and Semantic Model Ready pass.
- No publish work before the handoff pack and Publish Ready pass; the live
  publish itself is the deferred execution adapter (F016), not an agent
  action.

If evidence for the current stage is missing, the answer is the conservative
evidence-first action (go profile, go record status) -- never an assumed
`pass`.

## Current supported commands

| Command | What it does |
|---------|--------------|
| `seshat init-project <name>` | Scaffold a fresh, empty project workspace (no wizard). |
| `seshat status --format json` | Read-only projection of committed readiness state, per table. |
| `seshat next --format agent` | The guarded next-action document: stage, state, evidence, blockers, next allowed action, forbidden scope, validation commands, stop point. |
| `seshat next --table <t> --format json` | The original per-table run-next response (spec 080). |
| `seshat check` | Static governance gate over committed artifacts; the exit code is the authority. |
| `seshat validate` | LIVE data checks -- only when a database is configured (`db` extra + DSN); otherwise it reports the deferred state honestly. |

`retail` is the canonical dev alias of `seshat`; with the package installed,
`python -m retail.cli <verb>` runs every verb without the console script (from
a bare uninstalled clone, prefix with `PYTHONPATH=src`).

## How Claude Code should use Seshat safely

- Start every session with the loop above; re-run `seshat next` after every
  change instead of planning several stages ahead.
- Treat `blocking_reasons` and `stop_point` as hard instructions: a blocked
  stage means STOP and report, not "work around it".
- Author artifacts only for the stage `seshat next` names; keep diffs scoped
  to that table's `mappings/<table>/` + the stage's declared outputs.
- Run `seshat check` after each change; fix findings before continuing.
- Never write real credentials into tracked files; live values missing means
  `[PENDING LIVE PROFILE]`, never a fake number.
- Stop before commit / push / PR unless the human explicitly asks; never
  stage unrelated files (and never `git add -A`).

See also: `AGENTS.md` (operating contract),
`docs/readiness/readiness-model.md` (the seven-stage spine),
`docs/install/user-install.md` (install paths), and
`integrations/claude-code/` (the draft Claude Code plugin skeleton).
