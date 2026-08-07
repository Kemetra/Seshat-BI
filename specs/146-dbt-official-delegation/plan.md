# Implementation Plan: dbt official delegation

**Branch**: `146-dbt-official-delegation` | **Date**: 2026-08-07 | **Spec**: `specs/146-dbt-official-delegation/spec.md`

**Status**: ratified -- Phase 4 implementation authorized by Ahmed Shaaban on 2026-08-07

## Summary

Phase 4 is PARTIALLY-REQUIRED. The existing runtime already invokes dbt Core
behind strong Seshat gates and emits normalized evidence. Do not rebuild it.
Clarify the public intent router so generic dbt competence delegates to dbt
Labs' official skills, record the upstream capabilities and execution relation,
and retain the current activation/live-parity blockers.

## Constitution Check

- Readiness and named approvals: PASS; no gate behavior changes.
- Fail closed: PASS; undiscoverable upstream skills are not claimed usable.
- Official-first: PASS; dbt owns native semantics, Seshat owns policy/evidence.
- One authority: PASS; no new installer, runner, or execution schema.
- Live boundary: PASS; no database call or parity claim.

## Design Decisions

1. Keep `dbt-workflows` as the front door and add an explicit intent/owner table.
2. Keep `seshat dbt` for the governed Seshat workflow because its wrapper is the
   enforcement seam, while naming the dbt executable as native executor.
3. Delegate generic authoring, test design, command help, docs lookup, and job
   troubleshooting to official dbt Labs agent skills.
4. Represent official skills and dbt MCP as upstream capabilities whose
   activation/discovery remains deferred to Phase 6.
5. Preserve the Seshat-specific scaffold, metadata, plan, parity, and evidence.

## Implementation Sequence

1. Add routing/ownership contracts.
2. Update canonical public/internal skills and integration/capability docs.
3. Regenerate deterministic bundles.
4. Run focused dbt, capability, public-surface, lifecycle, and drift gates.
5. Review scope, record evidence, clear the active pointer, and commit locally.

## Risks and Rollback

An official skill may be installed but undiscoverable; guidance must call this a
Phase 6 gap rather than bypassing Seshat's wrapper. Rollback is a bounded revert
of documentation, metadata, contracts, generated projections, and spec files;
no runtime or external state changes.
