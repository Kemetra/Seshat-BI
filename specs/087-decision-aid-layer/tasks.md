# Tasks: 087-decision-aid-layer

Dependency-ordered. DEFINE-only (no scaffold/rule/wiring). Each cites its FR/SC.
STOPS at ratify.

## Phase 0 -- Owner seams (confirmed at ratify, do not self-clear)

- [ ] **T000a [OWNER SEAM]** Owner confirms C1: `action_on_breach` on the contract
  (A, recommended) vs a sibling response-policy artifact (B). _clarify C1._
- [ ] **T000b [OWNER SEAM]** Owner knowingly ratifies a spec spanning THREE governed
  artifacts (metric-contract F009 + blueprint/visual-spec F011A + new driver
  template). _clarify C2._
- [ ] **T000c** Owner confirms `direction_of_good` enum completeness for their KPI
  set (higher|lower|target_band). _clarify C3._

## Phase 1 -- US1: KPI decision-readiness on the metric contract (P1)

- [ ] **T101** Add `direction_of_good: higher|lower|target_band` to
  `templates/metric-contract.yaml` with a Principle-V owner-decision note +
  placeholder. _FR-001._
- [ ] **T102** Add a `thresholds:` block (`target`, `good`, `warn`, `critical` --
  band boundaries in the metric's own unit) with a comment explicitly forbidding
  any 0-100 confidence/health score (#9). _FR-002, SC-001._
- [ ] **T103** Add an `action_on_breach:` block (plain-language action keyed by
  band; placeholder, owner-supplied). _FR-003._
- [ ] **T104** Add an authoring note: unfilled `direction_of_good`/`target` on a
  `pass` contract is a blocking condition (owner supplies; consistent with the
  readiness/blocking model); thresholds are categorical, never a score. _FR-004._

## Phase 2 -- US2: narrative arc on the page blueprint (P2)

- [ ] **T201** Add a `narrative:` block to
  `templates/dashboard-page-blueprint.yaml` (alongside `sections`/`visuals`) with
  `headline`, `so_what`, `recommended_action`, `key_exception` -- plain-language
  placeholders. _FR-005._
- [ ] **T202** Add the reference-by-name discipline note: a narrative slot naming a
  metric cites its approved contract by name; NO inlined formula/DAX/SQL/gold
  column; a named metric with no approved contract is an orphan-reference blocking
  condition. _FR-006._

## Phase 3 -- US3: driver / decomposition vocabulary (P3)

- [ ] **T301** Extend the `visual_type` enum in `templates/visual-spec.yaml` with
  `key_influencers`, `decomposition_tree`, `smart_narrative` (design intent; note
  that F016 owns live rendering). _FR-007._
- [ ] **T302** Add `templates/driver-decomposition.md`: a metric = factor x factor
  relation in plain INTENT, each factor a contract NAME, NO DAX/SQL/number; header
  states the define/check + no-inline boundary (mirrors metric-contract.yaml).
  _FR-008._

## Phase 4 -- boundary + validity checks (no @register rule)

- [ ] **T401** Assert every new field/artifact is GENERIC (placeholders only, no
  tenant/C086 specifics), ASCII + UTF-8 no BOM. _FR-009._
- [ ] **T402** Boundary check: grep the new blocks for DAX/SQL tokens
  (`SUM(`/`DIVIDE(`/`gold.`) and a 0-100 score field -> none present. _SC-001/002/003._
- [ ] **T403** `retail check` stays green (no rule added; template exempted from
  contract scans; DEFINE-only). _FR-010, SC-004._
- [ ] **T404** Confirm the DQ control-room's "thresholds -> a metric contract
  (F009)" punt now has a real `thresholds` field to reference. _SC-005._

## Phase 5 -- explicitly OUT of scope (guard against creep)

- [ ] **T501 (NOT DONE HERE)** Backfilling filled contracts/blueprints with the new
  blocks (business values) is owner-gated, deferred. _FR-011._
- [ ] **T502 (NOT DONE HERE)** The optional enforcement `retail check` rule is a
  separate future spec. _FR-010._

## STOP -- ratify ledger

Ratification (owner confirms C1/C2/C3, signs the spec) is a human edit the workflow
is forbidden to make (Principle V). See `ratify-ledger.md`.
