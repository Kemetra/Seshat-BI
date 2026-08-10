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
`publicly-released`. This is a TEST, not a `seshat check` rule: it fails CI
but adds no gate, no registered rule, and no `blocking_reasons[]` entry.

## How this differs from the four existing authorities

| Surface | Question it answers | Reads | Writes | Grants readiness? |
|---|---|---|---|---|
| **capabilities** (this inventory) | "What can the kit do, in general?" | The capability manifest + its feeders (rules manifest, skill frontmatter, kit-source verbs, roadmap, status-claims) | Nothing | No |
| `seshat status` | "Where is THIS table in the readiness journey right now?" | Per-table `mappings/<table>/readiness-status.yaml` | Nothing | No (projects committed state verbatim) |
| `seshat next` | "What is the single next allowed action for THIS table?" | Per-table `readiness-status.yaml` | Nothing | No |
| `seshat doctor` | "Has the repo drifted from what the kit expects?" | Committed manifests/config for structural drift | Nothing | No |
| `seshat check` | "Does the committed text pass the governance gate?" | Committed SQL/TMDL/PBIR/docs/git text | Nothing (exit code is the authority) | No (the gate itself, not a grant) |

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

## The ownership axis (spec 142)

Every entry carries an `ownership:` mapping answering **who owns this
capability** -- an upstream project, or Seshat. `capability_owner` is
**required**; an entry that has not been classified declares the
`unclassified` sentinel rather than omitting the field.

That requirement is the point. If absence were allowed, it would read three ways
at once -- not yet classified, deliberately unclassified, or "no upstream owner,
so this is Seshat's". The third reading is dangerous: mid-migration a wrapper
around a third-party MCP would look like Seshat's own code.

| `capability_owner` | Means |
| --- | --- |
| `official-upstream` | An upstream project is authoritative; Seshat references or configures it. |
| `seshat-adapter` | Seshat gates or governs an upstream capability without reimplementing it. **Requires a non-empty `seshat_delta`.** |
| `seshat-governance` | Readiness gates, approvals, evidence, drift/lint checks, registries. Judges or records; produces no artifact. |
| `seshat-authoring` | Generates or scaffolds an artifact (DAX, theme JSON, blank templates, compiled output). Produces rather than judges. |
| `seshat-domain-knowledge` | BI/SQL/DAX/Python/retail reasoning no upstream tool owns. |
| `seshat-orchestrator` | Sequences Seshat's own verbs and stops at human seams. |
| `seshat-product-module` | An executable Seshat engine -- runs code rather than encoding reasoning. |
| `vendored-upstream` | Upstream content committed into this repo; `update_policy` carries the justification and re-vendor path. |
| `human-deliverable` | An artifact a person produces outside any tool. |
| `specified-not-built` | A ratified or drafted spec with no implementation yet. |
| `unclassified` | Explicitly not yet classified; the reason belongs in `overlap_note`. |

Optional sub-fields: `upstream_project`, `upstream_surface` (one of `plugin`,
`mcp`, `skill`, `cli`, `library`, `format`), `upstream_reference`,
`seshat_delta`, `canonical_source`, `overlap_note`, `update_policy`.

**`seshat_delta` is required of every upstream-backed `seshat-*` owner**, not
only `seshat-adapter` (spec 152 FR-001). Declaring `upstream_project` on any
`seshat-` token -- `seshat-governance`, `seshat-orchestrator`, `seshat-authoring`,
and the rest -- obliges the entry to state what Seshat adds on top; a blank
delta is absent, never a valid declaration. `official-upstream` and
`vendored-upstream` are **exempt from the requirement, not forbidden** a delta --
`claude-code-plugin` is `official-upstream` and usefully records that Seshat
authors the bundle contents while the plugin format stays upstream's. An
internal `seshat-*` entry with no `upstream_project` keeps its existing
contract.

Where `src/seshat/integrations/catalog.py` already declares an installable
upstream component, `upstream_reference` matches the coordinate declared there --
the catalog stays authoritative, and this axis points at it rather than restating
it. Bundle destination paths are **not** restated here either; they belong to
`distribution/public-knowledge-allowlist.yaml`.

**Validation lives in the oracle, not in a gate.** `seshat check` grows no rule
from this axis. `tests/unit/_capability_oracle.py` checks the token sets and the
adapter-delta requirement, and no ownership value may be a bare number or carry
a field name containing `score`/`maturity`/`confidence`/`completeness`/`health`
-- the kit never fabricates a confidence score, and this axis is exactly where
that temptation would appear.

## Public skill ownership and canonical sources (spec 143)

Every shipped skill in `distribution/public-command-surface.yaml` resolves to
exactly one capability. An explicit `references.public_skill` edge wins. When
there is no explicit edge, the oracle accepts only one same-named
`surface: skill` capability whose `references.skill` contains that public name.
This precedence prevents a CLI entry that merely calls a skill from becoming
its accidental owner, and ambiguity fails closed.

The public surface remains the distribution feeder; the capability manifest
records ownership rather than copying the bundle definition. Every declared
`ownership.canonical_source` must be a Git-tracked, regular, non-symlink file at
a repository-relative path. A generated Claude or Codex bundle path cannot be
canonical: deterministic bundle projections remain valid outputs, while their
authored bundle template or repository skill remains the source of truth.

`powerbi-workflows` owns the Seshat routing decision, readiness/business-semantic
pre-gates, and post-execution validation. Microsoft's official
`powerbi-report-design` and `powerbi-report-authoring` skills own their native
design and report-authoring mechanics once the exact capability is proven
discoverable through the closed-world firewall. The broader Power BI plugin is
not activated as a unit: planning, management, semantic-authoring overlap, and
its default-write moving MCP coordinate remain incompatible. Seshat's four
bounded PBIR writers are a temporary reviewed gap recorded in
`upstream-gaps.yaml`, not a competing general report-authoring implementation.

## How to read it

Run the module (there is no CLI verb -- see `.claude/skills/capabilities/SKILL.md`):

```
python -m seshat.capability_inventory
python -m seshat.capability_inventory --format json
```
