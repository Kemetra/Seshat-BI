# Scope review: Spec 145

**Date**: 2026-08-07

## In-scope changes

- Added one closed `report-authoring` intent, exact target selection, and
  target-scoped `dashboard_ready` detection to the existing pure doctor.
- Selected Microsoft's official report-authoring skill while blocking execution
  until Phase 6 proves activation/discovery.
- Kept `powerbi-workflows` broad, made `powerbi-dashboard-design` explicitly
  nested, and kept the doctor as execution-owner selector/preflight.
- Preserved bounded PBIR formatting commands and their safety delta.
- Corrected active design/docs/templates that incorrectly assigned native PBIR
  authoring to F016; F016 remains deferred and limited to live semantic execution.
- Added explicit official capability metadata with honest `unrecorded`
  provenance and deterministic Claude/Codex projections.

## Explicitly unchanged

- No dependency, lockfile, CI, integration installer/catalog, MCP registration,
  `.mcp.json.example`, readiness status, approval, database, or live executor.
- No capability, skill, router, adapter, or compatibility surface was deleted.
- F016 remains `deferred`; no park or human gate was lifted.
- Upstream activation/discovery remains Phase 6 and evidence-envelope work
  remains Phase 7.
- No push, PR, merge, release, or publication.

## Generated output

Only deterministic projections corresponding to the changed canonical public
skills/templates and their bundle manifests changed. The post-generation drift
gate passes for both Claude and Codex.

## Verdict

The diff is confined to Phase 3 ownership/routing, contracts, documentation,
generated projections, and Spec Kit lifecycle evidence. No scope creep found.
