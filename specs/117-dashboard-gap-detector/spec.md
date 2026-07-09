# Feature Specification: Dashboard Gap Detector -- read-only pre-design inventory of design-blocking gaps

**Feature Branch**: `117-dashboard-gap-detector`

**Created**: 2026-07-09

**Status**: Draft

**Input**: User description: "Dashboard Gap Detector -- read-only pre-design inventory of missing metric contracts / dimensions / owner decisions that block a page from being designed, emitting a categorical status per item reusing SL1's vocabulary plus a named blocker; extends SL1, invents nothing, records no pass"

## Clarifications

### Session 2026-07-09

- Q: What is the "required item" set the detector diffs committed evidence
  against -- and where does it come from? -> A: a HUMAN-SUPPLIED page-intent for
  ONE subject area: the business questions the page must answer, each declaring
  the metric(s) and the slicing dimension(s) it needs. This is a Principle-V
  input, mirroring dashboard-design **Precondition 4** ("the analyst supplies the
  business questions the page must answer ... if missing, ASK; do NOT invent a
  generic page"). The detector CLASSIFIES each supplied required item against
  committed evidence; it NEVER invents the required set. Detecting what is
  *missing* is only possible against a required set -- reading committed files
  alone can classify what EXISTS (e.g. a present-but-unapproved contract) but
  cannot detect a metric or dimension nobody has drafted (there is no file to
  read for it). When the page-intent input is absent or unreadable, the detector
  emits a document-level GAP naming the missing input path (the consumer-data-
  dictionary / F040 missing-input precedent) and fabricates no required list.
- Q: How is a "missing owner decision" gap detected -- from prose or a structured
  field? -> A: from the target table's committed `unresolved-questions.md`, by
  its STRUCTURED columns only: a row is an OPEN owner-decision gap when its
  `Status` column is not `answered` (and the doc-level `Gate status` is not
  `CLEARED`), and the blocker names the row's `Who must answer` owner
  (governance / analyst / data-owner) and its question text VERBATIM. The
  detector reads the structured `Status`/`Who must answer`/`Question` columns; it
  never scores or paraphrases the free-text question prose to decide openness
  (the same structured-owner-column discipline spec 115 uses for its refutation
  categories). A row that a required page item depends on and that is still open
  is a design-blocking owner-decision gap.
- Q: What is the output artifact -- printed only, or a committed companion file?
  -> A: PRINTED read-only view only (the shipped read-only-surface posture of
  `blocker_explainer` / `approval_inbox` / `run_next` and of spec 115's approver
  view). The detector writes NOTHING: no companion file, no `blocking_reasons[]`
  entry, no readiness-stage move. It DISPLAYS a named blocking reason per gap in
  its printed output (normal readiness recording of a reason, not a self-grant);
  it never WRITES a blocking reason into any artifact and never records a `pass`.
- Q: Does the detector reuse SL1's runtime, or only its vocabulary? -> A:
  VOCABULARY only. SL1 (`src/retail/rules/scorecard.py`) is a static `retail
  check` RULE that validates the STRUCTURE of a committed coverage-scorecard file
  and emits `Severity.ERROR` Findings into the gate. The detector is a read-only
  agent SURFACE that adds NO `retail check` rule and no gate (FR-008). It reuses
  SL1's CLOSED STATUS ENUM -- {Covered, Blocked -- missing field, Blocked --
  needs business definition, Planned, Out of scope} -- and nothing else. Whether
  the enum is imported from a shared extracted constant or restated with a test
  asserting equality to SL1's `_ENUM` is a plan-phase mechanism decision; the
  spec fixes that the vocabulary is SL1's, not a parallel one.
- Q: How do the three gap classes map onto SL1's five statuses (no new status is
  minted)? -> A: (1) a required metric whose contract exists and is
  `readiness.status: pass` -> **Covered**; (2) a required metric with a contract
  file present but not `pass` (e.g. `not_started`), OR a required metric whose
  need is blocked by an OPEN owner decision -> **Blocked -- needs business
  definition**; (3) a required metric with NO contract file drafted at all (and
  no open decision seeding it) -> **Planned**; (4) a required slicing dimension
  ABSENT from the table's committed `gold_star` -> **Blocked -- missing field**;
  (5) a required item whose subject the target table cannot serve (e.g. an
  inventory slice against a sales-only fact) -> **Out of scope**. Every emitted
  status is exactly one of SL1's five; the detector mints none.

## Why this feature exists

Before a dashboard page is designed for a subject area, the honest first
question is: *what is missing that must be resolved before we can draw this
page at all?* Today that question has no proactive answer. The design-blocking
gaps are real and already knowable from committed artifacts -- an approved
metric contract that does not exist, a slicing dimension absent from the gold
star, an owner decision still open in `unresolved-questions.md` -- but they are
scattered, and the only surface that confronts them is the design VERB itself,
which hits them one at a time, mid-authoring, as a wall.

The shipped `dashboard-design` skill is HARD-GATED on `semantic_model_ready:
pass` and, once inside authoring, STOPS per-visual on a blocking reason ("orphan
visual: no approved contract for `<question>`"). That is a narrow, reactive,
one-gap-at-a-time check discovered while drawing. A designer who reaches that
skill only to be turned away, visual by visual, has learned too late that the
page could not be drawn. There is no surface that, BEFORE design is attempted,
INVENTORIES every design-blocking gap for the whole page so the wall is seen up
front, not discovered mid-stride.

This feature is that pre-design inventory. Given a human-supplied page-intent
for one subject area (the business questions the page must answer, each naming
the metric(s) and dimension(s) it needs -- the same Principle-V input
`dashboard-design` requires), it CLASSIFIES each required item against the
table's committed evidence -- the metric contracts (`mappings/<table>/metrics/
*.yaml`), the gold-star dimensions (`mappings/<table>/source-map.yaml`
`gold_star`), and the open owner decisions (`mappings/<table>/unresolved-
questions.md`) -- and emits, per required item, a CATEGORICAL status from SL1's
closed vocabulary plus a NAMED blocker where the item blocks design. It answers,
before the first visual is placed: *which of the things this page needs already
exist and are approved, and which are missing, unapproved, or awaiting an owner
decision -- and what specifically blocks each?* It invents no metric, no
dimension, and no decision; it records no readiness pass; it moves no stage.

## What this feature is NOT (the scope wall)

The surface's whole value is naming design-blocking gaps; the risk is that a
gap-namer drifts into a gap-INVENTER, a design AUTHOR, or a gate. This wall is
load-bearing and is stated up front so the spec cannot drift.

- **It INVENTS nothing (evidence-gate, never a generator).** It reads committed
  metric contracts, the committed `gold_star` dimension list, and the committed
  open-questions record, and CLASSIFIES the human-supplied required items against
  them. It MUST NOT invent a metric, a dimension, an owner decision, or a
  required item the human did not supply. A required item with no committed
  backing is a GAP to REPORT, never a thing to synthesize (Principle V; the
  consumer-data-dictionary "gap-and-cite, never fabricate" posture).
- **It does NOT supply the required set.** The page-intent (the business
  questions and their required metrics/dimensions) is a human input, exactly as
  `dashboard-design` Precondition 4 requires. When it is absent or unreadable the
  detector emits a document-level GAP naming the missing input and STOPS
  classifying -- it never invents a generic page's required list.
- **It records NO pass and grants NO approval.** It MAY display a named
  `blocking_reason` per gap in its printed output (normal readiness recording of
  a reason, not a self-grant). It MUST NOT record a `pass`, write an
  `approvals[]` entry, or move any readiness stage. never_self_grant_approval
  (Principle V) holds absolutely.
- **It WRITES NOTHING.** No file-write path may exist STRUCTURALLY (grep-
  verifiable zero write calls, matching the shipped read-only surfaces). It does
  not write a companion file, does not edit `readiness-status.yaml`,
  `unresolved-questions.md`, `source-map.yaml`, any `metrics/*.yaml`, or any
  design artifact, and adds no `blocking_reasons[]` entry to any file. The output
  is a PRINTED view only.
- **It emits a CATEGORICAL status, NEVER a numeric score** (hard rule #9). Per
  required item: one status from SL1's closed five-value enum plus a named
  blocker. No coverage percentage, no readiness/confidence number, no "N of M"
  gap count, no computed priority to sort by. never_fabricate_a_confidence_score
  holds; the categorical status IS the house-style answer.
- **It adds NO gate and is NOT SL1's runtime.** It registers no new `retail
  check` rule, and its presence or absence is never a gate requirement. SL1
  (`src/retail/rules/scorecard.py`) is the static rule that gates a committed
  scorecard's STRUCTURE; this surface reuses SL1's status VOCABULARY only, adds
  no `@register` rule, and changes no rules manifest (no_dashboard_before_metric_
  contracts is REPORTED by this surface, ENFORCED by the existing gate, never by
  a rule this surface adds).
- **It designs NOTHING and executes NOTHING.** It authors no layout plan, no
  visual list, and no visual->contract binding map (that is the `dashboard-
  design` verb, which runs AFTER the gaps are cleared). It opens no DB, no Power
  BI / PBIP surface, and no network connection, and it writes no DAX and no PBIR
  (no_silver_before_mapping and the Never-Execute invariant hold; this surface is
  static committed-text only).
- **It is generic (Principle VII).** Table-parameterized over the committed
  `mappings/<table>/` artifacts; no hardcoded table names, column names,
  dimension names, metric names, or grain keys. C086/`retail_store_sales` is a
  cited filled instance, never the schema.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Designer sees every design-blocking gap before drawing (Priority: P1)

A BI designer about to design a page for one subject area supplies the page's
intent (the business questions, each naming its required metric(s) and slicing
dimension(s)). Before any visual is placed, the detector returns a per-item
inventory: for each required metric and dimension, a categorical status from
SL1's vocabulary (Covered / Blocked -- missing field / Blocked -- needs business
definition / Planned / Out of scope) and, where the item blocks design, a named
blocker citing the committed evidence that is missing or unapproved. The
designer learns up front which parts of the page can be drawn and which are
walled, without attempting design and being turned away visual by visual.

**Why this priority**: This is the feature -- the proactive, whole-page
inventory of design-blocking gaps against committed evidence. Without it there
is no MVP; the designer is left to discover gaps reactively inside the design
verb.

**Independent Test**: Supply a page-intent for a table (e.g. `retail_store_
sales`) whose committed evidence covers some required metrics (an approved
contract) but not others (a required metric with no `pass` contract, and a
required slicing dimension absent from `gold_star`); confirm each required item
gets exactly one status from the closed enum, the covered ones read `Covered`,
the missing/unapproved ones carry a named blocker, and NO numeric score or
percentage appears.

**Acceptance Scenarios**:

1. **Given** a page-intent naming a required metric whose contract exists at
   `mappings/<table>/metrics/<Metric>.yaml` with `readiness.status: pass`,
   **When** the detector runs, **Then** that item's status is `Covered` and it
   carries no blocker.
2. **Given** a page-intent naming a required metric whose contract file is
   present but `readiness.status` is not `pass`, **When** the detector runs,
   **Then** that item's status is `Blocked -- needs business definition` with a
   blocker naming the unapproved contract and its recorded status.
3. **Given** a page-intent naming a required slicing dimension that is ABSENT
   from the table's committed `gold_star` (neither a listed dimension nor a
   dated/degenerate dimension), **When** the detector runs, **Then** that item's
   status is `Blocked -- missing field` with a blocker naming the absent
   dimension and the `source-map.yaml` `gold_star` path checked.
4. **Given** a page-intent all of whose required items are covered by approved
   contracts and present dimensions with no open dependency, **When** the
   detector runs, **Then** every item is `Covered`, the detector states plainly
   there is nothing blocking design, and it emits no score and records no pass.

---

### User Story 2 - Open owner decisions block design and are surfaced as gaps (Priority: P1)

The detector must surface, as design-blocking gaps, the OPEN owner decisions in
the table's `unresolved-questions.md` that a required page item depends on -- a
governance/analyst/data-owner decision still owed. An unresolved build-blocking
question is exactly a reason a page cannot yet be designed against the affected
metric or dimension, and this is the input no shipped design-time check reads
proactively.

**Why this priority**: Equal-P1. Owner-decision gaps are the "missing owner
decisions" half of the feature and are what extend the inventory beyond SL1's
KPI-field coverage to the design-readiness moment; an inventory that omits open
decisions is incomplete.

**Independent Test**: Supply a page-intent whose required metric depends on an
OPEN (not `answered`) `unresolved-questions.md` row (owner = governance or
analyst); confirm that required item is `Blocked -- needs business definition`
with a blocker naming the row's `Who must answer` owner and its question text
verbatim, and that an `answered` row (Gate status CLEARED) produces no
owner-decision gap.

**Acceptance Scenarios**:

1. **Given** a page-intent whose required metric depends on an OPEN
   `unresolved-questions.md` row, **When** the detector runs, **Then** that item
   is `Blocked -- needs business definition` and the blocker names the row's
   `Who must answer` owner and quotes the question text verbatim, citing the
   `unresolved-questions.md` path.
2. **Given** a table whose `unresolved-questions.md` rows are all `answered`
   (Gate status CLEARED), **When** the detector runs, **Then** no `answered` row
   is reported as an open owner-decision gap; a required item backed by approved
   evidence reads `Covered`.
3. **Given** an OPEN row whose `Who must answer` owner is unrecognized, **When**
   the detector runs, **Then** the owner is echoed verbatim in the blocker and
   the item is still surfaced as a gap; the detector invents no owner class.

---

### User Story 3 - Missing or unreadable input is surfaced, never fabricated (Priority: P2)

A designer running the detector without a page-intent, or for a table missing
one of the committed evidence files (`metrics/`, `source-map.yaml`, or
`unresolved-questions.md`), gets an honest document-level GAP naming what is
missing -- never an empty inventory that reads as "nothing blocks design" and
never a fabricated required list.

**Why this priority**: Robustness at the input boundary; secondary to the core
classification but it protects the trust guarantee (a missing input must never
masquerade as a clean page).

**Independent Test**: Run the detector (a) with no page-intent supplied and (b)
for a table with a page-intent but no `source-map.yaml`; confirm each emits a
document-level GAP naming the missing path and classifies no fabricated items.

**Acceptance Scenarios**:

1. **Given** no page-intent is supplied, **When** the detector runs, **Then** it
   emits a document-level GAP naming the missing page-intent input and does not
   fabricate a required list or a "nothing blocks design" result.
2. **Given** a page-intent but a target table with no committed `source-map.yaml`
   (or no `metrics/` directory, or no `unresolved-questions.md`), **When** the
   detector runs, **Then** it emits a document-level GAP naming the missing path
   and does not present the absence as "no gaps"; any required item it cannot
   classify against a missing input is reported as an unresolved GAP, not as
   `Covered`.

---

### Edge Cases

- A required metric whose contract file is MISSING entirely versus present-but-
  not-`pass`: the two are distinguished -- a required metric with no contract
  drafted at all (and no open decision seeding it) is `Planned`; a contract file
  present but not `pass` is `Blocked -- needs business definition`. Neither is
  ever `Covered`.
- A required slicing dimension that IS present in `gold_star` (a listed
  dimension, a date dimension, or a degenerate dimension) -> `Covered` for the
  dimension item; presence is read from the committed `gold_star` structure, not
  guessed from a column merely appearing somewhere in the source.
- A required item whose subject the target table cannot serve (e.g. an inventory
  KPI against a sales-only fact) -> `Out of scope` (SL1's fifth status), not a
  blocker to be cleared -- it is not a gap the table can close.
- An OPEN `unresolved-questions.md` row that NO supplied required item depends on
  -> it is not forced into the page's gap inventory; the detector reports gaps
  for the SUPPLIED required items, and lists an open decision as a blocker only
  where a required item depends on it (the detector does not re-derive the whole
  readiness refusal case -- that is spec 115's approver view).
- A metric contract present with `readiness.status: pass` but whose `binds_to`
  gold column is not in the committed gold star -> the metric item is reported as
  a gap (`Blocked -- missing field`) naming the intra-artifact disagreement; the
  detector never silently reports `Covered` over a committed inconsistency.
- A page-intent naming a required item whose text cannot be matched to any
  committed metric or dimension by name -> reported as a GAP (unmatched required
  item), never silently dropped and never fuzzily matched to a near-name.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The detector MUST accept, for ONE subject area / target table, a
  HUMAN-SUPPLIED page-intent -- the business questions the page must answer, each
  declaring the metric(s) and slicing dimension(s) it requires -- and MUST NOT
  invent, infer, or default the required set (Principle V; `dashboard-design`
  Precondition 4). When the page-intent is absent or unreadable, the detector
  MUST emit a document-level GAP naming the missing input and MUST NOT fabricate
  a required list.
- **FR-002**: For each supplied required item, the detector MUST emit exactly ONE
  categorical status drawn from SL1's closed five-value enum -- {`Covered`,
  `Blocked -- missing field`, `Blocked -- needs business definition`, `Planned`,
  `Out of scope`} -- and MUST NOT mint any status outside that set (the reused
  vocabulary is authoritative; Clarification Q4/Q5).
- **FR-003**: The detector MUST classify a required METRIC by reading the target
  table's committed `mappings/<table>/metrics/*.yaml`: an approved contract
  (`readiness.status: pass`) -> `Covered`; a contract present but not `pass`, or a
  metric blocked by an open owner decision -> `Blocked -- needs business
  definition`; no contract file drafted at all -> `Planned`. It MUST read the
  committed `readiness.status`; it MUST NOT adjudicate whether an approval is
  deserved or grant one.
- **FR-004**: The detector MUST classify a required slicing DIMENSION by reading
  the target table's committed `mappings/<table>/source-map.yaml` `gold_star`
  (its `dimensions[]`, `date_dimension`, and `degenerate_dimensions[]`): a
  dimension present in the committed star -> `Covered`; a required dimension
  absent from it -> `Blocked -- missing field` naming the absent dimension and
  the path checked. Presence MUST be read from the committed `gold_star`
  structure, never inferred by fuzzy name match.
- **FR-005**: The detector MUST classify a required item the target table cannot
  serve (a subject outside the table's domain) as `Out of scope`, and MUST NOT
  present it as a clearable blocker.
- **FR-006**: The detector MUST detect an OPEN owner-decision gap by the
  STRUCTURED columns of the target table's committed `unresolved-questions.md`: a
  row is OPEN when its `Status` is not `answered` (and the doc `Gate status` is
  not `CLEARED`). For a required item that depends on an OPEN row, the emitted
  blocker MUST name the row's `Who must answer` owner and quote its question text
  VERBATIM, citing the `unresolved-questions.md` path. The detector MUST NOT
  score or paraphrase the free-text question prose to decide openness or to
  synthesize a category (the structured-owner-column discipline of spec 115).
- **FR-007**: For every required item that is not `Covered`, the detector MUST
  DISPLAY a named blocking reason in its printed output identifying the specific
  missing/unapproved/undecided evidence and the committed path checked; a blocker
  MUST be traceable to the committed field(s) it was composed from, never
  paraphrased into a substitute or generated.
- **FR-008**: The detector MUST add NO `retail check` rule and NO gate; it MUST
  NOT register a rule, change the rules manifest, or make its presence/absence a
  gate requirement. It reuses SL1's status VOCABULARY only and is NOT SL1's
  runtime (SL1 stays the static scorecard-structure rule).
- **FR-009**: The detector MUST record NO readiness `pass`, write NO `approvals[]`
  entry, and move NO readiness stage (never_self_grant_approval, Principle V). It
  MAY DISPLAY a `blocking_reason` per gap in its printed output; it MUST NOT WRITE
  a `blocking_reasons[]` entry into any artifact.
- **FR-010**: The detector MUST write NOTHING: no companion file and no edit to
  `readiness-status.yaml`, `unresolved-questions.md`, `source-map.yaml`, any
  `metrics/*.yaml`, or any design artifact. It MUST contain no file-write path
  (structurally verifiable: zero write calls, matching the shipped read-only
  surfaces). The output is a PRINTED view (Clarification Q3).
- **FR-011**: The detector MUST emit NO numeric score, coverage percentage,
  confidence value, priority number, or "N of M" gap count anywhere (hard rule
  #9). The per-item categorical status plus its named blocker is the only
  answer; ordering, if any, MUST use a fixed committed key, never a computed
  score.
- **FR-012**: The detector MUST read only committed on-disk artifacts
  (`mappings/<table>/metrics/*.yaml`, `mappings/<table>/source-map.yaml`,
  `mappings/<table>/unresolved-questions.md`, and the supplied page-intent) and
  MUST open no DB, Power BI / PBIP, or network connection; it MUST author no
  layout plan, visual list, binding map, DAX, or PBIR (design and execution are
  the deferred `dashboard-design` verb and F016 adapter, not this surface).
- **FR-013**: When any required committed input is missing or unreadable, the
  detector MUST surface a document-level GAP naming the path checked and MUST NOT
  classify an item it could not check as `Covered` (an unclassifiable item is a
  GAP, never a silent pass).
- **FR-014**: The detector MUST be generic across tables (Principle VII): no
  hardcoded table names, dimension names, metric names, column names, or grain
  keys; it operates over whatever the target table's committed artifacts and the
  supplied page-intent contain.
- **FR-015**: Output MUST be ASCII-only, UTF-8 without BOM, using `--` and `->`
  (no glyphs), with short repo-relative paths (Windows 260-char budget). The
  status strings MUST be the ASCII forms (`Blocked -- missing field`, not the
  em-dash template rendering).

### Key Entities *(include if feature involves data)*

- **Page-intent**: the human-supplied required set for one page -- the business
  questions, each declaring its required metric(s) and slicing dimension(s). A
  Principle-V input; the detector reads it, never authors it. Its input shape
  (committed file vs invocation parameter) is a plan-phase decision.
- **Required item**: one element the page needs -- a required metric or a
  required slicing dimension (or an out-of-domain subject). The unit the detector
  classifies. Attributes: the item name/text (from the page-intent), the
  committed evidence checked, the emitted status, and the named blocker (when not
  Covered).
- **Metric contract**: `mappings/<table>/metrics/<Metric>.yaml`; its
  `readiness.status` (pass / not_started / ...) and `binds_to` are read to
  classify a required metric. The detector never approves or edits it.
- **Gold-star dimension inventory**: the target table's committed
  `source-map.yaml` `gold_star` (`dimensions[]` + `date_dimension` +
  `degenerate_dimensions[]`); the set a required dimension is checked against.
- **Open owner decision**: an OPEN row of `unresolved-questions.md` (structured
  `Status` != answered), carrying a `Who must answer` owner and question text; a
  design-blocking gap for a required item that depends on it.
- **Gap inventory view**: the composed, printed, read-only output -- one status
  (from SL1's five) plus a named blocker per required item, plus any
  document-level GAP for a missing input. Records no pass; writes nothing.
- **Coverage status enum (reused)**: SL1's closed five-value set
  ({Covered, Blocked -- missing field, Blocked -- needs business definition,
  Planned, Out of scope}); the membership set every emitted status is drawn from.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a page-intent mixing covered and uncovered required items, the
  detector reports, per item, exactly one status from SL1's closed enum, with a
  named blocker on every non-`Covered` item, so a designer sees the whole page's
  design-blocking gaps before placing any visual -- without opening
  `metrics/*.yaml`, `source-map.yaml`, or `unresolved-questions.md` directly.
- **SC-002**: Every emitted per-item status is a member of SL1's five-value enum
  (verifiable against SL1's own status set); the detector emits no status outside
  it and mints no new status vocabulary.
- **SC-003**: The output contains zero numeric scores, coverage percentages,
  confidence values, priority numbers, and "N of M" counts (verifiable by
  inspection: each gap is a status + named blocker only).
- **SC-004**: An OPEN `unresolved-questions.md` row a required item depends on is
  reported as a `Blocked -- needs business definition` gap naming its
  `Who must answer` owner and verbatim question text; an `answered` row produces
  no owner-decision gap (demonstrated on a table with both states).
- **SC-005**: A required metric with no contract file is `Planned`; one with a
  present-but-not-`pass` contract is `Blocked -- needs business definition`; one
  with a `pass` contract is `Covered` -- the three are distinguished, and no
  uncovered item is ever reported as `Covered`.
- **SC-006**: A required dimension absent from the committed `gold_star` is
  `Blocked -- missing field` naming the absent dimension; a present one is
  `Covered` -- read from the committed `gold_star` structure, not a fuzzy match.
- **SC-007**: The detector writes nothing -- after a run, `git status` shows no
  new or modified tracked file attributable to it, the implementation contains no
  file-write call (grep-verifiable), and no readiness stage moved and no `pass`
  or `approvals[]` entry was recorded.
- **SC-008**: Missing inputs (no page-intent; a missing `source-map.yaml` /
  `metrics/` / `unresolved-questions.md`) each yield a document-level GAP naming
  the path checked, never a fabricated required list and never a "nothing blocks
  design" result.
- **SC-009**: The detector adds no `retail check` rule -- `retail check` exit
  behavior and the rules-manifest count are UNCHANGED after the feature lands
  (no gate added; SL1 is unmodified).
- **SC-010**: The detector produces a correct gap inventory for any conformant
  table + page-intent with no code change (generic), demonstrated on at least two
  distinct tables.

## Assumptions

- The required set is a HUMAN-SUPPLIED page-intent (Clarification Q1), mirroring
  `dashboard-design` Precondition 4; the detector classifies it and never
  invents it. Detecting a *missing* metric or dimension is only possible against
  this supplied required set -- committed files alone cannot reveal a contract
  nobody drafted.
- The three committed evidence families already exist for a mapped table before
  the detector runs: metric contracts under `mappings/<table>/metrics/`, the
  gold-star dimension inventory in `mappings/<table>/source-map.yaml`
  (`gold_star`), and open owner decisions in `mappings/<table>/unresolved-
  questions.md`. The detector surfaces gaps against them; it originates none.
  (Grounded: `mappings/retail_store_sales/` records five metric contracts, a
  five-dimension gold star, and a CLEARED unresolved-questions gate.)
- The detector reuses SL1's status VOCABULARY only, not its runtime (Clarification
  Q4). It is a read-only agent SURFACE grouped with `blocker_explainer` /
  `approval_inbox` / `run_next` / spec 115's approver view; it adds no `retail
  check` rule. Whether the enum is imported from a shared extracted constant or
  restated with a test asserting equality to `scorecard.py`'s `_ENUM` is a
  plan-phase mechanism decision.
- The output is a PRINTED read-only view (Clarification Q3), following the shipped
  read-only-surface posture. Whether an optional companion file is ever offered is
  explicitly OUT of scope for this version (114 writes a companion; 115 and this
  surface do not -- the read-only view is the closer neighbor for a pre-design
  inventory).
- This surface is the pre-design INVENTORY; `dashboard-design` is the gated
  design VERB that runs AFTER the gaps are cleared and blocks per-visual during
  authoring; spec 115's approver view is the signer's refutation-first reading of
  the whole readiness case at an APPROVAL moment; and the consumer-data-dictionary
  GAP-marks missing column/metric MEANING citations. This feature's "gap" is a
  design-COVERAGE gap for a page's required items -- distinct from all three, and
  never a prerequisite for any readiness stage.
- Owner-decision openness is read from `unresolved-questions.md`'s STRUCTURED
  `Status` / `Who must answer` columns (Clarification Q2), never from scoring the
  free-text question prose -- keeping every classification input a committed fact
  (hard rule #9 stays clean by construction).
