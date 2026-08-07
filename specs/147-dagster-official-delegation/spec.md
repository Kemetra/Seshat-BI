# Feature Specification: Dagster official delegation

**Feature Branch**: `147-dagster-official-delegation`

**Created**: 2026-08-07

**Status**: ratified -- Phase 5 implementation authorized by Ahmed Shaaban on 2026-08-07

**Input**: Official-first roadmap Phase 5: delegate generic Dagster competence
to Dagster's official skills while preserving Seshat's governed orchestration.

## User Scenarios & Testing

### User Story 1 - Unambiguous Dagster identities (Priority: P1)

An integration plan distinguishes Seshat's bundled `dagster-workflows` router
from the official `dagster-io/skills` payload without using one component ID
for two different owners.

### User Story 2 - One truthful Dagster front door (Priority: P2)

An agent entering through `dagster-workflows` routes generic asset, schedule,
sensor, project, CLI, and troubleshooting intent to Dagster's official skill,
while Seshat-governed runs retain their existing gates and evidence seam.

### User Story 3 - Preserve fail-closed activation truth (Priority: P3)

The official skill can be cataloged and installed, but no route calls it usable
until Phase 6 proves supported-harness activation and discovery.

## Requirements

- **FR-001**: The catalog MUST distinguish the bundled Seshat workflow router
  from the official Dagster skill package with separate stable identifiers.
- **FR-002**: The official package MUST use the allowlisted authoritative
  `dagster-io/skills` repository and validate its `dagster-expert` payload.
- **FR-003**: Existing callers of the legacy bundled `dagster-skills` component
  lookup MUST retain a thin compatibility resolution without keeping that
  ambiguous ID in current profile membership or lock output.
- **FR-004**: Generic Dagster authoring, project mechanics, automation, CLI
  guidance, and troubleshooting MUST delegate to the official skill.
- **FR-005**: Governed medallion execution MUST remain through
  `seshat dagster`, with all existing readiness gates, stopped automations,
  closed argv, redaction, fail-closed propagation, and derived evidence.
- **FR-006**: The capability manifest MUST record the official skill owner and
  the concrete Seshat orchestration delta separately.
- **FR-007**: Official skill activation/discovery MUST remain deferred to
  Phase 6; installed MUST NOT imply activated or discoverable.
- **FR-008**: No Dagster runtime, graph, job, schedule, sensor, pin, dependency,
  evidence schema, readiness state, or live execution behavior may change.
- **FR-009**: Canonical public-skill changes MUST converge deterministically
  into Claude and Codex bundles.

## Success Criteria

- The orchestration profile contains separate official-skill and Seshat-router
  component IDs with accurate source ownership.
- The public intent table names Seshat pre-gates, the Dagster execution owner,
  and Seshat evidence/post-validation.
- Generic Dagster competence routes upstream without copied official guidance.
- Existing focused integration and Dagster runtime tests remain green.

## Out of Scope

Official skill activation/discovery, live Dagster or database execution,
runtime refactoring, graph changes, version/dependency changes, evidence-envelope
work, readiness mutation, deletion, push, PR, merge, or publication.
