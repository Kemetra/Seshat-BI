# Implementation Plan: Integration control-plane convergence

**Branch**: `144-integration-control-plane` | **Date**: 2026-08-07 | **Spec**: `specs/144-integration-control-plane/spec.md`

**Status**: ratified -- Ahmed Shaaban, 2026-08-07; Phase 2 implementation authorized

## Summary

Phase 2 is REQUIRED. The shipped CLI already uses
`seshat.integrations.catalog` plus `installer.plan/apply`, but
`seshat.integrations_setup` still independently defines official skill bundles,
fallback MCP versions, clone/install behavior, MCP writes, runtime detection,
and Dagster provisioning. Replace that operational duplicate with a thin,
import-preserving facade. Move the one stronger legacy behavior -- required
skill-file validation -- into catalog metadata and the canonical installer.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: stdlib, PyYAML only through unrelated surfaces; no new dependency

**Storage**: Existing gitignored `.seshat/integrations/` lock, env, skill, node, and staging paths

**Testing**: pytest unit and contract tests

**Target Platform**: Windows and POSIX CLI/library consumers

**Project Type**: Python package and CLI

**Performance Goals**: No new network or subprocess work on a default plan

**Constraints**: Fail closed; no ambient interpreter mutation; no implicit live
resolver; no second registry; no readiness or approval mutation

**Scale/Scope**: Three source files, focused tests, one active install document,
and Spec Kit artifacts

## Phase Classification

**Initial status**: REQUIRED

Evidence:

- `integrations_main` imports `plan_profile` and `apply_profile` from the
  catalog-backed package through the facade.
- `integrations_setup.py` separately owns 158 executable statements, including
  `FABRIC_SKILLS`, `DBT_SKILLS`, MCP fallback pins, `_clone`, `_register`,
  `_provision_dagster`, and `setup_integrations`.
- Repository search finds direct consumers only in its focused test module and
  the CLI's explicit re-exports/prompt, but `__all__` makes compatibility an
  intentional package surface.
- The five focused integration test modules pass 88 tests at baseline, proving
  both implementations currently work rather than proving they are one system.

## Constitution Check

### Before design

- **Readiness ordering**: PASS; no stage or `next_action` change.
- **Human approvals**: PASS; implementation waits for named ratification and
  compatibility apply still requires an explicit caller decision.
- **Fail closed**: PASS; apply without exact resolvers refuses.
- **No confidence score**: PASS; categorical statuses only.
- **Official-first boundary**: PASS; official payloads remain upstream-owned;
  Seshat owns selection, compatibility, installation policy, and validation.
- **One canonical authority**: PASS; catalog and canonical installer own truth.
- **Windows safety**: PASS; no shell construction or broad filesystem target.

### After design

PASS. Required payload validation migrates into the canonical catalog/installer
rather than being lost. The compatibility layer is a projection, not a second
implementation. No new external execution surface is introduced.

## Design Decisions

### D1 - Catalog owns validation paths

Add an immutable `required_paths` tuple to `Component`. Validate each value at
construction. Populate it only for `fabric-skills` and `dbt-agent-skills` using
the required paths already enforced by the legacy installer.

### D2 - Canonical installer validates staging and presence

For GitHub components, `_is_installed` requires both the marker and all catalog
paths. `_install_github` validates staged content before rename and removes
failed staging. This preserves behavior without adding a validator elsewhere.

### D3 - Compatibility surface survives as projection

Keep the public facade dataclasses, prompt, render helper, catalog constants,
and planner/apply aliases. Derive `FABRIC_SKILLS`, `DBT_SKILLS`, and dbt pin
strings mechanically. `setup_integrations` projects canonical `ComponentPlan`
rows to `IntegrationResult`; canonical component IDs become the result names.
No hidden legacy grouping or membership list survives.

### D4 - Compatibility apply requires injected resolvers

Planning accepts no resolvers by default and therefore remains network-free.
`apply=True` without explicit `resolvers` returns a categorical failed result and
writes nothing. With resolvers it delegates to `apply_profile`. It never creates
`live_resolvers()` on a caller's behalf.

### D5 - Keep the CLI path stable

The CLI may continue importing catalog-backed aliases and `confirm` through the
facade. This retains import compatibility while tests prove the facade has no
installer logic. Moving the imports is unnecessary to achieve one authority.

## Project Structure

```text
src/seshat/
├── integrations_setup.py              # thin compatibility facade
└── integrations/
    ├── catalog.py                     # required_paths authority
    └── installer.py                   # canonical validation/execution

tests/unit/
├── test_integrations_setup.py         # facade and CLI compatibility
├── test_curated_stack_cli.py          # catalog/CLI contracts
└── test_curated_stack_install.py      # payload validation and apply

docs/install/
└── fabric-powerbi-integrations.md      # current canonical workflow

specs/144-integration-control-plane/
```

## Implementation Sequence

1. Record baseline and add red constructed tests.
2. Add and validate catalog `required_paths` metadata.
3. Make canonical presence/install logic consume that metadata.
4. Replace the legacy implementation with the compatibility projection.
5. Update focused tests and the active install document.
6. Run integration, architecture, capability, bundle, and static gates.
7. Review scope, record evidence, and clear the active Spec Kit fence.

## Validation Strategy

- `tests/unit/test_integrations_setup.py`
- `tests/unit/test_curated_stack_cli.py`
- `tests/unit/test_curated_stack_resolution.py`
- `tests/unit/test_curated_stack_lock.py`
- `tests/unit/test_curated_stack_install.py`
- `tests/unit/test_capability_inventory.py`
- public command and generated bundle contract tests
- `python scripts/export_agent_bundles.py --check`
- `python -m seshat.cli check`
- `git diff --check`

## Risks and Rollback

- **Compatibility result identity**: Direct callers will see canonical component
  IDs rather than seven legacy aggregate labels. Ratification explicitly accepts
  this truthful projection; import and type compatibility survive.
- **Validation too strict**: Paths are the exact legacy requirements. A focused
  staged-clone test proves complete official bundles pass.
- **Apply behavior**: Direct legacy apply becomes safer by requiring resolvers.
  The CLI already enforces `--refresh`, so CLI behavior does not regress.
- **Rollback**: Revert the facade, metadata field, installer checks, focused
  tests, and doc. No migration, committed runtime state, or generated output is
  created.
