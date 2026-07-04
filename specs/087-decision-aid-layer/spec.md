# Feature Specification: Decision-Aid Layer (KPI decision-readiness + narrative arc + driver vocabulary)

**Feature Branch**: `087-decision-aid-layer`

**Created**: 2026-07-04

**Status**: Ratified (Ahmed Shaaban, 2026-07-04) -- C1=action-on-contract, C2=combined, C3=enum-complete

**Input**: Owner request (2026-07-04): "cover gaps in visualizing and business logics." Scope accepted = the KEYSTONE 3 gaps from the 2026-07-04 presenting-gap analysis, authored as ONE coherent decision-aid feature: gap #2 (KPI decision-readiness), gap #1 (narrative arc), gap #3 (driver/decomposition vocabulary). Runs in worktree ZEUS.

## Context (grounded facts, verified 2026-07-04)

The gap analysis found the repo governs *which* visuals answer a question and
*where* they sit, but has no place to state *what the reader should conclude or
do*. Three template negatives verified directly:

- **`templates/metric-contract.yaml`** carries `name / grain / formula_intent /
  owner / binds_to / readiness / ambiguities` -- NO `direction_of_good`, NO
  threshold bands, NO action-on-breach. So "Gross Margin 38%" cannot be made
  decision-ready, and `reports/blueprints/data-quality-control-room.yaml` punts
  its ok/warn/fail thresholds to "a metric contract (F009)" that has no threshold
  field to reference (a dangling promise).
- **`templates/dashboard-page-blueprint.yaml`** carries `sections` (seven-key
  layout vocabulary) + `visuals` (reference list) -- NO narrative slot. The story
  arc exists only as physical section ORDER, never as a recorded
  headline -> so-what -> action sentence.
- **`templates/visual-spec.yaml`** `visual_type` enum is
  `card|kpi_card|line_chart|bar_chart|column_chart|combo_chart|matrix|table|slicer|map|tooltip`
  -- no `key_influencers`, `decomposition_tree`, or `smart_narrative`. An author
  has no token to request a driver visual.

All three gaps are git-verified OPEN (no shipping commit; no in-flight spec).

**Schema-safety verified (2026-07-04):** the two shipped rules that read
`metric-contract.yaml` (`assumptions.py` AL1, `assumption_coherence.py` AL2) both
(a) read SPECIFIC keys tolerantly via `contract.get(...)` -- they never close/
iterate the key set -- and (b) EXPLICITLY EXEMPT the template itself
(`p != _TEMPLATE_PATH`), scanning only filled `mappings/*/metrics/*.yaml`. Adding
new top-level blocks is invisible to both. Precedent: the ADL `ambiguities[]`
block was added to this exact template the same way (spec 058). So this spec adds
NO rule-scope change; no existing rule/test/snapshot guards the shape.

## Non-negotiable boundaries this spec inherits (verbatim, not re-decided)

1. **DEFINE / CHECK boundary (F009/F011A):** these templates DEFINE intent. This
   spec adds FIELDS to templates; it does NOT add a `retail check` rule, does NOT
   read `powerbi/`, and authors NO DAX/SQL/PBIR. (An OPTIONAL lint rule is called
   out as a deferred follow-up, not built here.)
2. **NO numeric score (roadmap hard rule #9 / `never_fabricate_a_confidence_score`):**
   thresholds are CATEGORICAL BANDS with named boundaries a human sets -- never a
   computed 0-100 health/confidence number. `direction_of_good` is an enum, not a
   score.
3. **Reference-by-name (Principle VII / gold-only / four-surface):** narrative and
   driver artifacts REFERENCE approved metric contracts by name; they never inline
   a metric formula, a DAX expression, or a gold column. C086/tenant specifics are
   never inlined (every value is a placeholder).
4. **Principle V -- the agent stops at judgment calls:** `direction_of_good`, the
   threshold band boundaries, `action_on_breach`, the headline/so-what/action
   sentences, and the driver attribution are HUMAN business judgments. The agent
   RECOMMENDS; the owner DECIDES. An unfilled decision is a placeholder / recorded
   blocking_reason -- never auto-invented.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - KPI decision-readiness on the metric contract (Priority: P1)

As a metric owner, I record on a metric contract which direction is "good", the
categorical threshold bands that make a value red/amber/green, and the action to
take when a band is breached -- so a downstream KPI card is decision-ready (has a
target and a known good-direction), and the DQ control-room's threshold promise
has a real field to reference.

**Why this priority**: The keystone. It is the cheapest change (one field-block on
an existing template) and it unblocks the narrative "action" line (US2), the
driver "why it breached" framing (US3), and the branch-ranking direction. Without
it, comparison is enforced at the card but resolves to nothing.

**Independent Test**: Fill the new block on a placeholder contract; a
well-formed-fixture test asserts the fields parse, the enum values validate, and
an unfilled `direction_of_good` on an approved (`pass`) contract is a documented
blocking condition (not auto-filled).

**Acceptance Scenarios**:

1. **Given** a contract with `direction_of_good: higher` and a `thresholds` block
   naming a target + good/warn/critical band boundaries, **When** it is reviewed,
   **Then** the block is valid and the boundaries are ordered coherently for the
   declared direction.
2. **Given** a contract whose `thresholds` omit a target while `readiness.status`
   is `pass`, **When** reviewed, **Then** it carries a blocking_reason (the owner
   must supply the target; the agent does not invent it).
3. **Given** any `thresholds` field, **When** reviewed, **Then** NO value is a
   numeric 0-100 confidence/health score (bands are named boundaries in the
   metric's own unit, not a fabricated score).
4. **Given** a `direction_of_good`, **When** reviewed, **Then** it is one of
   `higher | lower | target_band` (a value good only inside a range, e.g. stock
   cover) -- never blank on an approved contract, never agent-invented.

### User Story 2 - Narrative arc on the page blueprint (Priority: P2)

As a page author, I record on a dashboard-page blueprint a `narrative` block --
the headline insight, the so-what interpretation, the recommended action, and the
key exception -- each REFERENCING approved contracts by name, so the page ships
with a top-line message, not just a wall of well-formed visuals.

**Why this priority**: The marquee decision-aid slot -- the literal
data-wall -> decision-aid gap. It is stronger once US1 exists (the action line can
reference "breached its critical band" instead of empty prose), so it sequences
after US1.

**Independent Test**: Fill the `narrative` block on a placeholder blueprint;
assert the four slots are present, that they cite contract names (not inlined
formulas/DAX), and that an unfilled narrative on a page whose `dashboard_ready`
intent is set is a documented gap.

**Acceptance Scenarios**:

1. **Given** a blueprint with `narrative.headline`, `.so_what`,
   `.recommended_action`, `.key_exception`, **When** reviewed, **Then** all four
   slots are present and each references a contract BY NAME where it names a metric.
2. **Given** a narrative slot that inlines a DAX/SQL expression or a raw gold
   column, **When** reviewed, **Then** it is rejected (reference-by-name only).
3. **Given** a `recommended_action`, **When** reviewed, **Then** it is a business
   action (plain language), never a numeric score and never an auto-invented claim
   (a placeholder if the owner has not supplied it).

### User Story 3 - Driver / decomposition vocabulary (Priority: P3)

As a visual author, I can request a driver-explaining visual (`key_influencers`,
`decomposition_tree`, `smart_narrative`) via the visual-spec `visual_type` enum,
and I can record the additive attribution intent (e.g. `Net Sales = Transactions
x ATV`) in a driver-decomposition artifact that references contracts by name -- so
"why did the number move" is expressible as design intent.

**Why this priority**: Populates US2's "why it moved" line with real attribution.
It is vocabulary + a reference artifact (no live execution), staying on the
decision-aid axis.

**Independent Test**: Add the three enum entries; assert a visual-spec naming one
validates. Fill a driver-decomposition artifact; assert its factors reference
contract names and record no DAX.

**Acceptance Scenarios**:

1. **Given** a visual-spec with `visual_type: decomposition_tree`, **When**
   reviewed, **Then** the type is a recognized enum value.
2. **Given** a driver-decomposition artifact stating `Net Sales = Transactions x
   ATV`, **When** reviewed, **Then** each factor names an approved contract and no
   DAX/SQL is present.
3. **Given** a driver artifact, **When** reviewed, **Then** the attribution is
   recorded as INTENT (plain relation), never a computed number or a live query.

### Edge Cases

- **`direction_of_good: target_band`** (good only inside a range): the `thresholds`
  block must express a two-sided band; a one-sided good/warn/critical ladder is
  incoherent for it -- flagged for the owner, not auto-shaped.
- **A narrative that names a metric with no approved contract**: an orphan
  reference -- a documented blocking condition (mirrors the existing orphan-visual
  rule), never silently allowed.
- **A threshold band whose boundaries are out of order for the direction** (e.g.
  `critical` better than `good` for `higher`): a coherence defect surfaced for
  review; the agent does not reorder silently.
- **An unfilled decision on an approved contract/page**: placeholder + recorded as
  the owner's open item; NEVER agent-filled (Principle V).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add to `templates/metric-contract.yaml` a `direction_of_good` field:
  enum `higher | lower | target_band`. Documented as a Principle-V owner decision;
  placeholder default, never agent-invented.
- **FR-002**: Add to `templates/metric-contract.yaml` a `thresholds` block:
  `target` (a value in the metric's own unit or `none`), and named categorical
  bands (`good` / `warn` / `critical`) each a boundary in the metric's own unit.
  The block MUST NOT contain any 0-100 confidence/health score (rule #9); comment
  MUST say so.
- **FR-003**: Add to `templates/metric-contract.yaml` an `action_on_breach` field:
  plain-language business action(s) keyed by band; placeholder, owner-supplied.
- **FR-004**: The template's authoring notes MUST state that `direction_of_good` +
  `target` unfilled on a `pass` contract is a DISCIPLINE-level blocking condition
  the owner records (owner supplies it; consistent with the existing readiness/
  blocking model), and that thresholds are categorical bands, never a score.
  NOTE (adversarial review MEDIUM): this is documentary discipline, NOT live
  enforcement -- no `retail check` rule verifies it today (same posture as the
  existing `owner`/`formula_intent` fields). Making it a hard gate is the deferred
  optional rule in FR-010. The wording must not imply a live gate exists.
- **FR-005**: Add to `templates/dashboard-page-blueprint.yaml` a `narrative` block
  with `headline`, `so_what`, `recommended_action`, `key_exception` -- each a
  plain-language slot that REFERENCES approved contracts by name where it names a
  metric. Placed alongside `sections` / `visuals`, consistent with the page's
  reference-not-inline discipline.
- **FR-006**: The `narrative` block MUST NOT inline a metric formula, DAX, SQL, or
  a raw gold column (reference-by-name only); the template comment MUST say so and
  cite the orphan-reference rule for a named metric with no approved contract.
- **FR-007**: Extend the `templates/visual-spec.yaml` `visual_type` CONVENTION LIST
  (a documented comment vocabulary, not a code-enforced schema enum -- adversarial
  review LOW) with `key_influencers`, `decomposition_tree`, `smart_narrative` (the
  driver-visual vocabulary), documented as design intent (F016 owns any live
  rendering). No code reads this list as a closed set, so the extension is inert +
  risk-free.
- **FR-008**: Add a new `templates/driver-decomposition.md` artifact recording
  additive/factor attribution as plain INTENT (e.g. `Net Sales = Transactions x
  ATV`), each factor referencing an approved contract BY NAME, with NO DAX/SQL and
  NO computed number.
- **FR-009**: Every new field/artifact is GENERIC (placeholders only); no
  tenant/C086 specifics inlined (Principle VII). ASCII + UTF-8 no BOM.
- **FR-010**: This spec adds NO `retail check` rule and authors NO PBIP/PBIR/DAX/
  SQL (DEFINE-only). An OPTIONAL future enforcement rule (e.g. "an approved
  contract has a filled direction_of_good + target"; "a filled blueprint has a
  narrative block") is named as a deferred follow-up, NOT built here.
- **FR-011**: The four starter blueprints under `reports/blueprints/*.yaml` and the
  seeded contracts under `skills/retail-kpi-knowledge/contracts/` MAY be backfilled
  with the new blocks as a SEPARATE, owner-gated step -- this spec ships the
  TEMPLATE fields; backfilling filled instances is out of scope (it touches
  human-authored business values = Principle V).

### Key Entities

- **DecisionReadiness** (on a metric contract): `direction_of_good` +
  `thresholds{target, good, warn, critical}` + `action_on_breach{by band}`. All
  owner-supplied; categorical, never a score.
- **PageNarrative** (on a page blueprint): `headline`, `so_what`,
  `recommended_action`, `key_exception` -- plain text referencing contracts.
- **DriverDecomposition** (new artifact): a metric = factor x factor x ... relation
  in plain intent, each factor a contract name.
- **DriverVisualType**: three new `visual_type` enum members.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A filled placeholder metric contract expresses direction + target +
  bands + action-on-breach, and a reviewer can confirm it carries NO 0-100 score.
- **SC-002**: A filled placeholder page blueprint carries a four-slot narrative
  that references contracts by name and inlines no DAX/SQL/gold column.
- **SC-003**: A visual-spec can name `key_influencers` / `decomposition_tree` /
  `smart_narrative`, and a driver-decomposition artifact records a factor relation
  citing contract names with no DAX/number.
- **SC-004**: `retail check` stays green on the current tree after the template +
  new-artifact changes land (DEFINE-only, no rule added, generic placeholders).
- **SC-005**: The DQ control-room's "thresholds -> a metric contract (F009)" punt
  now has a real `thresholds` field to reference (the dangling promise is closed at
  the template level).

## Assumptions

- **Categorical, not computed**: thresholds are human-set band boundaries in the
  metric's own unit (e.g. margin %), NEVER a derived confidence number. This keeps
  rule #9 intact and is the whole reason the block is safe as DEFINE-only.
- **Template-only scope**: this ships the FIELDS + one new artifact template.
  Filling them for real KPIs (backfilling contracts/blueprints) is owner business
  work, deferred (FR-011).
- **F016-independent**: none of this needs live Power BI. Driver visual *rendering*
  is F016's; the *vocabulary + attribution intent* is design-as-code, shippable now.
- **Optional enforcement deferred**: making these fields REQUIRED via a lint rule
  is a strong follow-up, but adding a rule is a separate spec (keeps this one
  purely additive + boundary-clean). Named in FR-010.
- **Ratification pending**: this spec STOPS at a ratify ledger (Principle V). The
  owner decides direction/threshold/action semantics per real KPI later; this spec
  only provides the slots.
