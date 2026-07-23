# Feature Specification: analyst-narrative layer -- decision-driven design on top of the correctness gates

**Feature Branch**: `021-analyst-narrative-layer` (work on `main` per session convention; located via `.specify/feature.json`)

**Created**: 2026-07-23

**Status**: Draft

**Input**: Issue #452 ("Analyst-narrative design layer for powerbi-workflows -- combined-analyst vs traditional view"). Owner verdict from a real dogfooding review of a 4-page / 36-visual report whose every binding was valid and every KPI approved: the build "lacks the spirit of an analyst... made as a computer." Four confirmed sub-gaps: (1) no decision-questions driving design, (2) no analytical framing/comparisons, (3) no narrative/story order, (4) not domain-specific.

## Why this feature exists

F011 (`012-dashboard-design-skill`) shipped the **correctness** layer of Stage 6:
design FROM approved metric contracts, a visual->contract binding map with no
orphans, hard gates (no contracts -> no design; author, never publish). It works:
the dogfooding report that motivated this spec passed every one of those gates.

And it was still the wrong deliverable. The agent produced what the dashboard
literature calls a *monitoring* display (Few: "the most important information...
at a glance") when the owner needed a *decision* instrument (Eckerson: dashboards
must enable action, not observation). Given approved measures and dimensions, the
agent's default is the mechanically valid arrangement -- "measure x dimension ->
grid of totals" -- because nothing in the kit supplies the judgment layer that
turns approved numbers into an analysis:

- **No decision-questions.** Visuals are chosen from what exists, not from what
  the owner must decide (where do I push, what is leaking, is growth price or
  volume, where are returns concentrated).
- **No comparison framing.** A KPI card shows `39M`; it does not say whether 39M
  is good, what moved, or against what baseline. Raw totals carry no signal.
- **No story order.** Pages are topic buckets, not an arc (overview -> what
  changed -> why/where -> action).
- **No domain grounding.** Generic retail visuals, blind to what the profiled
  data specifically supports (its segments, its return signal, its seasonality).

This is a skill-content gap, not an agent defect: `retail-kpi-knowledge` defines
WHAT metrics mean, `dashboard-design`/`powerbi-workflows` gate WHERE numbers may
appear, and nothing teaches HOW an analyst frames them. The fix is the same
posture the kit always takes -- put the judgment in reviewable, gated artifacts.

## The hard gate (the load this feature respects)

Everything F011 enforces stays enforced, unchanged:

- **No approved contracts -> no design** (roadmap rule 5). The narrative layer
  runs strictly AFTER `semantic_model_ready: pass`; it frames approved numbers
  and never invents a metric, a number, or a meaning (Principles I, V).
- **Author, never publish** (roadmap rule 6). All outputs are committed text for
  human review. No PBIR automation implication; F016 stays walled off.
- **The named human still decides.** The new helper is read-only and categorical;
  it emits no score and grants no approval (Principle VIII). A clean check is
  evidence FOR the design review, never a substitute for it.

One NEW gate is added on top:

- **No layout before narrative.** A design that binds visuals to contracts but
  cannot say which owner decision each page serves is now itself a gap. The
  narrative brief must exist and be committed BEFORE layout/visual guidance is
  authored, exactly as contracts must exist before design.
- **A question the data cannot answer is a [GAP], never a visual.** Margin
  without a cost column, turnover without inventory, target attainment without a
  target feed: the brief states the owner question + the missing source fact +
  the feed that would unlock it, and stops (Principle V).

## Architecture (knowledge + skill route + read-only checker; no codegen)

Three components, matching how the kit already grows (Principle II: depend on
the shipped shapes, never fork them):

1. **Knowledge pack `knowledge/bi-analyst-knowledge/`** (naming follows
   `bi-sql-knowledge`, `bi-dax-knowledge`; INDEX.md + routed cards):
   - **Framing catalog** -- eight core framings, one card each: trend+anomaly,
     period variance (YoY/PoP/YTD-pace), contribution & mix-shift,
     concentration (Pareto/ABC), rate decomposition (a headline total
     decomposed into its driver rates -- domain instances live in the
     examples, never in the card), segment behavior, benchmark & threshold, and
     **signal vs noise (statistical guardrails)**. Each card: the question
     shape it answers -> required inputs (contract kinds + dims) -> visual
     guidance -> a statistical guardrail -> a "so-what" sentence template.
   - **Statistical guardrails** -- owner-grade methods only, integrated per
     card (not a separate stats pack): control bands (trailing mean +/- k x
     dispersion) for anomaly claims, seasonality-aware comparison (same period
     last year, not adjacent period) for variance claims, minimum-sample
     caveats for rate claims (a rate over too few lines is reported as
     insufficient-sample, not as a finding), and correlation-vs-causation
     caution on any driver-relationship claim. A band or trailing average is
     a DISPLAY DERIVATION of an approved measure -- allowed and labeled as
     such -- never a new metric; anything beyond these (regression,
     significance tests) is out of scope for v1.
   - **Decision-question derivation route** -- derive RANKED owner questions
     from exactly two committed inputs: the approved metric contracts and the
     committed source-profile. Grounded-only rule: a question may reference
     only measures/dims/facts those two artifacts contain.
   - **Story-order rule** -- overview -> what changed -> why/where -> action,
     carrying the five decision-driven elements (priority, thresholds, signals,
     driver relationships, action cues).
   - **Two worked examples** (Principle VII: examples, not the schema): the
     sanitized C086 pharmacy-retail redesign (born from the #452 review) and a
     generic retail weekly-business-review example.
2. **Skill route change** -- `dashboard-design` (and its marketplace mirror in
   `powerbi-workflows`) gains a MANDATORY first step: author the narrative
   brief, get it committed, THEN author layout guidance. The binding map
   becomes three-way -- **visual -> contract -> decision-question** -- and an
   orphan visual (bound but answering no question) is a defect of the same
   class as an unbound visual.
3. **Read-only checker** -- extend the installed design-helper family
   (`dashboard-gaps` / `pbir-validate-blueprint`) with a narrative check over
   the committed brief + design guidance: every page names >=1
   decision-question; every data-bound visual traces to (contract, question);
   every headline visual carries a named comparison framing; story order is
   declared; [GAP] items are stated, not visualized. Categorical findings with
   named blockers; fail-closed on unreadable/malformed input (the #453 lesson:
   a design helper must never silently classify nothing and exit 0).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Author a narrative brief from approved contracts (Priority: P1)

A data analyst (or the agent on their behalf) has a table at
`semantic_model_ready: pass` with approved metric contracts. Before any layout
work, they follow the `bi-analyst-knowledge` derivation route and author
`mappings/<table>/narrative-brief.md`: ranked decision-questions, one framing
per question from the catalog, a page/story order, and callout slots. The brief
cites only committed evidence and is reviewed by the named design reviewer.

**Why this priority**: This artifact IS the feature -- the judgment layer #452
found missing. Without it the other two components have nothing to route or
check.

**Independent Test**: On the C086 example workspace (contracts approved), follow
the route and produce a brief; verify every question references only approved
measures/dims and every framing names its catalog card.

**Acceptance Scenarios**:

1. **Given** approved contracts + a committed source-profile, **When** the route
   is followed, **Then** a narrative brief exists whose every decision-question
   cites only measures/dims/facts present in those two artifacts.
2. **Given** an owner question the data cannot answer (e.g. margin with no cost
   column), **When** the brief is authored, **Then** the question appears as a
   [GAP] entry (question + missing source fact + unlocking feed) and no visual
   is proposed for it.
3. **Given** `semantic_model_ready` is not `pass`, **When** the narrative step
   is attempted, **Then** the skill records the blocked stage and STOPS without
   authoring a brief.

---

### User Story 2 - Design guidance is narrative-gated and three-way bound (Priority: P1)

With a committed narrative brief, the `dashboard-design` route authors layout
and visual guidance where every data-bound visual traces to exactly one
approved contract AND exactly one decision-question from the brief, and pages
follow the brief's story order. Headline visuals (KPI cards) each carry a
comparison framing -- a bare total with no comparison is a defect.

**Why this priority**: This is where the judgment becomes enforceable structure.
The three-way map is the difference between "correct" (F011) and "analytical"
(this feature) being checkable at all.

**Independent Test**: Author design guidance from a brief on the C086 example;
verify the binding map lists (visual, contract, question) triples with no
orphans in either direction.

**Acceptance Scenarios**:

1. **Given** a committed brief, **When** design guidance is authored, **Then**
   its binding map is three-way and every page opens with the decision it
   serves.
2. **Given** no committed brief, **When** layout authoring is attempted,
   **Then** the route stops and names the missing brief as the blocker.
3. **Given** a proposed KPI card with no comparison framing, **When** the design
   is reviewed against the route, **Then** the card is flagged as a
   raw-total defect with the catalog framings offered as fixes.

---

### User Story 3 - Read-only narrative check before the design review (Priority: P2)

Before requesting the named human's design review, the agent runs the installed
narrative check against the committed brief + design guidance. It reports
categorical findings (missing question on page N, orphan visual X, headline Y
without comparison, undeclared story order, [GAP] item Z rendered as a visual)
with named blockers, and exits fail-closed on malformed input.

**Why this priority**: Automates the tedious completeness pass so the human
review spends judgment on the analysis itself; P2 because Stories 1-2 deliver
the value even reviewed fully by hand.

**Independent Test**: Run the checker against (a) the shipped worked example
(expect clean), (b) a mutated copy with one orphan visual and one bare KPI
(expect exactly those two findings, non-zero exit).

**Acceptance Scenarios**:

1. **Given** a complete brief + guidance, **When** the check runs, **Then** it
   reports no findings and exits 0, and the output states this is evidence for
   review, not an approval.
2. **Given** a visual bound to a contract but no question, **When** the check
   runs, **Then** it names the orphan visual and exits non-zero.
3. **Given** an unreadable or schema-invalid brief, **When** the check runs,
   **Then** it fails closed naming the parse problem (never "no items
   classified" with exit 0).

---

### Edge Cases

- A table whose approved contracts are all non-additive ratios: the catalog's
  contribution/Pareto framings are inapplicable -- the route must say which
  framings the contract set supports instead of forcing them.
- Two decision-questions answered by the same visual: allowed, but the map must
  list both triples explicitly (no implicit reuse).
- A brief authored against contracts that are later re-approved with changed
  meaning: the brief cites contract identities; the checker flags stale
  citations rather than silently passing (same posture as dbt model citations).
- Single-page reports: story order still applies within the page (zones), not
  across pages.
- A dataset with no date dimension: trend/variance framings are [GAP]-like --
  the route states why time framings are unavailable rather than omitting them
  silently.
- A rate framed over a thin slice (e.g. ReturnRate on a segment with a handful
  of lines): the guardrail reports insufficient-sample instead of presenting
  the rate as a finding -- a confident number on noise is the statistical twin
  of an invented metric.
- An anomaly callout on a series too short for a stable band (e.g. weeks of
  history for a monthly band): the card requires stating the band's basis;
  too little history -> the anomaly claim is withheld, the trend shown plain.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The kit MUST ship `knowledge/bi-analyst-knowledge/` with an
  INDEX.md routing to: the framing catalog (eight cards), the decision-question
  derivation route, the story-order rule, and two worked examples.
- **FR-002**: Each framing card MUST state: question shape, required inputs
  (contract kinds + dimension attributes), visual guidance, a statistical
  guardrail, and a "so-what" sentence template -- and MUST NOT define any
  metric meaning (that stays in contracts and `retail-kpi-knowledge`).
- **FR-002a**: Statistical guardrails MUST be owner-grade and bounded: control
  bands and trailing averages (labeled display derivations of approved
  measures), seasonality-aware comparisons, minimum-sample caveats for rates,
  and correlation-vs-causation caution -- and MUST NOT introduce methods that
  compute new business meaning (regression, forecasting, significance testing
  are out of scope for v1).
- **FR-003**: The derivation route MUST bound question sources to exactly two
  committed artifacts (approved metric contracts, source-profile) and MUST
  route unanswerable questions to [GAP] entries (question + missing source
  fact + unlocking feed).
- **FR-004**: The `dashboard-design` skill (and the `powerbi-workflows`
  marketplace mirror) MUST require a committed `mappings/<table>/
  narrative-brief.md` before authoring layout/visual guidance, and MUST stop
  with a named blocker when it is absent.
- **FR-005**: Design guidance MUST carry a three-way binding map (visual ->
  contract -> decision-question); an orphan in either direction is a defect.
- **FR-006**: Every headline (KPI-card class) visual in design guidance MUST
  name its comparison framing from the catalog; a bare total is a defect.
- **FR-007**: The installed helper family MUST gain a read-only narrative check
  over brief + guidance reporting categorical findings with named blockers,
  emitting no score and granting no approval.
- **FR-008**: The narrative check MUST fail closed (non-zero, named parse
  problem) on missing, unreadable, or schema-invalid input -- never exit 0
  having classified nothing.
- **FR-009**: The narrative brief and the three-way map MUST be committed,
  reviewable text artifacts; the named human design review remains the only
  approval (no self-granted pass, no numeric confidence).
- **FR-010**: All narrative artifacts MUST carry zero secrets, DSNs, PII, or
  absolute local paths (Principle IX), and worked examples MUST be sanitized
  (Principle VII).

### Key Entities

- **Narrative brief**: committed markdown at `mappings/<table>/
  narrative-brief.md`; ranked decision-questions, framing per question, story
  order, callout slots, [GAP] entries. Authored after contracts, before layout.
- **Decision-question**: one owner decision the data can inform; cites only
  approved measures/dims + profiled facts; ranked by owner priority.
- **Framing card**: one catalog entry in `bi-analyst-knowledge` (question shape
  -> inputs -> visual guidance -> so-what template). Defines HOW to frame,
  never WHAT a metric means.
- **Three-way binding map**: the F011 binding map extended to (visual,
  contract, decision-question) triples; orphan-free in both directions.
- **[GAP] entry**: an unanswerable owner question recorded as question +
  missing source fact + unlocking feed; the honest boundary of the analysis.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a workspace with approved contracts, following the routes
  yields a committed narrative brief whose every question cites only approved
  measures/dims -- verified on the C086 example end to end.
- **SC-002**: Design guidance produced after this feature contains zero orphan
  visuals (no question) and zero bare-total headlines, as reported by the
  narrative check on the shipped worked example.
- **SC-003**: The narrative check distinguishes the three outcome classes on
  fixtures: clean (exit 0), findings (non-zero with named items), malformed
  input (fail-closed with parse problem) -- no silent-nothing outcome exists.
- **SC-004**: An external reviewer comparing the worked example's "traditional
  baseline" pages to its analyst redesign can trace every redesigned visual to
  a decision-question and a framing card -- the #452 four sub-gaps each have a
  named countermeasure in the shipped routes.

## Assumptions

- F009 (metric-contract store), F010 (semantic-model readiness), and F011
  (dashboard-design skill) remain the substrate; this feature only adds the
  judgment layer between F010's pass and F011's layout step.
- The narrative check follows the installed-helper family's conventions
  (read-only, categorical findings, named blockers, fail-closed); the plan
  settles its shape as a small dedicated verb (`seshat narrative-check`)
  rather than overloading `dashboard-gaps`, whose page-intent surface is
  under repair in #453.
- The brief's location follows the mapping-artifact convention
  (`mappings/<table>/`); multi-table subject areas are out of scope for v1 and
  compose as one brief per table.
- Issues #453 (page-intent parse fails open) and #454 (offline PBIR binding
  validator) are separate fixes; this feature's checker composes with them but
  does not implement them.
- Sanitization of the C086 worked example (generic divisions, no client
  numbers, no PII) happens at authoring time under Principles VII and IX.
