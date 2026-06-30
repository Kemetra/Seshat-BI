# Feature Specification: Parked-On Map / Parked-On Dependency Map (DF1 -- F016 Bottleneck-Edge Reconciler)

**Feature Branch**: `051-parked-on-map`

**Created**: 2026-06-30

**Status**: Ratified (advisor-for-Ahmed-Shaaban, 2026-06-30)

**Ratification note**: Ratified by the advisor agent acting under an explicit,
recorded per-spec delegated override granted by the repo owner
(info@rahmaqanater.org) for the 2026-06-30 unattended overnight session. Provenance:
this Ratified line is AI-authored under recorded human authority; it is NOT a
human-typed ratification and the git author identity does not by itself attest a
human reviewer. The five clarify ambiguities and the one deferred non-Principle-V
question (roadmap F-row placement) are resolved as recorded rulings in the
Clarifications section (severity=ERROR; shipped-when-tracked detection; v1 scope = the
F016 cluster; empty-manifest passes clean; no amendment/ADR/stage; no F-row). No
Principle-V carve-out arose. analyze=clean (0 critical/0 high); plan-review=PASS-WITH-NOTES
(3 low, non-blocking).

**Input**: User description: "Parked-On Map / Parked-on dependency map (DF1 -- F016 bottleneck-edge reconciler)"

## Overview

The retail check kit already keeps two kinds of cross-document claim honest. Rule A1
reads a manifest of declared *routes* and fails the gate when a route's target file
does not match its declared status. Rule SC1 (spec 050) does the same for prose
*status claims*: a hand-curated manifest records, per claim, the doc + the literal
sentence asserting it + the claimed artifact + the claimed status (`built` /
`planned`), and the gate fails closed when the claim drifts from tracked-file reality.

A third class of cross-document claim is still unguarded: **parked-on dependency
edges**. The roadmap repeatedly asserts that several features are *parked on* a single
shared blocker (the Power BI execution adapter, F016) -- F016 is named across roughly
fifteen roadmap lines and is the stated reason that pbi-tools extract, the new L3
predicate operators, and the maintenance-automation features (F031-F033) are all
DEFERRED. Today these deferrals live as scattered, un-cross-checked English
sentences. Nothing fails when a parked-on edge cites a blocker that does not exist,
and nothing fails when a feature said to be "parked on F016" has in fact already
shipped (a "parked-but-shipped" contradiction). The roadmap could quietly say a thing
is blocked long after it stopped being blocked, or cite a blocker that was never real.

This feature adds **DF1**, the parked-on-edge analog of SC1: a single new static,
read-only rule plus a hand-curated YAML manifest (`docs/quality/parked-on.yaml`) that
records each parked-on dependency edge -- the blocked target, the shared blocker it is
parked on, the roadmap anchor (the literal sentence asserting the park), and a tracked
deferred-spec/spec file that is the evidence the park is real. DF1 reconciles every
declared edge against tracked-file evidence and fails LOUD (ERROR, non-zero exit, wired
into `retail check`) when an edge's blocker/evidence does not resolve, or when an edge
asserts a park that the repository contradicts.

DF1 adds **only the seam** -- the parked-on map and its loud check. It does NOT build,
wire, start, or vendor F016 or any F031-F033 runtime. F016 remains parked and gated by
hard rule #6 (not startable before Semantic Model Ready is `pass`); mapping its
parked-on edges is the opposite of starting it. DF1 reads committed roadmap text and
tracked deferred-spec files only -- it opens no database, network, or execution path.

### What this feature is NOT (scope guard)

- It is **not** the F016 Power BI execution adapter, nor any part of it. No
  execution-adapter machinery, no `.pbix`/connection code, no MCP wiring is added or
  touched. (Hard rule #6 / Principle II / CLAUDE.md YAGNI.)
- It is **not** a runtime for F031-F033. Those remain spec-only and parked; DF1 only
  records that they are parked, citing their existing tracked specs as evidence.
- It is **not** a free-text scanner of the roadmap. DF1 checks only the edges
  explicitly listed in the manifest, and verifies each edge's roadmap anchor sentence
  is literally present so a manifest entry cannot silently point at a moved or deleted
  sentence (mirroring SC1's anchor discipline).
- It assigns **no confidence score**. Each edge is categorical: it either reconciles
  against tracked evidence or it does not (Readiness System invariant / hard rule #9).
- It carries **no C086/pharmacy-specific facts**. The manifest is about generic kit
  roadmap/feature dependency edges only (Principle VII).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Catch a parked-but-shipped contradiction (Priority: P1)

A maintainer ships a feature that was previously parked on F016, or otherwise resolves
a blocker, but forgets to update the roadmap, which still asserts the feature is
parked. The next `retail check` run fails with a DF1 ERROR naming the edge whose
"parked" claim the repository now contradicts, so the stale parked-on assertion is
caught before it misleads a reader into thinking work is still blocked.

**Why this priority**: This is the core defect the feature exists to prevent -- a
silent drift where the roadmap claims a bottleneck that no longer exists. It is the
fail-closed half that delivers the headline value on its own.

**Independent Test**: With a manifest edge marked `parked` whose declared target/blocker
evidence indicates the target has shipped (per the manifest's shipped-evidence
criterion resolved in Clarifications), running the rule yields exactly one ERROR
finding naming the edge. Removing the contradiction yields zero findings.

**Acceptance Scenarios**:

1. **Given** a manifest edge that declares target T parked on blocker B with a
   shipped-evidence artifact now tracked, **When** DF1 runs, **Then** it emits one
   ERROR finding (`rule_id == "DF1"`) naming the edge and explaining the
   parked-but-shipped contradiction.
2. **Given** the same edge with no shipped-evidence artifact present (the park is
   still honest), **When** DF1 runs, **Then** it emits no finding.

---

### User Story 2 - Catch a nonexistent / unresolvable blocker (Priority: P1)

The manifest names a blocker or cites a deferred-spec evidence file that does not
resolve to a tracked file (a typo, a renamed spec, or a blocker that was never real).
`retail check` fails with a DF1 ERROR so a parked-on edge can never silently point at
evidence that is not there.

**Why this priority**: The fail-closed-other-direction half. An edge that cites a
phantom blocker or missing evidence is as defective as a stale park; both must fail
loud, never pass vacuously.

**Independent Test**: With a manifest edge whose cited deferred-spec evidence file is
not in the tracked set, running the rule yields exactly one ERROR naming the edge and
the missing evidence path.

**Acceptance Scenarios**:

1. **Given** an edge citing an evidence file that is not a tracked file, **When** DF1
   runs, **Then** it emits one ERROR naming the edge and the unresolved path.
2. **Given** an edge whose roadmap anchor sentence is NOT present in the cited roadmap
   doc, **When** DF1 runs, **Then** it emits one ERROR (the anchor is stale or
   misplaced).

---

### User Story 3 - Fail loud on a missing or malformed manifest (Priority: P2)

The parked-on manifest is missing, untracked, not valid YAML, the wrong shape, or has
an incomplete edge entry. DF1 fails loud with an ERROR rather than passing green with
nothing to check, so the gate can never be silently disabled by deleting or breaking
the manifest.

**Why this priority**: Guarantees the gate cannot be neutered by removing its input.
Mirrors SC1's missing/malformed-manifest fail-loud branches.

**Independent Test**: With no manifest file tracked, running the rule yields exactly
one ERROR naming the manifest path. With a malformed/wrong-shape manifest, running the
rule yields one ERROR describing the shape problem.

**Acceptance Scenarios**:

1. **Given** the manifest path is not in the tracked set, **When** DF1 runs, **Then**
   it emits one ERROR naming the manifest path.
2. **Given** a manifest that is not valid YAML, or not a mapping with the expected edge
   list, or an edge missing a required field, **When** DF1 runs, **Then** it emits one
   ERROR describing the defect.

---

### User Story 4 - The new rule is wired and counted (Priority: P2)

DF1 is registered like every other rule and appears in the rule-registry snapshot and
the regenerated `rules-manifest.json`; the wiring test's expected-id set gains exactly
one new id (`DF1`). A maintainer who adds the rule but forgets to wire it sees the
wiring/snapshot tests fail closed.

**Why this priority**: A registered-but-unwired rule is a silent no-op; the drift
guard must catch it. Required for the rule to actually run inside `retail check`.

**Independent Test**: After the change, the rule-registry snapshot test passes with
DF1 present, and the wiring test's expected-id set length increases by exactly one
(the count is derived from the set, never hard-coded).

**Acceptance Scenarios**:

1. **Given** DF1 is registered and `"DF1"` is added to the expected-id set, **When**
   the wiring + rule-registry snapshot tests run, **Then** they pass and reflect
   exactly one additional rule id.
2. **Given** DF1 is registered but `"DF1"` is NOT added to the expected-id set, **When**
   the wiring test runs, **Then** it fails closed (drift detected).

---

### Edge Cases

- **Empty manifest edge list**: an honest "no parked-on edges declared yet" state. Per
  Clarifications Q4, a present, well-formed manifest with zero edges passes CLEAN (zero
  findings) -- only a missing/untracked/malformed manifest fails loud (FR-004).
- **Multiple edges sharing one blocker (F016)**: the common case -- several targets
  parked on the same blocker. Each edge is evaluated independently; one bad edge does
  not suppress findings for the others.
- **An edge whose blocker is itself a real, tracked spec**: F016 has no `src/`
  footprint by design (it is parked), so the "blocker resolves" criterion is defined
  against the manifest's declared evidence file (a tracked deferred-spec/spec), not
  against an F016 implementation file. The exact resolution target is the manifest
  schema decision recorded in Clarifications.
- **A roadmap anchor sentence that is reworded**: the literal-substring anchor test
  fails loud, prompting the maintainer to re-sync the manifest with the roadmap (this
  is intended -- a moved/deleted anchor is itself drift).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a new rule, identified `DF1`, registered through
  the same central rule registry every other rule uses, so it runs as part of
  `retail check` and disposes the checker exit (non-zero on any DF1 ERROR).
- **FR-002**: DF1 MUST read a single hand-curated manifest of parked-on dependency
  edges at a fixed tracked path under `docs/quality/` (proposed
  `docs/quality/parked-on.yaml`), parsed via a lazy `import yaml` inside the rule body
  so the stdlib-only invariant of the `retail check` core chain is preserved (exactly
  as SC1 does).
- **FR-003**: Each manifest edge MUST declare, at minimum: a stable edge `id`; the
  blocked target; the shared blocker id (e.g. `F016`); the roadmap `doc` making the
  park assertion; the literal `anchor` sentence in that doc; and a tracked
  deferred-spec/spec `evidence` file substantiating the park. (Exact field names and
  the parked-but-shipped criterion are a manifest-schema decision -- see Clarifications.)
- **FR-004**: DF1 MUST emit an ERROR finding when the manifest is missing, untracked,
  not valid YAML, not the expected shape (a mapping with the expected edge list), or an
  edge is missing a required field -- never a vacuous green.
- **FR-005**: DF1 MUST emit an ERROR finding for an edge whose declared roadmap `doc`
  is not a tracked file, or whose `anchor` sentence is not literally present in that
  doc (the assertion moved or was removed).
- **FR-006**: DF1 MUST emit an ERROR finding for an edge whose cited `evidence`
  deferred-spec/spec file does not resolve to a tracked file (a nonexistent /
  unresolvable blocker evidence).
- **FR-007**: DF1 MUST emit an ERROR finding for a parked-but-shipped contradiction --
  an edge that asserts a target is parked on its blocker while the repository's tracked
  state shows the park no longer holds. The contradiction criterion (resolved in
  Clarifications Q2) is: each edge declares an OPTIONAL `shipped_when_tracked`
  artifact path; if that path is present in the tracked set, the park is contradicted
  (the target shipped) and DF1 fails loud. An edge that omits `shipped_when_tracked`
  asserts a park with no machine-checkable ship-signal yet and is reconciled only on
  its blocker/evidence/anchor (FR-005, FR-006).
- **FR-008**: DF1 MUST be categorical -- it emits findings (ERROR) or none; it MUST NOT
  emit, compute, or store any confidence/probability/readiness score.
- **FR-009**: DF1 MUST check only edges explicitly listed in the manifest; it MUST NOT
  free-scan roadmap prose for parked-on language.
- **FR-010**: DF1 and its manifest MUST be static and read-only: no database, no
  network, no query/DAX/agent execution, no module-scope import of a connection/network
  client in the governed core (consistent with the never-execute boundary).
- **FR-011**: The change MUST add exactly one new expected rule id, `"DF1"`, to the
  wiring test's expected-id set, and MUST NOT rely on a hard-coded rule count -- the
  count is derived from the set length. The rule-registry snapshot and the regenerated
  `rules-manifest.json` MUST reflect the new rule in the same change.
- **FR-012**: DF1 and its manifest MUST remain generic about kit roadmap/feature
  dependency edges; they MUST NOT contain pharmacy/C086-specific blockers, table names,
  or domain facts.
- **FR-013**: The shipped manifest MUST reconcile cleanly against the real repository
  (a live-manifest smoke check, mirroring SC1's, yields zero findings) so the feature
  ships green.
- **FR-014**: The feature MUST NOT add, wire, start, or vendor F016 or any F031-F033
  runtime; the only new runtime artifacts are the DF1 rule, its manifest, and the
  wiring/snapshot updates.
- **FR-015**: DF1 findings MUST be severity ERROR (resolved in Clarifications Q1). A
  nonexistent blocker, missing evidence, absent anchor, or parked-but-shipped
  contradiction is a proven defect (a false statement of fact in committed governance
  docs), not a suspect pattern; ERROR matches SC1's posture and Principle VIII's
  "ERROR is defensible for a proven contradiction" stance.

### Key Entities *(include if feature involves data)*

- **Parked-on edge**: one declared dependency-bottleneck relationship -- a blocked
  target, the shared blocker it is parked on, the roadmap sentence asserting the park,
  and the tracked deferred-spec/spec evidence that the park is real. Categorical, no
  score.
- **Parked-on manifest**: the single hand-curated YAML file listing every parked-on
  edge DF1 reconciles. Tracked; its absence/malformation fails the gate loud.
- **DF1 finding**: an ERROR-severity reconciliation failure naming the offending edge
  and the specific contradiction (unresolved blocker/evidence, absent anchor,
  parked-but-shipped, or manifest defect).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A stale parked-on assertion (a target the roadmap still calls parked,
  whose park the repository contradicts) is caught as a non-zero-exit `retail check`
  failure in a single run, with the offending edge named in the finding.
- **SC-002**: An edge citing a nonexistent blocker or a missing evidence file is caught
  as a non-zero-exit `retail check` failure in a single run.
- **SC-003**: Deleting, emptying-to-malformed, or untracking the manifest causes the
  gate to fail loud rather than pass, in 100% of cases (no vacuous green).
- **SC-004**: The registered rule-id set grows by exactly one (`DF1`); the wiring and
  rule-registry snapshot tests pass with the new rule and would fail closed if the rule
  were registered-but-uncounted.
- **SC-005**: The shipped manifest reconciles to zero findings against the real
  repository, so the feature ships green and the gate is meaningful from day one.
- **SC-006**: No F016 / F031-F033 runtime artifact is introduced (verifiable by
  inspection: the only new code is the DF1 rule + manifest + wiring/snapshot updates).

## Assumptions

- The unambiguous implementation template is SC1
  (`src/retail/rules/status_claims.py` + `docs/quality/status-claims.yaml` +
  the expected-id set in `tests/unit/test_rules_wiring.py`); DF1 mirrors its
  fail-closed-both-directions shape, its lazy-`import yaml`, its anchor-presence
  discipline, and its categorical (no-score) posture, applied to parked-on edges
  instead of prose status claims.
- F016 is a verified-real, verified-parked shared blocker (named across ~15 roadmap
  lines; gated by hard rule #6) with named dependents pbi-tools extract, L3 new
  operators, and F031-F033. These are the candidate v1 edges; the precise v1 edge
  inventory is a judgment call recorded in Clarifications.
- Real tracked evidence files exist to cite for the candidate edges -- e.g.
  `docs/superpowers/specs/2026-06-26-pbi-tools-extract-spike-deferred.md`,
  `docs/superpowers/specs/2026-06-26-l3-new-operators-deferred.md`, and the
  F031-F033 specs (`specs/025-adapter-maintenance-policy/spec.md`,
  `specs/026-adapter-compatibility-matrix/spec.md`,
  `specs/027-release-maturity-management/spec.md`).
- The known G6-wiring-latent-gap (40 raw `@register` occurrences vs 37 expected ids)
  is pre-existing and out of scope to fix here; this spec adds exactly one new expected
  id and relies on the set-length-derived count plus the rule-registry snapshot test,
  never a hard-coded number.
- `yaml` (PyYAML) is already an available dev/optional dependency used by SC1's lazy
  import; DF1 reuses the same pattern and adds no new runtime dependency to the
  stdlib-only core chain.

## Dependencies

- Existing central rule registry and rule-context (read-only `tracked_files` +
  `repo_root`) seams that every rule plugs into.
- Existing wiring test (expected-id set) and rule-registry snapshot / manifest
  regeneration (`retail manifest`) machinery.
- Committed roadmap text (`docs/roadmap/roadmap.md`) and the tracked deferred-spec/spec
  files cited as edge evidence (read-only).

## Clarifications

<!--
  Recorded in the clarify stage. Principle-V carve-out questions (grain/uniqueness,
  PII publish-safety, business rollup/segment, product identity) are NOT answered here
  by the workflow; if any arises it is recorded and reserved for the named human. None
  arose for this spec.
-->

### Session 2026-06-30

Advisor-resolved ambiguities (recorded for the human ratify gate). Each is an
engineering/posture call within delegated authority; none is a Principle-V carve-out.

- **Q1 -- DF1 severity: ERROR or WARNING?** Resolved: **ERROR**. A nonexistent
  blocker, missing evidence, absent anchor, or parked-but-shipped contradiction is a
  proven false statement of fact in committed governance docs, not a suspect pattern.
  ERROR matches the SC1 sibling exactly and is the defensible Principle-VIII posture
  for a proven contradiction. Reversible: easy (one severity constant). Folded into
  FR-015.

- **Q2 -- How is a "parked-but-shipped" contradiction detected without executing
  anything?** Resolved: each edge MAY declare an OPTIONAL `shipped_when_tracked`
  artifact path; if that path is present in the tracked-file set, the target has
  shipped and the still-asserted park is contradicted (DF1 ERROR). This is the
  static, tracked-file-presence analog of SC1's `planned`-but-now-tracked stale
  marker. An edge that omits `shipped_when_tracked` makes a park assertion with no
  machine-checkable ship-signal yet and is reconciled only on blocker/evidence/anchor
  presence. This keeps the criterion categorical and read-only (no execution, no
  score). Reversible: easy (manifest field + one branch). Folded into FR-007.

- **Q3 -- Which parked-on edges are in scope for v1?** Resolved: the F016 bottleneck
  cluster only -- the edges whose evidence is already tracked: pbi-tools extract
  (`docs/superpowers/specs/2026-06-26-pbi-tools-extract-spike-deferred.md`), L3 new
  operators (`docs/superpowers/specs/2026-06-26-l3-new-operators-deferred.md`), and
  F031-F033 (`specs/025-adapter-maintenance-policy/spec.md`,
  `specs/026-adapter-compatibility-matrix/spec.md`,
  `specs/027-release-maturity-management/spec.md`). The F034 built-page edge (a human
  Desktop action, not a deferred-spec blocker) is EXCLUDED from v1 -- it is a different
  blocker class (human action, not F016) and would muddy the generic "parked on a
  shared deferred blocker" semantics. v1 = F016 -> {pbi-tools, L3-ops, F031, F032,
  F033}, all citing tracked evidence so the shipped manifest reconciles clean (SC-005).
  Reversible: easy (manifest entries are additive). Recorded; no FR change beyond
  Assumptions.

- **Q4 -- Posture for a present-but-empty manifest (zero edges)?** Resolved: a
  present, well-formed manifest with an empty edge list passes CLEAN (zero findings),
  matching SC1's precedent that a present, well-formed manifest with no entries is
  honest "nothing declared yet," not a defect. A MISSING/untracked/malformed manifest
  still fails loud (FR-004). This keeps the fail-loud surface on structural breakage,
  not on emptiness. Reversible: easy (one guard). Consistent with FR-004; clarified in
  the Edge Cases note.

- **Q5 -- Does adding DF1 + its manifest require a constitution amendment / new ADR,
  and does DF1 advance a readiness stage?** Resolved: **No amendment, no new ADR, no
  stage advance.** DF1 is a within-posture addition exactly as SC1 was under spec 050:
  it adds one enforced static integrity rule of the A1/A3/SC1 family without changing
  any principle text, gate definition, or the seven-stage spine. Principle VIII already
  authorizes new static ERROR rules; the rule inventory is tracked by the
  set-length-derived wiring count + the rule-registry snapshot, which this change
  updates. DF1 advances NO readiness stage -- it is a governance-hygiene rule outside
  the stage model (the idea-bank item has no roadmap F-number; whether it later earns
  an F-row is the bank's own IL1 question, resolved as a no-F-row ruling below).
  Reversible: n/a (a no-op decision). Recorded.

### Principle-V carve-out (none arose)

- None identified. DF1 reconciles roadmap/feature dependency edges against tracked
  files; it computes no grain/uniqueness key, publishes no PII-bearing data, performs
  no business rollup/segmentation, and resolves no product identity. No grain/PII/
  rollup/identity question arose at specify or clarify time.

### Resolved at the ratify gate (recorded ruling)

- **Roadmap F-number / stage placement (IL1)** -- RESOLVED: ships as a
  **stage-independent integrity rule** of the A1/A3/SC1 family, with **no roadmap
  F-row** and no readiness-stage advance. Ruled by the advisor under the recorded
  per-spec override (see the Ratification note in the front-matter). Whether any
  idea-bank rule later earns an F-row is precisely the bank's own IL1
  idea-bank-to-roadmap hard-link question (a separate queued idea); DF1 does not
  pre-empt it. Assigning an F-row remains an additive, non-blocking follow-up, not a
  precondition for this rule. No Principle-V carve-out arose.
