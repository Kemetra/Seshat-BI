# Contract sketch: `report-intent-interview` behavior contract (NEW — US1)

**Proposed file**: `contracts/interview/report-intent-interview.yaml`
**Precedent mirrored**: `contracts/interview/business-knowledge-interview.yaml` (spec 121).
**Delivery**: a NEW skill `.claude/skills/report-intent-interview/SKILL.md` (Option-B: skill, not a CLI verb). Structurally MIRRORS the business-knowledge interview; does not extend it (different `required_inputs` and `focus`).

```yaml
# contracts/interview/report-intent-interview.yaml  (SKETCH)
interview:
  name: report-intent-interview
  produces: "mappings/<subject-area>/design/report-intent.yaml + a report_intent_approval decision"
  required_inputs:
    - "approved metric contracts (readiness: pass)"   # DIFFERS from business-knowledge (which needs a discovery profile)
    - "a ready semantic model (semantic_model_ready: pass)"
  behavior:
    focus:                                            # DIFFERS: intent fields, not kpi/grain/keys
      - audience
      - purpose
      - supported_decision
      - review_cadence
      - business_questions
      - metric_roles_by_name          # outcome/driver/guardrail, referenced not defined
      - comparisons
      - dimensions_and_filters
      - actions_and_exceptions
      - mobile_accessibility_language_rtl
      - exclusions
    load_existing_first: true          # REUSED verbatim: present for confirm/supersede, never overwrite
    question_grouping:                 # REUSED verbatim from business-knowledge-interview
      batch_low_risk: true
      critical_types_forbidden_in_batch: true
      item_level_exclusion: true
      requires_named_human_approval: true
    masking:                           # REUSED verbatim (SEC-003): PII masked by default; unmask = recorded pii_handling decision
      pii_masked_by_default: true
    critical_decision_type: report_intent_approval    # NEW type, authority class report_owner
  hard_stops:                          # REUSED verbatim from business-knowledge-interview
    - never_self_grant_approval
    - never_advance_a_readiness_stage
    - never_emit_a_confidence_score
    - stop_and_record_then_report_gate_verdict
```

**Reused machinery** (no re-implementation): the nine-status Decision Store lifecycle (`STATUS_VALUES`), `approval_is_valid`, DS4 supersession, and the interview STOP discipline all come from spec 121's shipped code. The intent interview only adds its own `focus` list, `required_inputs`, and the new `report_intent_approval` critical type.
