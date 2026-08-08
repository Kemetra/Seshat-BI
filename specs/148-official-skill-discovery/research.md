# Research: Official skill discovery

**Date**: 2026-08-07

## Repository truth

- GitHub skill bundles land in
  `.seshat/integrations/skills/<component>` at an exact resolved ref.
- `_is_installed` checks the marker and catalog-required payload files.
- The lock records landed coordinates, but has no harness activation or
  discovery evidence.
- Claude and Codex Seshat bundles are generated and discoverable through their
  own repository plugin marketplaces; upstream clones are outside those bundles.

## Official package layouts verified

- Microsoft/Fabric: `.claude-plugin/marketplace.json`, focused plugin manifests,
  root Agent Skills, and `plugins/powerbi-authoring/skills/...`.
- dbt Labs: `.claude-plugin/marketplace.json` and
  `skills/dbt/skills/<skill>/SKILL.md`.
- Dagster: `.claude-plugin/marketplace.json` and
  `skills/dagster-expert/skills/dagster-expert/SKILL.md`.

The current repository commits checked during preflight were Microsoft
`764ab77bb1b08e3ade44fb3b5667ae036882f210`, dbt Labs
`f0a666d4a9fe600b651bf005b8f1c712ce4e5788`, and Dagster
`fa3d023d6700767d3950f94ebe8ea73b5abbd015`.

## Decision

Treat installation, activation, and discovery as orthogonal facts. Prefer
upstream native plugin activation. A direct Agent Skills projection is valid
only when the target harness actually discovers that location and provenance
still points to the locked upstream payload.

## Rejected approaches

- `clone == activated`: disproved by current install layout.
- Copy official skills into Seshat canonical bundles: creates fork tax and false
  ownership.
- One universal activation command: upstream repositories and harnesses publish
  different supported mechanisms.
- Mutate the operator's real global harness configuration during tests: unsafe
  and unnecessary; isolated fixtures can prove classification.
