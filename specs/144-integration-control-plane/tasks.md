# Tasks: Integration control-plane convergence

**Spec**: `specs/144-integration-control-plane/spec.md`

**Plan**: `specs/144-integration-control-plane/plan.md`

**Status**: Ratified -- Ahmed Shaaban, 2026-08-07; Phase 2 implementation authorized

## Phase 1 - Baseline and red contracts

- [x] T001 Record the 88-test baseline, bundle drift, static gate, and clean generated roots in `evidence/baseline.md`.
- [x] T002 [US2] Add failing tests proving compatibility metadata derives from catalog/policy and plan/apply delegate to canonical functions.
- [x] T003 [P] [US3] Add failing catalog/installer tests for invalid validation paths, incomplete marked targets, and incomplete staged clones.
- [x] T004 [US1] Add a structural test that the facade contains no operational installer implementation or component registry.

## Phase 2 - Canonical validation metadata

- [x] T005 [US3] Add validated `Component.required_paths` metadata to `catalog.py` and populate the two official skill bundles.
- [x] T006 [US3] Make canonical installed-state and staged-clone validation consume only `required_paths`.

## Phase 3 - Thin compatibility facade

- [x] T007 [US2] Derive legacy bundle constants and dbt pin strings from catalog/policy authorities.
- [x] T008 [US1] Replace legacy planning/apply implementation with canonical delegation and `IntegrationResult` projection.
- [x] T009 [US1] Preserve CLI/import compatibility, including fail-closed apply without caller-supplied resolvers.
- [x] T010 Update the active installation document to the canonical `--refresh --apply` workflow and locations.

## Phase 4 - Exit gates and closeout

- [x] T011 Run the five focused integration modules and record exact results in `evidence/validation.md`.
- [x] T012 [P] Run capability, public-surface, and generated-bundle focused contracts.
- [x] T013 Run bundle drift, generated-root diff, `seshat check`, and `git diff --check`.
- [x] T014 Review the complete diff against the Phase 2 allowlist and record `evidence/scope-review.md`.
- [x] T015 Update the ratification ledger, keep status `ratified` until landing on `main`, clear the active Spec Kit fence, and rerun lifecycle contracts.

## Dependencies

```text
Ratification -> T001-T004 -> T005-T006 -> T007-T010 -> T011-T014 -> T015
```

## Explicitly not tasks

- Upstream discovery/activation, domain routing, evidence envelopes, re-vendoring,
  generic skill cleanup, dependency changes, bundle generation, push, PR, merge,
  or publication.
