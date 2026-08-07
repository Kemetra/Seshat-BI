# Data model: Public capability graph integrity

## PublicSkill

Source: `distribution/public-command-surface.yaml` `skills[]` records whose
`status` is `shipped`.

Relevant fields:

- `name`: stable public identity
- `wrapper_template`: reviewed authored distribution input
- `bundle_destination`: generated projection path
- `platforms`: supported generated bundles

## Capability

Source: `docs/capabilities/capabilities.yaml` `capabilities[]`.

Relevant fields:

- `id`: stable capability identity
- `ownership.capability_owner`: closed responsibility owner token
- `ownership.canonical_source`: authored tracked source
- `ownership.seshat_delta`: required by the existing rule for adapters
- `references.public_skill`: optional link to one shipped public skill

## OwnershipEdge

Resolution relationship:

```text
PublicSkill.name
  -> exactly one explicit Capability.references.public_skill, when present
  -> otherwise exactly one surface: skill Capability.references.skill
```

For shipped public skills the resolved relationship is total and one-to-one.
Multiple commands and aliases may still route to the same `PublicSkill`; their
CLI references do not add ownership edges.

## CanonicalSource

A path value belonging to any capability. When declared, it must be:

- a non-empty repository-relative path,
- contained within the repository after resolution,
- a regular file,
- tracked by Git,
- outside generated Claude/Codex bundle roots.

Every capability linked to a shipped public skill must declare one; other
capabilities may omit the optional field, but cannot declare an invalid value.

## Invalid states

- Public skill has zero ownership edges.
- Public skill has more than one ownership edge.
- Explicit public capability edge names no shipped public skill.
- Linked capability has an invalid/missing owner.
- Linked capability has an absent, escaping, untracked, non-file, or generated
  canonical source.
