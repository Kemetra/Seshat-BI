# Feature Specification: Source-onboarding packaging (roadmap M6, under Option B)

**Feature Branch**: `110-source-onboarding-packaging`

**Created**: 2026-07-07

**Status**: **BUILT** (docs-only) 2026-07-07 on branch `feat/110-source-onboarding-packaging`.
Under Option B (owner-ratified 2026-07-07): a discovery/packaging story over the shipped
`retail-onboard-table` + `source-mapping` skills — NO new CLI verb, NO new capability.
Deliverable: `docs/user/source-onboarding.md`.

**Input**: Roadmap M6 "Source Onboarding v1".

---

## Context (Option B framing)

The source-onboarding capability already ships as skills: `retail-onboard-table` (the
Source→Mapping front door) and `source-mapping` (the mapping gate → `source-map.yaml`).
Under B, M6 is NOT `seshat source profile` as a new verb — it is making those skills
**discoverable and runnable by a new user** in an installed workspace (the M3 workspace
gives them somewhere to land).

## Requirements (FR)

- **FR-001** A user-facing onboarding guide (`docs/user/source-onboarding.md`) that walks a
  new user from "I have a retail source" through the `retail-onboard-table` →
  `source-mapping` skill flow, in an installed/M3-scaffolded workspace.
- **FR-002** The workspace (M3) `mappings/` layout matches what `source-mapping` writes, so
  onboarding output lands in the right place with no extra wiring.
- **FR-003** No new readiness logic, no new verb, no capability the skills don't already
  own; this is packaging + docs over shipped skills (B).
- **FR-004** Respects the mapping gate hard-stop (`no_silver_before_mapping_cleared`) —
  the docs never suggest bypassing it; Principle V (owner approves business meaning/grain/
  PII), never the agent.

## Out of scope
- A `seshat source profile` CLI verb (B keeps this skill-driven).
- Live DB profiling automation (Stage-1 read-only profile stays in `retail-onboard-table`).

## Held-decision notes
Spec only. Depends on M3 (workspace shape). No `tasks.md`/code until owner review.
