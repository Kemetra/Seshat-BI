# Feature Specification: Drill/Navigation intent + Period-over-Period contract structure

**Feature Branch**: `088-drill-nav-periods`

**Created**: 2026-07-04

**Status**: Ratified (Ahmed Shaaban, 2026-07-04) -- C1=structure-only, C2=add-report-composition, C4=combined

**Input**: Owner request (2026-07-04): next gap wave = #4 (drill/nav) + #5
(period-over-period), from the 2026-07-04 presenting-gap analysis. Authored as one
combined DEFINE-only feature in worktree ZEUS, following the 087 playbook. Two
distinct risk profiles (see below) -- the ratify seam is honest about spanning two
feature areas.

## Context (grounded facts, verified 2026-07-04)

- **#4a drill fields absent**: `templates/visual-spec.yaml` has an `interactions:`
  block (`cross_filter`, `affects_visuals`, `drives_bookmark`) but NO
  `drill_through` or `drill_down` fields. `docs/powerbi/visual-qa.md` RECOMMENDS
  drill-through 3x but gives no field to capture source->target-page + carried
  filter (a doc advising a pattern with no way to record it).
- **#4b no report-level nav**: `templates/` has per-page blueprints and various
  *-report.md artifacts, but NO report-composition artifact (page order, landing
  page, cross-page nav). The repo is emphatically one-page-per-blueprint ("one file
  = one page"). `footer_status` promises a "link to the data-quality control room"
  with no field to specify that link.
- **#5 period-comparison unbound**: `reports/blueprints/executive-summary.yaml`
  references `<period-comparison-contract>` as a placeholder that resolves to
  nothing. The `skills/retail-kpi-knowledge/contracts/` dir has `net-sales`,
  `gross-margin`, etc. but NO `net-sales-growth` / `same-store-sales-growth` / `ytd`
  sealed contracts.

Both gaps git-verified OPEN 2026-07-04.

**Schema-safety verified (2026-07-04):** rule **AD1** (`additivity_consistency.py`)
and `test_additivity_consistency.py` GLOB and READ every
`skills/retail-kpi-knowledge/contracts/*.md`. Each contract's `**Additivity**`
heading MUST open with the closed vocabulary (`Fully additive` / `Semi-additive` /
`Non-additive`); a NON-additive (ratio) child composed by a DIRECT SUM in its
`**Derives from**` is an ILLEGAL ERROR, while a base-over-base recompute is LEGAL.
=> Any NEW growth contract this spec authors MUST declare `Non-additive` and
express its derivation as a base-over-base ratio, or it breaks the gate. This spec
honors that (FR-006).

## Non-negotiable boundaries (verbatim, not re-decided)

1. **DEFINE / CHECK boundary:** adds template FIELDS + a new template + new contract
   files. NO `retail check` rule, NO PBIR/DAX/SQL.
2. **#4 INTENT vs EXECUTION line (the #4-specific boundary):** drill-through,
   drill-down, and page-navigation are partly things the RENDERED report DOES --
   Power BI executes them in PBIR (F016's deferred territory). This spec captures
   only the DESIGN INTENT (which visual OFFERS a drill-through, to which target
   page, carrying which filter -- by name), never the runtime behavior. A field that
   specifies EXECUTION rather than intent is out of scope (mirrors 087's no-score
   line).
3. **#5 PRINCIPLE-V line (the #5-specific boundary, BLOCKING):** this spec authors
   the growth-contract STRUCTURE. It DOES NOT resolve the **comparison-baseline**
   question (same-period-last-year vs prior-period) or the comparable-store
   definition (= ambiguity **A11**). Those are named human judgment calls.
   IMPORTANT (adversarial review CRITICAL): the comparison-baseline question is
   **un-coded** in the canonical ambiguity register -- `kpi-ambiguities.md` A3 is
   "Sale date vs posting date vs return date", NOT the baseline; the baseline is a
   separate un-coded bullet in `domains/time-intelligence.md`. So each new growth
   contract flags the **comparison-baseline** ambiguity as PROSE (cite
   time-intelligence.md, "not yet assigned an A-code") -- NEVER a false `(A3)`
   citation -- plus **A11** (undecided/blocking) for same-store. The agent
   RECOMMENDS a baseline option, the owner DECIDES. The agent NEVER writes what
   "comparable store" or "the baseline period" means.
4. **Reference-by-name / no numeric score / generic placeholders / gold-only** --
   as 087. No tenant/C086 specifics.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Drill-through / drill-down INTENT on the visual spec (Priority: P1)

As a visual author, I record that a visual OFFERS a drill-through (to which target
page, carrying which filter -- by name) and/or a drill-down hierarchy axis, so the
drill-through pattern the QA doc recommends 3x is finally capturable as design
intent (F016 renders it).

**Why this priority**: The most-cited absent field; a doc advises a pattern with no
slot to record it. Pure intent, F016-independent.

**Independent Test**: Fill the new `drill_through`/`drill_down` blocks on a
placeholder visual-spec; assert they capture target-page + carried-filter (by name)
and a hierarchy axis, and that no field specifies runtime execution.

**Acceptance Scenarios**:

1. **Given** a visual with `drill_through.target_page` + `carried_filters` (by
   name), **When** reviewed, **Then** the intent is captured and references pages/
   filters by name (no inlined DAX/query).
2. **Given** a `drill_down.hierarchy` (e.g. region -> branch -> SKU), **When**
   reviewed, **Then** it names dimension levels (mapped fields), not a runtime
   action.
3. **Given** any drill field, **When** reviewed, **Then** it specifies INTENT, never
   the rendered behavior (F016 owns execution).

### User Story 2 - Report-composition artifact: the page-above-the-page (Priority: P2)

As a report author, I record the report-level composition -- page order, the
landing page, the cross-page navigation model, and the inter-page links the page
vocabulary already references (e.g. footer's DQ-control-room link) -- so a
multi-page report has a specifiable parent above the single page.

**Why this priority**: The repo is one-page-per-blueprint with no parent; multi-page
composition is currently unspecifiable. This is a NEW structural layer -- see
clarify C2 (confirm it is absent-by-gap, not absent-by-deliberate-design).

**Independent Test**: Fill a placeholder `report-composition.yaml`; assert it lists
pages by blueprint reference (not inlined), names a landing page, and captures the
nav links the vocabulary references.

**Acceptance Scenarios**:

1. **Given** a report-composition naming its pages by blueprint path + a landing
   page, **When** reviewed, **Then** each page is a REFERENCE (no inlined page def).
2. **Given** the composition, **When** reviewed, **Then** it can record the
   footer's DQ-control-room link + cross-page filter carry as intent.
3. **Given** a page referenced that has no blueprint, **When** reviewed, **Then**
   it is an orphan reference -> blocking condition (mirrors orphan-visual).

### User Story 3 - Period-over-Period contract STRUCTURE (baseline owner-owned) (Priority: P1)

As a metric owner, I have sealed-STRUCTURE growth contracts (Net Sales Growth %,
YTD, Same-Store Sales Growth %) that the executive-summary's
`<period-comparison-contract>` placeholder can reference -- with the comparison-baseline (uncoded)
and comparable-store (A11) definitions flagged UNDECIDED/blocking for me to rule,
never agent-invented.

**Why this priority**: The most common exec question ("vs last period?") is enforced
at the KPI card but binds to nothing. Sealing the STRUCTURE (not the definition)
closes the dangling placeholder while respecting Principle V.

**Independent Test**: Author the three growth contracts; assert each declares
`Non-additive` additivity, a base-over-base derivation (AD1-legal), and the comparison-baseline (uncoded) (+A11 for
same-store) as `undecided`/blocking -- and that NO baseline/same-store DEFINITION is
written by the agent.

**Acceptance Scenarios**:

1. **Given** `net-sales-growth.md`, **When** AD1 reads it, **Then** its
   `**Additivity**` opens with `Non-additive` and its `**Derives from**` is a
   base-over-base ratio (not a direct sum of a non-additive child) -> AD1 legal.
2. **Given** `same-store-sales-growth.md`, **When** reviewed, **Then** the comparison-baseline (uncoded)
   AND A11 (comparable-store) are recorded as open ambiguities the owner must rule;
   the file states the definition is owner-pending, and the agent has written no
   baseline/comparable-store definition.
3. **Given** any growth contract, **When** reviewed, **Then** its `Status` is a
   truthful open state (e.g. `Planned` / structure-only), never `Seeded` with an
   agent-invented definition.

### Edge Cases

- **A drill_through target page not in the report-composition**: orphan -> blocking.
- **A growth contract whose additivity is misdeclared** (e.g. "Fully additive"):
  AD1 ERROR -> the spec's fixtures/checks catch it before it lands.
- **report-composition turns out to be absent-by-design** (a deliberate F016-style
  omission): then US2 shrinks to intent-only fields or is deferred -- resolved at
  clarify C2, not assumed.
- **The owner has not ruled the comparison-baseline (uncoded) / A11**: the growth contract stays structure-only /
  blocked; the executive-summary reference resolves to a blocked contract (honest),
  never to an agent-invented definition.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add a `drill_through` block to `templates/visual-spec.yaml`:
  `offers: true|false`, `target_page` (by name), `carried_filters` (by name).
  Design intent only; no runtime/execution field.
- **FR-002**: Add a `drill_down` block to `templates/visual-spec.yaml`:
  `hierarchy` (ordered dimension levels, mapped-field names). Intent only.
- **FR-003**: Both drill blocks MUST reference pages/filters/dimensions BY NAME;
  no inlined DAX/SQL/query; comment states the intent/execution line (F016 renders).
- **FR-004**: Add `templates/report-composition.yaml` (NEW): `pages` (ordered list
  of blueprint REFERENCES), `landing_page`, `navigation` (cross-page links incl.
  the footer DQ-control-room link), `cross_page_filters` (carried, by name). A page
  with no blueprint is an orphan (blocking). Gated on clarify C2 (absent-by-gap
  confirmation).
- **FR-005**: Author three growth-metric contracts under
  `skills/retail-kpi-knowledge/contracts/`: `net-sales-growth.md`, `ytd.md`,
  `same-store-sales-growth.md` -- STRUCTURE only, following the existing contract
  markdown format.
- **FR-006**: Each growth contract MUST declare `**Additivity**` opening with
  `Non-additive` and express `**Derives from**` as a base-over-base ratio (AD1-legal
  -- NEVER a direct sum of a non-additive child), so AD1 + the additivity test stay
  green.
- **FR-007 (BLOCKING Principle-V line)**: Each growth contract MUST flag its
  **comparison-baseline** ambiguity as an OPEN owner decision, cited as PROSE
  ("comparison baseline SPLY vs prior period -- see domains/time-intelligence.md;
  not yet assigned an A-code"), NOT as `(A3)` (A3 is the date-axis ambiguity, a
  different thing -- a false citation is forbidden). `same-store-sales-growth.md`
  ADDITIONALLY flags **A11** (same-store definition). The file records the
  ambiguity, recommends an option, and states the definition is owner-pending. The
  agent MUST NOT write the baseline or comparable-store definition. `Status` = honest
  open state (`Planned` / structure-only), never `Seeded` with an invented definition.
- **FR-007b (adversarial review LOW)**: In each growth contract's **Business
  definition** and **Formula in business terms** sections, the baseline/comparable-
  store specifics MUST be left owner-pending (e.g. "vs the owner-ruled comparison
  baseline"), NOT filled with an agent-authored definition. Following the existing
  contract markdown format MUST NOT force the agent to state what "same-store" or
  "the baseline period" means.
- **FR-008**: The `<period-comparison-contract>` placeholder in
  `reports/blueprints/executive-summary.yaml` MAY be annotated to point at
  `net-sales-growth` as the reference target (a comment noting the now-authored
  structure); it stays a placeholder (backfilling the real binding is owner work,
  FR-011-class).
- **FR-009**: All additions GENERIC (placeholders); no tenant/C086 specifics; ASCII
  + UTF-8 no BOM.
- **FR-010**: NO `retail check` rule added; DEFINE-only. (An optional future rule --
  "a drill_through.target_page resolves to a page in report-composition" -- is a
  deferred follow-up, named not built.)
- **FR-011**: Filling drill/nav/growth values for REAL pages/KPIs (and RULING the comparison-baseline (uncoded) + A11)
  is owner business work, OUT of scope (Principle V). This spec ships the
  fields/structure + honest open-state contracts.

### Key Entities

- **DrillIntent** (on visual-spec): `drill_through{offers,target_page,carried_filters}`
  + `drill_down{hierarchy}` -- names only, intent not execution.
- **ReportComposition** (new): ordered page references + landing + nav + cross-page
  filters.
- **GrowthContract** (new x3): a Non-additive, base-over-base growth metric with the comparison-baseline (uncoded)
  (+A11) flagged undecided/blocking; baseline definition owner-pending.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A filled placeholder visual-spec captures drill-through (target+carried
  filter, by name) + drill-down hierarchy, with no execution field.
- **SC-002**: A filled `report-composition.yaml` references pages by blueprint,
  names a landing page, and records the nav links the vocabulary already references.
- **SC-003**: The three growth contracts are AD1-legal (Non-additive, base-over-base)
  and each flags the comparison-baseline (uncoded) (+A11) undecided/blocking with NO agent-written baseline
  definition. `retail check` (incl. AD1) stays green.
- **SC-004**: The executive-summary `<period-comparison-contract>` placeholder now
  has a real growth-contract structure to reference (dangling promise closed at the
  template/contract level).
- **SC-005**: `retail check` + `test_additivity_consistency` green after the changes.

## Assumptions

- **#5 = structure, not definition**: the growth contracts seal SHAPE + additivity +
  derivation; the comparison-baseline (uncoded) + A11 stay owner-ruled (Principle V). This is the load-bearing honesty
  of the spec.
- **#4 = intent, not execution**: drill/nav fields are design intent; F016 renders.
- **report-composition may be absent-by-design**: confirmed at clarify C2; if so, US2
  shrinks or defers.
- **Template/structure-only scope**: filling real values + ruling the comparison-baseline (uncoded) + A11 deferred
  (FR-011).
- **Ratification pending**: STOPS at a ratify ledger; two feature areas (F011A #4,
  F009 #5) with two risk stories, both listed for the owner's one signature.
