# Feature Specification: Severity-Posture Regression Lock (golden severity table)

**Feature Branch**: `046-severity-posture-lock`

**Created**: 2026-06-29

**Status**: Ratified (Ahmed Shaaban, 2026-06-29)

**Input**: User description: "Severity-Posture Regression Lock (golden severity table)"

## Overview

The governance contract for this analytics service rests on a single gate floor
(Principle I): a `retail check` run exits non-zero if and only if at least one
finding carries the ERROR severity class; WARNING and INFO findings are reported
but never fail the build. That floor is only as trustworthy as the severity each
rule actually emits. Today nothing guards severity: a rule whose finding is
silently changed from ERROR to WARNING -- by accident or otherwise -- flips a
previously failing build to passing, and no existing test notices.

Two sibling tests already guard adjacent properties of the rule set but stop
short of severity:

- the wiring/expected-id test guards rule EXISTENCE and SHAPE (the set of rule
  ids), never the severity any rule emits;
- the rule-registry snapshot manifest (the most recently shipped sibling) records
  each rule's id and title ONLY, and explicitly NOT its severity.

This feature adds the missing guard: a committed golden record of the severity
posture each rule emits, plus a snapshot test that fails closed when the
observed posture drifts from the committed record. It is test-only and adds no
new gating rule -- exactly the pattern of the manifest-snapshot sibling.

A load-bearing fact constrains the design: severity is NOT a property of a
registered rule. The registry entry for a rule carries an id and a title and no
severity field. Severity is decided per-finding, inside each rule, and a single
rule id can emit findings in more than one severity class depending on which
violation branch fires (one shipped SQL rule emits both ERROR and WARNING; some
rule families likewise mix classes). Therefore the golden record CANNOT be read
from the registry as a flat id-to-severity map -- it must be OBSERVED by forcing
each rule to fire over planted, synthetic, minimal input and recording the
severity class(es) it emits.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Catch a silent severity downgrade (Priority: P1)

A maintainer edits a rule and, deliberately or by mistake, changes a finding it
emits from the ERROR class to the WARNING class. On the next test run, the
severity-posture lock observes that the rule's emitted posture no longer matches
the committed golden record and FAILS, naming the rule and the before/after
posture, with a one-line instruction on how to regenerate the record if the
change was intentional.

**Why this priority**: This is the entire value of the feature -- it is the
direct protection of the Principle-I gate floor. Without it, an ERROR-to-WARNING
downgrade is invisible and silently lowers the gate. P1 because the feature has
no reason to exist without this behavior.

**Independent Test**: Force a known rule to emit a different severity class than
the committed record (for example via a temporary local edit or a stubbed
posture) and confirm the lock test fails with a message that names the rule and
the posture delta. Revert and confirm the test passes.

**Acceptance Scenarios**:

1. **Given** the committed golden severity record matches what every rule
   currently emits, **When** the lock test runs, **Then** it passes.
2. **Given** a rule is changed so a finding it emits moves from ERROR to WARNING
   (or any class change) without updating the golden record, **When** the lock
   test runs, **Then** it fails and the failure message names the rule and shows
   the recorded-versus-observed posture.
3. **Given** the same severity change is an INTENTIONAL, reviewed decision,
   **When** the maintainer regenerates the golden record in the same change,
   **Then** the lock test passes and the diff of the golden record is a small,
   reviewable, human-readable change.

---

### User Story 2 - Regenerate the golden record deterministically (Priority: P2)

A maintainer who has intentionally changed a rule's severity regenerates the
committed golden record with a single documented command, and the regenerated
record is byte-for-byte stable across repeated runs and across operating systems
(no ordering churn, no line-ending churn, no encoding churn).

**Why this priority**: The fail-closed lock is only usable if the intended
update path is trivial and deterministic, mirroring the existing manifest
discipline (edit the rule and the golden record in the same reviewed change).
P2 because the lock can ship and catch drift before the regeneration ergonomics
are perfected, but the feature is not complete without a stable update path.

**Independent Test**: Run the regeneration twice and confirm the output is
byte-identical; inspect the diff after a deliberate single-rule severity change
and confirm it is minimal and localized to that rule.

**Acceptance Scenarios**:

1. **Given** the live rule set, **When** the golden record is regenerated twice,
   **Then** the two outputs are byte-identical (deterministic ordering, stable
   key order, UTF-8 without BOM, `\n` line endings, single trailing newline).
2. **Given** a deliberate severity change to exactly one rule, **When** the
   record is regenerated, **Then** the diff is confined to that one rule's entry.

---

### User Story 3 - Cover newly added rules without silent gaps (Priority: P3)

When a maintainer adds a new registered rule, the lock surfaces the new rule's
severity posture as a record entry that must be committed, so a new gating rule
cannot enter the codebase with an unrecorded (and therefore unguarded) severity.

**Why this priority**: Keeps the lock honest as the rule set grows, mirroring how
the manifest snapshot fails closed when a rule is added without regenerating.
P3 because it is a consequence of the same mechanism rather than a separate
build; if P1 holds, this largely follows.

**Independent Test**: Add a throwaway registered rule locally, run the lock
without regenerating, confirm it fails naming the unrecorded rule; regenerate,
confirm it passes; remove the throwaway rule and regenerate.

**Acceptance Scenarios**:

1. **Given** a new registered rule whose posture is not in the golden record,
   **When** the lock test runs, **Then** it fails and names the missing rule.
2. **Given** a registered rule that has been removed but still appears in the
   golden record, **When** the lock test runs, **Then** it fails and names the
   stale entry.

---

### Edge Cases

- **A single rule id emits more than one severity class.** At least one shipped
  rule emits both ERROR and WARNING from different violation branches (and at
  least one other registered rule emits an INFO empty-case alongside an ERROR
  branch); some rule families mix classes. The golden record's grain MUST
  represent this without collapsing it to one class. The grain (key/uniqueness)
  is resolved to `rule_id -> sorted SET of classes` (option (a)) -- see
  Clarifications (Advisor-resolved).
- **A rule emits no finding over the planted input.** The observation harness
  must force the rule to fire; if a rule cannot be made to fire over a minimal
  synthetic fixture, the record must represent that explicitly rather than
  silently recording "no severity" (which would mask a future downgrade on that
  rule). See Clarifications.
- **A non-registry severity surface (the L3 governance posture) is also
  gate-bearing.** A separate, non-registered code surface maps a drift outcome
  to ERROR and an escalate outcome to WARNING. It is equally load-bearing for the
  gate but is NOT reachable by iterating the rule registry. It IS in scope: it is
  covered as a named second section of the record (key `L3:verdict_to_finding`),
  observed by driving the verdict-to-finding mapping in-process -- a pure function
  over a verdict value, so no live query/model/agent is needed (Principle VIII
  holds). See Clarifications (Advisor-resolved).
- **Test-fixture exemption interaction.** Rules that scan files skip paths under
  the test tree by design. The observation harness must plant fixtures in a way
  that actually triggers each rule (not in an exempt location that suppresses the
  finding), while keeping fixtures synthetic and generic.
- **Ordering / platform churn.** The record must be stable under the repo's
  cross-platform line-ending policy so a Windows checkout does not flake the
  comparison.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST maintain a committed golden record of the severity
  posture emitted by the registered rule set, stored as a generic, human-readable
  artifact alongside the existing committed golden rule artifacts.
- **FR-002**: The system MUST OBSERVE each registered rule's severity posture by
  forcing the rule to fire over planted, synthetic, minimal input -- NOT by
  reading severity from the registry (which carries no severity field).
- **FR-003**: A snapshot test MUST compare the live observed posture against the
  committed golden record and FAIL CLOSED on any drift (a class change, a missing
  rule, or a stale rule), naming the affected rule and the recorded-versus-observed
  delta.
- **FR-004**: The failure message MUST include a one-line instruction for
  regenerating the golden record, so an intentional change is a small reviewed
  diff committed in the same change as the rule edit.
- **FR-005**: The golden record MUST be regenerable by a single documented action,
  and regeneration MUST be deterministic and byte-stable across repeated runs and
  across operating systems (stable ordering, stable key order, UTF-8 without BOM,
  `\n` line endings, single trailing newline).
- **FR-006**: The golden record MUST key ONLY on generic rule ids and severity
  classes. It MUST NOT contain any example-domain-specific table, column, or
  value (Principle VII -- the example domain is an example, not the schema). The
  planted fixtures used to force rules to fire MUST likewise be synthetic/generic,
  and -- because `is_test_path` exempts them from the live rules -- the lock test
  MUST itself assert the fixture FILES contain no example-domain identifier (see
  SC-007).
- **FR-007**: This feature MUST add NO new registered (gating) rule and NO new
  expected-rule-id entry. It is a test-only golden assertion plus a generator,
  exactly like the manifest-snapshot sibling.
- **FR-008**: The observation harness MUST use only synthetic/minimal planted
  fixtures and MUST perform no live query, no model execution, no agent run, and
  no live database access (Principle VIII -- static-first; live deferred).
- **FR-009**: The golden record's GRAIN (its key and uniqueness) MUST be
  `rule_id -> the SORTED SET of severity classes that rule emits when forced to
  fire` (option (a), resolved by the planning advisor -- see Clarifications). The
  record MUST NOT collapse a multi-class rule to a single class: a rule that emits
  more than one class (e.g. the shipped SQL guard-form rule, which emits both
  ERROR and WARNING from different violation branches) MUST record the full sorted
  set `[ERROR, WARNING]`. This grain catches a class DISAPPEARING from a rule's set
  (an ERROR dropping out of `{ERROR, WARNING}` so the set becomes `{WARNING}`) and
  a class being ADDED. RESIDUAL TRADEOFF (stated honestly): this grain CANNOT catch
  a per-branch downgrade that leaves the SET unchanged -- but for the lock's core
  protection (an ERROR vanishing) the set necessarily changes, because dropping the
  last ERROR-emitting branch removes ERROR from the set.
- **FR-010**: The lock's COVERAGE boundary covers (1) the REGISTERED rules
  (registry-reachable via `all_rules()`) AND (2) the non-registered L3 governance
  severity surface (the verdict-to-finding mapping: drift -> ERROR / escalate ->
  WARNING), recorded as a SECOND, explicitly-named section of the same golden
  record (resolved by the planning advisor -- see Clarifications). The L3 surface
  is in scope because it emits ERROR and is therefore gate-bearing: a silent L3
  ERROR-to-WARNING downgrade is the same Principle-I bypass the lock exists to
  stop. L3 is modelled as a distinct named pseudo-rule entry (key `L3:verdict_to_finding`)
  whose severity set is OBSERVED by driving the verdict-to-finding mapping with a
  `drift` verdict and an `escalate` verdict in-process. This adds NO `@register`
  and NO new expected-rule-id (ADR-0007 stays intact): the registry-reachable rule
  count is unchanged; the L3 entry is recorded ALONGSIDE the registered rules, not
  AS one.
- **FR-011**: When a rule cannot be forced to emit a finding over a minimal
  synthetic fixture, the record MUST represent that state with an EXPLICIT
  no-finding marker entry (per clarify Q3) rather than omitting the rule, so the
  lock still fails closed if that rule later begins or ceases to emit a finding.
- **FR-012**: The committed golden record MUST be compared by parsing both the
  committed artifact and the freshly observed posture into data and comparing the
  data structures (not raw text), so a cross-platform line-ending round-trip
  cannot flake the comparison (per clarify Q2, mirroring the manifest sibling).

### Key Entities *(include if feature involves data)*

- **Severity class**: One of the three ordered build-impact classes -- the
  build-failing class (ERROR), the reported-but-non-failing class (WARNING), and
  the informational class (INFO). Only the ERROR class fails the build; this
  ordering is the posture the lock protects.
- **Registered rule**: A rule reachable by iterating the rule registry; carries
  an id and a title but NO severity field. Its severity posture exists only in
  the findings it emits at run time.
- **Severity posture (per rule)**: The SORTED SET of severity classes a rule
  emits when forced to fire -- the thing the golden record captures. The grain is
  `rule_id -> sorted set of classes` (option (a), advisor-resolved -- see
  Clarifications); a multi-class rule records the whole set, never one class.
- **Golden severity record**: The committed, generic, deterministic artifact
  recording the observed posture; the fail-closed comparison target. A sibling
  to the existing committed golden rule artifacts. It carries TWO explicitly-named
  sections: the registered-rule postures (keyed by rule id) and the L3
  governance-surface posture (keyed `L3:verdict_to_finding`).
- **L3 governance severity surface**: A separate, non-registered code surface
  mapping a drift outcome to the ERROR class and an escalate outcome to the
  WARNING class. Gate-bearing but not registry-reachable. It IS in scope
  (advisor-resolved -- see Clarifications), recorded as the record's named second
  section with severity set `[ERROR, WARNING]`, observed by driving the
  verdict-to-finding mapping over both verdict statuses. It is NOT registered
  (`@register`) and adds no expected-rule-id (ADR-0007).
- **Planted fixture (genericity)**: A synthetic, minimal input planted on a
  NON-exempt path to force a file-scanning rule to fire. Because the test-fixture
  exemption (`is_test_path`) suppresses the live rules under the test tree, the
  fixture FILES themselves are not scanned by the rules -- so the lock test MUST
  itself assert the planted fixtures contain no example-domain identifier (see
  SC-007).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A silent change of any single rule's finding from the ERROR class
  to a non-ERROR class, without updating the golden record, is caught by the lock
  test 100% of the time (the test fails).
- **SC-002**: Regenerating the golden record twice in succession produces
  byte-identical output (0 byte difference).
- **SC-003**: An intentional, reviewed severity change is expressible as a
  golden-record diff confined to the affected rule's entry (no unrelated churn).
- **SC-004**: The feature adds 0 new registered (gating) rules and 0 new
  expected-rule-id entries (the registered rule count is unchanged).
- **SC-005**: The golden record contains 0 example-domain-specific identifiers
  (no example table, column, or value names) -- only generic rule ids and
  severity classes.
- **SC-006**: Every registered rule has exactly one corresponding entry (or
  explicit no-finding marker) in the golden record, AND the L3 governance surface
  has exactly one named entry (`L3:verdict_to_finding`) in the record's second
  section -- 0 unrecorded registered rules and 0 unrecorded gate-bearing surfaces.
- **SC-007**: The planted fixture files under the test fixtures tree contain 0
  example-domain identifiers (no example table, column, or value names) -- asserted
  by the lock test scanning the fixture FILES themselves, not only the generated
  record. This closes the residual leak that `is_test_path` exempts fixtures from
  the live rules, so a fixture file is never scanned for genericity unless the
  lock test does it (plan-review LOW, axis 3).

## Assumptions

- The committed golden record lives alongside the existing committed golden rule
  artifacts (the same directory that holds the rule manifest), as a natural
  sibling. Exact filename/format is an implementation detail to be set in the
  plan, constrained by FR-005/FR-006.
- The intended update protocol mirrors the existing manifest discipline and is
  CONFIRMED (advisor-resolved -- see Clarifications): an intentional severity
  change edits the rule AND regenerates the golden record in the SAME PR/change
  (mirroring the EXPECTED_RULE_IDS + rules-manifest.json discipline), so an
  UNINTENTIONAL downgrade fails CI while an INTENTIONAL one is a small reviewed
  two-part diff. The failure message names the affected rule, the recorded-vs-
  observed severity-set delta, and the single regeneration command.
- The observation harness reuses the existing clear-and-reload registry pattern
  already proven by the manifest-snapshot sibling, so the test is order-proof and
  does not depend on global registry state left by sibling tests.
- This is an UNMAPPED test-hardening item BY DESIGN (advisor-resolved -- see
  Clarifications): no roadmap feature row maps to it, exactly parallel to the
  manifest-snapshot sibling (spec 043), which also has no roadmap F-row. The
  backlog "value/feasibility" score is NOT a roadmap feature number. It advances
  no readiness stage and is NOT gated behind any open idea -- it is a clean,
  shippable hardening item. No F-number is invented for it.
- The example domain remains an example only; no example-domain schema is
  promoted into a generic artifact.
- No deferred capability is assumed (no Power BI execution adapter, no spec-only
  runtimes); the lock is a pure static/test-only assertion over rule outputs.

## Clarifications

<!--
  Principle-V carve-outs: load-bearing human rulings the agent MUST NOT answer.
  Recorded here and surfaced to the operator. Stage 3 (clarify) harvests these
  and leaves them for human resolution; it does not invent answers.
-->

### Session 2026-06-29

> Operator: this session was run by the planning advisor. Fill the real date.
> The advisor RESOLVED the non-judgment ambiguities below (recording reasoning
> and reversibility). The four Principle-V judgment calls were SUBSEQUENTLY
> resolved by the planning advisor under EXPLICIT human authorization (see the
> "Advisor-resolved Principle-V calls" subsection). The advisor did NOT and MUST
> NOT set Status to Ratified or fill the session date -- those remain for the
> human (the ratify gate fails closed on an AI-authored Ratified line).

#### Advisor-resolved (non-judgment defaults)

- **Q1 -- Artifact format and location.** Recommended: a committed JSON file in
  the same directory as the existing rule manifest (the established committed
  golden-artifact directory), serialized with the SAME deterministic discipline
  the manifest uses (sorted by id, stable key order, UTF-8 without BOM, `\n`
  endings, single trailing newline). Reasoning: maximal symmetry with the shipped
  sibling minimizes review surface and reuses a proven cross-platform-stable
  format; RC default favors mirroring an existing accepted pattern over inventing
  a new one. Reversible: easy (format is internal to the test + generator).
  Integrated into FR-001/FR-005 and Assumptions.

- **Q2 -- Comparison method (line-ending robustness).** Recommended: compare by
  parsing the committed artifact and the freshly observed posture into data and
  comparing the data structures (not raw text), so a Windows CRLF round-trip
  under the repo autocrlf policy cannot flake the test -- exactly as the manifest
  snapshot sibling does. Reasoning: the sibling already proved this is the stable
  approach on this repo/OS. Reversible: easy. Integrated into FR-003/FR-005.

- **Q3 -- Representing a rule that cannot be forced to fire.** Recommended: the
  record carries an EXPLICIT no-finding marker entry for such a rule rather than
  omitting it, so the lock still fails closed if that rule later starts emitting
  (or stops emitting) a finding. Reasoning: silent omission would create exactly
  the blind spot the lock exists to remove; an explicit marker preserves
  fail-closed coverage. Reversible: easy. Integrated into FR-011/SC-006.

#### Principle-V judgment calls (REFUSED -- human resolution required)

None outstanding. The four Principle-V judgment calls originally recorded here
(grain / scope / readiness mapping / update protocol) have been resolved by the
planning advisor under explicit human authorization; see the next subsection.
This subsection is retained (empty) so the carve-out history is auditable.

#### Advisor-resolved Principle-V calls (human-authorized)

> These four Principle-V judgment calls were resolved by the planning advisor
> under EXPLICIT human authorization on 2026-06-29. Each records the
> {decision, option chosen, rationale, reversibility}. This authorization does
> NOT extend to ratification: Status stays Draft and the date stays pending --
> only a human commit may set the Ratified line (the ratify gate's git-blame
> provenance check fails closed on an AI-authored Ratified line).

- **GRAIN / UNIQUENESS (FR-009)** -- *option (a) chosen*.
  - **Decision**: the golden record keys `rule_id -> the SORTED SET of severity
    classes that rule emits when forced to fire`.
  - **Option chosen**: (a) `rule_id -> SET of severity classes`, over (b)
    `(rule_id, violation-branch/message) -> severity` and (c)
    `(rule_id, planted-fixture-case) -> severity`.
  - **Rationale**: (a) faithfully models the shipped multi-class SQL guard-form
    rule's `{ERROR, WARNING}` (verified live: WITHIN A SINGLE file scan it emits
    ERROR on a bronze bare DDL branch and WARNING on the silver/gold-non-transaction
    and unknown-zone branches) without collapsing it, so a flat id->class map
    provably loses information; another registered rule additionally carries an
    INFO empty-case branch alongside ERROR branches, reinforcing that a SET is the
    right grain. (a) is the COARSEST grain that still catches the failure the lock
    exists to stop: a class DISAPPEARING from a rule's set (an ERROR dropping out
    of `{ERROR, WARNING}` -> `{WARNING}`) and a class being ADDED. It avoids the
    unstable sub-keys of (b) (message text) and (c) (fixture-case) that the
    plan-review MEDIUM finding warns would flake the lock on innocuous wording
    edits. RESIDUAL TRADEOFF (stated honestly in FR-009): (a) cannot catch a
    per-branch downgrade that leaves the SET unchanged -- but dropping the last
    ERROR branch necessarily removes ERROR from the set, so the core ERROR-vanish
    protection holds.
  - **Reversible**: easy (the grain is internal to the generator + test; the
    record is regenerated from live observation, never hand-typed).

- **SCOPE / COVERAGE (FR-010)** -- *registered rules + named L3 surface*.
  - **Decision**: cover the REGISTERED rules now (registry-reachable via
    `all_rules()`) AND ALSO the non-registered L3 governance surface
    (verdict-to-finding: drift -> ERROR / escalate -> WARNING) as a SECOND,
    explicitly-named section keyed `L3:verdict_to_finding`.
  - **Option chosen**: registered-rules-plus-named-L3-surface, over
    registered-only.
  - **Rationale**: the L3 surface emits ERROR and is therefore gate-bearing -- a
    silent L3 ERROR-to-WARNING downgrade is the SAME Principle-I bypass the lock
    exists to stop, even though L3 is not registry-reachable. The Principle-VIII
    fallback (registered-only if L3 cannot be driven without live execution) does
    NOT trigger: reading the source confirms the verdict-to-finding mapping is a
    PURE function over a verdict VALUE (a frozen `status`/`detail` dataclass), so
    it is driven in-process by constructing a `drift` verdict and an `escalate`
    verdict -- no YAML load, no DB, no model, no agent (Principle VIII holds). L3
    is modelled as a distinct pseudo-rule entry observed by driving both verdict
    statuses; it is NOT given a `@register` and adds NO expected-rule-id, so
    ADR-0007 stays intact and the registry-reachable rule count is unchanged.
  - **Reversible**: easy (the L3 section is an extra observed entry; dropping it
    is a one-line change to the generator + a record regen).

- **READINESS MAPPING** -- *option (a): unmapped test-hardening item*.
  - **Decision**: file this as an UNMAPPED test-hardening item, exactly parallel
    to the manifest-snapshot sibling (spec 043), which also has no roadmap F-row.
  - **Option chosen**: (a) unmapped test-hardening item, over (b) attach to a
    governance/quality readiness row, over (c) gate behind the
    idea-bank-to-roadmap hard link.
  - **Rationale**: inventing an F-number would fabricate a roadmap mapping that
    does not exist, and gating behind an unrelated open idea (option (c)) would
    block a clean, shippable hardening item for no reason. The sibling 043 set
    the precedent: a test-only golden-assertion hardening item is unmapped by
    design. No fabricated readiness score is introduced (Hard rule #9).
  - **Reversible**: easy (a mapping can be added later if a governance/quality
    readiness row is created; nothing in the code depends on the mapping).

- **FAIL / UPDATE PROTOCOL** -- *same-PR two-part diff (confirmed)*.
  - **Decision**: the golden record is regenerated and committed in the SAME
    PR/change as any deliberate rule severity edit (mirroring the
    EXPECTED_RULE_IDS + rules-manifest.json discipline), so an UNINTENTIONAL
    downgrade fails CI while an INTENTIONAL one is a small reviewed two-part diff.
  - **Option chosen**: same-PR regeneration (confirm the manifest-mirrored
    protocol), over a separate follow-up change.
  - **Rationale**: this is the established discipline for the sibling golden
    artifacts; it keeps an accidental downgrade red in CI without forcing a
    rule author to chase a second PR for an intentional change. The failure
    message MUST name the affected rule, the recorded-vs-observed severity-set
    delta, and the single regeneration command (FR-003 / FR-004).
  - **Reversible**: easy (the protocol is a convention enforced by the test's
    fail-closed message; no code lock-in).
