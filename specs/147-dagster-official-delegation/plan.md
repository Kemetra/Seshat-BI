# Implementation Plan: Dagster official delegation

**Branch**: `147-dagster-official-delegation` | **Date**: 2026-08-07 | **Spec**: `specs/147-dagster-official-delegation/spec.md`

**Status**: ratified -- Phase 5 implementation authorized by Ahmed Shaaban on 2026-08-07

## Summary

Phase 5 is PARTIALLY-REQUIRED. The shipped Seshat adapter already uses Dagster
as the native orchestration engine behind real governance and evidence seams.
The remaining delta is to resolve the stale `dagster-skills` identity collision,
catalog Dagster's official skills, and route generic Dagster competence upstream.

## Constitution Check

- Readiness and named approvals: PASS; no gate behavior changes.
- Fail closed: PASS; installed official skills are not claimed discoverable.
- Official-first: PASS; Dagster owns native competence and Seshat owns policy.
- One authority: PASS; one official coordinate and one Seshat router identity.
- Live boundary: PASS; no Dagster job or database call.

## Design Decisions

1. Rename current profile membership from ambiguous `dagster-skills` to
   `seshat-dagster-workflows`; keep a lookup-only legacy alias.
2. Add `dagster-agent-skills` from `dagster-io/skills`, validating
   `skills/dagster-expert/SKILL.md`.
3. Keep `dagster-workflows` as the Seshat public router and `seshat dagster` as
   its governed execution seam.
4. Delegate generic assets, schedules, sensors, project structure, CLI usage,
   and troubleshooting to official `dagster-expert` after discovery is proven.
5. Preserve the current graph, runtime, pins, gates, evidence, and stopped
   automation posture.

## Implementation Sequence

1. Add catalog identity and routing contracts.
2. Update catalog/installer compatibility and focused tests.
3. Update canonical public/internal skills, capability metadata, and docs.
4. Regenerate deterministic bundles.
5. Run focused Dagster, integration, capability, lifecycle, and drift gates.
6. Review scope, record evidence, clear the active pointer, and commit locally.

## Risks and Rollback

The official package may install without being discoverable; routing therefore
blocks until Phase 6. A legacy machine-local lock may retain the old component
key, but current planning ignores it and an approved apply rewrites current
profile membership. Rollback is a bounded revert of catalog metadata, router
docs, contracts, generated projections, and spec files; runtime state is not
changed.
