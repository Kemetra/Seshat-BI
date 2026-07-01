# Feature Specification: Coverage Scorecard Linter (SL1)

**Feature Branch**: `056-coverage-scorecard-linter` (spec dir renumbered to `056-coverage-scorecard-linter` to avoid the 053 collision across the parallel kraken runs; roadmap F-number wins on any disagreement)

**Created**: 2026-07-01

**Status**: Ratified (advisor-for-Ahmed-Shaaban, 2026-07-01)

**Ratification note**: Ratified by the advisor agent under the explicit, recorded per-session
delegated override granted by the repo owner (info@rahmaqanater.org) for the 2026-07-01
"release the kraken" batch of seven idea-to-spec specs. Provenance: this Ratified line is
AI-authored under recorded human authority; NOT a human-typed ratification -- the git author
identity does not by itself attest a human reviewer. Design decisions confirmed at ratify:
new rule id **SL1**; filled scorecard instances live under `mappings/<table>/` (PP1 per-table
precedent); the generic template file is EXCLUDED from scanning by explicit path; the
contract-path-resolves invariant applies ONLY to `Covered` rows (Planned / Out-of-scope carry
`--`). The linter validates STRUCTURE only (status-enum membership, four-column shape,
blocker-present, contract-path-resolves-when-Covered, no-percentage) and NEVER adjudicates
whether a stated coverage is true (Principle V). Adds ONE `@register` rule + its id to
EXPECTED_RULE_IDS + a rules-manifest regen (38 -> 39). TDD: RED tests (T003/T004) precede the
GREEN rule (T005). analyze=clean (0 critical/0 high); plan-review=PASS-WITH-NOTES. Override is
per-session/per-this-set only; it covers ratification, not merge (normal CI gate still applies).

**Input**: User description: "Coverage Scorecard Linter"

## Overview

A KPI **coverage scorecard** answers one question for one source table: which KPIs
can this table support today, and what blocks the rest? The generic structure of
that scorecard was shipped earlier as a template
(`skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md`). The
template defines a small closed vocabulary: a per-table title line
(`> Table: ...`), a four-column status table
(`| KPI | Contract | Coverage status | Blocker ... |`), a closed set of coverage
statuses (Covered / Blocked -- missing field / Blocked -- needs business definition /
Planned / Out of scope), a named-blocker column, and one hard law: coverage is a
status plus a named blocker, **never a number or percentage** (hard rule #9, no
fabricated confidence -- the template literally says "if you are tempted to compute
a percentage, stop").

Today those laws are enforced only by prose and human review. A person could commit
a filled per-table scorecard whose status cell reads a value outside the closed
enum, whose Blocked row names no blocker, whose Covered row points at no contract,
or that quotes a coverage percentage -- and no gate would fail.

This feature adds ONE static rule -- labelled `SL1` in the idea-bank sequence --
that turns the template's own laws into a structural check. The rule scans every
committed filled per-table scorecard instance, parses its status table, and asserts
four structural invariants:

1. **Status-enum membership** -- every row's Coverage status cell is one of the five
   closed template statuses.
2. **Blocker presence** -- a row whose status is a `Blocked -- ...` value names a
   blocker (its Blocker cell is non-empty and is not the em-dash placeholder).
3. **Contract-path resolves (conditional)** -- a row whose status is `Covered` cites
   a contract path (`contracts/<file>.md`) that resolves to a committed tracked
   file; rows whose status is `Planned` or `Out of scope` legitimately carry the
   em-dash `--` and are exempt.
4. **No percentage** -- no row contains a percentage token (a number immediately
   followed by `%`) in any cell; coverage must be status + blocker, never a score.

A violation of any invariant produces a `Severity.ERROR` Finding so the gap is
caught by the gate rather than discovered downstream.

`SL1` is the CHECK sibling of the coverage-scorecard template, exactly as `PP1`
(`src/retail/rules/publish_pack.py`) is the completeness check over the handoff-pack
template. It follows the PP1 shape precisely: iterate `RuleContext.tracked_files`,
filter to per-table scorecard instances, EXCLUDE the generic template file itself
(it is placeholders and an illustrative worked example by design), parse the status
table positionally, emit `Severity.ERROR` Findings, and read committed text with the
stdlib only -- it never opens a connection, runs a query/DAX, or executes an agent,
and stays import-safe at module scope (the Never-Execute invariant, B1/B3 family).

**Principle-V boundary (structural check, never adjudication).** `SL1` checks that a
coverage STATUS is a member of the closed enum and that its supporting slots
(blocker cell, contract path) are STRUCTURALLY present when the status requires them.
It MUST NOT decide whether a stated `Covered` is TRUE (that would require knowing the
table's real fields and the contract's real status), grant any readiness stage, or
populate a status itself. This mirrors PP1's "slot present, never grant" discipline:
a filled slot passes; SL1 grants nothing and adjudicates no coverage correctness.

**Generic-only (Principle VII / hard rule #7).** C086/pharmacy is an example, not the
schema. `SL1` and every one of its fixtures validate STRUCTURE only -- the closed
status enum, the four-column table shape, blocker presence, contract-path resolution,
the no-percentage law. It hardcodes NO specific KPI name, field name, or domain table.
The template's own illustrative `raw.sales` worked example is explicitly excluded
from scanning (like PP1 excludes its template).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Catch a malformed filled scorecard (Priority: P1)

As the static checker (the gate a maintainer runs before merge), when a committed
per-table coverage scorecard breaks one of the template's structural laws, I report
a Finding naming the offending file, row, and law so the maintainer fixes it before
the malformed scorecard is trusted downstream.

**Why this priority**: This is the entire value of the rule -- turning the template's
prose laws into an enforced gate. Without it the laws are advisory only.

**Independent Test**: Point the rule at a synthetic filled scorecard fixture that
(a) uses a status outside the enum, (b) leaves a Blocked row's blocker cell empty,
(c) marks a row Covered but cites a contract path that does not resolve, and (d)
quotes a percentage. The rule reports at least one Finding for each defect.

**Acceptance Scenarios**:

1. **Given** a committed scorecard with a Coverage status cell reading a value not in
   the closed enum, **When** the checker runs, **Then** it reports an ERROR Finding
   for that row identifying the invalid status.
2. **Given** a committed scorecard row whose status is `Blocked -- missing field` and
   whose Blocker cell is empty or a bare `--`, **When** the checker runs, **Then** it
   reports an ERROR Finding for the missing named blocker.
3. **Given** a committed scorecard row whose status is `Covered` and whose Contract
   cell cites `contracts/<file>.md` that is not a tracked file, **When** the checker
   runs, **Then** it reports an ERROR Finding for the unresolved contract path.
4. **Given** a committed scorecard containing a percentage token (e.g. `70%`) in any
   cell, **When** the checker runs, **Then** it reports an ERROR Finding for the
   fabricated-confidence percentage.

---

### User Story 2 - Pass a well-formed scorecard and never fire on the template (Priority: P1)

As the static checker, a fully well-formed per-table scorecard produces zero
Findings, and the generic template file (and its illustrative worked example) is
never scanned -- so the rule adds no false positives.

**Why this priority**: A gate that false-positives on the shipped template or on a
correct scorecard is worse than no gate; the exclusion discriminator and the
clean-instance pass are as load-bearing as the catch.

**Independent Test**: Run the rule against (a) a synthetic well-formed scorecard
fixture and (b) the real generic template path; assert zero Findings from both.

**Acceptance Scenarios**:

1. **Given** a committed per-table scorecard where every row has a valid status, every
   Blocked row names a blocker, every Covered row cites a resolving contract path, and
   no cell holds a percentage, **When** the checker runs, **Then** it reports zero
   Findings for that file.
2. **Given** the generic template file at its committed path (which contains
   `<placeholder>` tokens and an illustrative worked-example table), **When** the
   checker runs, **Then** it reports zero Findings (the template is excluded).
3. **Given** committed test-fixture scorecards under `tests/`, **When** the checker
   runs, **Then** it reports zero Findings for them (the `is_test_path` exemption).

---

### User Story 3 - Register cleanly into the single-source rule set (Priority: P2)

As the rule registry, the new rule id joins the single source-of-truth expected id
set in the same change, so the wiring/snapshot test passes and there is no silent
rule-id drift.

**Why this priority**: A registered-but-unwired rule (or a wiring test out of sync)
is a known repo failure mode; this keeps the registry symmetric.

**Independent Test**: Add the id to `EXPECTED_RULE_IDS`, run the wiring test, confirm
`actual == EXPECTED` and the tuple length matches, with no hard-coded numeric baseline.

**Acceptance Scenarios**:

1. **Given** the new rule is registered and its id is added to `EXPECTED_RULE_IDS`,
   **When** the wiring test runs, **Then** the registered id set equals the expected
   set exactly and no duplicate registration exists.

---

### Edge Cases

- **No filled instances committed** (the state on main today): the rule finds zero
  scorecard instances and reports zero Findings -- a silent pass by absence, not by
  clean instances. The rule must not crash or emit a spurious finding when its glob
  matches nothing. (See Assumptions: instance location is a defined spec decision so
  the rule is not permanently dormant.)
- **Row with status `Planned` or `Out of scope` and a `--` contract cell**: legitimate;
  the contract-path-resolves invariant does NOT apply to these statuses.
- **A `Blocked -- ...` row whose Blocker cell is the bare em-dash `--`**: treated as a
  missing named blocker (ERROR) -- the em-dash is the "no blocker" placeholder and a
  Blocked status by definition has a blocker to name.
- **Unreadable tracked scorecard file**: fails loud with an ERROR Finding rather than
  crashing the gate (PP1's fail-loud-on-unreadable precedent).
- **A stray four-column table elsewhere in the scorecard document**: the status table
  is anchored (by the `> Table:` title line / the status-table header) so an unrelated
  table cannot inject phantom rows or mask a malformed one (PP1's section-anchoring
  precedent).
- **A percentage that is legitimately part of a KPI NAME** (e.g. a KPI literally named
  with `%`, as the template's own worked example shows "Returns Rate % (Value)"): see
  Clarifications -- the no-percentage law targets a NUMBER-then-`%` token (a computed
  score), not the literal `%` glyph inside a KPI name.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The rule MUST scan every committed filled per-table coverage scorecard
  instance and MUST NOT scan the generic template file
  (`skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md`) nor
  committed test fixtures under `tests/`.
- **FR-002**: The rule MUST assert that every status-table row's Coverage status cell
  is a member of the closed template enum {Covered, Blocked -- missing field,
  Blocked -- needs business definition, Planned, Out of scope}, emitting an ERROR
  Finding for any value outside the set.
- **FR-003**: The rule MUST assert that a row whose status is a `Blocked -- ...` value
  names a blocker (the Blocker cell is non-empty and is not the bare em-dash `--`),
  emitting an ERROR Finding when it does not.
- **FR-004**: The rule MUST assert that a row whose status is `Covered` cites a
  contract path (`contracts/<file>.md`) that resolves to a committed tracked file,
  emitting an ERROR Finding when the cited path does not resolve; rows whose status is
  `Planned` or `Out of scope` are EXEMPT from this check and may carry `--`.
- **FR-005**: The rule MUST emit an ERROR Finding for any scorecard containing a
  percentage token (a number immediately followed by `%`) in a status-table cell --
  the no-fabricated-confidence law.
- **FR-006**: The rule MUST verify STRUCTURE only (enum membership, blocker presence,
  contract-path resolution, no-percentage) and MUST NOT adjudicate whether a stated
  coverage is TRUE, grant any readiness stage, or populate/modify any status
  (Principle V, slot-present-not-granted).
- **FR-007**: The rule MUST read committed text using the standard library only,
  MUST open no database/network/Power BI connection, run no query/DAX/agent, and stay
  import-safe at module scope (Never-Execute, B1/B3 family).
- **FR-008**: The rule MUST fail loud (emit an ERROR Finding) on a tracked-but-
  unreadable scorecard rather than crashing the gate.
- **FR-009**: The rule MUST anchor its status-table parse (via the per-table title
  line and/or the status-table header) so an unrelated four-column table in the same
  document contributes no rows and masks no malformed row.
- **FR-010**: The rule's new registry id MUST be added to the single source-of-truth
  `EXPECTED_RULE_IDS` set in the wiring test in the same change; the wiring/snapshot
  test MUST pass with `actual == EXPECTED` and no hard-coded numeric baseline.
- **FR-011**: The rule, its enum, and every fixture MUST contain no domain-specific
  schema artifact (no specific table, column, or KPI name); fixtures are generic
  synthetic scorecards, and the illustrative worked-example content is never inlined
  as a fixture answer (Principle VII / hard rule #7).
- **FR-012**: All authored artifacts MUST be ASCII, UTF-8 without BOM (use `--` and
  `->`, no glyphs), per rule IX.

### Key Entities

- **Coverage scorecard instance**: a committed per-table markdown file carrying the
  template's status table; the artifact the rule scans. Its committed location and
  match glob are a spec decision (see Clarifications / Assumptions).
- **Coverage status enum**: the closed set of five statuses the template defines; the
  membership set the rule checks against.
- **Status-table row**: KPI + Contract + Coverage status + Blocker; the positional
  unit the rule parses and validates.
- **Contract path**: a `contracts/<file>.md` reference (or the em-dash `--`); resolved
  against tracked files when the status requires it.
- **Percentage token**: a number-then-`%` sequence; its presence is a violation of the
  no-fabricated-confidence law.
- **Finding**: an immutable result object (rule id, severity, message, locator) emitted
  per violation.
- **Rule registration record**: the rule's registry id + title, mirrored into the
  wiring test's expected id set.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A committed per-table scorecard with a status outside the closed enum, a
  Blocked row with no named blocker, a Covered row citing an unresolved contract path,
  or a percentage token each causes the checker to report at least one Finding.
- **SC-002**: A fully well-formed per-table scorecard produces zero Findings (no false
  positives on a correct instance).
- **SC-003**: The generic template file and committed test fixtures under `tests/`
  produce zero Findings (the template's placeholders and illustrative worked example
  are never flagged).
- **SC-004**: With zero filled scorecard instances committed, the checker reports zero
  Findings and does not crash (silent pass by absence).
- **SC-005**: The live registry id set and the wiring test's expected id set agree
  exactly after the rule is added (the snapshot test passes), with no hard-coded
  numeric baseline.
- **SC-006**: At least one test invokes the rule directly and observes it fire on a
  known-bad fixture (the rule is exercised, not merely listed).
- **SC-007**: The rule, its enum, and every fixture contain no domain-specific schema
  artifact (no specific table, column, or KPI name); fixtures are generic synthetic
  scorecards.
- **SC-008**: Running the checker with the rule added introduces no new third-party
  dependency and performs no network or database access.
- **SC-009**: No code path adjudicates coverage correctness, grants a readiness stage,
  or writes/populates any status cell (Principle-V boundary held).

## Assumptions

- **Instance location and glob** (spec decision, resolved in Clarifications): filled
  per-table scorecards live under `mappings/<table>/` following the PP1 per-table
  instance pattern, and the rule matches instances by filename suffix
  (`*coverage-scorecard.md`) while EXCLUDING the single generic template path. This
  makes the rule's target concrete so it is not permanently dormant; if the repo later
  standardizes a different committed location, the glob is updated with the location.
- **Template exclusion discriminator**: unlike PP1 (which excludes a fixed `templates/`
  prefix), the scorecard template lives under
  `skills/retail-kpi-knowledge/references/` -- so the exclusion is by the explicit
  template file path, not a directory prefix.
- **The rule is stdlib-only and static** -- it reuses the existing `RuleContext` /
  `Finding` / `Severity` / `is_test_path` / `register` API surface already consumed by
  PP1; no new runtime, dependency, or executor is introduced (Principle VIII,
  static-first).
- **Roadmap placement**: this idea belongs to the ongoing idea-bank rule sequence
  (A1/B1/A3/B3/PP1/SC1/DF1, specs 047-052) that the roadmap records as advancing NO
  readiness stage and granting no approval; it is NOT mapped to a roadmap F-number
  (see open question in Clarifications).
- **Live rule count is 38** (S/D/R/A/B/C/G/P + PP1/SC1/DF1); the spec keys off the live
  `EXPECTED_RULE_IDS` set, not the stale "33/34" prose baseline in some backlog panels.

## Clarifications

### Session 2026-07-01

(Advisor-resolved and human-carve-out clarifications are recorded below. Human
carve-out items -- Principle V judgment calls the agent is forbidden to answer -- are
marked OPEN FOR HUMAN and are NOT answered here.)

**Q1 (advisor-resolved) -- Where do filled per-table scorecards live, and what is the
authoritative match glob so the rule is not permanently dormant?**

- Decision: filled instances live under `mappings/<table>/` (the PP1 per-table
  instance pattern) and the rule matches by filename suffix `*coverage-scorecard.md`,
  scanning `RuleContext.tracked_files` and excluding the one generic template path and
  `tests/` fixtures.
- Reasoning: no filled instance exists on main today, so absent a defined location the
  rule would silently never fire. PP1 already establishes `mappings/<table>/...` as the
  per-table artifact home; reusing it keeps the retail-check family consistent and
  gives the rule a real target. The suffix match (not a fixed full path) tolerates the
  per-table subpath while still pinning the artifact kind.
- Reversible: easy (a one-line glob/suffix change if the repo later standardizes a
  different committed location).

**Q2 (advisor-resolved) -- What discriminator excludes the generic template (and its
illustrative worked example) from scanning?**

- Decision: exclude by the explicit template file path
  `skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md`. Because
  the template is a REFERENCES doc (not under `templates/`), PP1's directory-prefix
  exclusion does not transfer; an explicit-path exclusion is used instead. The
  template's illustrative `raw.sales` worked-example table lives inside that same file
  and is therefore excluded with it.
- Reasoning: the template is placeholders-plus-illustration by design; scanning it
  would false-positive (its worked-example contract paths are illustrative, its cells
  hold `<placeholder>` tokens, and its KPI names include a literal `%`). PP1 sets the
  exclude-the-template precedent; only the discriminator kind differs.
- Reversible: easy.

**Q3 (advisor-resolved) -- Which coverage statuses REQUIRE a resolving
`contracts/<file>.md` path versus may legitimately carry `--`?**

- Decision: only `Covered` requires a resolving contract path. `Planned` and
  `Out of scope` explicitly carry the em-dash `--` (the template shows this) and are
  EXEMPT. The two `Blocked -- ...` statuses are NOT required to cite a resolving
  contract path (a blocked KPI's contract may be un-seeded or its file may not yet
  exist); they are checked for a named BLOCKER instead (FR-003), not a contract path.
- Reasoning: the template's own worked example shows `Blocked -- ...` rows citing a
  `contracts/<file>.md` in some cases and the meaning of Blocked is "cannot cover yet",
  so requiring a resolving contract on a Blocked row would over-constrain. Tying the
  hard contract-resolution requirement to `Covered` only mirrors the template's
  semantic ("Covered = contract Seeded AND fields present") without adjudicating
  whether the contract is truly Seeded (that stays a human/readiness call, Principle V).
- Reversible: costly-ish (tightening Blocked rows later would newly fail existing
  instances) -- deliberately kept to the minimal `Covered`-only requirement now.

**Q4 (advisor-resolved) -- What exactly is a forbidden "percentage", given the
template's own example KPI name "Returns Rate % (Value)" contains a literal `%`?**

- Decision: the no-percentage law targets a NUMBER immediately followed by `%` (a
  computed score token such as `70%`), not the literal `%` glyph inside a KPI name. A
  KPI named with `%` but carrying no number-then-`%` token does not trip the rule.
- Reasoning: hard rule #9 forbids a fabricated numeric coverage SCORE, not the `%`
  character as text; a digit-then-`%` token is the score signature. This avoids a false
  positive on legitimately `%`-named KPIs while still catching "70% covered".
- Reversible: easy.

**OPEN FOR HUMAN (Principle V -- NOT answered by the agent)**

- **Roadmap-stage placement**: does a KPI-coverage linter advance any readiness stage
  or map to a roadmap F-number, or does it follow the prior idea-bank rule sequence
  (A1/B1/A3/B3/PP1/SC1/DF1) treatment of advancing NO stage and granting no approval?
  The spec assumes the "advances no stage, unmapped" treatment (see Assumptions) but
  the authoritative governance placement is a human ruling, not an agent guess.
- **Principle-V structural-only boundary confirmation**: confirm that `SL1` verifies
  STRUCTURE only (enum membership, blocker presence when the status is Blocked,
  contract-path resolution when the status is Covered, no-percentage) and MUST NEVER
  decide whether a stated `Covered` is TRUE, grant any readiness stage, or populate a
  status itself. The spec is authored to this boundary (FR-006, SC-009), but the
  judgment that "structure-only is the correct and sufficient scope" is a human
  governance confirmation, mirroring PP1's ratified Principle-V publish-safety ruling.
