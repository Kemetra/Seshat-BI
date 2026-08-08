# Feature Specification: Public capability graph integrity

**Feature Branch**: `143-official-first-graph`

**Created**: 2026-08-07

**Status**: ratified -- Ahmed Shaaban, 2026-08-07

**Status history**: draft

**Input**: Phase 1 of the official-first integration rationalization program:
make every shipped public skill resolve to exactly one owned capability with a
real authored canonical source, while preserving runtime and bundle behavior.

## Why this exists

Seshat's capability manifest classifies all 102 current capability entries by
owner, and its generated agent bundles are already deterministic. The two
control planes are not yet closed over one another: a skill can ship in the
public command surface without a capability link, and a linked capability can
name a canonical source that does not exist.

Current `main` demonstrates both failures. Same-name public skills normally
resolve through a unique `surface: skill` capability's `references.skill`;
portable wrappers whose name differs use `references.public_skill`. The shipped
`seshat-bi` and `powerbi-workflows` skills resolve through neither relationship,
while `pbi-mcp-doctor` links correctly but names a nonexistent canonical source.
Existing contracts pass because no contract reconciles these facts.

This feature closes that integrity boundary. It changes control-plane metadata
and fail-closed contracts only. It does not change what any public skill says or
does.

## User Scenarios & Testing

### User Story 1 - Resolve a shipped skill to its owner (Priority: P1)

A maintainer inspecting any skill in the public command surface can follow one
machine-checkable link to one capability and see its explicit responsibility
owner and authored canonical source.

**Why this priority**: Official-first routing is unsafe if a shipped front door
has no declared owner or has multiple competing owners.

**Independent Test**: Enumerate the public skills and reconcile them with the
capability manifest. Every public skill must produce exactly one match, whose
owner is declared and whose canonical source is a tracked authored file.

**Acceptance Scenarios**:

1. **Given** the committed public surface and capability manifest, **when** the
   ownership reconciliation runs, **then** all 21 shipped public skills resolve
   to exactly one capability.
2. **Given** a public skill with no capability link, **when** validation runs,
   **then** it fails and names the unowned public skill.
3. **Given** two capabilities linked to the same public skill, **when** validation
   runs, **then** it fails and names the ambiguous public skill and capabilities.

---

### User Story 2 - Trust the canonical source (Priority: P1)

A contributor can trust that a public capability's canonical source is the
authored input, not a missing path, directory, or generated bundle projection.

**Why this priority**: A nonexistent or generated source makes maintenance and
upstream delegation ambiguous even when ownership metadata is otherwise valid.

**Independent Test**: Mutate an in-memory capability to point to each invalid
source class and prove validation rejects it without changing repository files.

**Acceptance Scenarios**:

1. **Given** a linked public capability whose canonical source does not exist,
   **when** validation runs, **then** it fails and names the capability and path.
2. **Given** a linked public capability whose canonical source is a generated
   Claude or Codex bundle file, **when** validation runs, **then** it fails and
   explains that generated output cannot be canonical.
3. **Given** a linked public capability whose canonical source is an authored,
   tracked file, **when** validation runs, **then** it passes this integrity gate.

---

### User Story 3 - Preserve current distribution behavior (Priority: P2)

An existing Claude Code or Codex user receives byte-identical generated bundles
and unchanged commands after the ownership graph is repaired.

**Why this priority**: This phase establishes control-plane truth; executor and
router changes belong to later phases of the program.

**Independent Test**: Run public-surface, capability, plugin, and deterministic
bundle checks before and after the change and compare generated outputs.

**Acceptance Scenarios**:

1. **Given** the repaired ownership graph, **when** bundle drift validation runs,
   **then** both generated bundles still match their reviewed inputs.
2. **Given** the repaired ownership graph, **when** the public command-surface
   contracts run, **then** the same commands, aliases, skills, and server remain.

### Edge Cases

- A `references.public_skill` value not present in the public surface is rejected
  rather than silently treated as an internal skill.
- A public skill reference with a blank or non-string value is rejected by the
  existing manifest shape rules.
- A canonical source using an absolute path or escaping the repository is
  rejected before filesystem resolution.
- A canonical source that exists but is not a regular tracked file is rejected.
- Generated destinations remain legitimate projections; they are rejected only
  when claimed as the authored canonical source of a public capability.
- Multiple public commands may route to the same public skill; ownership remains
  one capability per skill, not one capability per command alias.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST derive the set of shipped public skills from the
  existing public command-surface manifest rather than maintaining a second list.
- **FR-002**: Every shipped public skill MUST resolve to exactly one capability:
  first through one explicit `references.public_skill` owner when present,
  otherwise through one same-name `surface: skill` capability whose
  `references.skill` includes that public name.
- **FR-003**: Validation MUST reject both zero-match and multiple-match public
  skill ownership and MUST identify the affected skill and capability IDs.
- **FR-004**: Every capability linked to a shipped public skill MUST carry a
  valid existing `ownership.capability_owner` value under the existing closed
  ownership vocabulary.
- **FR-005**: Every capability linked to a shipped public skill MUST declare one
  non-empty, repository-relative `ownership.canonical_source`.
- **FR-006**: Every declared canonical source, whether or not its capability is
  public, MUST resolve inside the repository to a tracked regular file.
- **FR-007**: A generated Claude Code or Codex bundle destination MUST NOT be
  accepted as a capability canonical source.
- **FR-008**: An explicit `references.public_skill` value that names no shipped
  public skill MUST fail validation as a stale ownership link. Internal
  `references.skill` values remain valid and are considered ownership candidates
  only when they match a shipped public name on a `surface: skill` capability.
- **FR-009**: The shipped `seshat-bi` and `powerbi-workflows` skills MUST gain
  explicit capability entries stating their current routing responsibilities,
  owners, canonical sources, and Seshat-specific deltas where applicable.
- **FR-010**: `pbi-mcp-doctor` MUST name its real authored bundle-template source
  as canonical; its generated projections MUST remain destinations only.
- **FR-011**: Enforcement MUST extend the existing capability/public-surface
  contract architecture and MUST NOT introduce a parallel ownership registry or
  a new runtime gate.
- **FR-012**: This feature MUST NOT change public skill content, CLI behavior,
  integration installation, MCP configuration, readiness policy, dependencies,
  or generated bundle bytes.
- **FR-013**: Validation errors MUST be deterministic and specific enough for a
  contributor to identify the offending public skill, capability, and source.

### Key Entities

- **Public skill**: A shipped skill record in the existing public command-surface
  manifest, independent of how many commands or aliases route to it.
- **Capability entry**: The existing manifest record that declares lifecycle,
  surface, ownership, references, and responsibility.
- **Ownership link**: Either an explicit `references.public_skill` relationship,
  or the unique same-name `surface: skill` relationship used by canonical public
  skills.
- **Canonical source**: The tracked authored repository file from which a public
  capability is maintained; generated bundle files are projections, not sources.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All 21 currently shipped public skills resolve to exactly one
  capability owner, with zero missing and zero ambiguous ownership links.
- **SC-002**: All canonical sources declared by capabilities resolve to
  tracked authored files, with zero missing, escaping, directory, or generated
  paths accepted.
- **SC-003**: Mutation tests prove each fail-closed condition: missing link,
  duplicate link, stale link, missing source, untracked source, and generated
  source.
- **SC-004**: The deterministic bundle check passes without regeneration and the
  generated Claude Code and Codex bundles remain byte-identical to baseline.
- **SC-005**: Focused capability and public-surface contract suites pass with no
  changes to the 20-command, 4-alias, 21-skill, 1-server public surface.
- **SC-006**: A maintainer can answer owner and canonical source for any shipped
  public skill using only the two existing manifests and their enforced link.

## Non-goals

- No Power BI, dbt, or Dagster execution delegation or router consolidation.
- No integration catalog or legacy installer convergence.
- No evidence-envelope design.
- No official-skill activation or upgrade work.
- No skill, command, MCP, plugin, or generated bundle deletion.
- No new readiness stage, approval, score, CLI command, dependency, or registry.

## Assumptions

- `distribution/public-command-surface.yaml` remains authoritative for what ships
  in the public agent bundles.
- `docs/capabilities/capabilities.yaml` remains authoritative for capability
  identity and ownership.
- Existing ownership-vocabulary validation remains the authority for allowed
  owner tokens; this feature composes it rather than duplicating it.
- The current public-surface count is a baseline assertion, not a permanent
  architectural limit; future additions are valid when they satisfy the same
  ownership and source contract.
- Ratification authorizes implementation of this phase only. Later roadmap
  phases require their own truth check and, where required, their own spec.
