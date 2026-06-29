# Feature Specification: Severity-Posture Regression Lock (golden severity table)

**Feature Branch**: `044-045-severity-posture-lock`

**Created**: (date pending -- operator to fill)

**Status**: Draft

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
  rule emits both ERROR and WARNING from different violation branches; some rule
  families mix classes. The golden record's grain MUST represent this without
  collapsing it to one class. The grain (key/uniqueness) is a load-bearing
  design ruling -- see Clarifications.
- **A rule emits no finding over the planted input.** The observation harness
  must force the rule to fire; if a rule cannot be made to fire over a minimal
  synthetic fixture, the record must represent that explicitly rather than
  silently recording "no severity" (which would mask a future downgrade on that
  rule). See Clarifications.
- **A non-registry severity surface (the L3 governance posture) is also
  gate-bearing.** A separate, non-registered code surface maps a drift outcome
  to ERROR and an escalate outcome to WARNING. It is equally load-bearing for the
  gate but is NOT reachable by iterating the rule registry. Whether the lock
  covers it is a scope ruling -- see Clarifications.
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
  value (Principle VII -- the example domain is an example, not the schema).
- **FR-007**: This feature MUST add NO new registered (gating) rule and NO new
  expected-rule-id entry. It is a test-only golden assertion plus a generator,
  exactly like the manifest-snapshot sibling.
- **FR-008**: The observation harness MUST use only synthetic/minimal planted
  fixtures and MUST perform no live query, no model execution, no agent run, and
  no live database access (Principle VIII -- static-first; live deferred).
- **FR-009**: The golden record's GRAIN (its key and uniqueness) MUST faithfully
  represent rules that emit more than one severity class.
  [NEEDS CLARIFICATION: grain is a Principle-V human ruling -- key options are
  (a) rule_id -> the SET of severity classes the rule can emit, (b)
  (rule_id, violation-branch/message) -> severity, or (c)
  (rule_id, planted-fixture-case) -> severity. Recorded to Clarifications; not
  to be answered by the agent.]
- **FR-010**: The lock's COVERAGE boundary MUST be explicit -- specifically
  whether it covers ONLY the registered rules (registry-reachable) or ALSO the
  non-registered L3 governance severity surface (drift -> ERROR / escalate ->
  WARNING), which is equally gate-bearing but not registry-reachable.
  [NEEDS CLARIFICATION: coverage of the non-registry L3 surface is a Principle-V
  scope ruling. Recorded to Clarifications; not to be answered by the agent.]
- **FR-011**: When a rule cannot be forced to emit a finding over a minimal
  synthetic fixture, the record MUST represent that state explicitly rather than
  recording an absence that would mask a future downgrade.

### Key Entities *(include if feature involves data)*

- **Severity class**: One of the three ordered build-impact classes -- the
  build-failing class (ERROR), the reported-but-non-failing class (WARNING), and
  the informational class (INFO). Only the ERROR class fails the build; this
  ordering is the posture the lock protects.
- **Registered rule**: A rule reachable by iterating the rule registry; carries
  an id and a title but NO severity field. Its severity posture exists only in
  the findings it emits at run time.
- **Severity posture (per rule)**: The set/structure of severity classes a rule
  emits when forced to fire -- the thing the golden record captures. Its exact
  grain is a human ruling (see Clarifications).
- **Golden severity record**: The committed, generic, deterministic artifact
  recording the observed posture; the fail-closed comparison target. A sibling
  to the existing committed golden rule artifacts.
- **L3 governance severity surface**: A separate, non-registered code surface
  mapping a drift outcome to the ERROR class and an escalate outcome to the
  WARNING class. Gate-bearing but not registry-reachable; in-scope-or-not is a
  human ruling (see Clarifications).

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
  explicit no-finding marker) in the golden record -- 0 unrecorded registered
  rules.

## Assumptions

- The committed golden record lives alongside the existing committed golden rule
  artifacts (the same directory that holds the rule manifest), as a natural
  sibling. Exact filename/format is an implementation detail to be set in the
  plan, constrained by FR-005/FR-006.
- The intended update protocol mirrors the existing manifest discipline: an
  intentional severity change edits the rule AND regenerates the golden record in
  the SAME reviewed change, so an unintentional downgrade fails the test while an
  intentional one is a small two-part diff.
- The observation harness reuses the existing clear-and-reload registry pattern
  already proven by the manifest-snapshot sibling, so the test is order-proof and
  does not depend on global registry state left by sibling tests.
- This is an UNMAPPED test-hardening item: no roadmap feature row maps to it
  (parallel to the manifest-snapshot sibling). The backlog "value/feasibility"
  score is NOT a roadmap feature number. Which readiness stage (if any) this
  advances is a human decision recorded to Clarifications.
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

### Session (date pending)

The following are Principle-V judgment calls (grain / scope / readiness mapping /
update protocol). They are RECORDED for human resolution and intentionally left
UNANSWERED by the planning agent. The operator MUST fill the session date and
resolve these before ratification.

- **GRAIN / UNIQUENESS (FR-009)**: What is the golden record's key? A flat
  rule_id -> single-severity map is WRONG for rules that emit multiple classes.
  Options: (a) rule_id -> SET of severity classes it can emit; (b)
  (rule_id, violation-branch/message) -> severity; (c)
  (rule_id, planted-fixture-case) -> severity. This is the load-bearing decision:
  too coarse misses a per-branch downgrade; too fine is unmaintainable.
- **SCOPE / COVERAGE (FR-010)**: Does the lock cover ONLY the registered rules
  (registry-reachable), or ALSO the non-registered L3 governance severity surface
  (drift -> ERROR / escalate -> WARNING)? The L3 surface is equally gate-bearing
  but is a separate, non-registry surface.
- **READINESS MAPPING**: No roadmap feature row maps to this test-only item. A
  human must decide whether to (a) file it as an unmapped test-hardening item
  (like the manifest-snapshot sibling), (b) attach it to a governance/quality
  readiness row, or (c) gate it behind the idea-bank-to-roadmap hard link first.
- **FAIL / UPDATE PROTOCOL**: Confirm the intended workflow on a deliberate
  severity change -- the golden record is edited in the SAME change as the rule
  change (mirroring the manifest discipline), so an unintentional downgrade fails
  the test while an intentional one is a reviewed diff.
