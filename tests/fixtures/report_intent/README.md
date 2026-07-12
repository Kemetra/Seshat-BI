# Report Intent fixtures (spec 123, US2 -- T017)

A HAND-AUTHORED approved-intent workspace so the US2 coordinator
(`src/seshat/dashboard_coordinator.py`) is testable WITHOUT running the US1
interview. The `approved_happy/` tree is a minimal but real committed workspace:

- `.seshat/kpi-contracts.yaml` -- a VALID, named-human `report_intent_approval`
  decision (`report_owner`, all APPROVAL_REQUIRED_FIELDS, evidence_identity keyed
  to a real committed evidence file so the shared `approval_is_valid` predicate +
  the decision gate both accept it). No self-grant: an agent identity never
  satisfies `approved_by`.
- `mappings/demo_report_area/readiness-status.yaml` -- `semantic_model_ready: pass`
  (the hard gate the coordinator must never bypass -- FR-010).
- `mappings/demo_report_area/metrics/*.yaml` -- two APPROVED (`readiness.status:
  pass`) metric contracts the intent references by name (FR-003).
- `mappings/demo_report_area/design/report-intent.yaml` -- the committed intent
  whose metric references all resolve.
- `mappings/demo_report_area/design/visual-contract-binding-map.md` -- the authored
  design: every visual binds to exactly one approved contract, zero orphans
  (SC-003), each blueprint `business_question` traces to an intent question
  (FR-002a).
- `mappings/demo_report_area/design/dashboard-layout.md`, `visual-list.md`,
  `report-composition.yaml` -- the rest of the reviewable design.
- `contracts/knowledge/{database-to-pbip-flow,approval-authority}.yaml` and the
  intent evidence file are copied in by the test harness from the real repo so the
  gate machinery reads the shipped truth.

The fail-closed matrix test (T019) drives the REAL coordinator against COPIES of
this tree, each mutated to trip one precondition (semantic model not pass, a
missing/unapproved contract, an orphan visual, a missing approval). The oracle
sits ON the risk: the real helper reads the real committed state, not a mock.

`demo_report_area` is an EXAMPLE workspace, never the schema (Principle VII).
