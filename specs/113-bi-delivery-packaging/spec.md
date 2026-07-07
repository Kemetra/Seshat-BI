# Feature Specification: BI-delivery packaging (roadmap M10, under Option B)

**Feature Branch**: `113-bi-delivery-packaging`

**Created**: 2026-07-07

**Status**: **BUILT** (docs-only) 2026-07-07 on branch `feat/113-bi-delivery-packaging`.
Under Option B: a delivery-flow walkthrough over the shipped dashboard-design skills +
PBIR authoring adapters — NO new CLI verb, NO new capability; publish stays gated (F016).
Deliverable: `docs/user/bi-delivery.md`.

**Input**: Roadmap M10 "BI Delivery Layer".

---

## Context (Option B framing)

Dashboard design + PBIP handoff already ship as skills (`dashboard-design`,
`powerbi-dashboard-design`, `pbip-workflow`) and the PBIR authoring adapters
(`pbir-apply-theme`/`format-visual`/`set-page-background`/`set-geometry`, all shipped).
Under B, M10 is NOT `seshat pbi review/handoff` as verbs — it is a user-facing delivery-flow
guide over the shipped skills/adapters, keeping publish/execution gated.

## Requirements (FR)

- **FR-001** A user-facing delivery guide (`docs/user/bi-delivery.md`): dashboard design →
  metric-contract-bound visuals → PBIP handoff, via the shipped skills/adapters.
- **FR-002** Documents the hard-stops: `no_dashboard_before_metric_contracts`, and that
  **publish/execution stays gated** (F016, hard rule #6 — Semantic Model Ready = pass,
  execution-only, last). The guide never suggests publishing early.
- **FR-003** No new logic/verb; packaging + docs over shipped skills/adapters (B).
- **FR-004** No fabricated "great dashboard" claim — the honesty guard from the F034 work
  holds: the mechanism writes formatting; design quality is a human render judgment.

## Out of scope
- `seshat pbi review/handoff/publish` CLI verbs (B keeps skill-driven; publish is F016,
  parked/gated regardless of A-vs-B).

## Held-decision notes
Spec only. Depends on the metric-contract + semantic-model-ready stages. No `tasks.md`/code
until owner review.
