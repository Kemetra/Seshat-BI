# Phase 1 Data Model: Governed Dashboard Intelligence and PBIR Authoring

**Feature**: 123-governed-dashboard-intelligence
**Date**: 2026-07-12

Entities below are the *new or extended* artifact shapes. Shipped shapes (page blueprint, visual spec, report composition, metric contract, binding map, implementation trace, Decision Store record) are reused as-is and only referenced here.

---

## Entity: Report Intent (NEW — US1)

**Owner of**: audience, report purpose, supported decision, primary business questions (FR-038). Upstream of page blueprints (FR-002a).
**Location**: template `templates/report-intent.yaml`; filled `mappings/<subject-area>/design/report-intent.yaml`.
**Format**: YAML (machine-read by coordinator, audit, DL5 rule).

```yaml
report_id: "<short_stable_id>"              # e.g. branch_performance_weekly (used for deterministic IDs downstream)
subject_area: "<mappings/<table> this intent targets>"

audience: "<who reads it>"                   # e.g. branch_manager | executive | analyst
purpose: "<executive|monitoring|diagnostic|action_oriented|analytical_exploration>"
supported_decision: "<the decision this report supports>"
review_cadence: "<weekly|daily|ad_hoc|...>"

business_questions:                          # >= 1 required to commit (US1 AC#4); DL5 checks presence
  - question_id: "<q1>"                       # stable id blueprint.business_question traces to (FR-002a)
    text: "<primary business question, plain language>"

# metric roles — REFERENCE BY NAME ONLY (same triple as dashboard-page-blueprint.required_metric_contracts);
# NO formula/DAX field exists here by design (FR-003).
outcome_metrics:
  - name: "<approved_metric_contract_name>"
    store_ref: "mappings/<table>/metrics/<Name>.yaml"
    status_required: "pass"
driver_metrics: []                           # same shape
guardrail_metrics: []                        # same shape

comparisons:
  - "<e.g. vs prior period | vs target | vs peer branch>"
dimensions_and_filters:
  - field: "<dim_table>.<attribute>"          # a MAPPED field (F010)
expected_actions_and_exceptions:
  - "<action/exception the report should surface>"
pages_and_drill_paths:
  - "<page/drill intent, later referenced by blueprint.page_name>"
mobile_accessibility_language_rtl:
  mobile_needs: "<free text | none>"
  accessibility_needs: "<free text | none>"
  language: "<en|ar|...>"
  rtl_required: "<true|false>"
exclusions_and_non_goals:
  - "<explicitly out of scope>"

owner: "<Person Name> (report_owner)"         # decision_store.owner_shape_ok shape
readiness:
  status: "<not_started|blocked|warning|pass>"# four-status only, NO numeric score (FR-035)
  evidence: []                                # e.g. ["approved by <owner> on <YYYY-MM-DD>"]
  blocking_reasons: []                        # e.g. ["metric X has no approved contract (FR-004)"]
open_questions: []                            # ambiguity ledger (mirrors metric-contract.ambiguities)
  # - id: "<slug>"
  #   decision_status: "decided|undecided"
  #   ruling: ""
  #   evidence: []
```

**Validation (FR / rule)**:
- FR-003: every `*_metrics[].name` MUST resolve to a metric contract at `store_ref` with `readiness.status: pass` (coordinator runtime check, NOT the DL5 static rule).
- FR-004: an unresolved metric → a `blocking_reasons` entry + `readiness.status: blocked`; intent does not commit.
- DL5 (new shape rule): presence of `audience`, `purpose` (in enum), `supported_decision`, `review_cadence`, ≥1 `business_questions`, valid `owner`; `readiness.status: pass` never with empty `evidence[]`. Presence-only; grants no approval.
- US1 AC#4: cannot commit until `audience`, `purpose`, and ≥1 business question are resolved.

**State/lifecycle**: mirrors readiness statuses; approval recorded separately as a `report_intent_approval` Decision Store record (below). Post-approval change → prior approval `superseded` (DS4), renewed approval required.

---

## Decision type: report_intent_approval (NEW — US1/US6)

Additive wiring (FR-037-safe):
- `src/seshat/decision_store.py` `CRITICAL_DECISION_TYPES` += `"report_intent_approval"`.
- `contracts/knowledge/approval-authority.yaml` eligibility += `report_intent_approval: [report_owner]`.
- `contracts/knowledge/database-to-pbip-flow.yaml`: add `report_intent_approval` to `blocking_decision_categories` of the `report_intent` stage AND the `dashboard_blueprint` stage (blueprint blocked until intent approved — realizes FR-032 through the existing gate).
- Validity rides on the shipped `approval_is_valid()` (owner shape + authority map); `_ROLE_TOKENS` already includes `report_owner`, so **no RS1 change is entailed by this type** (RS1's FR-022a change is separate, scoped to `dashboard_blueprint` spine sign-off).

---

## Entity: Dashboard Pattern (NEW — US3)

**Owner of**: reusable, generic design guidance (FR-038). Defines NO KPI meaning; adds NO tenant logic.
**Location**: `docs/patterns/dashboard/<pattern>.md` (distinct from the data-modeling `docs/patterns/` docs) + optional skill index.

Fields (guidance only): `suitable_audiences`, `intended_purpose`, `common_question_families`, `metric_roles` (outcome/driver/guardrail *roles*, not named metrics), `common_page_structure`, `recommended_visual_roles`, `expected_action_paths`, `common_design_risks`. Initial families: Executive Performance, Sales Diagnosis, Branch Performance, Inventory Health, Product Performance, Promotion Effectiveness, Returns & Refunds, Customer Behavior, Data Quality Control Room, Action & Exceptions.

**Validation**: MUST NOT name specific KPIs or fabricate metrics; unavailable requirements surface as gaps via `retail dashboard-gaps` (FR-013). Human accepts/adapts/rejects (FR-014).

---

## Entity: Semantic Audit Finding (NEW — US5)

**Owner of**: report-level coherence findings (FR-038). No numeric score.
Record shape: `{ check: <FR-018 check id>, category: <enum>, evidence: [<committed path(s)>], owner_or_correction: <named> }`.
Category enum (spec-fixed, verbatim): `covered | incomplete | missing | conflicting | warning | blocked | not_applicable_with_reason`.

**Check → committed-artifact map** (each reuses a shipped tool's *output*, never recomputes — FR-020):

| FR-018 check | Reads |
|---|---|
| every intent question covered | Report Intent `business_questions` vs blueprint `business_question` across composition pages (FR-002a spine) |
| page single coherent purpose | blueprint `business_question` (singular) + `sections.*` |
| primary outcomes visible | visual specs in `kpi_strip`/`main_insight` vs intent `outcome_metrics` |
| diagnostic has drivers | intent `purpose: diagnostic` + driver visual types (`key_influencers`/`decomposition_tree`/`smart_narrative`) / filled `driver-decomposition.md` |
| guardrails/comparisons | visual `anti_pattern_checks.kpi_without_comparison` + intent `guardrail_metrics` |
| action/exception paths | blueprint `narrative.recommended_action`/`key_exception` + visual `drill_through` vs intent actions |
| pages not duplicate | recorded `retail dashboard-planner` verdict (cited, not re-run) |
| composition matches purpose | `report-composition` audience/order/landing vs intent audience/purpose |
| navigation coherent | `report-composition.navigation` (orphan `to:` with no page) + visual `drill_through` |
| cross-page filters consistent | `report-composition.cross_page_filters` vs page `slicers` |
| narrative supported | blueprint `narrative` text vs page `required_metric_contracts` + `visuals` |
| a11y/mobile/rtl addressed | filled `a11y-rtl-readiness-checklist.md` (cited, never re-derive CT1) + blueprint `mobile_notes` |
| freshness addressed | blueprint `sections.footer_status` |
| (orphan/unmapped hygiene) | filled `visual-contract-binding-map.md` + (if PBIR exists) `visual-implementation-trace.md` |

---

## Entity: PBIR creation primitive (NEW — US7, gated)

**New capability** the four shipped adapters structurally refuse: `create_page()` / `create_visual_container()`. Everything else (theme/format/background/geometry) calls the shipped adapters.

Contract:
- Writes only NEW pages/visual containers; never mutates an existing visual's `query`/`visualType` (FR-003 snapshot, inherited from adapters).
- Binds only to fields on the approved `visual-contract-binding-map.md` (no orphan visual, no unmapped field — FR-027).
- Requires a **verified Desktop-authored reference sample** for the element type (FR-029; D10 gating table). No JSON guessing.
- Deterministic ID minting: page/visual `name` = a deterministic function (e.g. truncated `hashlib` digest) of the blueprint element's stable id (`report_id` + element slug) — NEVER random/time-based (FR-027 / US7#4).
- Multi-file atomicity: stage the complete file tree, validate the batch, then commit; on failure leave no partial write (temp-dir approach by increment 3/4) — recovery net `git checkout -- <report-dir>`.
- Authorized only under a NEW owner-ratified ADR (D11); ADR drafted in planning, ratified by the named owner (human seam).

---

## Entity: Blueprint Preview (NEW — US4)

Deterministic SVG (HTML twin) at `mappings/<subject-area>/design/preview/<page_id>-preview.svg`, produced by pure `src/seshat/blueprint_preview.py` from committed blueprint/visual-spec/composition/grid YAML. Every data value is a labeled `PLACEHOLDER`. Determinism via `sorted(...)` inputs + fixed serialization. No live DB / DAX / PBIR (SEC-001/FR-016).

---

## Shipped entities reused (referenced, not redefined)

Page Blueprint (`templates/dashboard-page-blueprint.yaml`), Visual Spec (`templates/visual-spec.yaml`), Report Composition (`templates/report-composition.yaml`), Metric Contract (`templates/metric-contract.yaml`), Visual-Contract Binding Map (`templates/visual-contract-binding-map.md`), Visual Implementation Trace (`templates/visual-implementation-trace.md` — extended by US8, not replaced), Decision Store record (`src/seshat/decision_store.py`), a11y/RTL checklist (`templates/a11y-rtl-readiness-checklist.md`).
