# Feature Specification: Decision-Question Answerability Reconciler

**Feature Branch**: `069-answerability-reconciler-build`

**Created**: 2026-07-02

**Status**: Ratified (Ahmed Shaaban, 2026-07-02)

> Ratified by the owner in their own name (2026-07-02), authorizing the build of the
> deferred ADOPT idea H3. plan-review: PASS-WITH-NOTES (0 critical / 0 high) -- SEE
> CORRECTION (2026-07-02) in plan-review.md: the "analyze: clean" evidence is RETRACTED
> (no analysis.md/plan.md/tasks.md was ever committed; by the repo's own preconditions
> this build should have been BLOCKED). The
> Principle-V line is drawn and held by FR-015 / OPEN-3 (the rule reports a
> question/contract conflict, never rules which side is canonical). The three OPEN
> Principle-V items (OPEN-1 severity posture, OPEN-2 roadmap slot, OPEN-3 canonical-side
> conflict) stay DEFERRED to a human and are OUT OF SCOPE for this build. Build guard:
> the "Routes to" cell is a backtick-quoted contract path + optional parenthetical --
> extract the backtick path, not the whole cell; match Status by startswith to cover
> "Seeded (base)"; messages surface drift and STOP (no answerability recommendation).

**Input**: User description: "H3. Decision-Question Answerability Reconciler"

## Overview

The retail KPI knowledge skill publishes, in each domain file, a "Decision
questions this domain answers" table. Every row states a business question, a
"Routes to" target (a contract file or an honest placeholder), and a Status
("Seeded" or "Planned (...)"). Today that table is prose: nothing mechanically
checks that a question said to be answered actually routes to a contract that
exists, or that a question NOT yet answered is honestly marked planned. A row
can silently rot -- claim "Seeded" while pointing at a contract that was renamed
or never written -- and the gate stays green.

This feature adds one static, read-only rule to the existing `retail check` rule
set. The rule parses every domain decision-question table and, per question,
asserts categorically that the route either resolves to an existing contract OR
is honestly marked planned. It reports Findings; it never edits, renders, or
executes anything. It emits no numeric score, percentage, or rollup -- only a
per-question pass / fail / warn verdict. This categorical shape is deliberate:
a prior numeric "Model-Wide Answerability Rollup" idea was rejected, and this
rule must stay clear of it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gate operator catches a dangling KPI route (Priority: P1)

A maintainer edits or renames a contract file under the KPI skill and forgets to
update a domain decision-question table that still claims the question is
"Seeded" and routes to the old contract path. When the maintainer runs the
retail governance gate, the rule reports an ERROR naming the domain file, the
question, and the unresolved contract path, and the gate fails. The maintainer
fixes the route (or re-marks the row honestly) and the gate passes.

**Why this priority**: This is the core value -- it makes the F7-shipped
answerability surface machine-checkable and fails loud on the most damaging
drift (a claimed-answered question pointing at a contract that is not there).
Without it the rule delivers nothing.

**Independent Test**: Point a decision-question row's "Routes to" cell at a
contract path that does not exist under the skill's contract store, run the gate,
and confirm one ERROR Finding is emitted for that row and the gate exit code is
non-zero. Restore the row to a resolvable contract and confirm the Finding
disappears.

**Acceptance Scenarios**:

1. **Given** a domain decision-question row with Status "Seeded" whose "Routes
   to" cell names a contract file that exists under the skill contract store,
   **When** the gate runs, **Then** no Finding is emitted for that row.
2. **Given** a domain decision-question row with Status "Seeded" whose "Routes
   to" cell names a contract file that does NOT exist under the skill contract
   store, **When** the gate runs, **Then** exactly one ERROR Finding is emitted
   for that row identifying the domain file, the question, and the missing
   contract path, and the gate fails.
3. **Given** a domain decision-question row whose "Routes to" cell is the honest
   placeholder marker and whose Status begins "Planned", **When** the gate runs,
   **Then** no Finding is emitted for that row (a planned question with no
   contract yet is honest, not broken).

### User Story 2 - Reviewer trusts that every question is either resolved or honestly planned (Priority: P2)

A reviewer approving a change to the KPI knowledge skill wants assurance that no
decision-question row is in an ambiguous middle state -- neither a resolvable
"Seeded" route nor an honest "Planned" marker. The rule flags any such row as a
WARNING so the reviewer sees it without necessarily blocking the build.

**Why this priority**: It closes the honesty gap in the other direction (rows
that are neither resolvable nor honestly planned), but a WARNING is a softer
posture than the P1 ERROR and is not required for the rule to deliver its core
value.

**Independent Test**: Author a decision-question row whose Status is neither
"Seeded" nor begins "Planned" (for example a blank or "TBD" status), run the
gate, and confirm one WARNING Finding is emitted for that row and the gate does
not fail solely because of it.

**Acceptance Scenarios**:

1. **Given** a decision-question row whose Status cell is neither "Seeded" nor
   begins "Planned", **When** the gate runs, **Then** one WARNING Finding is
   emitted for that row and the gate is not failed by that WARNING alone.

### User Story 3 - Rule scales to the whole domain corpus generically (Priority: P3)

A maintainer adds a brand-new domain file to the KPI skill (the corpus is not a
fixed size). The rule discovers and checks the new file's decision-question
table automatically, with no code change and no hardcoded domain count or KPI
name.

**Why this priority**: This guarantees the rule stays generic and does not rot
as the corpus grows, honoring the "C086 is only an example" principle. It is a
correctness property of the discovery mechanism rather than a distinct
user-visible check, so it is lowest priority.

**Independent Test**: Add a new domain file with a well-formed decision-question
table containing one dangling "Seeded" route, run the gate, and confirm the new
file is scanned and its dangling row reported -- with no edit to the rule code.

**Acceptance Scenarios**:

1. **Given** an additional domain file with a well-formed decision-question
   table, **When** the gate runs, **Then** the new file's rows are checked with
   the same rules as every other domain file.
2. **Given** the domain corpus contains a number of files that differs from any
   count mentioned in prose roadmap documents, **When** the gate runs, **Then**
   the rule checks whatever files are actually present (it globs the corpus and
   never asserts a fixed count).

### Edge Cases

- **Domain file has no decision-question table at all**: The rule treats a
  domain file that does not contain the recognized table as having zero
  question rows to check (no Finding). It does NOT fail merely because one
  domain omits the table (Clarifications C4: silent-pass; table-presence
  coverage is a different rule's concern).
- **Empty table (header only, no rows)**: No question rows -> no Finding.
- **"Routes to" placeholder glyph**: A planned row's placeholder is a specific
  literal glyph in the source, not an ASCII hyphen. The parser MUST match the
  exact glyph used in the corpus so it does not misclassify planned rows as
  broken.
- **Contract path base**: A "Routes to" value is resolved relative to the KPI
  skill root, not the repository root and not the domain subfolder. Resolving it
  against the wrong base would make every genuinely-resolvable route falsely
  appear dangling.
- **Malformed / unparseable table row** (wrong column count, missing pipes):
  The rule fails loud on a row it cannot parse rather than skipping it silently,
  consistent with the fail-loud posture of the analogous shipped routing rule.
- **A "Seeded" row whose "Routes to" cell is the planned placeholder glyph**
  (status and route disagree): This mixed row is inconsistent -- it is not a
  resolvable-Seeded route (no contract path to resolve) and not an
  honest-Planned row (Status is not "Planned"). It therefore falls into the
  neither-category and is reported as a WARNING (FR-006).
- **A "Planned" row whose "Routes to" cell names an existing contract** (the
  contract was built but the row was never flipped to "Seeded"): reported as a
  stale planned marker ERROR (FR-017), mirroring the routing rule's
  bidirectional honesty.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a single new static rule, registered in
  the existing retail governance rule set under one rule id, that participates in
  the standard `retail check` run and contributes its Findings and exit-code
  effect like every other rule.
- **FR-002**: The rule MUST discover the domain corpus by globbing all domain
  files in the KPI knowledge skill's domains folder. It MUST NOT hardcode the
  number of domain files, any specific domain name, or any specific KPI or
  contract name.
- **FR-003**: For each discovered domain file, the rule MUST locate the
  decision-question table (the three-column table under the domain's
  decision-questions heading, with columns "Decision question", "Routes to",
  "Status") and extract its data rows.
- **FR-004**: For each decision-question row whose Status indicates the question
  is answered ("Seeded"), the rule MUST resolve the "Routes to" value against
  the KPI skill root and verify the named contract file exists. If it does not
  exist, the rule MUST emit an ERROR Finding identifying the domain file, the
  question text, and the unresolved contract path.
- **FR-005**: For each decision-question row honestly marked planned (Status
  begins "Planned" and "Routes to" is the honest placeholder glyph), the rule
  MUST emit no Finding for that row (a planned question with no contract yet is
  honest, not broken).
- **FR-006**: For each decision-question row that is neither a resolvable
  "Seeded" route nor an honest "Planned" marker, the rule MUST emit a WARNING
  Finding identifying the domain file and the question.
- **FR-007**: The rule MUST resolve every "Routes to" value relative to the KPI
  skill root (the skill's top-level folder), NOT relative to the repository root
  and NOT relative to the domains subfolder.
- **FR-008**: The rule MUST recognize the honest planned placeholder using the
  exact literal glyph used in the corpus source, and MUST NOT treat an ASCII
  hyphen as equivalent to that glyph.
- **FR-009**: The rule MUST key its Status logic on the vocabulary actually used
  by the KPI corpus ("Seeded" and "Planned (...)") and MUST NOT assume the
  status vocabulary of any other rule.
- **FR-010**: The rule MUST NOT emit any numeric score, percentage, ratio,
  count-based grade, or any model-wide or domain-wide answerability rollup. Its
  output MUST be strictly per-question categorical (pass / ERROR / WARNING).
- **FR-011**: The rule MUST be read-only: it parses text and checks file
  existence only. It MUST NOT write, render, execute, or modify any file, and
  MUST NOT reach any network or database.
- **FR-012**: The rule's core logic MUST use only the language standard library
  (text/pattern and path handling); it MUST NOT introduce a third-party
  dependency into the governance core path.
- **FR-013**: When the rule cannot find any domain corpus to check at all (the
  domains folder or the KPI skill is absent), it MUST fail loud with a Finding
  rather than passing vacuously with nothing checked.
- **FR-014**: When the rule encounters a decision-question table row it cannot
  parse into the expected three columns, it MUST report that malformed row
  rather than silently skipping it.
- **FR-015**: The rule MUST NOT make an answerability judgment beyond
  route-resolution honesty. Specifically it MUST NOT decide whether a "Planned"
  KPI is "really" answerable, invent or propose a contract, or decide which side
  of a conflict is canonical. Such judgments remain a human ruling.
- **FR-016**: Adding the rule MUST keep the governance rule wiring consistent:
  the new rule id MUST appear in the authoritative registered-rule-id set, and
  the rule-manifest and severity-posture reference artifacts MUST be regenerated
  so the wiring self-consistency tests pass.
- **FR-017**: A row honestly marked planned uses the placeholder glyph in its
  "Routes to" cell, so there is no contract path to resolve and no stale-marker
  ambiguity in the normal case. However, if a planned row's "Routes to" cell
  names an EXISTING contract path (i.e. it is no longer the placeholder glyph and
  the named contract file exists), the rule MUST report that row as a stale
  planned marker (ERROR), mirroring the bidirectional honesty of the analogous
  routing rule: the contract was built but the row was never flipped to
  "Seeded". (Resolved in Clarifications C1.)
- **FR-018**: A single "Routes to" cell contains exactly one target; the rule
  does not attempt to parse multiple contract paths from one cell. (Resolved in
  Clarifications C5.)

### Key Entities *(include if feature involves data)*

- **Domain file**: A markdown file in the KPI knowledge skill's domains folder.
  Contains at most one decision-question table. Discovered by glob; the set is
  open-ended.
- **Decision-question row**: One row of the decision-question table. Attributes:
  question text, "Routes to" target (a skill-root-relative contract path or the
  honest placeholder glyph), and Status ("Seeded" or "Planned (...)").
- **Contract file**: A markdown file in the KPI knowledge skill's contract store
  (at the skill root, not under the domains folder). A "Seeded" route resolves
  iff its named contract file exists here.
- **Finding**: The rule's output unit -- rule id, severity (ERROR / WARNING),
  message, and a locator pointing at the offending domain file / row. This is
  the rule's only authority; it reports, it does not fix.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every decision-question row across the entire domain corpus that
  claims to be answered ("Seeded") but points at a contract that does not exist
  is reported as an ERROR, with zero such dangling rows passing undetected.
- **SC-002**: Every decision-question row that is honestly marked planned (with
  the correct placeholder glyph and a "Planned" status) produces no Finding --
  the rule creates zero false positives on honest planned rows across the whole
  corpus.
- **SC-003**: When a new domain file is added to the corpus, its
  decision-question table is checked with no change to the rule code (the rule
  never needs editing to keep pace with corpus growth).
- **SC-004**: The rule produces no numeric answerability score or rollup in any
  output mode -- a reviewer inspecting its output sees only per-question
  categorical verdicts.
- **SC-005**: The governance gate's wiring self-consistency checks pass with the
  new rule present (the registered-rule-id set, rule manifest, and
  severity-posture artifacts all agree on the new rule).

## Assumptions

- The decision-question table format observed across the corpus today (a
  three-column markdown table with "Decision question", "Routes to", "Status"
  columns under a decision-questions heading) is the stable surface the rule
  parses. A future change to that format is out of scope for this feature.
- "Routes to" contract paths are skill-root-relative. This is treated as the
  resolution base. (Whether the skill root should be a configurable parameter
  vs. a fixed join base is raised in Clarifications, since a hypothetical second
  KPI skill would break a hardcoded root.)
- The status vocabulary is exactly "Seeded" and "Planned (...)"; it is NOT the
  "Built"/"Deferred" vocabulary used by the analogous routing rule.
- The rule runs inside the existing static, read-only `retail check` rule set
  and inherits its execution model (pure function: context in, Findings out).
- Severity is observed per branch by the existing severity-posture mechanism;
  the ERROR-vs-WARNING intent stated here is the rule's authored posture, subject
  to the human confirmation raised in Clarifications.
- No deferred runtime or execution adapter is assumed to exist; this feature
  adds a static text-and-path check only.

## Dependencies

- The KPI knowledge skill's domains corpus and contract store (read-only inputs).
- The existing retail governance rule framework: the rule-context surface
  (repository root + tracked-file view), the Finding / Severity types, and the
  registration mechanism.
- The existing wiring self-consistency tests and the rule-manifest /
  severity-posture reference artifacts (must be regenerated).

## Out of Scope (YAGNI)

- Any numeric answerability score, percentage, grade, or model-wide/domain-wide
  rollup (explicitly rejected direction).
- Deciding whether a "Planned" KPI is genuinely answerable, or authoring /
  proposing any contract content.
- Executing, rendering, or publishing anything; any network or database access.
- Validating the internal correctness of a contract file's content (a separate
  concern); this rule only checks that the routed contract file EXISTS.
- Generalizing to a second KPI skill or a configurable corpus root beyond what
  the Clarifications resolve.

## Clarifications

### Session 2026-07-02

The following ambiguities were resolved by the advisor against the constitution,
the shipped analogous routing rule, and the H3 first-step scope. Each is an
engineering-posture decision provable from the analog or the corpus, NOT a
Principle-V business/PII/grain/rollup judgment. The genuine judgment calls that
the workflow is FORBIDDEN to settle are recorded separately under "Deferred to
human ruling (Principle V)" below and are left open.

**C1 -- Stale planned marker direction (Impact: high, Uncertainty: high).**
Q: Should a "Planned" row whose "Routes to" now names an existing contract be
reported? A (recommended, adopted): Yes -- ERROR (stale planned marker). Mirrors
the shipped routing rule, which fails a "planned" route whose target now exists
("built but the manifest was never flipped"). This keeps honesty bidirectional
without adding any score. Reversible: easy (single branch of the rule).
Integrated as FR-017.

**C2 -- Severity split for the two failure modes (Impact: high, Uncertainty:
medium).** Q: Dangling "Seeded" route = ERROR, and a row that is neither
resolvable-Seeded nor honestly-Planned = WARNING -- is this the intended posture?
A (recommended, adopted as the authored default): Yes. A "Seeded" claim pointing
at a missing contract is a broken promise (ERROR, fails the gate); a row in an
ambiguous middle state is a hygiene smell worth surfacing but not necessarily
build-blocking (WARNING). This matches the H3 first-step wording verbatim.
NOTE: severity is observed per branch by the severity-posture mechanism (ratified
044), so the final effective severity is confirmed by that artifact, not by this
prose. Integrated as FR-004 / FR-006. (The observed-per-branch confirmation is
recorded as an open item below because it is a posture ruling, not a code fact.)

**C3 -- Contract-path resolution base (Impact: high, Uncertainty: low).** Q:
Resolve "Routes to" relative to the skill root, the repo root, or the domains
subfolder? A (recommended, adopted): the KPI skill root. Confirmed by the corpus
today -- "contracts/<name>.md" resolves at the skill root; there is no
domains/contracts folder, and the repo-relative exact-match used by the routing
rule would make every seeded route falsely dangle. YAGNI: hardcode the single
known skill root now; do NOT introduce a configurable-root parameter for a second
KPI skill that does not exist (leave that as a noted future seam). Integrated as
FR-007. Reversible: easy.

**C4 -- Domain file that omits the decision-question table entirely (Impact:
medium, Uncertainty: medium).** Q: silent-pass or WARNING? A (recommended,
adopted): silent-pass (no Finding). The rule's job is to reconcile rows that
exist; a domain legitimately may not yet publish the table, and flagging its
absence would be a coverage/completeness check -- a different rule's concern
(YAGNI, and it risks a vacuous-scope creep). A domain that DOES publish the table
but leaves it empty (header only) likewise yields no rows to check. Integrated in
Edge Cases. Reversible: easy.

**C5 -- Multiple targets per "Routes to" cell (Impact: low, Uncertainty: low).**
Q: Can one cell route to several contracts? A (recommended, adopted): No -- the
corpus uses exactly one target (a contract path or the placeholder) per cell, so
the rule treats the cell as a single target and does not split it. Integrated as
FR-018. Reversible: easy.

### Deferred to human ruling (Principle V -- NOT answered by this workflow)

These are posture/authority rulings the agent must not self-grant. They are
recorded here and remain open for a human to settle during ratification; the
spec is written to work either way where possible.

- **OPEN-1 (severity posture confirmation)**: The ERROR-on-dangling /
  WARNING-on-ambiguous split (C2) is the authored intent, but effective severity
  is observed per branch by the severity-posture mechanism (ratified 044). A
  human must confirm this posture when the severity-posture artifact is
  regenerated; the agent records the intent, it does not rule on the posture.
- **OPEN-2 (roadmap slot / spec number for H3)**: No roadmap feature id maps to
  H3 (the "V7/F6" tag is a value/feasibility panel score, not a roadmap feature).
  A human must assign the roadmap readiness slot this rule advances; the workflow
  does not invent one.
- **OPEN-3 (canonical-side ruling on a genuine question/contract conflict)**: If
  a question's Status and its route disagree in a way that implies the domain
  corpus and the contract store contradict each other about what is answerable,
  the rule reports the inconsistency but MUST NOT decide which side is canonical
  or whether the KPI is "really" answerable -- that is a human/analyst ruling
  (FR-015). Recorded, not answered.
