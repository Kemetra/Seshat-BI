# Quickstart: the Governed Dashboard Intelligence MVP journey

**Feature**: 123-governed-dashboard-intelligence
**Scope**: walks the MVP (US1 + US2) on the `retail_store_sales` example subject area. Preview (US4), audit (US5), patterns (US3), and PBIR compilation/validation (US7/US8) are later slices, not covered here.

**Preconditions** (fail closed if unmet — FR-033):
- Approved metric contracts exist for `retail_store_sales` (`mappings/retail_store_sales/metrics/*.yaml`, `readiness.status: pass`).
- Semantic model is ready (`semantic_model_ready: pass` in `mappings/retail_store_sales/readiness-status.yaml`).
- No live database is used at any step (SEC-001).

## Step 1 — Capture Report Intent (US1)

1. Invoke the `report-intent-interview` skill with a conversational request, e.g. *"weekly report for branch managers to spot underperforming branches."*
2. The interview (mirroring `business-knowledge-interview`): loads any existing intent first, batches low-risk questions, asks critical ones individually, masks PII by default.
3. It refuses to commit until `audience`, `purpose`, and ≥1 business question are resolved (US1 AC#4).
4. Every metric named must resolve to an approved contract; an unresolved metric records a gap + `readiness.status: blocked` and routes upstream (FR-004) — it is never invented.
5. Output: `mappings/retail_store_sales/design/report-intent.yaml` + a `report_intent_approval` decision recorded by a named `report_owner` in the Decision Store.

**Verify**: `report-intent.yaml` exists; DL5 shape rule passes; the approval record passes `approval_is_valid` (agent identity is rejected — no self-grant).

## Step 2 — Coordinate the shipped design capabilities (US2)

Given the approved intent, run the `dashboard-intelligence` coordinator skill. On each step it inspects committed state, picks one next allowed action, invokes the shipped capability, and re-evaluates:

1. `retail dashboard-gaps` — categorical pre-design inventory (Covered/Blocked/Planned/…). If a required metric/dimension is blocked, the coordinator STOPS naming the blocker + owner (FR-009/FR-034).
2. `retail dashboard-planner` — deterministic `new`/`extends <page>`/`duplicate of <page>` verdict per proposed page (no score). Duplicates surfaced for human decision.
3. `dashboard-design` (F011) — authors page blueprints + visual specs + the visual-contract binding map. Hard-gated on `semantic_model_ready: pass` (coordinator never bypasses — FR-010).
4. Compose `report-composition.yaml` (page order, navigation, cross-page filters). Each blueprint `business_question` must trace to an intent question (FR-002a).
5. Dashboard QA (the shipped 13-anti-pattern catalog) runs on the visuals.
6. STOP at the human blueprint review seam — the coordinator never self-grants `dashboard_ready: pass` (FR-010).

**Verify** (MVP done): a reviewable dashboard design exists (intent + blueprints + visual specs + composition + binding map), every visual traces to an approved contract + mapped field (SC-003, zero orphan visuals), and the journey stopped at human review with no preview and no PBIR (SC-012).

## What the MVP deliberately does NOT do

- No preview rendering (US4), no semantic audit (US5), no pattern recommendation (US3).
- No PBIR creation/validation (US7/US8) — those are P3, sample-gated, and require a new owner-ratified ADR.
- No Power BI Service publish/refresh/export (FR-036, SC-011) — ever.

## Fail-closed smoke checks (SC-005)

| Trigger | Expected |
|---|---|
| `semantic_model_ready` ≠ pass | coordinator BLOCKED, names missing readiness |
| a required metric has no approved contract | BLOCKED, names missing contract + owner, routes upstream |
| a visual has no approved contract | BLOCKED (orphan visual) |
| design authored, no valid blueprint approval | STOP at human review; no self-grant of `dashboard_ready: pass` |
