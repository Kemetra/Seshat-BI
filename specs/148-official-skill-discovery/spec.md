# Feature Specification: Official skill discovery

**Feature Branch**: `148-official-skill-discovery`

**Created**: 2026-08-07

**Status**: ratified -- Phase 6 implementation complete

**Ratification**: Ahmed Shaaban authorized Phase 6 implementation on 2026-08-07.

**Input**: Official-first roadmap Phase 6: distinguish official skill packages
that were obtained from packages that are activated and discoverable in a
supported agent harness.

## User Scenarios & Testing

### User Story 1 - Truthful installation state (Priority: P1)

An operator can inspect Microsoft/Fabric, dbt Labs, and Dagster skill packages
and see separate installed, activated, and discoverable facts. A clone alone
never produces a discoverable verdict.

### User Story 2 - Supported harness route (Priority: P2)

For Claude Code and Codex, each supported official package names the upstream-
supported or host-supported activation route, expected skill identity, and the
read-only proof that confirms discovery. Unsupported combinations block with a
specific reason instead of guessing.

### User Story 3 - Preserve upstream ownership (Priority: P3)

Activation points at exact locked upstream content or the upstream native
plugin. Seshat does not copy upstream instructions into its canonical skills or
claim the upstream package as Seshat-authored.

## Requirements

- **FR-001**: The integration control plane MUST represent `installed`,
  `activated`, and `discoverable` as separate facts for official skill bundles.
- **FR-002**: Catalog-backed activation metadata MUST cover `fabric-skills`,
  `dbt-agent-skills`, and `dagster-agent-skills` without a second registry.
- **FR-003**: Every supported Claude Code/Codex combination MUST name its
  activation mechanism, expected discovered skill identities, and proof method.
- **FR-004**: Native upstream plugin installation MUST be preferred when the
  upstream project publishes a compatible plugin marketplace.
- **FR-005**: A projection route MAY be used only where the harness and upstream
  Agent Skills layout support it; it MUST retain provenance and MUST NOT copy
  content into Seshat canonical ownership.
- **FR-006**: Detection MUST be read-only. Global plugin/skill configuration
  MUST NOT be changed by a normal plan or discovery check.
- **FR-007**: Any activation action MUST remain behind the existing explicit
  `--refresh --apply` and confirmation boundary or be reported as a named
  operator action when the harness owns installation.
- **FR-008**: A stale, missing, ambiguous, or mismatched activation MUST fail
  closed and MUST NOT be written to the lock as discoverable.
- **FR-009**: Upgrade guidance MUST explain how activation follows a new locked
  upstream version without producing an independently maintained copy.
- **FR-010**: Existing MCP registration, runtime adapters, readiness state,
  generated Seshat bundles, dependencies, and execution behavior MUST remain
  unchanged.

## Success Criteria

- Plan and machine-readable output distinguish the three lifecycle facts.
- Microsoft/Fabric, dbt, and Dagster each have a mechanically validated
  discovery route for every harness Seshat declares supported.
- Unsupported or unverified harness combinations remain explicit blockers.
- Focused catalog, installer, lock, CLI, and public-routing contracts pass.
- No official `SKILL.md` content is copied into a Seshat canonical directory.

## Out of Scope

Official executor result envelopes (Phase 7), upgrade/re-vendor automation
(Phase 8), generic development skill cleanup, runtime execution, global user
configuration mutation during tests, dependency changes, readiness mutation,
deletion, merge, release, or publication.
