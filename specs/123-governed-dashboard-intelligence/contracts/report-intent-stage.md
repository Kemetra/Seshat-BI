# Contract sketch: `report_intent` stage contract (NEW — US1)

**Proposed file**: `contracts/report/report-intent.yaml`
**Precedent mirrored**: `contracts/report/dashboard-blueprint.yaml` (structure, `required_inputs`, `non_goals`, `blocking_decision_categories`).
**Status**: sketch for `/speckit.tasks` — final field names are plan/implementation detail; this fixes the shape and the wiring intent only.

This contract REFERENCES the `report_intent` route already declared in `contracts/knowledge/database-to-pbip-flow.yaml`; it never duplicates it (same convention the dashboard-blueprint contract header states).

```yaml
# contracts/report/report-intent.yaml  (SKETCH)
stages:
  - stage: report_intent
    purpose: >
      Capture what business report is needed, as a committed, reviewable Report
      Intent artifact, before any dashboard design begins. References approved
      metric contracts by name; never defines metric meaning.
    required_inputs:
      - "approved metric contracts for the subject area (readiness: pass)"
      - "a ready semantic model (semantic_model_ready: pass)"
    required_outputs:
      - "a committed report-intent.yaml under mappings/<subject-area>/design/"
      - "a report_intent_approval decision (report_owner)"
    handoff: dashboard_blueprint
    blocking_decision_categories:
      - report_intent_approval        # NEW critical type
      - kpi_definition                # pre-existing (metric meaning)
      - pii_handling                  # pre-existing (masking)
    stop_rules:
      - "a required metric has no approved contract -> record a gap, route upstream, block"
      - "audience/purpose/>=1 business question unresolved -> do not commit intent"
      - "intent not owner-approved -> block dashboard_blueprint stage"
    non_goals:
      - "defining metric meaning (owned by metric contracts)"
      - "authoring page blueprints or visuals (downstream)"
      - "publishing/exporting (F016, deferred)"
```

**Downstream wiring (see data-model.md)**: `report_intent_approval` is also added to the `dashboard_blueprint` stage's `blocking_decision_categories` so the blueprint stage cannot proceed without an approved intent — realizing FR-032's flow order through the existing `decision_gate` machinery, not new gate code.

**Verification note (from spec 122 Codex review, memory)**: confirm the gate's behavior when the store has NO `report_intent_approval` record yet — spec 122's review found the gate returns `pass` (not `blocked`) on an absent/empty store for empty-category stages. Tasks must include a test asserting an *unapproved* intent yields `blocked` (per FR-033), not a false `pass`, so this feature does not inherit that gap.
