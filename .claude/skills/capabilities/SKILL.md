---
name: capabilities
description: >-
  Show the read-only capability inventory for this kit -- each capability by lifecycle state, authority, requirements and provenance. Use when someone asks what the kit can do or what works without a database. Writes nothing and emits no score.
---

# capabilities

The read-only capability inventory: one truthful, categorical read of
everything Seshat BI can do, derived from committed, reviewable metadata
(never from a file's mere existence).

## What it does

Reads the committed capability manifest (`docs/capabilities/capabilities.yaml`)
and reconciles it against the feeders that already own each fact -- the
`_DISPATCH` command table, `.claude/skills/*/SKILL.md` frontmatter,
`.seshat/kit-source.yaml` verbs, `docs/roadmap/roadmap.md` F-numbered ship
status, and `docs/quality/status-claims.yaml` -- then renders:

- a grouped human-readable read (the default), or
- a stable, deterministic JSON machine form (`--format json`).

## How to invoke it

Run the module directly from the repo root:

```
python -m seshat.capability_inventory
python -m seshat.capability_inventory --format json
```

There is no `retail capabilities` / `seshat capabilities` CLI verb -- this is a
deliberate, ratified choice (`docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`,
Option B). Do not add one; do not touch `src/seshat/cli/parser.py` or
`_DISPATCH` to "wire this up". Simply run the module command above and relay
its output.

## What it is NOT

- **Not a gate.** It adds no `seshat check` rule; its presence/absence never
  blocks anything.
- **Not a readiness surface.** It reads no `readiness-status.yaml`, moves no
  stage, grants no approval. For per-table readiness use `seshat status`; for
  the next allowed action use `seshat next`; for repo drift use
  `seshat doctor`; for the governance gate use `seshat check`.
- **Not a scoring surface.** No maturity/confidence/completeness/health value
  is ever emitted, and nothing is ranked by a computed number.
- **Not a writer.** It writes nothing, connects to no database, runs no
  Power BI.

## See also

- `docs/capabilities/README.md` -- the fail-closed truthfulness contract and
  how this differs from `status`/`next`/`doctor`/`check`.
- `docs/capabilities/capabilities.yaml` -- the manifest this skill renders.
