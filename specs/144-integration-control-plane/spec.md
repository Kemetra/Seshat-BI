# Feature Specification: Integration control-plane convergence

**Feature Branch**: `144-integration-control-plane`

**Created**: 2026-08-07

**Status**: ratified -- Ahmed Shaaban, 2026-08-07

**Amended**: 2026-08-20 by spec 154 (issue #671) -- FR-010's **approval prompt**
clause is narrowed: the prompt no longer confers provisioning authorization. All
other FR-010 clauses and every other requirement in this spec are unchanged. See
FR-010 below and `specs/154-secure-provisioning-approval/spec.md`.

**Status history**: draft

**Input**: Official-first roadmap Phase 2: retain a thin compatibility facade
while making the catalog-backed planner, installer, validation, and lock path the
only operational integration authority.

## User Scenarios & Testing

### User Story 1 - One truthful installer (Priority: P1)

An operator using `seshat integrations setup` receives a plan or approved apply
result derived only from the catalog, compatibility policy, resolver, installer,
and lock pipeline.

**Why this priority**: Two independently maintained installers can disagree
about membership, versions, paths, safety gates, or what counts as installed.

**Independent Test**: Mutate catalog membership and prove both the CLI and the
legacy facade reflect the mutation without editing a second registry.

**Acceptance Scenarios**:

1. **Given** no lock and no live resolvers, **when** an operator plans, **then**
   the result is network-free, write-free, and identifies missing exact pins.
2. **Given** explicit apply plus injected exact resolvers, **when** the legacy
   facade is called, **then** it delegates to the catalog installer and returns a
   compatibility projection of the canonical result.
3. **Given** apply without exact resolvers, **when** the legacy facade is called,
   **then** it fails closed and writes nothing.

---

### User Story 2 - Preserve compatibility without duplicated truth (Priority: P2)

A downstream Python caller can continue importing the documented/exported
compatibility names from `seshat.integrations_setup`, but those names are derived
from or delegate to the canonical integration package.

**Why this priority**: Removing an import surface without consumer evidence is
unnecessary breakage; preserving the old installer behind that surface would
preserve the architectural defect.

**Independent Test**: Import every compatibility symbol, compare derived bundle
and pin data to catalog/policy data, and spy on planner/apply delegation.

**Acceptance Scenarios**:

1. **Given** the compatibility module, **when** its bundle coordinates and pins
   are inspected, **then** they equal values derived from catalog/policy sources.
2. **Given** a plan result, **when** it is projected through
   `IntegrationResult`, **then** canonical component IDs, categorical statuses,
   and details survive without a second membership list.

---

### User Story 3 - Validate official skill payloads canonically (Priority: P3)

An official GitHub skill bundle is considered present or installed only when its
catalog-declared required files exist.

**Why this priority**: The legacy installer checks required skill paths, while
the catalog installer currently trusts only a marker. Convergence must preserve
the stronger behavior in the canonical owner.

**Independent Test**: A clone or marked directory missing a required file is
refused and never reported present; complete content passes.

**Acceptance Scenarios**:

1. **Given** a clone missing a required skill, **when** installation validates
   staging, **then** activation fails and no installed marker is written.
2. **Given** a marked skill directory later missing a required file, **when** a
   plan runs, **then** it is not reported present.

## Edge Cases

- An unreadable integration lock remains a fail-closed result.
- Unknown profiles retain the existing `UnknownProfile` behavior.
- Existing MCP registrations are never silently replaced.
- Compatibility apply never creates live resolvers implicitly.
- Validation paths must be contained relative POSIX paths without `..`.
- A failed staged clone is removed without touching an existing target.
- This phase does not activate upstream skills in Claude or Codex.

## Requirements

### Functional Requirements

- **FR-001**: `src/seshat/integrations/catalog.py` MUST remain the sole source of
  integration membership, profiles, source types, channels, coordinates, and
  MCP classification.
- **FR-002**: Official GitHub skill components MUST declare their required
  payload paths in catalog metadata rather than in the compatibility facade.
- **FR-003**: Catalog validation paths MUST reject absolute, backslash, empty,
  and traversal-containing values.
- **FR-004**: The catalog installer MUST validate required payload paths before
  activating a staged GitHub clone and when deciding that an installed clone is
  present.
- **FR-005**: `seshat.integrations_setup` MUST contain no clone, MCP-write,
  runtime-provisioning, installed-state, or component-membership implementation.
- **FR-006**: The existing exported compatibility types, constants, prompt, and
  planner/apply/render aliases MUST remain importable unless exact repository
  evidence proves a symbol private.
- **FR-007**: Compatibility bundle coordinates, locations, required paths, and
  dbt pins MUST be derived from catalog/policy authorities.
- **FR-008**: Compatibility `setup_integrations` planning MUST delegate to the
  catalog-backed planner and project canonical component results.
- **FR-009**: Compatibility apply MUST require caller-supplied exact resolvers,
  delegate to the catalog-backed apply function, and never infer approval or
  enable network access itself.
- **FR-010**: The current CLI flags, approval prompt, exit-code behavior, JSON
  shape, workspace validation, and catalog-backed routing MUST survive.
  **AMENDED by spec 154 (issue #671), 2026-08-20 -- one clause narrowed.** The
  **approval prompt** clause no longer guarantees that the prompt (or the
  `--yes` flag that suppresses it) CONFERS AUTHORIZATION. The prompt may survive
  as a user-experience affordance, but provisioning authority now comes from a
  committed, named-human approval record read at HEAD; a caller-supplied flag,
  a TTY answer, or a stdin response is not authority. Rationale: this FR was a
  Phase-2 no-regression guarantee, not a trust-model endorsement -- FR-009 above
  already required that compatibility apply "never infer approval". The other
  five clauses of this FR (CLI flags exist, exit-code behavior, JSON shape,
  workspace validation, catalog-backed routing) are UNAMENDED and still bind.
  See `specs/154-secure-provisioning-approval/spec.md`, section "Amendment to
  Spec 144 FR-010".
- **FR-011**: Existing exact-version, isolation, non-clobbering MCP, lock, and
  compatibility-policy contracts MUST remain green.
- **FR-012**: Active installation documentation MUST describe the canonical
  `--refresh --apply` workflow and canonical machine-local locations.
- **FR-013**: No public skill, readiness state, generated bundle, dependency,
  lockfile, Power BI/dbt/Dagster execution adapter, or upstream activation path
  may change in this phase.

### Key Entities

- **Component**: Catalog-owned installable unit, extended with optional required
  payload paths for post-clone validation.
- **SetupOutcome / ComponentPlan**: Canonical plan/apply result.
- **IntegrationResult**: Compatibility-only projection of one canonical row.
- **Compatibility facade**: Import-preserving adapter with no operational truth.

## Success Criteria

- **SC-001**: A source search finds only one operational clone/install/MCP-write
  implementation for curated integrations.
- **SC-002**: All catalog and compatibility tests pass, including constructed
  delegation and invalid-payload cases.
- **SC-003**: Changing an official skill component's validation paths in the
  catalog changes both install validation and compatibility metadata without a
  second edit.
- **SC-004**: Compatibility apply without resolvers performs zero filesystem or
  subprocess mutation and returns a categorical failure.
- **SC-005**: Existing CLI, resolution, lock, install, public-surface, capability,
  and generated-bundle contracts remain green.
- **SC-006**: The complete diff contains only Phase 2 control-plane convergence,
  tests, active documentation, and Spec Kit artifacts.

## Out of Scope

- Power BI, dbt, or Dagster intent routing.
- Official skill discovery/activation.
- A shared upstream evidence envelope.
- Spec Kit re-vendoring or generic development skill rationalization.
- Dependency changes, generated bundle regeneration, deletion of public APIs,
  push, PR, merge, or publication.
