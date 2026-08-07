# Phase 2 scope review

**Reviewed**: 2026-08-07

**Verdict**: PASS. The implementation stays within Spec 144's control-plane
convergence boundary.

## Product and documentation changes

- `src/seshat/integrations/catalog.py`: adds contained, validated
  `required_paths` component metadata and declares the existing Microsoft and
  dbt official-skill payload requirements.
- `src/seshat/integrations/installer.py`: consumes only catalog metadata when
  checking installed GitHub components and staged clones.
- `src/seshat/integrations_setup.py`: retains the shipped import surface as a
  catalog-derived projection and removes independent clone, MCP-write,
  runtime-provisioning, installed-state, coordinate, and membership behavior.
- `docs/install/fabric-powerbi-integrations.md`: documents the canonical
  `--refresh --apply` gates and machine-local layout.

## Contract changes

- `tests/unit/test_curated_stack_cli.py`: validates required-path construction
  and official bundle declarations.
- `tests/unit/test_curated_stack_install.py`: proves incomplete marked and
  staged official bundles fail closed.
- `tests/unit/test_integrations_setup.py`: replaces retired legacy-installer
  implementation tests with facade delegation, compatibility, and CLI routing
  contracts. Operational installer coverage remains in the four canonical
  curated-stack modules.

## Governance-only files

- `.specify/feature.json`, `AGENTS.md`, and `CLAUDE.md` carry the temporary
  active-plan pointer and are cleared during closeout.
- `specs/144-integration-control-plane/` contains only the ratified lifecycle
  artifacts and recorded evidence.

## Explicit absence of scope creep

- No capability manifest, public skill, router, readiness state, dependency,
  package lock, CI workflow, MCP example, or execution adapter changed.
- No generated Claude/Codex/plugin output changed or was regenerated.
- No upstream integration was installed, activated, or contacted by apply.
- No file was deleted; the externally consumable compatibility facade remains.
- No push, PR, merge, release, or publication occurred.

The net product diff removes an independently maintained operational installer
while preserving its stronger payload validation in the canonical catalog and
installer. This satisfies the phase exit gate without entering later routing,
activation, evidence-envelope, or re-vendoring phases.
