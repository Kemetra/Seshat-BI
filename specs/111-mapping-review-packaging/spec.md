# Feature Specification: Mapping-review packaging (roadmap M7, under Option B)

**Feature Branch**: `111-mapping-review-packaging`

**Created**: 2026-07-07

**Status**: **BUILT** (docs-only) 2026-07-07 on branch `feat/111-mapping-review-packaging`.
Under Option B: a review-flow walkthrough over the shipped `source-mapping` +
`grain-confidence-reviewer` skills — NO new CLI verb, NO new capability. Deliverable:
`docs/user/mapping-review.md`.

**Input**: Roadmap M7 "Mapping Review UX".

---

## Context (Option B framing)

Mapping review already ships as `source-mapping` (the gate producing `source-map.yaml`)
plus `grain-confidence-reviewer` (F008, grain candidate review). Under B, M7 is NOT
`seshat mapping review` as a verb — it is a user-facing review-flow guide + ensuring the
review artifacts the skills already emit are discoverable in an installed workspace.

## Requirements (FR)

- **FR-001** A user-facing mapping-review guide (`docs/user/mapping-review.md`): how a user
  reviews and approves the grain/PK/PII/placement decisions `source-mapping` surfaces,
  using `grain-confidence-reviewer`, before the mapping gate clears.
- **FR-002** Documents the owner-approval point (Principle V — business meaning/grain/PII
  are the human's call), never an agent-auto-approve.
- **FR-003** No new logic/verb; packaging + docs over shipped skills (B). The review
  artifacts (`source-map.yaml`, grain-confidence output) are already produced by the skills.
- **FR-004** Honors `no_silver_before_mapping_cleared`.

## Out of scope
- A `seshat mapping review` CLI verb (B keeps skill-driven).
- Auto-resolving any mapping ambiguity the owner owns.

## Held-decision notes
Spec only. Depends on M6/M3 flow. No `tasks.md`/code until owner review.
