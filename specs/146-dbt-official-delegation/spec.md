# Feature Specification: dbt official delegation

**Feature Branch**: `146-dbt-official-delegation`

**Created**: 2026-08-07

**Status**: ratified -- Phase 4 implementation authorized by Ahmed Shaaban on 2026-08-07

**Input**: Official-first roadmap Phase 4: make dbt Labs the explicit owner of
generic dbt execution semantics while preserving Seshat's governed adapter.

## User Scenarios & Testing

### User Story 1 - One truthful dbt front door (Priority: P1)

An agent entering through `dbt-workflows` can distinguish a Seshat-governed
shadow build from generic dbt authoring, command help, documentation lookup, or
troubleshooting and route each intent to the correct owner.

### User Story 2 - Preserve the Seshat gate around governed execution (Priority: P2)

For a governed Seshat build, the existing wrapper still checks Mapping Ready,
source-map citations, immutable plan identity, shadow schemas, redaction, locks,
parity, and evidence while invoking the official dbt executable for native work.

### User Story 3 - Keep unresolved activation honest (Priority: P3)

Official dbt skills and MCP are represented as upstream capabilities, but no
route claims them usable until Phase 6 proves supported-harness discovery.

## Requirements

- **FR-001**: `dbt-workflows` MUST remain the broad governed dbt front door.
- **FR-002**: Generic dbt model authoring, tests, command syntax, documentation
  lookup, and troubleshooting MUST delegate to dbt Labs official agent skills.
- **FR-003**: Native compile/build/test/run/show semantics MUST remain owned by
  dbt Core/dbt MCP, not restated as Seshat behavior.
- **FR-004**: Governed Seshat execution MUST continue through `seshat dbt` so
  Mapping Ready, accepted-plan, selector, shadow-schema, redaction, lock,
  artifact, parity, and evidence contracts cannot be bypassed.
- **FR-005**: Seshat's source-map-derived scaffold and `meta.seshat`/parity
  contracts MUST remain Seshat-owned deltas.
- **FR-006**: Official skills/MCP MUST be explicit capability owners with honest
  activation/discovery state.
- **FR-007**: Live compile/parity and named compatibility attestation MUST remain
  blocked exactly as recorded; this phase MUST NOT fabricate activation.
- **FR-008**: No runtime command, dependency, pin, evidence schema, readiness
  state, integration activation, or migration-default behavior may change.
- **FR-009**: Canonical public-skill changes MUST converge deterministically into
  Claude and Codex bundles.

## Success Criteria

- The dbt intent table names Seshat pre-gate, official executor, and Seshat
  evidence/post-validation for governed execution.
- Generic dbt competence points to official dbt Labs skills, not copied guidance.
- Capability metadata distinguishes the Seshat adapter, official agent skills,
  dbt Core, and dbt MCP.
- Existing focused dbt/runtime tests remain green and no deletion occurs.

## Out of Scope

Official skill activation/discovery, live database execution, parity attestation,
runtime refactoring, evidence-envelope work, dependency changes, deletions,
push, PR, merge, or publication.
