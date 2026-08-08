# Implementation Plan: Power BI ownership and routing

**Branch**: `145-powerbi-ownership-routing` | **Date**: 2026-08-07 | **Spec**: `specs/145-powerbi-ownership-routing/spec.md`

**Status**: ratified -- Ahmed Shaaban, 2026-08-07; Phase 3 implementation authorized

## Summary

Phase 3 is PARTIALLY-REQUIRED. Seshat already separates design, PBIP inspection,
bounded PBIR edits, and Microsoft semantic-model surfaces, but the public router
does not select the new official Microsoft report-authoring surface and several
documents still describe all report authoring as deferred F016 work. Add the
smallest routing/fact delta, clarify hierarchy, and preserve current safety seams.

## Constitution Check

- Readiness ordering: PASS; report authoring requires governed dashboard design.
- Human approvals: PASS; no approval is inferred or executed.
- Fail closed: PASS; absent readiness or official discovery blocks execution.
- Official-first: PASS; Microsoft owns native report/model mechanics.
- Seshat delta: PASS; governance, design, bounded safety, inspection, and
  post-validation remain local.
- F016: PASS; remains parked and no live execution occurs.

## Design Decisions

1. Keep `powerbi-workflows` as the broad front door and make its intent table
   explicit.
2. Extend the existing pure recommender with a distinct `report-authoring`
   intent and dashboard-readiness fact; do not overload `report-formatting`.
3. Route native report construction to official `powerbi-report-authoring` when
   discoverable. Retain bounded Seshat formatting only for its explicit safety
   delta.
4. Clarify that the internal dashboard-design router selects Seshat design
   knowledge; it does not select execution owners.
5. Correct F016 documentation without changing F016 compatibility state.
6. Generate committed Claude/Codex projections from canonical public templates.

## Implementation Sequence

1. Add red contracts for report-authoring selection and readiness.
2. Add the minimum detector/recommender fact and surface.
3. Update canonical skills, capability metadata, and focused Power BI docs.
4. Regenerate deterministic bundles.
5. Run focused and architecture gates, review scope, record evidence, and clear
   the active Spec Kit pointer.

## Risks and Rollback

The upstream report skill may be installed but not discoverable; Phase 3 must
surface that as a blocked integration gap and Phase 6 will prove activation.
Rollback is a bounded revert of routing facts, guidance, tests, generated
projections, and Spec 145 artifacts; no runtime migration or external state exists.
