# Requirements checklist: spec 140

Review gate for the specification itself, before ratification. Each item is checked
against the written package, not against intentions.

## Completeness

- [x] Every user story from the outline is carried forward (US1-US5, all five)
- [x] Every FR from the outline is carried forward or explicitly corrected
- [x] Corrections are flagged in-place with rationale, not silently applied
- [x] New FRs added where the outline was silent (FR-140-021..023)
- [x] Success criteria are testable, each naming the test that proves it
- [x] Key entities defined with field-level shapes
- [x] Assumptions stated rather than left implicit
- [x] Out-of-scope list retained, plus the new git-automation exclusion

## Consistency

- [x] No requirement contradicts another
- [x] FR-140-011 reconciled with the read-only store (was unsatisfiable as written)
- [x] FR-140-015 reconciled with the committed-state gate
- [x] Spec, data-model, contracts, and quickstart agree on the three-state model
- [x] Entity names match between spec, data-model, and API contract
- [x] Dependency claim (139 accepted) verified against 139's own status and task count

## Ambiguity

- [x] `pending commit` defined once, used consistently
- [x] Provenance `kind` is a closed enum, not an open string
- [x] "Authoritative" defined as committed-and-read-at-HEAD, not "recorded"
- [x] Who supplies each `NamedHumanDecision` field is stated per field
- [x] Static-vs-live verification distinction stated wherever verification appears

## Placeholders

- [x] No TBD, TODO, or unresolved bracket in the package
- [x] Deferred structural choices named explicitly and routed to the plan
- [x] No fabricated example decision entry (repo tracks none; model built from
      validators instead)

## Governance

- [x] Status line says `draft`, not `ratified` -- no agent-written ratification
- [x] Status history records the promotion and the direction ruling separately
- [x] Direction ruling stated as scope agreement, explicitly not implementation
      authority
- [x] FR-140-020 (fence clause) retained verbatim in effect
- [x] Promotion Gate section updated to say expansion delivered, ratification pending
- [x] No second approval-validity predicate authorized anywhere
- [x] `never_self_grant_approval` expressed as a type constraint (single-member enum)
      and not only as prose

## Scope

- [x] Package is one coherent feature, not a program
- [x] Spec 141 territory (operations history, client export) left to 141
- [x] Phasing keeps the security-critical write path first and independently testable
- [x] **Owner judgement**: all-five-stories scope confirmed by the owner 2026-08-21
      ("All five as the outline lists them"). The Phase-D split remains a noted
      contingency in `plan.md` under Complexity Tracking if review finds the package
      too large to judge as one unit.

## Claims about shipped code (verified against the tree, not against this package)

An adversarial review found that the first draft asserted field names, enum members, and
a dependency it had never read — the `decision_store` side was built from validators,
but the `projection` side was built from a class-name grep. Internal consistency passed
precisely because all three documents repeated the same guesses.

- [x] `WorkspaceSnapshot.input_defects` (draft said `.defects`)
- [x] `InputDefect` has no `table_id` — so defects cannot be filtered by table identity
- [x] `StageState` has no `pending_live` — derived from `EvidenceRef.live_state` instead
- [x] `build_workspace_snapshot(root)` is the builder (draft said `projection.snapshot`)
- [x] `status` values are `STATUS_VALUES`; there is no `decided` (draft used it)
- [x] `decision_type` values checked against `CRITICAL_DECISION_TYPES` (draft invented
      `metric_definition` and `non_critical_note`)
- [x] `pyyaml` only — draft's `ruamel.yaml` would have added a dependency and tripped
      the freshness gate
- [x] Existing test helpers found and reused (`_studio_workspace_fixtures.py`, the
      `_client` pattern) rather than reinvented
- [x] Every symbol the package names re-confirmed present in `src/`
- [x] Every projection attribute the tasks dereference re-confirmed declared

**Standing rule this produced**: internal consistency across a spec package is not
verification. Each claim about shipped code must be checked against the file, and a
class-name grep is not a read of the fields.

## Verification discipline

- [x] Every obligation in the write-boundary contract has a named proof
- [x] Proofs are specified to fail when the guard is removed, not merely to pass now
- [x] The vacuity risk in the readiness test called out with its paired positive case
- [x] Fixture-lie risk called out (no real store file exists to copy from)
