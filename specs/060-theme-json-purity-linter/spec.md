# Feature Specification: Theme JSON Purity Linter

**Feature Branch**: `060-theme-json-purity-linter`

**Created**: 2026-07-01

**Status**: Ratified (Ahmed Shaaban, 2026-07-01)

> Ratified under the recorded per-spec delegated ratify override for A2 dated
> 2026-07-01 (owner-authorized full-autonomous run; advisor exercised the
> delegated authority to make the recommended calls and resolve the two
> Principle-V items with conservative defaults). This is a per-spec override,
> not a standing waiver of the ratify gate. analyze: clean (0 critical/0 high);
> plan-review: PASS-WITH-NOTES (no BLOCKED finding).

**Input**: User description: "A2. Theme JSON Token-Contract / Four-Surface Purity Linter"

## Overview

Power BI theme JSON files are "surface 3" of the four design surfaces. Their only
job is styling DEFAULTS -- colors, fonts, and the default formatting a visual
inherits. The purity contract in `docs/powerbi/theme-json.md` states plainly what
a theme file MUST NOT carry: business logic (DAX, measures, calculated
columns/tables), metric definitions, semantic-model relationships, source
mapping, sentiment thresholds/rules, and data validation. That meaning lives in
other surfaces and other features (metric contracts, the semantic model), where
it is reviewed.

Today the contract is prose enforced only by agent judgment. A metric definition
smuggled into a styling file is unreviewed business logic in the wrong place: it
bypasses metric-contract review, it is invisible to anyone reading the contracts,
and it silently changes meaning when someone edits a "color file." This feature
turns that prose contract into a static, CI-enforced governance rule: a new
registered rule that scans committed theme JSON files for forbidden
business-logic keys and fails the contract check (non-zero exit) when it finds
one.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A contaminated theme file fails the contract check (Priority: P1)

A contributor edits a committed theme JSON file and, intending to centralize a
KPI's coloring logic, adds a key that carries business meaning (for example a
measure definition or a numeric sentiment threshold). When the contract check
runs (locally or in CI), the check reports an ERROR that names the offending file
and the exact location of the forbidden key, and the check exits non-zero so the
change cannot pass silently.

**Why this priority**: This is the whole point of the feature -- catching
business logic that has leaked into a styling file. Without it, the feature
delivers nothing. It is a viable MVP on its own: a single ERROR finding on a
contaminated file is the complete value.

**Independent Test**: Point the rule at a fixture theme file that contains a
forbidden business-logic key; confirm it emits exactly one ERROR finding per
forbidden key, each carrying the file path and a location pointer, and that the
contract check exits non-zero.

**Acceptance Scenarios**:

1. **Given** a committed theme JSON file that contains a forbidden business-logic
   key, **When** the contract check runs, **Then** it emits an ERROR finding that
   identifies the file and the location of the forbidden key, and the overall
   check exits non-zero.
2. **Given** a theme JSON file with a forbidden key nested inside a deeper object,
   **When** the contract check runs, **Then** the finding's location points to the
   nested key (not merely the top-level file), so the author can find it.
3. **Given** a theme JSON file that contains two distinct forbidden keys, **When**
   the contract check runs, **Then** two separate ERROR findings are emitted (one
   per forbidden key), so no violation is masked by another.

### User Story 2 - A clean, allowed theme file passes (Priority: P1)

A contributor authors or edits a theme JSON file that stays within the allowed
styling vocabulary (color palette, fonts, visual defaults, page/wallpaper
defaults, filter-pane defaults, sentiment COLORS). When the contract check runs,
the rule produces no findings for that file, so legitimate styling work is never
blocked.

**Why this priority**: A purity rule that flags legitimate styling is worse than
no rule -- it trains contributors to ignore it. The allowed-vocabulary pass is as
essential as the forbidden-key catch; the two together define the rule's
correctness boundary.

**Independent Test**: Point the rule at a fixture theme file that uses only
allowed styling keys (including a sentiment COLOR such as a success green);
confirm the rule emits zero findings.

**Acceptance Scenarios**:

1. **Given** a theme JSON file that sets only allowed styling defaults, **When**
   the contract check runs, **Then** the rule emits zero findings for that file.
2. **Given** a theme JSON file that sets a sentiment COLOR (an allowed styling
   default) but carries no sentiment threshold or rule, **When** the contract
   check runs, **Then** the rule emits zero findings -- the color is allowed even
   though the threshold would not be.
3. **Given** the repository's single committed starter theme file in its current
   clean state, **When** the contract check runs, **Then** the rule emits zero
   findings (the rule does not break the existing green build).

### User Story 3 - The rule is generic and self-registering (Priority: P2)

A maintainer adds a second theme file for a different subject area or tenant. The
rule scans it automatically because it discovers theme files by a generic file
pattern, not by an enumerated list, and it applies the same generic vocabulary
derived from the shared purity contract -- never a tenant-specific or
example-specific key. The rule also appears in the project's governance records
(the rule registry and its golden records) so its presence is verifiable.

**Why this priority**: Generality and self-registration are what make the rule
durable and trustworthy, but the rule delivers its core value (US1 + US2) even
before a second theme file exists. This story protects against the rule silently
missing new files or hardcoding one tenant's shape.

**Independent Test**: Add a second fixture theme file (outside the test-exemption
path) and confirm the rule scans it without any code change; confirm the rule's
identifier appears in the registry and the governance golden records; confirm no
tenant/example-specific key or palette value appears anywhere in the rule's
vocabulary.

**Acceptance Scenarios**:

1. **Given** more than one committed theme JSON file, **When** the contract check
   runs, **Then** the rule scans every committed theme file discovered by the
   generic pattern, not a hardcoded list.
2. **Given** the rule is registered, **When** the governance records are
   generated and the wiring test runs, **Then** the rule's identifier is present
   in the registry, the rule manifest, and the severity-posture record, and the
   wiring test passes.
3. **Given** a theme file that lives under the test-fixture exemption path,
   **When** the contract check runs against the live corpus, **Then** the
   fixture is not treated as a live theme file (fixtures may deliberately carry
   forbidden keys to exercise the rule).

### Edge Cases

- **Malformed theme JSON**: A committed theme file that is not valid JSON cannot
  be scanned for keys. The rule must not crash the whole contract check on a
  parse failure; it surfaces a finding that the file could not be parsed rather
  than silently passing it. (See FR-009.)
- **Empty or trivial theme file**: A theme file with no keys, or only allowed
  keys, emits no findings.
- **Forbidden key appearing as a value, not a key**: A legitimate string value
  that happens to equal a forbidden word (for example a color literally named
  "measure") must not be flagged; the rule inspects key names / structural
  positions, not free-text values. (See FR-005.)
- **Same forbidden key at multiple locations**: Each distinct occurrence is
  reported at its own location so none is masked.
- **No committed theme files at all**: The rule emits no findings and does not
  error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a governance rule that scans committed theme
  JSON files for keys that carry business logic, metric meaning, model structure,
  source mapping, sentiment thresholds/rules, or data validation, per the purity
  contract in `docs/powerbi/theme-json.md`.
- **FR-002**: The system MUST discover the theme files it scans by a generic file
  pattern (all committed theme JSON files), never by an enumerated or
  tenant-specific list.
- **FR-003**: When a forbidden business-logic key is present in a theme file, the
  system MUST emit an ERROR finding that identifies the file and the location of
  the offending key within that file, using the existing file-plus-pointer locator
  convention already used by the project's JSON-scanning rules.
- **FR-004**: The system MUST emit one distinct finding per forbidden key
  occurrence so that no violation is masked by another.
- **FR-005**: The rule MUST decide violations by a categorical present/absent
  check on key names and structural positions. It MUST NOT flag a key based on a
  free-text data value, and it MUST NOT adjudicate a borderline business-meaning
  question -- any genuinely ambiguous case is surfaced for a human, never
  auto-resolved (Principle V).
- **FR-006**: A theme file that uses only the allowed styling vocabulary (color
  palette, fonts, visual defaults, page/wallpaper defaults, filter-pane defaults,
  and sentiment COLORS) MUST produce zero findings.
- **FR-007**: The forbidden-key vocabulary and allowed-key vocabulary MUST be
  derived from the generic purity contract, and MUST NOT contain any
  tenant-specific, example-specific, or brand-specific key or value (Principle
  VII).
- **FR-008**: The rule MUST fail the contract check closed -- a purity violation
  is an ERROR that causes a non-zero exit, not an advisory note (Principle I).
- **FR-009**: The rule MUST handle a committed theme file that cannot be parsed as
  JSON by surfacing a finding rather than crashing the whole contract check or
  silently passing the file.
- **FR-010**: The rule MUST exempt committed test fixtures from the live scan, so
  fixtures that deliberately carry forbidden keys (used to exercise the rule) do
  not fail the live contract check, following the existing file-scanning-rule
  exemption pattern.
- **FR-011**: The rule MUST declare a single freshly-allocated rule identifier
  that does not collide with any already-registered rule identifier (the backlog
  letters A1/A2 collide with shipped ids, so a bare backlog letter MUST NOT be
  reused; a design/theme-namespaced identifier is preferred). The exact literal id
  is finalized against the TRUE live registry at wiring time. Its severity is
  OBSERVED per branch from its emitted findings, not declared as a governed
  per-rule severity table (ratified 044).
- **FR-012**: The rule MUST be wired into the five governance records so its
  presence is verifiable and drift fails closed: the rule module, the
  side-effecting import registration and public export list, the expected-rule-id
  set the wiring test asserts, the generated rule manifest, and the generated
  severity-posture record.
- **FR-013**: The exact forbidden-key vocabulary boundary -- which literal key
  names count as business-logic contamination and which sentiment-adjacent keys
  stay allowed, plus whether the rule asserts any REQUIRED-key presence in
  addition to forbidden-key absence -- MUST be settled before wiring, because the
  golden records freeze it. [NEEDS CLARIFICATION: this is a Principle-V boundary
  judgment about where styling ends and business meaning begins; it is deferred to
  the Clarifications block for a human ruling and is not auto-resolved here.]

### Key Entities *(include if feature involves data)*

- **Theme file**: A committed styling-defaults document (surface 3). The unit the
  rule scans. Attributes relevant here: its file location, and the set of keys and
  their nesting it contains.
- **Purity contract**: The generic, already-shipped MUST / MUST-NOT statement of
  what a theme file may and may not carry (`docs/powerbi/theme-json.md`). The
  source of the rule's allowed / forbidden vocabulary.
- **Finding**: A single reported violation, carrying the rule identifier, a
  severity, a human-readable message, and a location that names the file and the
  position of the offending key within it.
- **Governance records**: The registry plus the four golden records (import
  registration and export list, the expected-rule-id set, the rule manifest, the
  severity-posture record) that make the rule's presence verifiable and fail
  closed on drift.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of committed theme files that carry a forbidden business-logic
  key produce at least one ERROR finding and cause the contract check to exit
  non-zero.
- **SC-002**: 100% of committed theme files that use only the allowed styling
  vocabulary produce zero findings (zero false positives on legitimate styling).
- **SC-003**: The existing committed starter theme, in its current state, produces
  zero findings -- the rule does not break the current green build.
- **SC-004**: When two forbidden keys are present in one file, exactly two
  findings are produced (one per occurrence), so no violation is masked.
- **SC-005**: A newly added committed theme file is scanned with no change to the
  rule's code (generic discovery), and no tenant/example-specific key or value
  appears anywhere in the rule's vocabulary.
- **SC-006**: The rule's identifier is present in the registry and all governance
  golden records, and the wiring test passes (drift fails closed).

## Assumptions

- The purity contract in `docs/powerbi/theme-json.md` is the authoritative,
  generic source of the allowed / forbidden vocabulary; the rule enforces exactly
  that contract and no tenant-specific extension of it.
- Scope is the PURITY (forbidden-key-absent) concern only. The distinct
  token-to-theme FIDELITY concern (whether the theme's palette matches the design
  tokens) is a separate, currently-unbuilt rule and is OUT OF SCOPE here.
- The rule runs entirely over committed text using the project's existing static
  governance mechanism; it requires no Power BI Desktop, no live service, and no
  network access (Principle VIII, static-first).
- The rule declares one identifier and observes its severity per branch; it does
  not introduce a governed per-rule severity table (ratified 044).
- The rule reads styling source that carries no secrets; all authored artifacts
  are ASCII, UTF-8 without BOM, with short paths (Principle IX).
- The existing file-scanning rules' test-fixture exemption behavior is reused so
  fixtures may deliberately carry forbidden keys.

## Clarifications

### Session 2026-07-01

Advisor-resolved ambiguities (recommended answers integrated into the spec):

- **Q1 -- Rule-id allocation.** The backlog letters A1/A2 collide with the
  already-registered routes-family identifiers (A1 = Route Registry Manifest,
  A3 = Route Coverage). The theme PURITY rule needs a fresh, non-colliding
  identifier. **Recommended answer**: allocate a fresh identifier that is not any
  currently-registered id, and prefer a design/theme-namespaced identifier over a
  bare backlog letter so future design-lint rules (for example the unbuilt
  token-to-theme fidelity rule) share a legible namespace rather than reusing an
  ambiguous single letter. The exact literal string is finalized against the TRUE
  live registry at wiring time (reconcile against the real set, not a count
  claim). **Reasoning**: reusing "A2" as a rule id when A1/A3 already mean
  something unrelated would freeze a confusing id into the golden records; a
  namespaced id is self-documenting and collision-safe. **Reversible**: costly
  (the id is frozen into golden records once wired; changing it later is a
  breaking rename across five places).

- **Q2 -- Violation location format.** How should a finding point at the offending
  key? **Recommended answer**: use the existing file-plus-pointer locator
  convention already used by the co-shipped JSON-scanning rule (a `file#/pointer`
  form that walks the key path to the offending key). **Reasoning**: this is the
  established precedent in the codebase for JSON findings; reusing it keeps
  findings consistent and requires no new convention. **Reversible**: easy (a
  message/locator format detail, not a golden-record contract).

- **Q3 -- Theme-file discovery mechanism.** How are the files to scan selected?
  **Recommended answer**: discover them generically from the committed file set by
  a theme-file naming pattern, excluding the test-fixture exemption path -- never
  an enumerated or tenant-specific list. **Reasoning**: Principle VII requires the
  rule be generic; an enumerated list would silently miss new theme files and
  couple the rule to today's corpus. **Reversible**: easy (the discovery predicate
  can be widened/narrowed without touching the golden records).

Principle-V rulings (RESOLVED by the owner-delegated advisor under the recorded
per-spec ratify override for A2 dated 2026-07-01; conservative defaults per the
autonomous directive -- each ruling narrows scope, never expands it):

- **RESOLVED -- Exact forbidden-key vocabulary boundary.** The rule forbids a
  frozen, case-insensitive literal set of JSON key names that carry business
  logic, derived directly from the prose MUST-NOT categories in
  `docs/powerbi/theme-json.md`. A key is a violation when its normalized name
  (lowercased, separators removed) equals or contains any of: `dax`, `measure`,
  `calculatedcolumn`, `calculatedtable`, `calculated`, `expression`,
  `threshold`, `rule`, `relationship`, `sourcemapping`, `validation`,
  `metricdefinition` (so `calculated-table`, `calculatedTable`, and
  `calculated_table` all match). Sentiment-adjacent COLOR keys stay ALLOWED
  explicitly: `good`, `neutral`, `bad`, `dataColors`, `foreground`,
  `background`, `tableAccent`, and color/font/format-default keys under
  `visualStyles`. The line: a sentiment COLOR is styling (allowed); a sentiment
  THRESHOLD or RULE is business meaning (forbidden). This literal list is the
  frozen contract the golden records encode; widening it later is a deliberate
  follow-on rule change, not a silent edit. **Rationale**: converts the
  already-shipped prose contract verbatim into machine form without inventing new
  prohibitions -- the conservative reading.

- **RESOLVED -- Required-key assertion scope.** The rule is **MUST-NOT-only**: it
  asserts forbidden keys are ABSENT and asserts NOTHING about required keys. The
  purity contract mandates no theme key as REQUIRED, so asserting any required
  key would invent a rule the contract does not support (a Principle-V and
  Principle-VII overreach). Any future required-key assertion is a separate,
  additive rule with its own spec. **Rationale**: the narrowest seam that fully
  satisfies the idea's purity intent; strictly the conservative default.

Both rulings above are now ANSWERED, so the final golden-record wiring freeze is
unblocked for implement. No OPEN Principle-V item remains for this spec.
