# Feature Specification: Non-Duplicate Dashboard Planner -- read-only categorical new/extends/duplicate verdict on a proposed dashboard idea

**Feature Branch**: `116-dashboard-duplicate-planner`

**Created**: 2026-07-09

**Status**: Draft

**Input**: User description: "Non-Duplicate Dashboard Planner -- a read-only agent surface that, given a PROPOSED dashboard/report idea for a subject area, returns a CATEGORICAL verdict -- new / extends <existing page> / duplicate of <existing page> -- by comparing the proposal against the already-committed dashboard artifacts for that table (the committed page layout, visual list, and visual->contract binding map). It writes nothing, grants no approval, moves no readiness stage, invents no metric. It answers the owner's real pain: is this new dashboard idea actually new, or a repeat of one we already have?"

## Clarifications

### Session 2026-07-09

- Q: What EXACTLY is the committed comparison corpus, and at what unit is a match
  decided? -> A: The corpus is the one target table's committed design directory
  `mappings/<table>/design/`: `dashboard-layout.md` (the page/section structure +
  analyst business questions), `visual-list.md` (the proposed visuals), and
  `visual-contract-binding-map.md` (each visual -> exactly one approved contract +
  the mapped dimension field). The unit of comparison is a committed PAGE,
  characterized as the SET of its `(business_question, bound_contract, dimension)`
  tuples read from those files. Cross-table / whole-repo deduplication is OUT of
  scope -- the planner compares one proposal against one table's design dir only.
- Q: How is the verdict decided without computing a similarity/overlap score
  (hard rule #9)? -> A: The verdict is a DETERMINISTIC SET RELATIONSHIP over the
  committed tuples, never a threshold on an overlap percentage. The proposal is
  reduced to the same `(business_question?, bound_contract, dimension)` tuple shape
  it supplies. For a committed page P: `duplicate of P` iff the proposal has >=1
  readable tuple AND shares >=1 tuple with P AND EVERY proposal tuple is already
  covered by P's tuple set; `extends P` iff the proposal shares >=1 tuple with P
  AND adds >=1 tuple absent from P; `new` iff the proposal shares no
  `(bound_contract, dimension)` tuple with ANY committed page (this includes an
  empty / no-readable-tuple proposal -- nothing to match is `new`, never a
  vacuously-true duplicate). The three verdicts are mutually exclusive and
  exhaustive. Across multiple
  matching pages, precedence is `duplicate` > `extends` > `new`, naming the matched
  page. There is NO computed overlap number, NO threshold, and NO ranking; the
  decision reduces to set membership over committed facts. If a rule ever needed
  ">= N% overlap" it would be a smuggled score and is forbidden.
- Q: What is the output vehicle -- a printed view or a written companion file? ->
  A: PRINT-ONLY (with an optional `--format json` machine shape). The planner is a
  pre-design triage answer, not a durable disclosure artifact; writing a file into
  `mappings/<table>/design/` would conflate the transient triage with the committed
  corpus it reads. "Writes nothing" is thus a STRUCTURAL guarantee (grep-verifiable
  zero write calls), matching the three shipped read-only surfaces (`approval_inbox`,
  `blocker_explainer`, `run_next`) -- distinct from F040 / spec 114, which DO write
  a companion file because their output is a durable published disclosure.
- Q: What if the target table has NO committed dashboard design yet? -> A: Every
  proposal is `new` BY ABSENCE. The planner explicitly names the absent corpus path
  so the reader understands "new" here means "no committed page exists to compare
  against", NOT "compared against pages and found distinct". Absence is neither
  fabrication nor failure; it is an honest robustness signal (mirrors the P2 story
  of specs 114/115).
- Q: What shape is the PROPOSED dashboard idea, the transient input? -> A: A
  caller-supplied proposal for a named subject area: a free-text description PLUS an
  optional structured list of proposed `(business_question, measure/contract,
  dimension)` tuples (the same tuple shape the corpus exposes). The classifier
  reduces the proposal to tuples and classifies WHAT IS GIVEN; it does NOT invent,
  expand, or enrich the proposal's content, and it does NOT invent a metric to fill
  a gap. This transient proposal-in is the ONE structural difference from specs
  114/115 (which read only committed files) and is exactly idea-engine's shape (a
  rough idea in -> a categorical verdict out).

## Why this feature exists

An owner who has already built one dashboard for a subject area and is handed a
NEW dashboard idea has a real, recurring question: "is this genuinely new, or a
repeat of a page we already have?" Today the evidence needed to answer it is
already committed -- for `retail_store_sales` the design directory
`mappings/retail_store_sales/design/` holds `dashboard-layout.md` (a single
executive overview page whose regions each answer a business question Q1-Q6),
`visual-list.md` (10 measure-bearing visuals, each answering one question), and
`visual-contract-binding-map.md` (each visual bound to exactly one of the 5
approved metric contracts by name plus its mapped dimension field). That is a
precise, machine-readable inventory of "what pages, answering what questions,
over what measures and dimensions, already exist."

But NO shipped surface reads that inventory to triage a NEW proposal against it.
The proven verdict mechanism DOES exist elsewhere: `.claude/workflows/idea-engine.js`
returns a categorical new / extension / duplicate (SHIPPED) verdict -- but against
REPO FEATURE ship-status, for repo feature IDEAS, not dashboards. So an owner
proposing "let me add a sales-trend-over-time page" must open the design dir and
hand-compare their idea against the committed pages, visual list, and binding map
themselves -- exactly the manual, drift-prone assembly the kit exists to remove.

This feature is the missing triage: it RETARGETS idea-engine's proven
new/extends/duplicate verdict mechanism from repo ideas to DASHBOARD ideas, and
grounds the verdict in the committed `mappings/<table>/design/` corpus that the
`dashboard-design` verb (Stage 6) already produces. Given a proposal for a subject
area, it returns a categorical verdict citing the specific committed rows that
justify it, so the owner sees at a glance whether the idea is new, an extension of
a named existing page, or a duplicate of one. It ORIGINATES no judgment beyond the
set relationship, invents no metric, writes nothing, and moves no stage.

## What this feature is NOT (the scope wall)

The surface's NAME ("planner", a verdict on a "dashboard idea") is itself the risk
flag; this wall is load-bearing and is stated up front so the spec cannot drift.

- **It computes NO score and NO overlap number** (hard rule #9). The verdict is a
  DETERMINISTIC SET RELATIONSHIP over committed tuples (Clarification Q2), never a
  similarity/overlap percentage, a confidence value, or a threshold. A rolled-up
  number the surface itself computes trips hard rule #9 EVEN when expressed as
  ranking or list position rather than a printed number. The three verdict values
  are `new` / `extends <page>` / `duplicate of <page>` -- categorical, mirroring
  idea-engine's ADOPT/PARK/REJECT and the readiness statuses; never a number.
- **It is a COMPOSER/CLASSIFIER over committed evidence, never a generator.** It
  reads the already-committed design artifacts and classifies the proposal against
  them. It invents no page, no visual, no metric, and no business question; it does
  not expand or enrich the proposal's content (Clarification Q5). Every verdict
  cites the specific committed rows it was decided from.
- **A `new` verdict is NOT clearance to build and is NOT any readiness gate.** The
  planner is gate-agnostic: it neither enforces nor requires the
  `no_dashboard_before_metric_contracts` hard-stop (that is the `dashboard-design`
  verb's `semantic_model_ready` gate, an orthogonal concern) and never touches
  `readiness-status.yaml`. `new` means "no committed page covers this", not "you
  may proceed" and not "the design gate is cleared". never_self_grant_approval and
  no_dashboard_before_metric_contracts hold absolutely and are untouched.
- **It does NOT rank proposals or recommend which to build.** It classifies ONE
  proposal against the corpus and reports the categorical verdict + evidence. It
  offers no "build this / drop that" recommendation and no priority ordering -- that
  would be a synthesized judgment (Principle V) and, if numeric, a hard-rule-#9
  score. A `duplicate` verdict is advisory triage, NOT a decision to discard the
  idea; the human decides build / extend / drop.
- **It WRITES NOTHING and opens NO connection.** No write path may exist
  STRUCTURALLY (grep-verifiable zero write calls, matching `approval_inbox`,
  `blocker_explainer`, `run_next`); it prints only (Clarification Q3). It never
  edits `dashboard-layout.md`, `visual-list.md`, `visual-contract-binding-map.md`,
  `readiness-status.yaml`, or any artifact, and never opens a DB, Power BI, or
  network connection. It authors no PBIP/PBIR and generates no DAX.
- **It is not QA.** `dashboard-qa` (the 13-anti-pattern catalog in
  `powerbi-dashboard-design`) critiques a BUILT page's visuals for design defects;
  this planner triages whether a PROPOSED page duplicates an existing one. Different
  input (a proposal vs a built page), different question (novelty vs visual quality),
  different output (a categorical verdict vs anti-pattern findings).
- **It is generic (Principle VII).** Per-table over the committed
  `mappings/<table>/design/` corpus; no hardcoded table names, page names, business
  questions, contract names, or dimension fields baked into the classifier. It
  operates over whatever committed design artifacts the target table contains.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Owner gets a categorical new/extends/duplicate verdict on a proposal (Priority: P1)

An owner who already has a committed dashboard for a subject area proposes a new
dashboard/report idea and asks the planner "is this new?". The planner reads the
committed `mappings/<table>/design/` corpus, reduces the proposal and each committed
page to their `(business_question, bound_contract, dimension)` tuples, and returns
ONE categorical verdict -- `new`, `extends <existing page>`, or `duplicate of
<existing page>` -- naming the matched page (when any) and citing the specific
committed rows (from the binding map / visual list) that justify the verdict. The
owner sees at a glance whether the idea is genuinely new or a repeat.

**Why this priority**: This is the whole feature -- the categorical verdict on a
proposal grounded in the committed corpus is the net-new capability no shipped
surface provides. Without it there is no MVP.

**Independent Test**: Run the planner against `retail_store_sales` with a proposal
that re-states an already-committed cut (e.g. "TotalSales by product category",
committed as v06 in the binding map); confirm the verdict is `duplicate of` the
committed overview page, citing v06's row, and that no overlap number or score
appears.

**Acceptance Scenarios**:

1. **Given** a table whose `mappings/<table>/design/` corpus contains a committed
   page, **When** a proposal is classified whose every `(bound_contract, dimension)`
   tuple is already covered by that page, **Then** the verdict is `duplicate of
   <that page>`, the matched committed rows are cited verbatim, and no numeric
   score/overlap value appears.
2. **Given** the same table, **When** a proposal shares at least one tuple with a
   committed page AND adds at least one tuple absent from it (e.g. a NEW measure or
   a NEW dimension cut alongside an existing one), **Then** the verdict is `extends
   <that page>`, naming both the shared committed row(s) and the added tuple(s), and
   no numeric value appears.
3. **Given** the same table, **When** a proposal shares no `(bound_contract,
   dimension)` tuple with any committed page, **Then** the verdict is `new`, stating
   plainly that no committed page covers it, with no score.

---

### User Story 2 - The proposal is ingested and every verdict cites committed evidence (Priority: P1)

The owner must be able to trust the verdict: the planner must ingest the
caller-supplied proposal exactly as given (not invent or enrich it), reduce it to
the same tuple shape the corpus uses, and prove the verdict by CITING the specific
committed rows it matched -- so the owner can audit the classification against the
files themselves. This is the half that makes the planner a classifier over
committed evidence rather than an opinion.

**Why this priority**: Equal-P1 with Story 1. A verdict with no cited committed
evidence, or one that silently rewrote the proposal, would be an authored judgment
(Principle V hazard) rather than a set relationship over committed facts. The
proposal-ingest-and-cite behavior is what makes the verdict verifiable.

**Independent Test**: Run the planner with a structured proposal listing two
tuples, one that matches a committed binding-map row and one that does not; confirm
the output echoes the proposal tuples as given, cites the exact committed row for
the matched tuple (with its source file + row id), and marks the unmatched tuple as
adding-new -- yielding `extends`, with no proposal content the planner authored.

**Acceptance Scenarios**:

1. **Given** a caller-supplied proposal (free-text description plus optional
   structured tuples), **When** the planner classifies it, **Then** the output
   reproduces the proposal's supplied tuples verbatim and does NOT add, expand, or
   invent any proposal tuple, business question, or metric.
2. **Given** a proposal whose verdict is `duplicate of` or `extends` a committed
   page, **When** the planner composes the verdict, **Then** each match is cited to
   the specific committed row (the file and the visual/binding row it came from),
   and every cited row exists in the corpus (no fabricated citation).
3. **Given** a proposal that references a measure NOT present as any committed
   contract in the binding map, **When** the planner classifies it, **Then** it
   treats that tuple as adding-new (contributing to `extends`/`new`) rather than
   inventing a contract to match it, and never emits a metric definition of its own.

---

### User Story 3 - Missing or unreadable design corpus is surfaced, not fabricated (Priority: P2)

An owner running the planner for a subject area that has NO committed
`mappings/<table>/design/` directory (or an unreadable one) must get an honest
signal -- every proposal is `new` BY ABSENCE, with the absent corpus path named --
rather than a verdict that reads as "compared against pages and found distinct".

**Why this priority**: Robustness at the input boundary. It protects the trust
guarantee when the corpus is absent, but is secondary to the core verdict behavior.

**Independent Test**: Point the planner at a table directory with no `design/`
subdirectory (or an empty one); confirm the verdict is `new` with an explicit note
that no committed dashboard design was found at the named path, and that no
committed pages are fabricated.

**Acceptance Scenarios**:

1. **Given** a target table with no committed `mappings/<table>/design/` corpus (or
   an unreadable one), **When** the planner classifies any proposal, **Then** the
   verdict is `new` explicitly qualified as "by absence -- no committed dashboard
   design found at <path>", and no committed page or visual is fabricated.
2. **Given** a table whose `design/` directory exists but has no readable page (an
   empty or malformed corpus), **When** the planner classifies a proposal, **Then**
   it names what was checked and treats the proposal as `new by absence`, never
   presenting the empty corpus as "found distinct".

---

### Edge Cases

- A proposal whose tuples match committed rows on MORE THAN ONE page -> apply the
  precedence `duplicate` > `extends` > `new` (Clarification Q2) and name the page
  that yields the strongest (most-covered) relationship; never emit two conflicting
  verdicts.
- A proposal that is PARTLY covered by page A and PARTLY by page B (no single page
  covers it all, but every tuple is covered by SOME committed page) -> this is NOT a
  duplicate of any one page; it is `extends` the page it shares the most-covered
  tuple set with, with the cross-page coverage recorded in the evidence. The planner
  does not synthesize a merged "duplicate of A+B" page (that would be an invented
  page).
- A committed page region that maps to a dimension SLICER but not a measure-bound
  visual (the filter-rail slicers, which `dashboard-layout.md` notes are NOT in the
  binding map) -> slicer dimensions are not `bound_contract` tuples and are not
  matched as coverage; only measure-bearing `(bound_contract, dimension)` tuples
  from `visual-list.md` / `visual-contract-binding-map.md` are the comparison unit.
- A proposal supplied as free-text only (no structured tuples) -> the planner
  reduces only the tuples it can read directly from the given description; it does
  NOT infer measures/dimensions the caller did not state (no enrichment). If nothing
  tuple-shaped can be read, it says so and returns `new` (nothing to match), never a
  fabricated match.
- A proposal that names a business QUESTION already answered by a committed page but
  over a DIFFERENT measure/dimension -> classified by the `(bound_contract,
  dimension)` tuples, not by question-text similarity; sharing only a question label
  is not coverage (question text is free prose and is never the match key, mirroring
  spec 115's "map by the structured column, not by scoring free-text prose").
- The corpus and the proposal disagree on a contract NAME spelling/casing -> the
  match key is the committed contract name as recorded in the binding map; the
  planner echoes both and treats a non-exact match as NOT covered (adds-new), never
  fuzzily equating them (a fuzzy equate would be a smuggled similarity score).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The planner MUST accept, for ONE named subject area / table, a
  caller-supplied PROPOSED dashboard idea (a free-text description plus an OPTIONAL
  structured list of `(business_question, measure/contract, dimension)` tuples) and
  return exactly ONE categorical verdict from the closed set `new` / `extends
  <existing page>` / `duplicate of <existing page>`.
- **FR-002**: The comparison corpus MUST be the target table's committed design
  directory `mappings/<table>/design/` -- specifically `dashboard-layout.md` (pages
  + business questions), `visual-list.md` (proposed visuals), and
  `visual-contract-binding-map.md` (visual -> approved contract + dimension). Each
  committed page MUST be characterized as the SET of its `(business_question,
  bound_contract, dimension)` tuples read from those files. The planner MUST NOT
  read any other table's design dir (single-table scope, Clarification Q1).
- **FR-003**: The verdict MUST be a DETERMINISTIC SET RELATIONSHIP over the
  committed tuples (Clarification Q2): `duplicate of P` iff the proposal has >=1
  readable tuple AND shares >=1 tuple with P AND every proposal tuple is covered by
  committed page P; `extends P` iff the proposal shares >=1 tuple with P and adds
  >=1 tuple absent from P; `new` iff the proposal shares no `(bound_contract,
  dimension)` tuple with any committed page (an empty / no-readable-tuple proposal
  is `new`, never a vacuously-true duplicate). The three verdicts MUST be mutually
  exclusive and exhaustive. The match key is
  `(bound_contract, dimension)` compared by exact committed value. The planner MUST
  NOT compute a similarity/overlap percentage, confidence value, threshold, or any
  rolled-up number to decide the verdict (hard rule #9), and MUST NOT fuzzily equate
  near-match contract/dimension names.
- **FR-004**: When a proposal's tuples match committed rows across MORE THAN ONE
  page, the planner MUST apply the fixed precedence `duplicate` > `extends` > `new`
  and name the single matched page yielding the strongest relationship; it MUST NOT
  emit conflicting verdicts and MUST NOT synthesize a merged/invented page.
- **FR-005**: Every `duplicate`/`extends` verdict MUST cite the specific committed
  row(s) it matched -- the source file plus the visual/binding row id (e.g. `v06`)
  and the contract + dimension -- verbatim as recorded; every cited row MUST exist
  in the corpus (no fabricated citation). An `extends` verdict MUST also name the
  proposal tuple(s) that are absent from the matched page.
- **FR-006**: The planner MUST classify the proposal AS GIVEN: it MUST reproduce the
  proposal's supplied tuples without adding, expanding, enriching, or inventing any
  tuple, business question, or metric, and MUST NOT emit a metric definition of its
  own. A proposal measure with no matching committed contract MUST be treated as
  adding-new, never matched by inventing a contract.
- **FR-007**: When the target table has NO committed `mappings/<table>/design/`
  corpus, or it is unreadable/empty, the planner MUST return `new` explicitly
  qualified as "by absence -- no committed dashboard design found at <path>",
  naming the path checked, and MUST NOT fabricate a committed page, visual, or
  match.
- **FR-008**: The planner MUST write NOTHING and MUST grant/self-grant no approval
  and move no readiness stage; it MUST contain no file-write path (structurally
  verifiable: zero write calls, matching the shipped read-only surfaces
  `approval_inbox`, `blocker_explainer`, `run_next`). Output is printed (with an
  optional machine `--format json`), never a written companion file (Clarification
  Q3).
- **FR-009**: The planner MUST add NO `retail check` rule or any gate; its
  presence/absence MUST NOT be a gate requirement, and it MUST neither enforce nor
  require the `no_dashboard_before_metric_contracts` / `semantic_model_ready` gate
  (gate-agnostic; a `new` verdict is NOT clearance to build and NOT a gate pass).
- **FR-010**: The planner MUST emit no numeric score, count, overlap percentage,
  confidence value, or ranking anywhere (hard rule #9). It classifies ONE proposal
  and reports one categorical verdict + cited evidence; it MUST NOT rank proposals
  or recommend which to build (Principle V).
- **FR-011**: The planner MUST read only committed on-disk artifacts (the target
  table's `mappings/<table>/design/` corpus) and MUST open no DB, Power BI, or
  network connection, author no PBIP/PBIR, and generate no DAX.
- **FR-012**: Every verdict and cited match MUST be traceable to the committed
  field(s) it was composed from -- the content MUST be 100% derived from the named
  committed corpus rows (a page's business questions from `dashboard-layout.md`, its
  visuals from `visual-list.md`, and its `(bound_contract, dimension)` bindings from
  `visual-contract-binding-map.md`) plus the proposal tuples as supplied, with no
  other source of content. (This is the mechanically-enforceable guarantee that
  distinguishes this classifier from a free-composed opinion.)
- **FR-013**: The planner MUST be generic across tables (Principle VII): no
  hardcoded table names, page names, business questions, contract names, or
  dimension fields; it operates over whatever committed design artifacts the target
  table contains.
- **FR-014**: The verdict MUST be deterministic and stable (re-running on unchanged
  proposal + corpus yields the identical verdict and evidence order), reusing a
  fixed lexical secondary order for ties so no computed value is needed to break
  them.
- **FR-015**: Output MUST be ASCII-only, UTF-8 without BOM, using `--` and `->`
  (no glyphs), with short repo-relative paths (Windows 260-char budget).

### Key Entities *(include if feature involves data)*

- **Proposed dashboard idea (transient input)**: the caller-supplied proposal for a
  named subject area -- a free-text description plus an OPTIONAL structured list of
  `(business_question, measure/contract, dimension)` tuples. It is NOT committed and
  is NOT written anywhere; the planner classifies it as given (never enriches it).
- **Committed page**: a page read from the target table's `mappings/<table>/design/`
  corpus, characterized as the SET of its `(business_question, bound_contract,
  dimension)` tuples (business questions from `dashboard-layout.md`; visuals from
  `visual-list.md`; each visual's approved contract + mapped dimension from
  `visual-contract-binding-map.md`). Slicer-only dimensions are not tuples.
- **Verdict**: the composed categorical output for one proposal -- one of `new` /
  `extends <page>` / `duplicate of <page>` -- with the matched page named (when any)
  and the specific committed rows cited as evidence. Read-only; printed, never
  written. Never a number, ranking, or overlap value.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a table with a committed page, an owner submitting a proposal that
  re-states an already-committed `(contract, dimension)` cut receives a `duplicate
  of <page>` verdict citing the exact committed row, without opening
  `visual-contract-binding-map.md` directly.
- **SC-002**: The output contains zero numeric scores, overlap percentages,
  confidence values, counts, or rankings (verifiable by inspection: the verdict is
  one of the three categorical values and the decision is by set membership only).
- **SC-003**: Every `duplicate`/`extends` verdict cites committed rows that all
  exist in the corpus (no fabricated citation), and an `extends` verdict names at
  least one proposal tuple absent from the matched page -- demonstrated on a proposal
  that is a strict superset of a committed page.
- **SC-004**: The planner writes nothing -- after a run, `git status` shows no new or
  modified tracked file attributable to the planner, and the implementation contains
  no file-write call (grep-verifiable), matching the three shipped read-only
  surfaces.
- **SC-005**: For a table with no committed `mappings/<table>/design/` corpus, every
  proposal returns `new by absence` naming the path checked; in no case is an absent
  corpus presented as "compared and found distinct", and no committed page is
  fabricated.
- **SC-006**: The planner produces a correct categorical verdict for any conformant
  table with no code change (generic), demonstrated on at least two distinct tables.

## Assumptions

- The committed dashboard design corpus (`dashboard-layout.md`, `visual-list.md`,
  `visual-contract-binding-map.md`) is produced UPSTREAM by the Stage-6
  `dashboard-design` verb and is already committed before the planner runs; this
  feature READS that output as its comparison corpus and never authors, edits, or
  gates it. (Grounded: `mappings/retail_store_sales/design/` records a single
  overview page, 10 measure-bearing visuals, and a binding map of 5 approved
  contracts across dimensions -- a fully filled worked example.)
- The verdict MECHANISM (categorical new / extension / duplicate) is NOT invented
  here: it retargets the SHIPPED `.claude/workflows/idea-engine.js` verdict shape
  (which returns new/extension/duplicate against repo ship-status for repo feature
  IDEAS) to DASHBOARD ideas compared against the committed design corpus. This spec
  reuses that categorical shape; it authors no new scoring scheme.
- Verified net-new against `main`: no shipped `src/retail` surface or CLI command
  triages a PROPOSED dashboard for duplication (a grep for
  `dashboard.*(duplicate|dedup|planner|proposal)` across `src/retail` +
  `cli/commands` returns no such surface); the shipped `dashboard-design` verb
  AUTHORS a page and `dashboard-qa` CRITIQUES a built page's visuals -- neither
  triages a proposal's novelty. This planner is the missing triage.
- The planner is an OPTIONAL, pre-/around-design triage companion; it is never a
  prerequisite for any readiness stage and is gate-agnostic (it neither enforces nor
  clears `no_dashboard_before_metric_contracts`), following the read-only
  optional-companion posture of specs 114/115.
- The precise output VEHICLE mechanics (a standalone read-only runtime module +
  CLI verb mirroring `blocker_explainer.py` vs a skill) and the exact enforcement
  mechanism for FR-012 (the derived-from-named-corpus-rows faithfulness verifier)
  are implementation decisions for the plan phase; the spec fixes the BEHAVIOR (the
  set-relationship verdict, the corpus, print-only, new-by-absence), not the
  mechanism. The verdict decision rule (set membership, not a score), the corpus,
  and the output vehicle are NOT deferred -- they are fixed by Clarifications Q1-Q5.
- The comparison unit is the `(bound_contract, dimension)` tuple compared by exact
  committed value; question text is free prose and is NEVER the match key (mirrors
  spec 115's "map by the structured column, not by scoring free-text prose"), so no
  category or match is synthesized from prose similarity.
