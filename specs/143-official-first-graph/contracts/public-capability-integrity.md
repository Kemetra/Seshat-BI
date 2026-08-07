# Contract: Public capability integrity

## Inputs

1. Shipped `skills[]` records from `distribution/public-command-surface.yaml`.
2. Capability records from `docs/capabilities/capabilities.yaml`.
3. The repository's Git-tracked file set.

## Required invariants

For every shipped public skill `S`:

1. If one or more capabilities explicitly declare
   `C.references.public_skill == S.name`, exactly one such capability is the
   owner.
2. Otherwise, exactly one `surface: skill` capability whose `references.skill`
   contains `S.name` is the owner.
3. The resolved `C.ownership.capability_owner` passes the existing ownership
   vocabulary gate.
4. `C.ownership.canonical_source` is a non-empty repository-relative path.
5. The path resolves inside the repository to a tracked regular file.
6. The path is not under `integrations/claude-code/seshat-bi/` or
   `integrations/codex/seshat-bi/`.

For every capability declaring `references.public_skill`:

7. The referenced name exists in the shipped public skill set.

For every capability declaring `ownership.canonical_source`, public or internal:

8. The source satisfies invariants 4 through 6 above.

## Findings

Findings are deterministic strings. Each finding names:

- the public skill when one is involved,
- the capability ID when one exists,
- the offending source path when source validation fails,
- the violated invariant in plain language.

The detector returns an empty list only when all invariants hold. It grants no
approval and has no readiness effect.

## Ownership records added by this feature

| Public skill | Capability ID | Current owner | Canonical source |
| --- | --- | --- | --- |
| `seshat-bi` | `seshat-bi-public-router` | `seshat-orchestrator` | `distribution/bundle-templates/shared/skills/seshat-bi/SKILL.md` |
| `powerbi-workflows` | `powerbi-workflows-public-router` | `seshat-orchestrator` | `distribution/bundle-templates/shared/skills/powerbi-workflows/SKILL.md` |

`powerbi-workflows` is intentionally classified from current behavior. Official
Microsoft execution delegation is a later phase and may change its relationship
only after the routing behavior exists.
