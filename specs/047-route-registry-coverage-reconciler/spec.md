# Feature Specification: Route-Registry Coverage Reconciler (A3)

**Feature Branch**: `047-route-registry-coverage-reconciler`

**Created**: 2026-06-30

**Status**: Draft

**Input**: User description: "Route-Registry Coverage Reconciler (A3) -- map rows == routes.yaml ids [bank verdict: ADOPT]"

## Overview

The repository routes work through a knowledge map (`docs/knowledge-map.md`,
"Route by task" table) and a machine-checkable manifest (`docs/routing/routes.yaml`).
The manifest is hand-mirrored from the map: each manifest route corresponds to a
map row. Today, the shipped A1 rule reads ONLY the manifest and verifies each
route target resolves on the filesystem -- it never reads the map. Nothing checks
that the *set of route ids* in the map equals the set of route ids in the
manifest. A row can be added to the map without a manifest route, or a manifest
route can be added without a map row, and no gate notices.

This feature adds a static governance rule, **A3**, that reconciles the two id
sets as a bijection: every map "Route by task" id MUST appear as a manifest route
id, and every manifest route id MUST appear as a map id. A difference in either
direction fails the `retail check` gate. The two id sets are identical on the
current main branch, so A3 emits zero findings today; it locks an invariant that
is currently true but unguarded, catching FUTURE drift the moment only one side
is edited.

A3 is a routing-integrity static rule in the same family as A1 (route target
resolution) and B1 (never-execute). It reads two tracked text files, compares
sets, and reports differences. It executes nothing, opens no connection, and
writes neither document.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Drift between map and manifest fails the gate (Priority: P1)

A contributor edits the "Route by task" table in the knowledge map to add a new
routed task but forgets to add the matching route to the routing manifest (or
vice versa). When the governance gate runs, it must fail loudly and name the
specific id that exists on one side but not the other, so the contributor fixes
the mirror in the same change instead of shipping a half-wired route.

**Why this priority**: This is the entire reason the rule exists -- it closes the
currently-unguarded drift class at the map<->manifest boundary. Without it the
feature delivers no value.

**Independent Test**: Stage a map with id set {1, 2} and a manifest with id set
{1} (or the reverse) in an isolated context; assert the rule reports exactly one
ERROR finding naming the missing id and the direction of the difference.

**Acceptance Scenarios**:

1. **Given** a map id set and a manifest id set that are identical, **When** the
   rule runs, **Then** it reports zero findings.
2. **Given** a map that contains an id absent from the manifest, **When** the rule
   runs, **Then** it reports an ERROR finding that names the id and states the map
   contains it but the manifest does not.
3. **Given** a manifest that contains an id absent from the map, **When** the rule
   runs, **Then** it reports an ERROR finding that names the id and states the
   manifest contains it but the map does not.

---

### User Story 2 - Malformed or missing inputs fail loud, never vacuously green (Priority: P1)

If either source document is missing, untracked, or structurally unreadable (the
"Route by task" table cannot be located, or the manifest is not parseable / not
the expected shape), the rule must fail with an ERROR rather than silently
passing with an empty id set. A vacuous green would let real drift hide behind a
parsing failure.

**Why this priority**: The static-governance invariant (Principle VIII) requires
fail-loud-on-malformed-input. A rule that passes when it cannot read its inputs is
worse than no rule, because it manufactures false confidence.

**Independent Test**: Stage a context with no manifest tracked, then one with a
manifest that is not a routes mapping, then one whose map text has no locatable
"Route by task" table; assert each yields an ERROR finding describing the
unreadable input.

**Acceptance Scenarios**:

1. **Given** the manifest is missing or untracked, **When** the rule runs, **Then**
   it reports an ERROR naming the manifest as unreadable.
2. **Given** the map's "Route by task" table cannot be located, **When** the rule
   runs, **Then** it reports an ERROR naming the map section as unreadable.
3. **Given** the manifest is present but not a valid routes mapping, **When** the
   rule runs, **Then** it reports an ERROR describing the malformed manifest.

---

### User Story 3 - The rule is discoverable and counted in the gate (Priority: P2)

A maintainer must be able to trust that A3 is actually wired into the gate and not
silently dormant. The registered rule-id set is the single source of truth and
must include A3; the wiring smoke test must catch the rule if it is ever removed
or fails to register.

**Why this priority**: A registered-but-unvalidated rule is the exact symmetry gap
the project has been bitten by before. Adding the id to the expected set in the
same change is the guard. It is P2 only because it is mechanical given P1.

**Independent Test**: Run the wiring test and assert the registered rule-id set
equals the expected set, with A3 present and the count increased by exactly one.

**Acceptance Scenarios**:

1. **Given** the rule package is imported, **When** the registered rule-id set is
   collected, **Then** it contains "A3".
2. **Given** the expected rule-id set, **When** its size is compared to the prior
   baseline, **Then** it has grown from 33 to 34 (A3 is the only addition).

---

### Edge Cases

- **Sub-lettered ids** (e.g. `12a`, `17d`): the map id column uses a leading
  number-or-number-letter token followed by a period (`1.`, `12a.`, `17d.`). The
  extractor MUST capture these exactly and not normalize `12a` to `12`.
- **Other pipe-tables in the map**: the map contains additional pipe tables ("Route
  by symptom", supporting references) whose rows would pollute the id set if the
  extractor scanned the whole file. The extractor MUST read ONLY the "Route by
  task" table and stop at the next section heading.
- **Duplicate ids within one source**: if the same id appears twice on one side, the
  rule still compares sets; a within-source duplicate is out of scope for A3 (it is
  a different defect class) unless it changes the comparison outcome, in which case
  the set comparison still surfaces any cross-source asymmetry correctly.
- **Whitespace / formatting variance** in the map table cells (extra spaces, blank
  lines) must not change the extracted id set.
- **Bijection already holds on main**: on a clean checkout the rule reports zero
  findings; a live guard must prove this end-to-end against the committed repo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The rule MUST extract the set of route ids from the knowledge map's
  "Route by task" table id column (the leading token of each data row).
- **FR-002**: The rule MUST extract the set of route ids from the routing manifest.
- **FR-003**: The rule MUST report an ERROR finding for every id present in the map
  but absent from the manifest, naming the id and the direction of the difference.
- **FR-004**: The rule MUST report an ERROR finding for every id present in the
  manifest but absent from the map, naming the id and the direction of the
  difference.
- **FR-005**: The rule MUST report zero findings when the two id sets are equal.
- **FR-006**: The rule MUST scan ONLY the "Route by task" table when extracting map
  ids, stopping at the next section heading, so other pipe-tables in the map do not
  contribute ids.
- **FR-007**: The rule MUST fail with an ERROR (never a vacuous pass) when the map's
  "Route by task" table cannot be located.
- **FR-008**: The rule MUST fail with an ERROR (never a vacuous pass) when the
  manifest is missing, untracked, unparseable, or not the expected routes shape.
- **FR-009**: The rule MUST be registered under the gate's rule registry with id
  "A3" and a human-readable title, discoverable via the same import-side-effect
  mechanism as the existing rules.
- **FR-010**: The expected rule-id set used by the wiring drift guard MUST be
  updated from 33 ids to 34 ids by adding "A3" in the same change, so the wiring
  test passes and would catch A3's removal.
- **FR-011**: The rule MUST be a pure read-only function of its context: it executes
  nothing, opens no connection, and modifies neither source document.
- **FR-012**: Every finding the rule emits MUST be generic -- it MUST reference only
  abstract route ids and document structure, never any domain-specific route value,
  table name, billing code, segment, or column.
- **FR-013**: The feature MUST include a live guard that runs the rule against the
  committed repository and asserts zero findings, proving the shipped map and
  manifest are in bijection end-to-end.
- **FR-014**: A ledger row MUST be recorded in the roadmap's idea-bank execution
  sequence noting A3 shipped and the rule count moved from 33 to 34.

### Severity posture *(see Clarifications)*

The idea's first-step states "ERROR on asymmetric difference" in both directions.
The default adopted here is that BOTH directions (map-id-missing-from-manifest AND
manifest-id-missing-from-map) are ERROR severity, consistent with A1's fail-closed
posture. A human ruling is requested to confirm this is not a one-direction-WARNING
posture (recorded in Clarifications).

### Key Entities *(include if feature involves data)*

- **Map id set**: the set of route id tokens extracted from the knowledge map's
  "Route by task" table. A read-only derived value; the map is never written.
- **Manifest id set**: the set of route id tokens declared in the routing manifest.
  A read-only derived value; the manifest is never written.
- **Finding**: a single gate result (rule id, severity, message, locator) emitted
  when the two id sets differ or an input is unreadable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the current main branch, the rule reports zero findings (the
  bijection already holds and is now locked).
- **SC-002**: An asymmetric difference introduced on either side (an id added to one
  source only) causes the gate to exit non-zero with a finding that names the exact
  drifting id.
- **SC-003**: A missing or malformed input causes the gate to exit non-zero rather
  than pass, in 100% of the malformed-input cases tested.
- **SC-004**: The registered rule-id set contains A3 and totals 34, and the wiring
  guard fails if A3 is removed.
- **SC-005**: No finding message or test fixture contains any domain-specific route
  value, table name, or code -- all are generic.

## Assumptions

- The knowledge map's "Route by task" table is a GFM pipe table whose id column is
  the leading cell of each data row, and the table is delimited above by its section
  heading and below by the next section heading. (Verified true on main.)
- The routing manifest is a mapping with a top-level routes list, each route a
  mapping carrying an id. (Verified true on main -- this is the A1 manifest shape.)
- The id-comparison scope for v1 is the knowledge map's "Route by task" table only.
  Whether to also reconcile the COMPASS fast-routing table (which the map header says
  the manifest mirrors) is deferred -- see Clarifications.
- The rule reuses the existing rule contract (context in, findings out) and the
  existing manifest-parsing approach (a lazy parse kept out of the core import path),
  and adds a hand-rolled standard-library text extractor for the map table -- it adds
  no new markdown-parsing dependency.
- The current registered rule-id baseline is 33 (verified in the wiring test on this
  branch's HEAD), and A3 takes it to 34. The idea-bank synthesis text that calls the
  baseline "already 34" is a known off-by-one and is NOT trusted.
- No deferred runtime (Power BI execution adapter / spec-only live runtimes) is
  assumed to exist; A3 is a pure static check over committed text.

## Clarifications

The following are deferred to human ruling (Principle V / governance-posture
decisions the spec must not self-answer). They are recorded here and reconciled in
the clarify stage where a recommended default is proposed without binding the human.

- [NEEDS CLARIFICATION: Roadmap stage. This idea carries no confirmed roadmap
  F-number. Does A3 advance a readiness stage, or is it a routing-integrity rule
  outside the 7-stage spine like A1/B1 (which advance no stage)? The idea-backlog
  card labels it "V7 / F7" but the grounding could not confirm an F7 row owns it.]
- [NEEDS CLARIFICATION: Bijection scope. Should A3 compare ONLY the knowledge map's
  "Route by task" id column against the manifest, or also reconcile the COMPASS
  fast-routing table the map header says the manifest mirrors? Widening adds coverage
  but more false-positive surface.]
- [NEEDS CLARIFICATION: Severity posture. Confirm BOTH difference directions
  (map-only id AND manifest-only id) are ERROR, versus one direction being WARNING.
  The default adopted is ERROR-both, matching A1; a human should ratify this,
  consistent with the severity-posture-lock work.]
