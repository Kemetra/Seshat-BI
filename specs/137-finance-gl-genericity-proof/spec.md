# Feature Specification: Finance GL Budget-vs-Actual Genericity Proof

**Feature Branch**: `137-finance-gl-genericity-proof`

**Created**: 2026-07-30

**Status**: Ratified (Ahmed Shaaban, 2026-07-30)

**Status history**: draft

<!-- Ratification note: the owner ratified the complete planning package (spec + plan +
     tasks) on 2026-07-30 as an explicit human action; the agent transcribed that decision
     and did not self-ratify (Principle V, never_self_grant_approval). Ratification of THIS
     SPEC does not resolve any of OD-1..OD-5, which remain open and blocking, and does not
     grant any readiness stage. -->

<!-- One of: draft | ratified | implemented | superseded (ADR 0019).
     draft       -- authored, not yet ratified by a named human
     ratified    -- a named human approved THE SPEC; record their name and the date
     implemented -- the capability exists on `main`; MUST name its artifact, e.g.
                    `**Status**: implemented -- artifact `src/seshat/foo.py``, and gets a
                    `spec-<NNN>-implemented` claim in docs/quality/status-claims.yaml
     superseded  -- replaced; name the superseding spec id
     When changing this value, move the previous text verbatim into a
     `**Status history**:` line rather than deleting it. -->

**Input**: User description: "Finance GL Budget-vs-Actual genericity proof: the repo's
SECOND worked-example domain, and the first NON-RETAIL one. Executes spec 084's
worked-example-factory recipe and instantiates spec 095's actuals-vs-target pattern in a
finance (P&L budget vs actual) domain, traversing the existing readiness spine Source ->
Mapping -> Silver -> Gold -> Semantic Model -> Dashboard Ready and ending at a committed
data-bound PBIR page. Deliverables: a deterministic offline synthetic generator (seed
20260730); separate Actual and Budget facts at their native grains sharing conformed
dimensions; governed metric contracts using the existing metric-contract template with
zero new fields; deterministic defective fixture variants whose expected governed outcome
uses the existing categorical vocabulary; and a genericity ledger recording every
retail-specific obstruction encountered. The ledger -- not prior assumption -- decides
whether a domain-profile abstraction is ever justified."

## Purpose and Readiness Stage

This feature grows the **example corpus**. It advances no NEW stage semantics and adds no
capability: it drives ONE new subject area (`finance_gl`) through the EXISTING seven-stage
spine as far as **Dashboard Ready**, and records what the kit made hard.

It exists because Constitution Principle VII (`.specify/memory/constitution.md`, "C086 Is
An Example, Not The Schema") asserts that "the templates, this Constitution, and the
architecture MUST stay generic" -- and that assertion has never been falsified, because
every worked example, mapping artifact, and gold star in the repo to date is retail. A
claim that has never been tested is not evidence. This feature is the test.

The result is deliberately two-sided and both sides are a success:

- If the spine runs on finance with few or no forced kit changes, Principle VII is
  vindicated by evidence, and the correct follow-on is **positioning and documentation
  only**.
- If the spine forces genuine semantic changes, the ledger enumerates them, and a
  SEPARATELY approved feature may propose a minimal domain-profile seam.

Neither outcome is assumed here. This feature produces the evidence that decides.

## Boundary against neighbouring specs and shipped work (read first)

Four neighbours must stay distinct, un-duplicated, and un-edited by this feature.

- **Spec 084 (`worked-example-factory`, draft)** owns the worked-example PROCESS: the
  domain-selection method, the artifact list a "complete" example must produce, the
  repo-only completeness tier, and the docs-vs-capability distinction. This feature
  **EXECUTES** that recipe against a finance domain. It does not redefine the recipe, does
  not add a second completeness contract, and does not edit spec 084.
- **Spec 095 (`actuals-vs-target-budget-fact`, draft)** owns the target/budget MODELLING
  PATTERN (`docs/patterns/target-budget-fact.md`) and the variance CONTRACT SHAPE
  (`templates/metric-contract-shape.variance-vs-target.yaml`), walked against a
  HYPOTHETICAL target fact conformed to the retail actuals star, with no rows anywhere.
  This feature is the FIRST instantiation of that pattern with real (synthetic) rows, in a
  different domain. It CITES 095's pattern and shape; it does not restate, fork, or edit
  them, and it does not claim to be 095's implementation.
- **Spec 091 (`semi-additive-snapshot-grain`, draft)** owns semi-additive snapshot /
  balance grain. This feature is **P&L flow only**: additive amounts at journal-line grain
  and additive budget amounts at quarter grain. It models NO balance-sheet snapshot and
  derives NO semi-additive balance inside a journal-line fact. Consequently the genericity
  ledger MUST NOT claim that semi-additive handling was proven generic -- that axis stays
  untested by this feature and belongs to 091.
- **`docs/worked-examples/retail-store-sales.md`** (the kit's only full-spine example)
  stays unedited except for the index row required by FR-030. This feature does not
  re-narrate its stages and does not copy its answers (Principle VII: the questions
  generalize, the answers do not).

## What this feature explicitly does NOT claim (spec 084 User Story 3)

The kit's capability surface -- `src/retail/`, `src/seshat/`, the rule set, the CLI verbs,
the skills -- **does not change**. Only the example corpus grows.

The following statements would each be FALSE after this feature ships and MUST NOT appear
in any artifact, release note, PR body, status claim, or README text produced by it:

- "Seshat BI now supports finance."
- "The kit gained general-ledger / budgeting / variance capability."
- "Seshat is now domain-general" (the LEDGER reports the evidence; it does not confer a
  property).

The honest statement is: *a second, non-retail worked example exists, and the obstructions
it encountered are recorded.*

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An author drives a non-retail domain through the existing spine (Priority: P1)

An author (agent or analyst) has a finance P&L source -- actuals posted at journal-line
grain plus budgets supplied at quarter grain -- and walks the existing readiness spine with
the existing verbs, templates, and gate: profile the source, fill the five mapping
artifacts, clear the mapping gate with a named human approval, author silver and gold SQL,
define metric contracts, and reach a governed semantic model. Every obstruction that is
retail-shaped rather than analysis-shaped is written to the ledger as it is encountered,
with its location and minimal resolution.

**Why this priority**: this is the experiment. Without it, Principle VII remains an
untested assertion and every claim about domain-generality is opinion.

**Independent Test**: hand a fresh agent only the finance clean fixtures and the existing
generic templates (no retail example as a copy source) and confirm it can produce the five
mapping artifacts and a `readiness-status.yaml` record for `finance_gl_actuals` without
inventing a new template and without editing kit code -- and that every place it WANTED to
edit kit code is a ledger row.

**Acceptance Scenarios**:

1. **Given** the clean finance fixtures and the existing mapping templates, **When** the
   author fills the mapping artifacts for `finance_gl_actuals`, **Then** every artifact is
   the existing template filled with finance answers, with zero new template files and
   zero edits to any template.
2. **Given** two source tables at different grains, **When** the author records the grain
   decision, **Then** `finance_gl_actuals` and `finance_gl_budget` each carry their OWN
   declared grain and PK, and no artifact declares a single shared grain for both.
3. **Given** an obstruction encountered mid-walk (for example a template comment,
   checklist item, or rule message that presumes retail vocabulary), **When** the author
   records it, **Then** a ledger row exists naming the file, the observed problem, its
   classification, and the minimal resolution -- and the walk continues rather than
   stopping to redesign the kit.
4. **Given** no live database is available, **When** any stage requires a live check,
   **Then** that leg is recorded as `[PENDING LIVE PROFILE]` and the example is scored
   against spec 084's repo-only completeness tier, never silently marked complete.

---

### User Story 2 - The gate refuses correctly on a domain it was never built for (Priority: P1)

A reviewer wants to know whether the governance layer is genuinely analytical or merely
tuned to retail. Deterministic DEFECTIVE fixture variants are run through the gate: seven
structural defects that a static/mechanical check should catch, and six business-judgment
cases where the only correct behaviour is to stop and ask a named human.

**Why this priority**: a gate that passes everything in a new domain is not general, it is
blind; a gate that refuses everything is not general either, it is paralysed. Both failure
modes must be observable, and the repo already has the vocabulary to observe them.

**Independent Test**: run each defective variant and confirm the observed behaviour equals
the declared expected behaviour drawn from the existing categorical set
(`proceed`, `refuse`, `block_for_evidence`, `request_human_decision`) -- with
over-refusal counted as a failure, not a success.

**Acceptance Scenarios**:

1. **Given** the structural defect variants (unknown account code, unknown department
   code, irreconcilable actual-vs-budget account hierarchy, missing/invalid fiscal period,
   mixed currency with no approved conversion policy, duplicate journal-line identifier,
   budget row violating quarterly grain), **When** each is run through the existing static
   gate and mapping checks, **Then** each produces its declared expected outcome and names
   the specific offending rows or columns.
2. **Given** the business-judgment variants (ambiguous debit/credit presentation,
   ambiguous revenue sign convention, Original-Budget vs Latest-Forecast baseline
   ambiguity, monthly reporting requested from quarterly budget with no allocation policy,
   actuals present with no budget row, a new budget version that would overwrite history),
   **When** each is encountered, **Then** the outcome is `request_human_decision` or
   `block_for_evidence` with a named open question -- never a silently chosen default and
   never a self-granted approval.
3. **Given** a department that legitimately has a budget but no actual transactions in the
   period, **When** the checks run, **Then** this is reported as a business exception
   surfaced to the report, NOT as a mapping failure or a data defect.
4. **Given** the six business-judgment variants, **When** they are registered as scenarios
   in the existing benchmark scenario format, **Then** each declares one expected
   behaviour from the existing categorical set and cites the observable evidence for it.

---

### User Story 3 - The journey finishes in a committed, data-bound report page (Priority: P2)

The owner wants one subject area that reaches an actual report artifact rather than an
approved design document. After metric contracts are approved, an executive P&L page is
authored and committed as PBIR, with each visual bound to exactly one approved contract.

**Why this priority**: the repo currently contains zero committed report visuals
(`find powerbi -name visual.json` returns 0), so "Dashboard Ready" has to date always
meant an approved DESIGN. Finishing once, in the new domain, makes the corpus honest.
It is P2 rather than P1 because it depends on US1 and on a human authoring action, so US1
plus US2 alone still deliver a complete genericity verdict.

**Independent Test**: confirm one committed PBIR page exists whose every visual resolves
to an approved metric contract, and that the binding validation passes without any visual
referencing an unapproved or non-existent measure.

**Acceptance Scenarios**:

1. **Given** approved metric contracts, **When** the executive page is authored, **Then**
   every visual on it binds to exactly one approved contract, and a binding map records
   each visual-to-contract pair.
2. **Given** the current authoring boundary, **When** the plan names each intended visual,
   **Then** each is classified as adapter-bindable or human-only, with the boundary cited
   from the committed adapter documentation rather than assumed.
3. **Given** the page is committed, **When** readiness is recomputed, **Then** Dashboard
   Ready is derived from the committed artifacts, and Publish Ready remains explicitly out
   of scope and unclaimed.

---

### User Story 4 - A reviewer can tell example growth from capability growth (Priority: P2)

Someone reading the PR, the release notes, or the worked-example index after this feature
lands can determine in one read that no capability was added, and cannot smuggle a
"Seshat now supports finance" claim past review.

**Why this priority**: this is the specific misrepresentation risk spec 084 User Story 3
names, and it is cheap to prevent at authoring time and expensive to retract later.

**Independent Test**: diff the feature's branch and confirm zero changes under the rule
registry and zero new or renamed CLI verbs or skills; then confirm every claim text the
feature introduces is scoped to "an example exists" rather than "a capability exists".

**Acceptance Scenarios**:

1. **Given** the completed feature, **When** the diff is reviewed, **Then** no rule module
   is added, removed, or renamed, no CLI verb is added or renamed, and no skill directory
   is added or renamed.
2. **Given** the ledger's conclusion, **When** it is written, **Then** it reports
   classified obstruction rows and a categorical conclusion, with NO numeric confidence,
   health, maturity, readiness, or genericity score anywhere.

### Edge Cases

- **A defect variant fires no rule at all.** That is a RESULT, not a bug to hide: it is
  recorded as a ledger row (the gate is silent where a general analytical gate arguably
  should speak) and the corresponding benchmark scenario records the observed behaviour
  honestly rather than being deleted to keep the run green.
- **An obstruction is ambiguous between nominal and semantic.** The ledger records the
  MORE conservative classification (`semantic_leak`) plus the reason, so Phase-2 scoping
  never under-counts.
- **The same obstruction recurs at several stages.** It is one ledger row with multiple
  cited locations, never one row per sighting (row inflation would fake the evidence).
- **A stage cannot be reached at all.** The stage's verdict records the blocker with
  evidence and the ledger carries a row; an unreachable stage is a finding, not a failure
  of the feature.
- **Fiscal-calendar and posting dates disagree** (a posting date lands outside every
  declared fiscal period). Treated as a structural defect variant, not silently coerced.
- **Regeneration produces different bytes.** The generator is defective until byte
  identity holds; no downstream artifact is authored from a non-reproducible fixture.

## Requirements *(mandatory)*

### Functional Requirements

**Source generation (deterministic, offline, synthetic)**

- **FR-001**: The feature MUST provide a synthetic source generator whose only inputs are
  a fixed seed (`20260730`) and declared shape parameters -- no network access, no
  database connection, and no current-clock or random-UUID input.
- **FR-002**: Repeated generation with the same seed MUST produce byte-identical files:
  stable row order, stable date formatting, stable numeric formatting, stable line endings.
- **FR-003**: The generator MUST emit five clean sources: `finance_gl_actuals`,
  `finance_gl_budget`, `accounts`, `departments`, `fiscal_calendar`.
- **FR-004**: Generated content MUST contain no real company data, no personal data, no
  secrets, no local absolute paths, and no third-party dataset committed into the repo.
  External finance standards MAY inform the SHAPE (chart-of-accounts structure, fiscal
  period conventions) but MUST NOT be committed as data.
- **FR-005**: The shape MUST cover approximately 2 fiscal years, 30 accounts, 6
  departments, 4-8 cost centers, ~5,000 journal lines, quarterly budgets, and at least 2
  budget versions -- enough to exercise the grain mismatch without becoming a bulk data
  commit.
- **FR-006**: Each defective variant MUST isolate exactly ONE defect, so an observed outcome
  attributes to a single cause. Variants that are expressible as DATA (a bad row, a missing
  reference, a duplicate key) MUST be separate, deterministic, minimal perturbations of the
  clean fixture. Variants that are NOT data states -- a question about presentation, or an
  attempted action a human frames -- MUST instead be declared as scenarios in the existing
  benchmark format. Which variant is expressed which way is declared once, in the feature's
  variant-expression map, and neither form may be silently substituted for the other.

**Grain and model integrity**

- **FR-007**: `finance_gl_actuals` MUST declare its own grain (journal entry x journal line
  x account x department x posting date) and its own primary key.
- **FR-008**: `finance_gl_budget` MUST declare its own grain (fiscal quarter x account x
  department x budget version) and its own primary key, distinct from the actuals grain.
- **FR-009**: Actuals and budget MUST be modelled as SEPARATE gold facts sharing conformed
  `dim_date`, `dim_account`, and `dim_department`, following the existing conformed-
  dimension convention (including the existing unknown-member convention) rather than
  building parallel dimensions.
- **FR-010**: Actuals MAY be aggregated UPWARD to the budget comparison grain. Budget MUST
  NOT be disaggregated downward to month or line grain unless a named human has approved an
  explicit allocation policy; absent that approval the request is refused with the reason
  named.
- **FR-011**: Budget version MUST be preserved as part of budget identity. A new version
  MUST NOT overwrite or silently supersede a prior version's rows.

**Metrics**

- **FR-012**: Metric contracts MUST be authored for: Actual Amount, Budget Amount,
  Variance Amount, Variance %, Actual YTD, Budget YTD, and Missing Budget Flag.
- **FR-013**: Every contract MUST use the EXISTING metric-contract template field set with
  zero new fields, zero renamed fields, and no forked template.
- **FR-014**: Actual and Budget MUST aggregate separately, with Variance % computed AFTER
  aggregation. Averaging precomputed variance percentages MUST be prohibited in the
  contract's stated intent.
- **FR-015**: Missing budget MUST be distinguishable from zero budget in both the contract
  semantics and the report surface.
- **FR-016**: Debit/credit presentation and revenue sign convention MUST each be an open,
  named decision requiring a human ruling; the feature MUST NOT choose one as a default.
- **FR-017**: Where the comparison baseline could mean Original Budget, Revised Budget, or
  Latest Forecast, the ambiguity MUST be recorded as an open decision and MUST block
  finalisation of the affected contract until a named human rules.
- **FR-018**: The feature MUST NOT invent RAG thresholds, financial targets, exchange-rate
  policy, account sign policy, allocation method, a preferred budget version, or any fiscal
  policy not supported by committed evidence.

**Governance behaviour**

- **FR-019**: Every readiness verdict MUST derive from committed evidence; no stage may be
  marked passed on the strength of narrative.
- **FR-020**: No approval anywhere in this feature may be self-granted. Every approval
  records a named human and a date, or the stage stays blocked.
- **FR-021**: Each defective variant MUST declare exactly one expected outcome from the
  existing categorical set (`proceed`, `refuse`, `block_for_evidence`,
  `request_human_decision`) plus the observable evidence for it.
- **FR-022**: The six business-judgment variants MUST be registered as scenarios in the
  EXISTING benchmark scenario format (no new format, no new runner), so the refusal
  behaviour is repeatably observable.
- **FR-023**: Over-refusal MUST be treated as a failure outcome, not a safe default.
- **FR-024**: The feature MUST emit no numeric confidence, health, maturity, readiness, or
  genericity score in any artifact.

**Dashboard**

- **FR-025**: The feature MUST end with one committed report page ("Executive P&L
  Overview") covering: Actual Amount, Budget Amount, Variance Amount and Variance % as
  cards; an actual-vs-budget trend; variance by department; an account-hierarchy matrix;
  and a missing-budget exceptions table.
- **FR-026**: Every visual MUST bind to exactly one approved metric contract, recorded in a
  visual-to-contract binding map.
- **FR-027**: The authoring boundary MUST be represented honestly: each intended visual is
  classified adapter-bindable or human-only against the committed adapter documentation.
  Power BI Service publishing and any Power BI MCP mutation are OUT of scope.

**Ledger and registries**

- **FR-028**: The feature MUST produce `docs/worked-examples/finance-gl-genericity-ledger.md`
  where every obstruction records: location, observed problem, classification, existing rule
  or surface, minimal resolution, whether a core change is required, and evidence.
- **FR-029**: Classification MUST be exactly one of `no_leak`, `nominal_leak`,
  `documentation_leak`, `semantic_leak`, `authority_leak`. No numeric leak threshold may be
  used, and the ledger's conclusion MUST be categorical.
- **FR-030**: The feature MUST register itself in the repo's existing declaration surfaces
  wherever their completeness contracts require it -- the worked-example index, the
  doc-anchored status-claims surface, and the capability manifest -- WITHOUT creating any new
  registry and without declaring a capability that does not exist.
- **FR-031**: The feature MUST NOT rename any `retail-*` verb, add any command alias, add
  any finance-specific command surface, add any rule, add any dependency, or change any
  readiness or approval semantics.
- **FR-032**: Domain-profile extraction MUST NOT be implemented by this feature. The
  completed ledger is the sole input that decides whether a separately approved feature
  proposes such a seam.

### Key Entities

- **Finance GL Actuals source**: posted journal lines. Attributes: journal entry id, line
  id, posting date, account code, department code, cost center code, currency code, debit
  amount, credit amount, description. Additive P&L flow amounts only.
- **Finance GL Budget source**: planned amounts at coarser grain. Attributes: fiscal year,
  fiscal quarter, account code, department code, budget version, currency code, budget
  amount.
- **Reference sources**: accounts (code, name, type, parent for hierarchy), departments
  (code, name, cost centers), fiscal calendar (period boundaries for two years).
- **Conformed dimensions**: `dim_date`, `dim_account`, `dim_department` -- shared by both
  facts, with the existing surrogate-key and unknown-member conventions.
- **Gold facts**: `fact_gl_actuals` (line grain), `fact_gl_budget` (quarter grain) -- two
  facts, never merged.
- **Metric contract**: the existing contract entity, filled for the seven metrics.
- **Defect variant**: a named, minimal, deterministic perturbation plus its declared
  expected governed outcome and observable evidence.
- **Genericity ledger row**: one obstruction with location, classification, minimal
  resolution, and evidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reader can determine, from the ledger alone, whether the readiness workflow
  required core changes to run a non-retail domain -- without reading any other document.
- **SC-002**: Regenerating the fixtures from the same seed twice produces byte-identical
  output, verified by comparison rather than assertion.
- **SC-003**: Every one of the 13 declared defect variants has a declared expected outcome
  and an observed outcome, and every mismatch (including over-refusal) is reported rather
  than suppressed.
- **SC-004**: Actuals and budget remain two facts at two declared grains through every
  stage; no artifact declares a merged grain.
- **SC-005**: Every business judgment named in this spec is either resolved by a named
  human with a recorded date, or visibly open and blocking. None is silently defaulted.
- **SC-006**: One committed report page exists in which every visual traces to exactly one
  approved metric contract.
- **SC-007**: The feature's diff contains zero rule-registry changes, zero CLI verb changes,
  and zero skill additions or renames.
- **SC-008**: No artifact produced by the feature contains a numeric confidence, health,
  maturity, readiness, or genericity score.
- **SC-009**: Every stage the example could not reach is recorded as a blocker with evidence
  and a ledger row, so an incomplete traversal is legible as a finding.
- **SC-010**: A reviewer reading only the PR body and the ledger conclusion cannot mistake
  the outcome for "the kit gained finance capability".

## Open owner decisions (approval-gated; NOT spec ambiguity)

These are Principle V judgment calls the feature is REQUIRED to leave open until a named
human supplies their CONTENT. They are listed here so review does not mistake them for gaps
in this specification.

Three were ruled on 2026-07-30. Each ruling below is TRANSCRIBED from the owner's explicit
answer; the agent supplied the options and the recommendation, never the decision
(Principle V, never_self_grant_approval).

- **OD-1 -- RESOLVED (Ahmed Shaaban, 2026-07-30)**: revenue and expenses are both PRESENTED
  as positive magnitudes. Whether higher is better is carried by each metric contract's
  existing `direction_of_good` field, never by the arithmetic sign. The GL's own debit/credit
  posting is unchanged in silver/gold; this ruling governs PRESENTATION only. Consequence:
  the Variance % sign alone does not indicate good or bad -- every variance visual and
  contract must state the direction explicitly.
- **OD-2 -- RESOLVED (Ahmed Shaaban, 2026-07-30)**: the variance BASELINE is the `ORIGINAL`
  budget version -- the plan of record. `REVISION-1` remains present in the fixture and is
  exercised for version identity (FR-011) and for the baseline-ambiguity variant D10, but it
  does NOT move the headline Variance Amount / Variance % measures. Consequence: every
  variance contract names `budget_version = ORIGINAL` in its stated intent, so the baseline
  cannot drift silently when a later version lands.
- **OD-3 -- RESOLVED (Ahmed Shaaban, 2026-07-30)**: no monthly view may be derived from the
  quarterly budget. Monthly ACTUALS may be displayed; budget and variance are reported at
  quarter grain only. A monthly-budget request is REFUSED with the reason named, which is
  exactly the outcome defect variant D11 declares. No allocation policy exists, and none may
  be inferred.
- **OD-4 -- STILL OPEN**: the mapping-gate approval for each finance table. This one CANNOT
  be pre-granted: the maps do not exist yet (they are authored in Slice C), and the gate's
  purpose is that a named human reviewed the declared grain and PK BEFORE any silver SQL is
  authored. Approving an artifact that does not exist would be a blank cheque, not an
  approval.
- **OD-5 -- STILL OPEN (an action, not an approval)**: the human report-authoring session in
  Power BI Desktop that US3 depends on. It cannot be delegated or approved away -- the PBIR
  adapter creates and binds no visuals.

## Assumptions

- The fiscal calendar is treated as calendar-aligned (January-December, four quarters) in
  the synthetic fixture. This is a FIXTURE simplification, recorded as such; it is not a
  claim that finance calendars are calendar-aligned in general, and the
  fiscal-period-mismatch defect variant exists precisely so the assumption is not
  load-bearing.
- Amounts are single-currency in the clean fixture, with mixed currency isolated to one
  defect variant, so currency policy is a governed decision rather than a modelling default.
- No live database is assumed. Live legs are recorded as `[PENDING LIVE PROFILE]` and the
  example is scored against spec 084's repo-only completeness tier.
- The six business-judgment variants are in scope as benchmark scenarios in the existing
  format; extending the benchmark's runner, participants, or output format is not.
- Whether the generated files are committed or generated at verification time is an
  implementation decision to be made in planning ON THE EVIDENCE of existing fixture sizes
  and the repository's raw-data safeguards -- not by preference.
- Spec 084 and spec 095 remain `draft`. This feature depends on their CONTENT (the recipe,
  the pattern, the contract shape), which is committed and readable, not on their ratified
  status; it does not ratify, edit, or supersede either.
- The example's subject-area name (`finance_gl`) and any report or page names are kept short
  to stay inside the Windows path-length limit that governs project artifacts in this repo.
