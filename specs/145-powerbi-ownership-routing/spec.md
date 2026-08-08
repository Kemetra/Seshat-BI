# Feature Specification: Power BI ownership and routing

**Feature Branch**: `145-powerbi-ownership-routing`

**Created**: 2026-08-07

**Status**: ratified -- Ahmed Shaaban, 2026-08-07

**Input**: Official-first roadmap Phase 3: make Power BI intent routing explicit
without deleting Seshat governance, inspection, or bounded safety adapters.

## User Scenarios & Testing

### User Story 1 - Route each Power BI intent to one executor (Priority: P1)

An agent entering through `powerbi-workflows` can determine the Seshat pre-gate,
the authoritative executor, and the Seshat post-validation for report authoring,
semantic-model editing, published querying, bounded formatting, and inspection.

**Independent Test**: Each supported intent produces one categorical routing
decision and names its prerequisites and validation boundary.

### User Story 2 - Preserve Seshat's governance delta (Priority: P2)

Seshat continues to own metric contracts, readiness, design judgment, evidence,
PBIP inspection, and deterministic bounded PBIR transformations while official
Microsoft surfaces own native execution mechanics.

**Independent Test**: Capability metadata and public skills distinguish design,
governance, bounded local mutation, and official execution.

### User Story 3 - Fail closed before official report authoring (Priority: P3)

An agent requesting native report-page authoring receives the official Microsoft
report-authoring route only after the governed dashboard design is ready. If the
official skill is not discoverable, the result names the integration gap rather
than silently emulating it.

**Independent Test**: Report authoring is blocked without dashboard readiness
and never routes through the semantic-model MCP or the bounded formatting adapter.

## Requirements

- **FR-001**: `powerbi-workflows` MUST remain the broad public Power BI router.
- **FR-002**: `powerbi-dashboard-design` MUST be represented as a nested design
  router, not a second broad execution router.
- **FR-003**: `seshat pbi-mcp doctor` MUST remain the machine-checkable execution
  owner selector/preflight used for execution-shaped intents.
- **FR-004**: Native report-page authoring MUST route to Microsoft's official
  `powerbi-report-authoring` skill after `dashboard_ready: pass`.
- **FR-005**: Semantic-model editing MUST remain gated on
  `semantic_model_ready: pass` and route to Microsoft's modeling surface.
- **FR-006**: Published semantic-model querying MUST route to Microsoft's remote
  Power BI MCP/consumption surface.
- **FR-007**: The bounded PBIR adapter MAY remain for its allow-listed,
  deterministic, binding-preserving, no-publish delta.
- **FR-008**: PBIP inspection, readiness, metric governance, design reasoning,
  evidence, and post-execution validation MUST remain Seshat-owned.
- **FR-009**: F016 MUST describe live semantic-model connection, refresh, query,
  or publish execution; it MUST NOT claim all PBIR authoring is deferred.
- **FR-010**: This phase MUST NOT activate upstream skills, unpark F016, execute
  live Microsoft operations, delete compatibility surfaces, or introduce the
  Phase 7 evidence envelope.
- **FR-011**: Canonical public-skill changes MUST converge deterministically into
  Claude and Codex bundles.

## Success Criteria

- Every important Power BI intent has one documented pre-gate, executor, and
  post-validation path.
- Report authoring and semantic-model editing are distinct official routes.
- No broad router ambiguity remains in capability metadata or public guidance.
- Focused recommender, capability, public-surface, and bundle tests pass.
- The complete diff stays inside Phase 3.

## Out of Scope

Official skill activation/discovery implementation, live Power BI execution,
F016 activation, common evidence schemas, dbt/Dagster routing, dependencies,
push, PR, merge, or publication.
