# Implementation Plan: Official skill discovery

**Branch**: `148-official-skill-discovery`

**Status**: ratified; Phase 6 implementation authorized by Ahmed Shaaban on
2026-08-07 and completed

## Phase classification

**REQUIRED.** The catalog installs three official GitHub repositories under
`.seshat/integrations/skills/<component>`, but current state detection validates
only payload presence. It has no harness activation metadata and cannot prove
Claude Code or Codex discovery.

## Smallest remaining delta

1. Extend the existing catalog component model with declarative, per-harness
   discovery metadata. Do not create another registry.
2. Add a read-only discovery classifier that returns distinct installed,
   activated, and discoverable facts plus concrete blockers.
3. Surface those facts through the existing planner/renderer and compatibility
   facade without changing the default network-free/write-free posture.
4. Use official Claude plugin marketplaces where published. Use only a verified
   Agent Skills projection or explicit unsupported result for Codex; never copy
   upstream skill bodies into Seshat.
5. Add focused fixtures/contracts for Microsoft/Fabric, dbt, and Dagster, then
   update the integration docs with install/activation/routing/upgrade truth.

## Upstream evidence

- Microsoft publishes a Fabric plugin marketplace and separate Fabric and
  Power BI authoring bundles. The repository also carries Agent Skills and
  host-specific root instructions.
- dbt Labs publishes `dbt@dbt-agent-marketplace` for Claude Code and documents
  Agent Skills installation for other clients.
- Dagster publishes `dagster-expert@dagster`, documents `npx skills`, and names
  the Codex skill directory for manual installation.
- None of the three repositories currently publishes a native Codex plugin
  manifest; a Codex route therefore requires verified Agent Skills discovery,
  not a fabricated plugin claim.

## Scope guard

No new package dependency, no upstream content copy, no readiness or evidence
schema change, no MCP/runtime modification, no live activation of the operator's
global Claude/Codex profile, and no generated Seshat bundle regeneration unless
a reviewed canonical Seshat document actually changes.

## Validation

- focused integration catalog/installer/lock/render/CLI tests
- new activation/discovery contract tests with isolated fake harness roots
- capability and public-routing contracts
- `ruff format --check src tests scripts`
- `ruff check src tests scripts`
- `python scripts/export_agent_bundles.py --check`
- `python -m seshat.cli check`
- `git diff --check`

## Rollback

Revert the Phase 6 commit. Existing cloned payloads and MCP registrations remain
unchanged because discovery classification is additive and activation is not
performed implicitly.
