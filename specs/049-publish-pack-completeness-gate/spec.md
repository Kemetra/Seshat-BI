# Feature Specification: Publish-pack completeness gate (PP1)

**Feature Branch**: `049-publish-pack-completeness-gate`

**Created**: 2026-06-30

**Status**: Ratified (advisor-for-Ahmed-Shaaban, 2026-06-30)

**Ratification note**: Ratified by the advisor agent acting under an explicit,
recorded per-spec delegated override granted by the repo owner
(info@rahmaqanater.org) for the 2026-06-30 unattended overnight session. Provenance:
this Ratified line is AI-authored under recorded human authority; it is NOT a
human-typed ratification and the git author identity does not by itself attest a
human reviewer. All governance questions (readiness stage, Principle-V publish-safety
boundary, required-section set, severity, no-packs behavior, template exclusion,
receipt optionality) are resolved as recorded rulings in the Clarifications section.
The Principle-V publish-safety boundary is confirmed: PP1 verifies the approval slot
is PRESENT and non-placeholder ONLY -- it never inspects, validates, populates, or
grants the sign-off. analyze=clean (0 critical/0 high); plan-review=PASS-WITH-NOTES.

**Input**: User description: "Publish-pack completeness gate (PP1)"

## Overview

When a table or report reaches Publish Ready (the final readiness stage), the
agent assembles a committed BI Handoff Pack -- a documentation/evidence bundle
that composes the table's readiness evidence (metric contracts, readiness
scorecard, reconciliation evidence, known-data caveats, data dictionary) and
records a human publish approval. The generic structure of that pack lives in
`templates/handoff/bi-handoff-pack.md`; each table copies it to
`mappings/<table>/handoff/bi-handoff-pack.md`, fills every `<placeholder>`, and
commits it.

Today nothing structurally checks that a committed pack is actually COMPLETE. A
pack can be committed with required sections left as unfilled `<placeholder>`
text, or with a section pointing at a missing/failed artifact recorded as the
literal token `GAP`, and no gate fails. The template states in prose that "a
section that points at an UNFILLED or FAIL artifact ... is a GAP -> the pack
cannot reach complete", but that discipline is enforced only by prose and human
review, not by the static checker.

This feature adds ONE static rule -- the idea-bank labels it `PP1` -- that turns
that prose contract into a structural check. The rule scans every committed
`mappings/<table>/handoff/bi-handoff-pack.md`, confirms the required sections are
present, and confirms each required section is FILLED (does not remain a
`<placeholder>` and is not recorded as an unresolved `GAP`). An incomplete pack
produces a Finding so the gap is caught by the gate rather than discovered after
a consumer receives a half-filled pack.

The rule is the completeness SIBLING of the existing `G6` parameter-hygiene rule.
`G6` (`src/retail/rules/g6.py`) treats an angle-bracket `<...>` token as the safe
PLACEHOLDER form and flags committed parameter values that are NOT placeholders
(a real leaked value). `PP1` reuses the SAME `<...>` placeholder-detection idea
but with INVERTED polarity: in a handoff pack a remaining `<placeholder>` (or a
`GAP` token) marks an UNFILLED required section, which is exactly what `PP1` must
flag. Like `G6` and the other file-scanning rules, `PP1` reads committed text
with the stdlib only, parses-not-executes, opens no database/network/Power BI
connection, and skips committed test fixtures via the shared `is_test_path()`
exemption.

`PP1` keys ONLY off the GENERIC template's structural markers -- the named
required sections and the `<placeholder>`/`GAP` convention. It carries no
specific table's column list, no business KPI, and no PII rules. It works
identically for any table that follows the template.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An incomplete publish pack fails the gate (Priority: P1)

A maintainer commits a `mappings/<table>/handoff/bi-handoff-pack.md` that still
has a required section left as an unfilled `<placeholder>` (or recorded as a
`GAP`). When the static checker runs, `PP1` flags that pack and names the
unfilled section, so the incomplete handoff is caught in CI rather than shipped
to a BI consumer.

**Why this priority**: This is the entire value of the feature -- converting the
template's prose "cannot reach complete" contract into an enforced gate. Without
it, nothing here delivers value.

**Independent Test**: Feed the rule a synthetic generic handoff-pack source that
contains a required section whose value remains a `<placeholder>` (or `GAP`);
assert exactly one Finding naming that pack and section. Feed it a fully-filled
generic pack; assert no Finding.

**Acceptance Scenarios**:

1. **Given** a committed handoff pack with a required section whose value is still
   an unfilled `<placeholder>`, **When** the static checker runs, **Then** `PP1`
   emits a Finding naming the pack and the unfilled section, and the gate exit
   reflects the finding's severity.
2. **Given** a committed handoff pack with a required section recorded as the
   literal token `GAP`, **When** the static checker runs, **Then** `PP1` emits a
   Finding naming the pack and the unresolved-GAP section.
3. **Given** a committed handoff pack in which every required section is present
   and filled (no remaining `<placeholder>`, no `GAP` in a required section),
   **When** the static checker runs, **Then** `PP1` emits NO Finding for that
   pack.

### User Story 2 - A pack missing a required section is flagged (Priority: P1)

A reviewer needs confidence that a committed pack actually contains every
required section, not just that the sections it does contain are filled. If a
required section heading is absent entirely, `PP1` flags the pack as incomplete.

**Why this priority**: A missing section is the most severe form of incompleteness
-- the consumer never even sees the contract. Presence is a precondition of
"filled".

**Independent Test**: Feed the rule a generic pack source that omits one required
section heading; assert a Finding naming the missing section. Feed it a pack with
all required sections present; assert no missing-section Finding.

**Acceptance Scenarios**:

1. **Given** a committed handoff pack that omits a required section heading,
   **When** the static checker runs, **Then** `PP1` emits a Finding naming the
   missing required section.
2. **Given** a committed handoff pack that contains every required section
   heading, **When** the static checker runs, **Then** `PP1` emits no
   missing-section Finding.

### User Story 3 - The rule is genuinely wired, not just listed (Priority: P1)

A reviewer needs confidence that adding the rule actually closed the gap rather
than merely registering an id. The rule appears in the live registry, in the
regenerated `docs/rules/rules-manifest.json`, and in the wiring test's expected
id set -- AND a test exercises the rule firing against a known-bad fixture so it
cannot silently no-op.

**Why this priority**: The repo's memory records a prior "wiring latent gap" where
a registered rule was listed but never validated to fire. This story prevents
repeating that gap. A registered-but-inert rule delivers zero protection.

**Independent Test**: Run the rule-registry snapshot test and the wiring test;
assert the new id is present in both the live registry and the regenerated
manifest, AND that a test directly invokes the rule against a known-bad fixture
and observes a Finding.

**Acceptance Scenarios**:

1. **Given** the rule is registered, **When** the rule-registry snapshot test
   runs, **Then** the live registry id set equals the expected id set and the
   regenerated manifest contains the new id.
2. **Given** a synthetic known-bad pack source, **When** the rule is invoked
   directly in a test, **Then** it returns a non-empty Finding set (proving the
   rule fires, not just that its id is listed).

### User Story 4 - The publish-approval slot is checked present, never granted (Priority: P1)

An auditor confirms that `PP1` verifies the publish-approval section EXISTS and is
non-placeholder, but NEVER inspects who signed, whether the sign-off is
legitimate, or populates the approval itself. The human sign-off remains a human
seam.

**Why this priority**: This is the single most-scrutinized eligibility boundary
for the rule. A rule that validated or self-granted the approval would breach the
agent-stops-at-judgment-calls discipline that the whole readiness system rests on.

**Independent Test**: Inspect the rule and its fixtures; assert the publish-approval
check asserts only presence-and-non-placeholder of the approval slot, and that no
code path reads the approving owner, the date, or the legitimacy of the sign-off,
and no code path writes any approval.

**Acceptance Scenarios**:

1. **Given** a handoff pack whose publish-approval section is still an unfilled
   `<placeholder>` (or `GAP`), **When** the static checker runs, **Then** `PP1`
   flags the approval slot as an unfilled required section.
2. **Given** a handoff pack whose publish-approval section is filled (non-placeholder),
   **When** the static checker runs, **Then** `PP1` emits no approval-slot Finding
   and does NOT read or validate the identity, date, or legitimacy of the recorded
   sign-off.

### Edge Cases

- A repository with ZERO committed handoff packs: `PP1` scans only the
  `mappings/<table>/handoff/bi-handoff-pack.md` files that exist, so it produces no
  Finding when none exist (silent pass), consistent with `G6` scanning only files
  present in the tree. (The require-at-least-one alternative is NOT adopted -- see
  Assumptions.)
- A handoff pack that is the GENERIC template itself
  (`templates/handoff/bi-handoff-pack.md`): the template is deliberately full of
  `<placeholder>` tokens and is NOT a per-table instance, so `PP1` MUST NOT scan
  it. The rule scans only instance paths under `mappings/<table>/handoff/`.
- A committed test fixture pack under `tests/`: skipped via the shared
  `is_test_path()` exemption (fixtures deliberately carry unfilled sections to
  exercise the rule).
- A handoff pack whose `GAP` token appears in narrative prose (e.g. the word "gap"
  inside a caveat sentence) rather than as a section-resolution marker: the rule
  keys the GAP signal off the structured resolution position (the required-section
  index "Resolved?" cell), not a free-text substring match, so prose mentions never
  trip it (advisor-resolved 2026-06-30; FR-003).
- The four MANDATORY caveats (PII exclusion / returns handling / known gaps /
  out-of-scope): in this first step `PP1` checks the caveats section is
  present-and-resolved at index granularity only; per-caveat individual enforcement
  is a later, separate increment (advisor-resolved 2026-06-30; FR-007). Confirmed at
  ratify.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a single registered static rule that scans
  every committed per-table handoff pack at
  `mappings/<table>/handoff/bi-handoff-pack.md` and emits a Finding for each
  required section that is absent, or present but unfilled.
- **FR-002**: The rule MUST detect an unfilled section using the same
  angle-bracket `<placeholder>` convention that `G6` already uses, with inverted
  polarity: a required-section value that still matches the `<...>` placeholder
  form is UNFILLED and is flagged (whereas `G6` treats the placeholder form as the
  safe state). The rule MUST reuse the existing placeholder-detection mechanism
  rather than authoring a second placeholder parser (Principle II -- Depend, Never
  Fork).
- **FR-003**: The rule MUST also treat a required section recorded as the literal
  resolution token `GAP` (the template's "points at an UNFILLED or FAIL artifact"
  marker) as incomplete and flag it. The `<placeholder>`/`GAP` signal MUST be read
  from the STRUCTURED resolution position of the required-section index (its
  "Resolved?" cell), NOT by a free-text substring scan of narrative prose, so the
  word "gap" appearing in a caveat sentence never trips the rule. (Advisor-resolved
  2026-06-30; confirmed at ratify.)
- **FR-004**: The rule MUST parse committed text only (stdlib) and MUST NEVER
  open a database, network, or Power BI connection, NEVER execute the pack, and
  introduce no third-party dependency -- it joins the static `retail check` rule
  set, not the live `retail validate` surface (Principle VIII).
- **FR-005**: The rule MUST scan ONLY per-table instance packs under
  `mappings/<table>/handoff/`; it MUST NOT scan the generic template at
  `templates/handoff/bi-handoff-pack.md` (which is intentionally full of
  placeholders), and MUST skip committed test fixtures via the shared
  `is_test_path()` exemption.
- **FR-006**: The rule MUST verify the publish-approval section is present and
  non-placeholder ONLY. It MUST NOT read or validate WHO signed, the sign-off
  date, or the legitimacy of the approval, and MUST NEVER populate, grant, or
  self-validate any approval (Principle V -- the human sign-off is a human seam).
- **FR-007**: The authoritative set of required sections the rule enforces MUST be
  defined explicitly in one named place, derived from the generic template's
  structure, and expressed generically (no specific table, column, KPI, or PII
  rule). The recommended set (advisor-resolved 2026-06-30; confirmed at ratify) is
  the template's six required-section-index rows a-f -- metric contracts, readiness
  scorecard, reconciliation, known caveats, data dictionary, publish approval --
  checked at index granularity (the four MANDATORY caveats are NOT decomposed
  individually in this first step; that is a separate later increment).
- **FR-008**: When a scanned pack cannot be read, the rule MUST emit a Finding
  (fail loud) rather than crash the gate or silently pass.
- **FR-009**: On a repository with no committed per-table handoff packs, the rule
  MUST produce no Finding (silent pass -- it checks only packs that exist).
- **FR-010**: Adding the rule MUST update the wiring test's expected rule-id set
  AND regenerate `docs/rules/rules-manifest.json` in the same change, so the
  rule-registry snapshot stays consistent. The change MUST NOT hard-code any
  numeric baseline rule count (the snapshot keys off the length of the expected
  id set, not a literal number).
- **FR-011**: The wiring/validation coverage MUST exercise the rule firing against
  a known-bad fixture, not merely assert that its id is registered (close the
  prior wiring-latent-gap).
- **FR-012**: Each Finding MUST be a new immutable value object identifying the
  rule id, the severity, the offending pack path with the unfilled/missing section
  (locator), and a message; the rule MUST NOT mutate shared state.
- **FR-013**: The rule MUST emit a single uniform severity for every violation.
  The recommended posture (advisor-resolved 2026-06-30; confirmed at ratify) is
  ERROR -- proven-incomplete, fail-closed, matching `G6`/`B1`/`B3` and the
  template's "a GAP -> the pack cannot reach complete" language. The exit-code
  mapping for ERROR is the existing gate behavior; this feature adds no new
  severity tier.
- **FR-014**: The rule MUST add NO new readiness stage and MUST move NO table's
  readiness stage to pass; it only checks the committed pack's structural
  completeness over the existing Publish Ready stage (it never self-grants a
  readiness pass).

### Key Entities *(include if feature involves data)*

- **Handoff pack instance**: a committed `mappings/<table>/handoff/bi-handoff-pack.md`
  file that the rule scans. The generic template and committed test fixtures are
  explicitly out of the scanned set.
- **Required-section set**: the explicit, named collection of sections the rule
  requires to be present-and-filled, derived from the generic template (candidate:
  metric contracts, readiness scorecard, reconciliation, known caveats, data
  dictionary, publish approval). Final membership is a ratify decision (see
  Clarifications).
- **Incompleteness markers**: the angle-bracket `<placeholder>` form (reused from
  `G6`) and the literal `GAP` resolution token -- the two ways the template marks a
  section as unfilled.
- **Rule registration record**: the rule's registry id + title, mirrored into the
  wiring test's expected id set and the generated rules manifest.
- **Finding**: an immutable result object (rule id, severity, message, locator)
  emitted per violation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A committed per-table handoff pack with any required section left as
  an unfilled `<placeholder>` or recorded as `GAP` causes the static checker to
  report at least one Finding for that pack (the incompleteness is caught).
- **SC-002**: A fully-filled per-table handoff pack (every required section present
  and non-placeholder, no unresolved `GAP`) produces zero Findings (no false
  positives on a complete pack).
- **SC-003**: The generic template at `templates/handoff/bi-handoff-pack.md` and
  committed test-fixture packs under `tests/` produce zero Findings (the rule does
  not flag the placeholder-bearing template or fixtures).
- **SC-004**: The live registry id set, the regenerated manifest, and the wiring
  test's expected id set agree exactly after the rule is added (the snapshot test
  passes), with no hard-coded numeric baseline.
- **SC-005**: At least one test invokes the rule directly and observes it fire on a
  known-bad fixture (the rule is exercised, not merely listed).
- **SC-006**: The rule, its required-section set, and every fixture contain no
  domain-specific schema artifact (no specific table, column, KPI, or PII rule);
  fixtures are generic/synthetic packs, never the worked-example answers inlined.
- **SC-007**: Running the static checker with the rule added introduces no new
  third-party dependency and performs no network or database access.
- **SC-008**: The publish-approval check observes only presence-and-non-placeholder;
  no code path reads the approving owner/date/legitimacy and no code path writes an
  approval.

## Clarifications

All questions below are RESOLVED as recorded rulings made at the ratify gate by the
advisor acting under an explicit, recorded per-spec delegated override granted by
the repo owner (info@rahmaqanater.org) for the 2026-06-30 unattended session (see the
Ratification note in the front-matter). All are easily reversible.

### Resolved at the ratify gate (recorded rulings)

- **Readiness stage + roadmap provenance** (RESOLVED -> advances NO readiness stage;
  gets a roadmap sub-row). `PP1` is a completeness *gate* that supports Stage 7
  (Publish Ready) by checking the committed handoff pack is structurally complete; it
  does NOT itself advance or grant Publish Ready (Principle V forbids self-granting a
  stage). It therefore advances no readiness stage on its own, exactly like its A1 /
  A3 / B1 / B3 governance-rule siblings, and receives a roadmap sub-row under the
  idea-bank sequence (as A3 did at roadmap.md:224) recording spec/PR provenance --
  not a top-level F-number.
- **Principle V publish-safety boundary** (RESOLVED -> CONFIRMED: structural presence
  only). `PP1`'s exact contract is "the publish-approval section/index row is PRESENT
  and its structured Resolved? cell is non-placeholder/non-GAP" ONLY. It NEVER
  inspects, validates, populates, or grants WHO signed or WHETHER the sign-off is
  legitimate -- it verifies the slot exists and is filled, nothing about the slot's
  contents' authority. This is the load-bearing eligibility boundary the idea-bank
  panel required of every approval-adjacent rule; it is hereby confirmed and binding.

### Session 2026-06-30 (advisor-resolved, reversible)

- Q: On a repository with no committed handoff packs, should `PP1` silent-pass
  (no packs to check) or require at least one pack to exist? -> A: Silent pass.
  Reasoning: this mirrors `G6`, which scans only the parameter files that exist and
  reports nothing when none are present; a "require at least one" rule would couple
  a generic governance check to a workflow-progress assumption (that some table has
  reached Publish Ready), which is not `PP1`'s job. Reversible: easy.
- Q: Should `PP1` scan the generic template
  `templates/handoff/bi-handoff-pack.md` itself? -> A: No. Reasoning: the template
  is deliberately full of `<placeholder>` tokens by design; scanning it would
  guarantee a false-positive flood. `PP1` scans only per-table instances under
  `mappings/<table>/handoff/`. Reversible: easy.
- Q: Should the Publish Approval Receipt (spec 041) be a hard dependency of `PP1`?
  -> A: No -- receipt-presence is at most an OPTIONAL check, not a hard dependency.
  Reasoning: the value realist sequenced `PP1` behind the receipt so it has a
  concrete slot to verify, but `PP1`'s core contract (required sections present and
  filled, including the approval slot already defined in the template today) does
  not require the receipt to ship first. Treat receipt-presence as out of first-step
  scope unless the human rules otherwise. Reversible: easy.
- Q: What is the authoritative required-section set, where is each section's
  filled/unfilled state located, and are the four MANDATORY caveats checked
  individually? -> A (advisor RECOMMENDATION, reversible at ratify): enforce the
  template's six structured required-section-INDEX rows a-f (metric contracts,
  readiness scorecard, reconciliation, known caveats, data dictionary, publish
  approval). For each of the six, the rule checks (i) the section/index row is
  PRESENT and (ii) its structured "Resolved?" cell is FILLED -- i.e. not a remaining
  `<placeholder>` and not the literal `GAP` token in that cell. The GAP/placeholder
  signal is located in the STRUCTURED "Resolved?" position of the required-section
  index, NEVER by a free-text substring scan of narrative prose (this resolves the
  GAP-location edge case and the prose-"gap" false-positive risk). The four
  MANDATORY caveats are NOT decomposed and checked individually in this first step --
  `PP1` checks the caveats section is present-and-resolved at the index granularity
  only; per-caveat enforcement is a larger, separate increment (YAGNI). Reasoning:
  this is the minimal generic set derived directly from the template's own index
  table, mirrors B3's single explicit closed set, and avoids baking any specific
  table's caveat wording into a generic rule (Principle VII). FR-003/FR-007 and the
  GAP-location edge case are resolved to this. Final membership is CONFIRMED by the
  human at the ratify gate (mirror B3's closed-set-at-ratify pattern). Reversible: easy.
- Q: Severity posture -- ERROR or WARNING for an incomplete publish pack? -> A
  (advisor RECOMMENDATION, reversible at ratify): ERROR, applied uniformly to every
  violation. Reasoning: the siblings `G6`, `B1`, and `B3` all emit ERROR for a
  proven structural breach, and the template states plainly that a section pointing
  at an unfilled/FAIL artifact "is a GAP -> the pack cannot reach complete" -- an
  incomplete committed pack is a proven-incomplete state, not a suspect pattern with
  a legitimate override clause. Principle VIII's "static rules WARN" applies to
  suspect patterns carrying an ADR override-when clause; an unfilled required section
  has no legitimate override. FR-013 is resolved to ERROR. Final posture CONFIRMED by
  the human at the ratify gate. Reversible: easy (a single severity constant).

## Assumptions

- The existing `G6` placeholder-detection mechanism (`<...>` angle-bracket token =
  placeholder) is the correct, complete definition of an unfilled marker; this
  feature reuses that idea rather than re-deriving a placeholder parser.
- The generic template `templates/handoff/bi-handoff-pack.md` is the authoritative
  source of the required-section structure; the rule keys off the template's
  structure, never off any specific table's columns or caveats.
- `PP1` checks only packs that exist (silent pass on an empty tree); it does not
  assert that any table has reached Publish Ready.
- The rule-registry snapshot test and wiring test are the authoritative consistency
  gate for adding a rule; satisfying them (id set + regenerated manifest + a firing
  test) is sufficient to consider the rule wired.
- No deferred capability is assumed: this is a pure static-text rule and does not
  depend on any Power BI execution adapter (F016), live database, spec-only runtime,
  or the Publish Approval Receipt (spec 041) having shipped.
- The rule is generic governance infrastructure; it carries no business-domain
  schema knowledge (Principle VII). Test fixtures are generic/synthetic packs; the
  worked-example (c086) answers are never inlined.
