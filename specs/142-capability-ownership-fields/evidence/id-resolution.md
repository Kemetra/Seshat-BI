# T004 -- skill name to manifest `id` resolution

**Why this exists**: audit and spec prose names capabilities by *skill name*, which
is not always the manifest `id`. SC-003 requires every later task to edit by
**resolved `id`**, never by skill-name match. Resolved against
`docs/capabilities/capabilities.yaml` at `ce66dc6`.

---

## Resolution table

| Prose name | Manifest `id` | Note |
| --- | --- | --- |
| `dbt-transformation-adapter` | `dbt-transformation-adapter` | exact |
| `dagster-orchestration-adapter` | `dagster-orchestration-adapter` | exact |
| `pbi-mcp-doctor` | `pbi-mcp-doctor` | exact |
| **`pbir-authoring-adapter`** | **`pbir-authoring-adapter-skill`** | ⚠ **no exact id** -- see Trap 1 |
| `friendly-pr-reviewer` | `friendly-pr-reviewer` | exact |
| `pr-readiness-reviewer` | `pr-readiness-reviewer` | exact |
| `release-notes-generator` | `release-notes-generator` | exact |
| `showcase-build` | `showcase-build` | exact |
| `powerbi-dashboard-design` | `powerbi-dashboard-design` | exact, but see Trap 2 |
| **`powerbi-workflows`** | **(none)** | ⚠ **not a manifest entry** -- see Trap 3 |
| `governed-statistical-core` | `governed-statistical-core` | exact |
| `claude-code-plugin` | `claude-code-plugin` | exact |

## Trap 1 -- `pbir-authoring-adapter` has no entry of its own

The bare name is a `references.skill` **value on five entries**:

```
pbir-apply-theme
pbir-format-visual
pbir-set-page-background
pbir-set-geometry
pbir-authoring-adapter-skill   <-- the actual skill entry
```

A name-match edit would have written ownership onto **four CLI verbs** that merely
reference the skill. **T023 targets `pbir-authoring-adapter-skill` only.**

The four `pbir-*` CLI verbs are separate capabilities needing their own
classification in Phase 4 -- they write an upstream-owned format (PBIR) but gate no
upstream *capability*, so `seshat-adapter` does not fit them cleanly. Flagged for
T042.

## Trap 2 -- `powerbi-dashboard-design` is also a shared `references.skill`

It is an exact `id`, but the same string is a `references.skill` value on three
other entries: `pbir-validate-blueprint`, `pbir-validate-bindings`,
`tmdl-doc-comment-lint`. Edit the entry whose `id` matches; leave the referencing
entries to their own classification.

## Trap 3 -- `powerbi-workflows` is not a tracked capability (new finding)

`docs/capabilities/ownership-audit.md` named `powerbi-workflows` as a MERGE
candidate against `powerbi-dashboard-design`. Verified state:

- **No manifest entry** -- no `id`, no `references.skill` value.
- **No `.claude/skills/powerbi-workflows/`** source directory.
- **It DOES ship**: `integrations/claude-code/seshat-bi/skills/powerbi-workflows/`
  exists in the built bundle.
- Its only manifest trace is prose inside `claude-code-plugin`'s `summary`
  (`capabilities.yaml:1402`), which calls it "the guarded powerbi-workflows
  routing skill".

So a **shipped** skill has no capability entry of its own. That is a manifest
coverage gap, not an ownership question, and it is **out of scope** for spec 142 --
this axis classifies entries that exist; it does not create them.

Recorded here so the audit's MERGE row is understood as comparing an entry
against a non-entry. Worth its own look.

## Consequence for the task list

- **T023** edits `pbir-authoring-adapter-skill`, not `pbir-authoring-adapter`.
- **T041/T042** must classify the four `pbir-*` CLI verbs on their own terms.
- The audit's `powerbi-dashboard-design` / `powerbi-workflows` MERGE row cannot be
  actioned through this axis; `powerbi-workflows` has nothing to carry a token.
