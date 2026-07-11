# Capability Inventory -- what this is, and how it differs from status/next/doctor/check

This directory holds the single committed, categorical capability manifest
(`capabilities.yaml`) and the contract behind it. The inventory answers ONE
question: **"what can this kit actually do right now?"** -- read-only, never a
computed score, never a granted readiness state.

## The fail-closed truthfulness contract

A file existing on disk is NOT evidence that a capability is shipped. The
manifest may claim `state: shipped` for a capability ONLY when a committed
feeder POSITIVELY backs that claim:

- an F-numbered row marked SHIPPED in `docs/roadmap/roadmap.md`,
- a `claimed-status: built` entry in `docs/quality/status-claims.yaml`,
- a wired command (a real `_DISPATCH` key in `src/seshat/cli/__init__.py`), or
- a committed `SKILL.md` bearing declaring frontmatter (`name` + `description`)
  for a skill-shaped capability.

"Not contradicted" is not "confirmed". A spec directory existing, or a module
with no declaring metadata, is explicitly NOT positive shipped evidence -- a
capability with no such backing must be recorded `spec-only` or `deferred`,
never `shipped`. The same fail-closed rule applies to
`provenance: publicly-released`: it requires committed external-release
evidence, or the field must read `locally-verified` / `unrecorded`.

An independent pytest oracle (`tests/unit/test_capability_inventory.py`) reads
these feeders directly -- never through the inventory's own rendering code --
and fails CI when the manifest drifts from them in either direction: an
orphaned reference, an unlisted real capability, a false `shipped`, or a false
`publicly-released`. This is a TEST, not a `retail check` rule: it fails CI
but adds no gate, no registered rule, and no `blocking_reasons[]` entry.

## How this differs from the four existing authorities

| Surface | Question it answers | Reads | Writes | Grants readiness? |
|---|---|---|---|---|
| **capabilities** (this inventory) | "What can the kit do, in general?" | The capability manifest + its feeders (rules manifest, skill frontmatter, kit-source verbs, roadmap, status-claims) | Nothing | No |
| `seshat status` | "Where is THIS table in the readiness journey right now?" | Per-table `mappings/<table>/readiness-status.yaml` | Nothing | No (projects committed state verbatim) |
| `seshat next` | "What is the single next allowed action for THIS table?" | Per-table `readiness-status.yaml` | Nothing | No |
| `seshat doctor` | "Has the repo drifted from what the kit expects?" | Committed manifests/config for structural drift | Nothing | No |
| `retail check` | "Does the committed text pass the governance gate?" | Committed SQL/TMDL/PBIR/docs/git text | Nothing (exit code is the authority) | No (the gate itself, not a grant) |

The capability inventory is orthogonal to all four: it never reads or
computes a per-table readiness state, and none of the four existing
authorities' behavior, argparse surface, or exit code changes because this
feature exists. A reader who wants to know "what can this kit do in general"
reads `capabilities`; a reader who wants to know "where is table X right now"
reads `status`/`next`; a reader who wants "is the repo internally consistent"
reads `doctor`; a reader who wants "does my change pass the gate" reads
`check`.

## Superseded prose predecessors

`docs/quality/post-idea-bank-capability-state.md` and this repo's
`README.md` "What is built today" table are hand-narrated snapshots that
predate this manifest. They are frozen historical snapshots, not rewritten
here; this manifest is now the structured, testable authority for the same
question. A future doc edit may point readers here instead of duplicating the
list again.

## How to read it

Run the module (there is no CLI verb -- see `.claude/skills/capabilities/SKILL.md`):

```
python -m seshat.capability_inventory
python -m seshat.capability_inventory --format json
```
