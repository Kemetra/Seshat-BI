# Feature Specification: Shared-Checklist Fork Detector

**Feature Branch**: `086-shared-checklist-fork`

**Created**: 2026-07-04

**Status**: Ratified (Ahmed Shaaban, 2026-07-04) -- fork=distinct, id=SF1, agent authorized to scaffold the spine shape transcribing the distinct ruling

**Input**: User description: "Shared-Checklist Fork Detector" -- idea I3 from docs/roadmap/idea-backlog.md (CONSIDER / HORIZON). As more cross-layer checklists appear under `skills/**/checklists/`, two skills can end up carrying the SAME-basename checklist that has silently diverged (a fork). Nothing declares which same-basename files are intentionally shared (must stay identical) vs intentionally distinct (per-layer specialization) -- so a fork cannot be distinguished from drift.

## Context (grounded facts, verified 2026-07-04)

- **The glob target exists**: 17 checklist files under `skills/**/checklists/*.md`
  (verified via `git ls-files` on the branch) across `bi-bigdata-knowledge`,
  `bi-python-knowledge`, `bi-dax-knowledge`, `bi-sql-knowledge`,
  `retail-kpi-knowledge`.
- **Exactly ONE same-basename collision exists today**: `aggregation-grain-checklist.md`
  appears in BOTH `skills/bi-bigdata-knowledge/checklists/` and
  `skills/bi-python-knowledge/checklists/`. (The other 15 basenames are unique;
  15 unique + this 2-copy pair = 17 files.)
- **That collision is a VERIFIED DIVERGENT FORK**: the two files have different
  SHA-256 hashes (`9fd3507a...` vs `9789c295...`) and different content -- one is
  "Aggregation / Grain Checklist (at scale)" for the distributed route, the other
  "Aggregation / Grain Checklist" for the groupby/python route. Neither
  cross-references the other.
- **The reviewers repeatedly cite this exact fork** as the live target and note
  I3 keeps I2's "reference the spine, don't copy" discipline honest as more
  cross-layer checklists appear.
- **THE CENTRAL UNRESOLVED QUESTION (an owner judgment call)**: is this divergence
  INTENTIONAL (two legitimately-different per-layer checklists that happen to share
  a basename -> declared DISTINCT) or ACCIDENTAL DRIFT (they were meant to stay in
  sync -> declared SHARED, and the drift is a defect to fix)? The rule CANNOT
  decide this. Only a named human can. That decision is the content of the
  `docs/quality/shared-spine.yaml` manifest, which does NOT yet exist.
- I3 is git-verified OPEN as of 2026-07-04 (no shipping commit).

## The owner-authored precondition (Principle V -- the agent must NOT fabricate it)

I3 cannot land until a human authors `docs/quality/shared-spine.yaml` declaring,
for each cross-layer basename, whether it is `shared` (all copies MUST be
byte-identical) or `distinct` (copies MAY differ; the collision is intentional).
Authoring that manifest is a JUDGMENT the rule exists to enforce, not one the
agent may make -- writing it would resolve a human's ambiguity (grain/identity/
per-layer-scope call) and self-supply the very contract the gate checks. This spec
DEFINES the rule and the manifest SHAPE; the owner supplies the manifest CONTENT.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fail on an UNDECLARED same-basename collision (Priority: P1)

As the `retail check` gate, I glob `skills/**/checklists/*.md`, group by basename,
and for any basename appearing in 2+ skills that is NOT declared in
`docs/quality/shared-spine.yaml`, I emit an ERROR -- so a new cross-layer
collision cannot appear without a human explicitly ruling it shared or distinct.

**Why this priority**: This is the core "fork detector" value and the MVP. It
forces every same-basename collision to be a DECLARED decision, which is exactly
the I2 "reference the spine, don't copy" discipline made machine-checked. It is
shippable and valuable on its own.

**Independent Test**: Add a fixture with two same-basename checklists absent from
the manifest; assert one ERROR naming the basename + both skill paths.

**Acceptance Scenarios**:

1. **Given** a basename in 2+ skills with NO shared-spine entry, **When** the rule
   runs, **Then** it emits one ERROR naming the basename and every path.
2. **Given** every collision basename is declared, **When** the rule runs, **Then**
   no undeclared-collision Finding.
3. **Given** a basename appears in exactly one skill, **When** the rule runs,
   **Then** no Finding (a unique basename is not a collision).

### User Story 2 - Enforce a DECLARED-SHARED basename stays byte-identical (Priority: P2)

As the gate, for a basename the manifest declares `shared`, I compare the SHA-256
of every copy and emit an ERROR if any two differ -- so a "must stay in sync"
checklist that drifts is caught.

**Why this priority**: A `shared` declaration is only meaningful if drift from it
fails. This is the enforcement half of the manifest for the sync-required case.

**Independent Test**: Declare a basename `shared`, provide two copies with
different content; assert one ERROR naming the basename and the two hashes.

**Acceptance Scenarios**:

1. **Given** a `shared` basename whose copies are byte-identical, **When** the rule
   runs, **Then** no Finding.
2. **Given** a `shared` basename whose copies differ, **When** the rule runs,
   **Then** one ERROR naming the basename and the divergent paths/hashes.

### User Story 3 - Allow a DECLARED-DISTINCT basename to differ (Priority: P3)

As the gate, for a basename the manifest declares `distinct`, I allow the copies to
differ (the collision is intentional per-layer specialization) and emit no
Finding -- so the aggregation-grain-checklist fork, IF the owner rules it
intentional, passes cleanly.

**Why this priority**: Without this, the rule would force merging two legitimately
different per-layer checklists. It is the escape valve that makes `distinct` a
real, honest option -- but only a human may set it.

**Independent Test**: Declare a basename `distinct`, provide two differing copies;
assert no Finding. Then remove the declaration; assert the US1 undeclared ERROR.

**Acceptance Scenarios**:

1. **Given** a `distinct` basename with differing copies, **When** the rule runs,
   **Then** no Finding.
2. **Given** a `distinct` basename whose copies became identical, **When** the rule
   runs, **Then** a WARNING (a `distinct` declaration is now moot -- surface it,
   do not silently pass) -- final severity confirmed at clarify.

### Edge Cases

- **A declared basename no longer collides** (a copy was deleted, only one remains):
  the manifest entry is stale -> WARNING, so the manifest cannot rot silently.
- **The manifest declares a basename that does not exist at all**: stale entry ->
  WARNING.
- **The manifest itself is missing/malformed**: ERROR (the gate has no contract to
  check against) -- fail-closed, never skip.
- **Three+ copies of one basename**: US2 shared = ALL identical; US1 undeclared
  fires once naming all paths.
- **The rule module and its fixtures under tests/**: exempt from the glob (reuse
  the existing is_test_path exemption pattern), so fixtures never self-trip.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The rule MUST be a single `@register`ed static rule, stdlib-only
  (`hashlib`, `pathlib`, `re`), reading only committed files via
  `ctx.tracked_files` -- never the live filesystem, never a DB, never executing.
- **FR-002**: The rule MUST glob `skills/**/checklists/*.md`, group by basename,
  and identify basenames appearing in 2+ skill directories (collisions).
- **FR-003**: The rule MUST read `docs/quality/shared-spine.yaml` declaring each
  collision basename as `shared` or `distinct`. The manifest is HUMAN-AUTHORED;
  the rule NEVER writes or generates it (Principle V).
- **FR-004**: An undeclared collision MUST be a fail-closed ERROR naming the
  basename and every colliding path (US1).
- **FR-005**: A `shared` basename whose copies are not byte-identical MUST be an
  ERROR naming the basename and the divergent paths + hashes (US2).
- **FR-006**: A `distinct` basename MUST allow differing copies (no Finding); if
  its copies became identical, a WARNING (the declaration is moot) (US3).
- **FR-007**: A stale manifest entry (declared basename no longer collides / does
  not exist) MUST be a WARNING (no silent rot).
- **FR-008**: A missing/unparseable `docs/quality/shared-spine.yaml` MUST be an
  ERROR (fail-closed -- no contract, no pass).
- **FR-008b**: A well-formed YAML entry whose VALUE is not exactly `shared` or
  `distinct` (e.g. a typo `shred`) MUST be an ERROR naming the basename and the bad
  value (adversarial review MEDIUM: a human-authored YAML will hit typos; an
  unrecognized enum must never be treated as "declared").
- **FR-009**: The rule MUST exempt test fixtures from the glob (existing
  is_test_path pattern), so its own good/bad corpus never self-trips.
- **FR-010**: The rule MUST NOT emit any numeric confidence/health score (hard
  rule #9); output is categorical Findings only.
- **FR-011**: The rule MUST be wired across ALL required places so `@register`
  fires: (a) module added to `src/retail/rules/__init__.py` import tuple + __all__
  (the ONLY step that makes it discoverable -- no autodiscovery; PRINTED by
  scaffold, applied by hand), (b) EXPECTED_RULE_IDS membership,
  (c) glossary rules-table row, (d) rules-manifest.json, (e) severity-posture; and
  bump the rule-count claim (`docs/quality/rule-count-claims.yaml` + the glossary
  "Currently N rules" anchor) in the same commit. `all_rules()` MUST contain the
  new id post-wiring; `tests/unit/test_wiring_meta_gate.py` +
  `tests/unit/test_rule_count_claims.py` stay green.
- **FR-012**: The rule MUST ship with an adversarial good/bad fixture corpus and a
  fail-closed test asserting exact locator + severity + count, mirroring
  `tests/unit/test_design_*.py`.

### Key Entities *(include if feature involves data)*

- **ChecklistFile**: `(basename, skill_dir, path, sha256)` for one checklist under
  `skills/**/checklists/`.
- **SpineDeclaration**: a `docs/quality/shared-spine.yaml` entry
  `{basename: shared|distinct}` -- HUMAN-AUTHORED, the contract the rule enforces.
- **ForkFinding**: `Finding(rule_id, severity, message, locator)` for an undeclared
  collision, a shared-drift, a moot-distinct, a stale entry, or a missing manifest.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Once the owner authors `docs/quality/shared-spine.yaml` covering the
  one existing collision (`aggregation-grain-checklist.md`, ruled shared OR
  distinct), the rule produces ZERO ERROR Findings on the current tree.
- **SC-002**: Adding a new same-basename checklist in a second skill WITHOUT a
  spine entry causes the rule to ERROR (mutation-verified).
- **SC-003**: Declaring a basename `shared` and letting two copies drift causes an
  ERROR; declaring it `distinct` lets them differ with no Finding.
- **SC-004**: The rule adds no numeric score and never writes the manifest or any
  checklist (verified by test + review).
- **SC-005**: The wiring + rule-count lockstep stays green after the rule lands
  (`test_wiring_meta_gate.py` + `test_rule_count_claims.py` pass; `all_rules()`
  contains the new id).

## Assumptions

- **The owner authors the manifest (BLOCKING, Principle V)**: `docs/quality/shared-spine.yaml`
  and the ruling on `aggregation-grain-checklist.md` (shared vs distinct) are
  HUMAN work. The agent supplies the manifest SHAPE and an EMPTY/example scaffold
  ONLY at the owner's instruction; it never rules the existing fork. This is the
  central [OWNER SEAM] on the ratify ledger -- without it the rule has no contract
  and cannot land green.
- **Severity of a moot `distinct` / stale entry**: assumed WARNING (surface, don't
  block); undeclared-collision, shared-drift, and missing-manifest are ERROR.
  Confirmed at clarify. Observed-not-declared severity (ratified 044): severity is
  emitted per branch, not declared on `@register`.
- **Glob scope**: exactly `skills/**/checklists/*.md`. `.claude/skills/**` and
  non-checklist files are out of scope for v1 (YAGNI); extending scope is a future
  spec.
- **Value today is future-proofing**: it guards ONE known collision now; its value
  grows as cross-layer checklists multiply. Reviewers correctly scored it
  HORIZON -- present-defect value is modest, drift-prevention value is real.
- **Reused mechanism**: `retail scaffold <ID>` (wiring), `@register`/`RuleContext`/
  `Finding` from `src/retail/core.py` + `src/retail/registry.py`, fixture pattern
  from `tests/unit/test_design_*.py`. Nothing new at the mechanism layer.
- **Ratification pending**: this spec STOPS at a ratify ledger; DEFINED and
  CHECKED, never approved or implemented here (Principle V).
