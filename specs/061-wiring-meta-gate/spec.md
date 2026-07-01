# Feature Specification: 5-Place Wiring Meta-Gate / Registry Lockstep Self-Check

**Feature Branch**: `061-wiring-meta-gate`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "5-Place Wiring Meta-Gate / Registry Lockstep Self-Check"

## Overview

The rule registry is wired across five places that must stay mutually
consistent. Adding one rule today touches all five, and each place has its own
golden/snapshot test that fails closed independently. Yet nothing proves the
five places agree with each other, and one seam is entirely un-guarded: the
package import list, the `__all__` export list, and the on-disk submodule set in
the rules package can drift apart silently. A documented real incident (the G6
latent gap) showed the suite could "pass only by omission symmetry" -- a rule
present in the registry but missing from the id source-of-truth and the reload
set, so the suite validated N-1 rules and stayed green.

This feature adds a single test-only, standard-library-only "meta-gate": a
lockstep self-check that treats the live registry as ground truth and proves the
other four wiring places agree with it, while additionally closing the one
un-guarded seam (import list == exports == on-disk submodules). It is pure
governance infrastructure over the generic rule registry. It adds no new
registered rule, no new expected rule id, executes nothing (no database,
network, Power BI, query, or agent), and carries zero example-domain
identifiers.

## The Five Wiring Places (context)

1. **Rule modules** -- the source files under the rules package; each declares
   its rules via a registration decorator.
2. **Package import list + exports** -- the rules package imports every
   submodule (so registration fires) and re-declares the same names in its
   public export list. The equality of these two lists and the on-disk submodule
   set is currently un-asserted.
3. **Expected-rule-id source of truth** -- a hand-maintained set of every rule
   id, asserted equal to the live registry ids.
4. **Golden manifest** -- a generated, committed inventory of registry
   `{id, title}` entries with a snapshot test asserting live == committed.
5. **Golden severity-posture record** -- a generated, committed record of each
   rule's observed severity classes, with a snapshot test asserting live ==
   committed. It legitimately also records one non-registered governance surface
   (per ADR-0007) that adds no rule id.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Un-guarded package-symmetry seam is closed (Priority: P1)

As a governance maintainer, when someone edits the rules package so the import
list, the export list, and the on-disk submodule set no longer agree (for
example adds a submodule to the import list but forgets the export list, or
leaves an orphan file), the test suite must fail with a message that names the
mismatch -- instead of passing silently as it does today.

**Why this priority**: This is the single genuinely-new coverage the feature
adds beyond the four existing golden tests. It is the exact class of silent drift
the existing suite cannot catch. Delivering only this story already removes a
real blind spot and is a viable MVP.

**Independent Test**: Runnable in isolation via the unit-test marker. Temporarily
diverge the export list from the import list in a throwaged copy / by a planted
fixture representation and confirm the meta-gate fails closed with a diff naming
the missing/extra name; restore and confirm it passes.

**Acceptance Scenarios**:

1. **Given** the import list, export list, and on-disk submodule set are equal,
   **When** the meta-gate runs, **Then** it passes.
2. **Given** a submodule name is present in the import list but absent from the
   export list, **When** the meta-gate runs, **Then** it fails closed and the
   message names the offending symbol and which list it is missing from.
3. **Given** an on-disk rules submodule exists that is absent from both lists (an
   orphan), **When** the meta-gate runs, **Then** it fails closed and names the
   orphan.

---

### User Story 2 - Five places proven in mutual lockstep (Priority: P1)

As a governance maintainer, when any single wiring place falls out of step with
the live registry (a rule id missing from the id source of truth, a manifest
entry not regenerated, a posture entry not regenerated), the meta-gate must fail
closed and its message must name which place disagrees and how -- so a partial
edit cannot merge green.

**Why this priority**: This is the core promise of a "lockstep" gate: the whole
point is that the five places cannot silently diverge. The G6 incident proves the
"passes by omission symmetry" failure is real, not hypothetical.

**Independent Test**: With a planted representation of each of the four
cross-checked places, remove/alter one entry at a time and confirm the meta-gate
fails closed naming that place; with all places consistent, confirm it passes.

**Acceptance Scenarios**:

1. **Given** every rule id known to the live registry is present in the id
   source of truth and vice versa, **When** the meta-gate runs, **Then** the
   id-place check passes.
2. **Given** a rule reachable in the live registry whose id is absent from the id
   source of truth, **When** the meta-gate runs, **Then** it fails closed naming
   the missing id and the id-source-of-truth place (this is the G6 failure
   class).
3. **Given** the committed golden manifest omits (or mis-titles) a live rule,
   **When** the meta-gate runs, **Then** it fails closed naming the manifest
   place and the offending id.
4. **Given** the committed golden severity-posture record omits a live
   registered rule, **When** the meta-gate runs, **Then** it fails closed naming
   the posture place and the offending id.

---

### User Story 3 - Non-registered governance surface exception is honored (Priority: P2)

As a governance maintainer, the meta-gate must not falsely fail on the one
legitimate non-registered governance surface that the posture record includes
(per ADR-0007). That surface intentionally adds no rule id; the meta-gate must
encode this exception rather than naively demanding every observed posture entry
appear in the id source of truth.

**Why this priority**: Without encoding the exception the meta-gate would produce
a false failure on a known-good repo state, undermining trust in the gate. It is
P2 because it is a correctness guard on the checks defined in Stories 1-2, not a
new class of coverage.

**Independent Test**: With the repo in its known-good state (registered rules
plus the single non-registered posture surface), confirm the meta-gate passes and
does NOT require the non-registered surface's key to appear in the id source of
truth or the manifest.

**Acceptance Scenarios**:

1. **Given** the posture record's non-registered governance surface entry exists
   and has no corresponding rule id, **When** the meta-gate runs, **Then** it
   passes and does not demand a rule id for that surface.
2. **Given** the set of non-registered surfaces the meta-gate exempts is itself
   recorded explicitly (not implicit), **When** a NEW non-registered surface
   appears that is not on the exemption list, **Then** the meta-gate fails closed
   (a new non-registered surface is a deliberate governance decision, not a
   silent pass).

---

### Edge Cases

- **Duplicate registration**: two decorators register the same id. The meta-gate
  MUST fail closed (the registry tuple length must equal the unique-id count).
- **Empty registry / empty package**: if no submodules or no rules are
  discovered, the meta-gate MUST fail closed rather than pass vacuously (a green
  run over zero rules is the omission-symmetry trap).
- **Ordering / serialization noise**: a place that differs only by ordering,
  encoding (BOM), or line endings MUST still be compared on normalized content so
  the gate neither false-passes nor false-fails on cosmetic differences; the
  normalization matches the existing golden serialization contract.
- **Relationship to existing tests**: the three/four existing standalone tests
  continue to exist. Whether the meta-gate subsumes them or sits beside them is
  an open scope decision (see Clarifications) with a recommended default of ADD.
- **Windows long paths**: any path the meta-gate constructs or reports MUST stay
  within the platform path limit; no absolute-path assumptions that break on a
  deep checkout.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The meta-gate MUST treat the live rule registry (the in-process
  set of registered rules, re-loaded deterministically so it does not depend on
  global state left by other tests) as the single ground truth against which the
  other wiring places are compared.
- **FR-002**: The meta-gate MUST assert that, within the rules package, the
  side-effecting import list, the public export list, and the on-disk submodule
  set are exactly equal, and MUST fail closed naming any symbol present in one
  but not the others.
- **FR-003**: The meta-gate MUST assert that the set of rule ids in the live
  registry equals the expected-rule-id source of truth, failing closed with the
  missing and unexpected ids named (the G6 omission-symmetry failure class).
- **FR-004**: The meta-gate MUST assert that the committed golden manifest,
  reduced to its `{id, title}` entries, equals what the live registry would
  generate, failing closed naming any added/removed/retitled id.
- **FR-005**: The meta-gate MUST assert that every live registered rule appears
  in the committed golden severity-posture record's registered section, failing
  closed naming any registered rule absent from the record.
- **FR-006**: The meta-gate MUST encode an EXPLICIT exemption list of
  non-registered governance surfaces (per ADR-0007) so that those surfaces are
  neither required to have a rule id nor treated as drift; a non-registered
  surface NOT on the exemption list MUST cause a fail-closed.
- **FR-007**: The meta-gate MUST fail closed (non-zero test outcome) on any
  single place falling out of lockstep; it MUST NOT emit only an advisory
  warning.
- **FR-008**: The meta-gate MUST fail closed on a vacuous state (zero discovered
  submodules or zero registered rules) rather than passing.
- **FR-009**: The meta-gate MUST fail closed on duplicate rule-id registration
  (registry length must equal the unique-id count).
- **FR-010**: The meta-gate MUST add NO new registered rule and NO new
  expected-rule-id entry; it is a test-only assertion (mirroring how the manifest
  and severity-posture generators were built as test-only golden assertions).
- **FR-011**: The meta-gate MUST be standard-library-only, introducing no new
  third-party dependency.
- **FR-012**: The meta-gate MUST NOT execute any query, DAX, agent, database
  call, network call, or Power BI operation; it reads committed text plus the
  in-process registry object only.
- **FR-013**: Any content the meta-gate serializes or compares MUST use the
  existing deterministic serialization contract: sorted/deterministic ordering,
  UTF-8 without BOM, `\n` line endings, and platform-path-safe paths.
- **FR-014**: The meta-gate MUST carry zero example-domain identifiers; every
  symbol it references is generic rule-registry infrastructure.
- **FR-015**: On any failure the meta-gate MUST identify which of the wiring
  places disagrees and the specific offending symbol/id, so the fix location is
  unambiguous.
- **FR-016**: The meta-gate's relationship to the existing standalone wiring
  tests (ADD a fourth cross-referencing check vs. REPLACE/subsume the existing
  ones) MUST follow the decision recorded in Clarifications; the default is ADD,
  so no existing guard is deleted in this feature.

### Key Entities *(include if feature involves data)*

- **Live registry snapshot**: the deterministically re-loaded set of registered
  rules (id + title), the ground truth. No new field is added to it.
- **Wiring place**: one of the five consistency surfaces (rule modules; package
  import list + exports; expected-rule-id set; golden manifest; golden posture
  record).
- **Non-registered-surface exemption list**: an explicit, recorded set of
  governance surfaces (per ADR-0007) that legitimately carry no rule id.
- **Lockstep report**: the failure output naming the disagreeing place and the
  offending symbol/id (no new persisted golden file is required by this feature).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Introducing any single wiring-place divergence (an import/export
  asymmetry, an orphan submodule, a missing id in the id source of truth, a
  stale manifest entry, or a missing posture entry) causes the test suite to fail
  -- 100% of the five places are covered by a fail-closed check.
- **SC-002**: The specific G6-style failure (a rule reachable in the registry but
  absent from the id source of truth) is caught by the meta-gate, whereas today
  it can pass by omission symmetry.
- **SC-003**: In the repo's known-good state (all places consistent, including
  the single non-registered governance surface), the meta-gate passes with zero
  false failures.
- **SC-004**: The meta-gate runs in the existing unit-test lane with no new
  third-party dependency and no database/network/Power BI access, completing
  within the same order of magnitude as the existing wiring/snapshot tests.
- **SC-005**: A reviewer reading a meta-gate failure message can identify the
  exact wiring place and offending symbol/id without opening the source, in 100%
  of the divergence cases enumerated in SC-001.

## Clarifications

### Session 2026-07-02

- Q: Should the meta-gate REPLACE/subsume the existing standalone wiring tests,
  or ADD a fourth cross-referencing check alongside them? -> A: ADD. The
  meta-gate is a new cross-referencing lockstep check that sits beside the
  existing per-place tests; no existing guard is deleted in this feature.
  Rationale: deleting working fail-closed guards in the same change that adds a
  new one increases risk and loses the per-place failure locality the existing
  tests give; consolidation, if ever wanted, is a separate follow-on. Reversible:
  easy (a later spec can consolidate).
- Q: Should the meta-gate re-observe severity posture in-process (which shells
  out to a version-control subprocess over a throwaway temp directory) or read
  the committed golden posture record statically? -> A: Read the committed golden
  record statically. Rationale: re-observing inherits a subprocess dependency and
  duplicates the existing posture snapshot test; the meta-gate's job is
  cross-consistency, and static comparison keeps it purely static (Principle
  VIII) and cheap. Reversible: easy.
- Q: How is the ADR-0007 non-registered-surface exception encoded? -> A: As an
  explicit, recorded exemption list, so a NEW non-registered surface that is not
  on the list fails closed. Rationale: an implicit "ignore anything without a
  rule id" rule would let a new un-vetted surface slip in silently, defeating the
  gate. Reversible: easy.

## Assumptions

- The meta-gate lives in the existing unit-test suite and runs under the existing
  unit-test marker; it is not a runtime rule and never appears in the rule
  registry, the expected-rule-id set, the manifest, or the posture record.
- The live registry exposes exactly id + title per rule (no severity field); the
  meta-gate reads only these plus the package/module structure and committed
  golden files.
- "On-disk submodule set" is discovered dynamically (package introspection),
  matching the approach the existing wiring test already uses, and excludes the
  package initializer itself.
- Reading the committed golden files statically is sufficient for the manifest
  and posture cross-checks; the meta-gate does not re-generate them (the existing
  snapshot tests already assert live == committed for each).
- ADR-0007 defines the one currently-known non-registered governance surface; the
  exemption list starts with exactly that surface.
- This feature is governance-internal: it maps to no data-readiness stage and no
  numbered roadmap feature (f_number = none, roadmap stage = unmapped); if it
  earns a roadmap row it joins the lettered wiring-symmetry governance family, a
  decision left to the human (see Clarifications is silent on this; recorded as an
  open item for the ratifier below).

## Dependencies

- The live rule registry and its deterministic re-load helper (existing).
- The expected-rule-id source of truth (existing test constant).
- The committed golden manifest and its generator (existing).
- The committed golden severity-posture record and its generator (existing).
- ADR-0007 (the non-registered governance-surface exception).

## Out of Scope

- Adding, removing, or renaming any runtime rule.
- Introducing a new registered rule id or a new persisted golden file.
- Any live/executing behavior (database, network, Power BI, DAX, agent).
- Consolidating or deleting the existing per-place tests (default is ADD).
- Assigning a roadmap letter/row or a readiness stage (deferred to the human).
