# Feature Specification: Scaffold-Rule Authoring Generator + Doctor

**Feature Branch**: `062-scaffold-rule-generator`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "E6. retail scaffold-rule / new-rule Authoring Generator + Doctor"

## Overview

Adding a new static governance rule to the kit today requires a rule author to
edit the same five places, by hand, every time -- a ceremony that is written
down only in a private memory note, never in a machine-usable form. When one of
the five places is missed, the rule is silently under-governed: it can be
registered and enforced yet be invisible in the human-facing catalog. This has
already happened in the codebase (a shipped rule that is registered, in the
expected-id set, and in the generated manifest, yet has no rule-family row in the
prose glossary), which proves the ceremony genuinely drifts.

This feature adds an authoring helper with two modes:

- **Scaffold (author) mode** -- given a new rule id and title, WRITE the
  mechanical boilerplate a new rule needs (a stub rule module, a matching failing
  test stub, and an insertion of the new id into the expected-id source-of-truth
  set), and PRINT -- never run -- the follow-up commands and prose a human must
  execute and paste for the remaining places.
- **Doctor (verify) mode** -- given an existing rule id (or a sweep of all
  registered ids), READ the five places and report, per place, whether that id is
  present or drifted. Read-only: it reports drift, it never repairs it.

The helper is a thin author over the existing hand-written shape. It is not an
authority: whether a rule is correctly wired is still decided by the existing
test suite and the gate exit code, not by this helper.

## Clarifications

### Session 2026-07-02

- Q: Does Doctor verify one id given on the command line, or sweep every
  registered rule id? -> A: Both. A rule id argument verifies that one id; with no
  id argument, Doctor sweeps every registered rule. The drift that motivates this
  feature (a rule missing from the glossary) is only discoverable by a sweep, so
  the sweep is the default value driver; single-id is the fast targeted check.
- Q: May the generator edit the prose glossary at all, or is prose strictly
  print-only? -> A: Prose is strictly PRINT-only. The generator MUST NEVER write to
  the glossary file. Rule-family prose carries human editorial judgment (wording,
  ordering, which family a rule belongs to); auto-editing it would fabricate
  intent the author owns (Principle V). The generator prints a suggested row for a
  human to paste.
- Q: Is the list of "five wiring places" allowed to be hardcoded in the helper,
  or must it be derived/introspectable? -> A: The five-place list is authored as an
  explicit, in-code declaration in this feature, BUT it MUST itself be covered by
  a test that fails if the real repo grows a sixth place the list does not name
  (so the list cannot silently drift the way the ceremony it documents already
  did). Deriving the list dynamically from the repo is out of scope for this first
  step (YAGNI); the declared-plus-guarded list is the seam.
- Q: Do the two golden regenerations (the rule-inventory manifest and the
  severity-posture record) get run by the generator, or only printed? -> A:
  PRINT-only. The generator prints the exact regen command for each; a human runs
  it. Running a golden regeneration is a build action that rewrites a
  source-of-truth record; the helper stays a static author (Principle VIII) and
  never mutates a golden record.
- Q: When the generator writes the stub rule and test, must the placeholder rule
  logic be generic, or may it seed an example rule body? -> A: Strictly generic.
  The stub MUST carry zero worked-example / domain specifics (no example table
  names, column names, billing codes, or report paths). It emits a minimal
  placeholder that a human replaces with real logic (Principle VII).

### Deferred to human (Principle V -- the helper MUST NOT decide these)

- **DEC-1 (rule intent)**: The helper MUST NOT invent what a new rule checks or
  what its title/family means. The author supplies the id, title, and real logic;
  the helper only writes the mechanical shell around them. Fabricating rule intent
  is a judgment call the helper is forbidden to make.
- **DEC-2 (whether a rule "passes" its wiring)**: The helper's Doctor mode reports
  presence/absence per place; it MUST NOT declare a rule "fully wired and
  approved." Whether the wiring is correct is disposed of by the existing test
  suite and gate exit code, never self-granted by this helper (Principle I).
- **DEC-3 (ledger id + roadmap placement)**: Whether this feature takes an
  idea-bank sequence id and whether it advances any readiness stage is a human
  call recorded in the roadmap/backlog, not decided in this spec. This feature is
  DX/governance tooling and is authored as advancing NO readiness stage.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Author scaffolds a new rule's boilerplate (Priority: P1)

A rule author has decided a new governance rule is needed and knows its id and
one-line title. Instead of hand-editing five places from memory, the author runs
the scaffold helper with the id and title. The helper writes the mechanical
boilerplate it can safely author, and prints the exact remaining steps (commands
to run, prose to paste) the author must do by hand. The author is left with a
rule module they fill in with real logic and a red test that will go green once
the logic and remaining wiring are in place.

**Why this priority**: This is the core value -- collapsing a five-place,
memory-only ceremony into one command plus a printed, auditable checklist. It is
the feature's reason to exist and is independently demonstrable on its own.

**Independent Test**: Run the scaffold helper for a throwaway rule id in a
scratch copy of the repo; confirm a stub module and a failing test stub are
written, the id is inserted into the expected-id set, and the two regen commands
plus a glossary row are PRINTED (not applied). Delete the scratch changes.

**Acceptance Scenarios**:

1. **Given** a new rule id and title that are not yet registered, **When** the
   author runs the scaffold helper, **Then** a stub rule module and a matching
   failing test stub are written with generic placeholder logic, the new id is
   inserted into the expected-id source-of-truth set, and the helper prints the
   two golden-regen commands and a suggested glossary row -- and it writes nothing
   to the glossary and runs no regeneration.
2. **Given** a rule id that is ALREADY registered, **When** the author runs the
   scaffold helper with that id, **Then** the helper refuses to overwrite,
   reports the id already exists, and makes no changes.
3. **Given** the scaffold helper has just run for a new id, **When** the author
   runs the existing test suite without filling in the stub, **Then** the new
   stub test fails (red), proving the scaffold left an honest not-yet-done state
   rather than a false green.

---

### User Story 2 - Author (or reviewer) runs Doctor to find wiring drift (Priority: P2)

A reviewer suspects, or wants to prove, that every registered rule is wired
across all five places. They run the Doctor in sweep mode. The Doctor reads each
of the five places and reports, per rule id, which places it is present in and
which it is missing from -- surfacing exactly the kind of drift that has already
occurred (a registered rule with no glossary row). They can also point Doctor at
a single id for a fast targeted check.

**Why this priority**: This is the "Doctor" half named in the feature. It is the
only automated check that covers all five places at once (the existing suite
covers only the expected-id place; the glossary place has no automated check at
all). It depends on the five-place model that Story 1 establishes, so it is P2.

**Independent Test**: Run Doctor in sweep mode against the current repo; confirm
it reports the known drifted rule as missing from the glossary place and present
in the others, and reports fully-wired rules as present in all five. Run Doctor
for a single id and confirm the same per-place verdict for just that id.

**Acceptance Scenarios**:

1. **Given** a rule that is registered, in the expected-id set, and in the
   generated records but has NO glossary row, **When** Doctor runs in sweep mode,
   **Then** Doctor reports that id as present in four places and MISSING from the
   glossary place, and does not modify any file.
2. **Given** a fully-wired rule id passed as an argument, **When** Doctor runs for
   that single id, **Then** Doctor reports it present in all five places.
3. **Given** an id that is not registered at all, **When** Doctor runs for that
   id, **Then** Doctor reports it as absent everywhere (or as an unknown id),
   without error-exiting the way a real defect would -- Doctor is a report, and
   its exit-code contract is defined explicitly (see FR-014).

---

### User Story 3 - Generator's own place-list is guarded against drift (Priority: P3)

The five-place list the helper encodes is itself a hardcoded artifact that could
drift from the real repo the same way the ceremony it documents already did. A
maintainer who later adds a sixth wiring place should be forced to update the
helper's list, not silently leave it stale.

**Why this priority**: This closes the meta-risk the idea bank flagged (a
hardcoded list that will itself drift). It is a guardrail on the feature's own
integrity rather than a user-facing capability, so it is P3.

**Independent Test**: A test asserts the helper's declared five-place list
matches the set of wiring places the repo actually has; deliberately removing an
entry from the declared list makes the test fail.

**Acceptance Scenarios**:

1. **Given** the helper's declared list of wiring places, **When** the guard test
   runs, **Then** it fails if the declared list is missing a place the repo
   actually has, or names a place the repo does not have.

---

### Edge Cases

- **Malformed / non-conforming id or title**: an id that does not match the
  expected id shape, or an empty title, is rejected with a clear message before
  anything is written.
- **Id already registered** (Story 1 scenario 2): refuse and report; never
  overwrite an existing module or duplicate an id.
- **Partial prior scaffold**: if a stub module already exists for the id but the
  id is not yet registered, the helper refuses rather than clobbering, and reports
  what it found.
- **Doctor on a repo where a golden record is stale**: Doctor READS the golden
  record as-is and reports what it finds; it never regenerates or "fixes" the
  record (that is a human-run command). If a golden record file is absent or
  unreadable, Doctor reports that place as unverifiable rather than crashing.
- **Windows path length / encoding**: authored files use short repo-relative
  paths and are written UTF-8 without BOM (repo hard rules).
- **Concurrent / re-run**: re-running scaffold for the same new id after a
  successful first run hits the "already registered" refusal (idempotent-safe: it
  will not double-insert).

## Requirements *(mandatory)*

### Functional Requirements

**Scaffold (author) mode**

- **FR-001**: The system MUST provide an authoring command that takes a new rule
  id and a one-line title as input.
- **FR-002**: The system MUST write a new stub rule module that registers the
  given id and title through the existing rule-registration mechanism, containing
  generic placeholder logic only.
- **FR-003**: The generated stub rule and its test MUST contain zero
  worked-example / domain-specific content (no example table names, column names,
  codes, or report paths) -- generic scaffolding only.
- **FR-004**: The system MUST write a matching test stub that FAILS until a human
  fills in the real rule logic (honest red state; no false green).
- **FR-005**: The system MUST insert the new rule id into the expected-id
  source-of-truth set used by the wiring test.
- **FR-006**: The system MUST PRINT, and MUST NOT run, the command that
  regenerates the rule-inventory golden record.
- **FR-007**: The system MUST PRINT, and MUST NOT run, the command that
  regenerates the severity-posture golden record.
- **FR-008**: The system MUST PRINT a suggested rule-family row for the human to
  paste into the prose glossary, and MUST NEVER write to the glossary file.
- **FR-009**: The system MUST refuse to act, and report clearly, when the given id
  is already registered or when writing would overwrite an existing stub module;
  it MUST make no changes in that case.
- **FR-010**: The system MUST validate the id and title at the boundary and reject
  malformed input with a clear message before writing anything.

**Doctor (verify) mode**

- **FR-011**: The system MUST provide a read-only Doctor mode that, given a rule
  id, reports for each of the five wiring places whether that id is present or
  missing.
- **FR-012**: The Doctor MUST also support a sweep over every registered rule id,
  reporting per-id, per-place presence -- this is the default when no id is given.
- **FR-013**: The Doctor MUST NOT modify, repair, or regenerate any file,
  including golden records and the glossary; it only reads and reports.
- **FR-014**: The Doctor MUST define an explicit process-exit contract:
  reporting is its purpose, and its exit code semantics (e.g., non-zero when drift
  is found vs always-zero informational) MUST be stated so a human or CI can rely
  on it deterministically.
- **FR-015**: If a place cannot be read (e.g., a golden record file is absent),
  the Doctor MUST report that place as unverifiable rather than crash.

**Shared / integrity**

- **FR-016**: The helper MUST be static and self-contained: no database, no
  network, no execution of the rules or the model, matching every existing
  generator in the kit (Principle VIII).
- **FR-017**: The helper's encoded list of the five wiring places MUST be covered
  by a guard test that fails if the repo grows a place the list does not name (so
  the list cannot silently drift).
- **FR-018**: The helper MUST NOT self-grant a wiring "pass" or claim a rule is
  approved; the existing test suite and gate exit code remain the authority
  (Principle I).
- **FR-019**: All files the helper writes MUST be UTF-8 without BOM, ASCII-safe,
  and use short repo-relative paths (repo hard rules, Principle IX).
- **FR-020**: The helper MUST be exposed as a subcommand alongside the existing
  governance subcommands, following the same command surface as the existing
  generators.

### Key Entities

- **Wiring place**: one of the five locations a rule must appear in to be fully
  wired -- (1) a registered rule module, (2) the module import list + public
  export list, (3) the expected-id source-of-truth set, (4) the two golden
  records (rule inventory + severity posture), (5) the rule-family prose row.
  Modeled as an explicit, guard-tested declaration.
- **Rule id + title**: the author-supplied identity of a new rule; the helper
  writes boilerplate around it but never invents its meaning.
- **Scaffold result**: the set of files WRITTEN (stub module, test stub,
  expected-id insertion) plus the set of actions PRINTED (two regen commands, one
  glossary row) -- a strict write/print split.
- **Doctor report**: a per-id, per-place presence/absence record produced
  read-only from the repo state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A rule author can produce all the mechanical boilerplate for a new
  rule with a single command invocation, replacing the five-place hand ceremony.
- **SC-002**: After scaffolding a new id and before any human fills in logic, the
  test suite is RED (the stub test fails) -- the scaffold never leaves a false
  green.
- **SC-003**: Doctor's sweep correctly identifies the already-known drifted rule
  (present in four places, missing from the glossary) with zero manual inspection.
- **SC-004**: Doctor and Scaffold make zero writes to any golden record or to the
  prose glossary (verified: the only files scaffold writes are the stub module,
  its test, and the expected-id set; Doctor writes nothing).
- **SC-005**: The helper's five-place list is guard-tested, so adding a sixth
  wiring place to the repo without updating the list fails a test.
- **SC-006**: The helper runs with no database, network, or execution dependency
  (pure static, matching the existing generators).

## Assumptions

- The five wiring places are exactly the set named in this spec; this is
  confirmed against the current repo (all five exist and are individually
  observable) and is guard-tested (FR-017) so a future sixth place cannot slip in
  unnoticed.
- The already-existing drift instance (a registered rule with no glossary row) is
  treated as a fixture-quality real example for Doctor, cited generically, not as
  a defect this feature repairs -- repairing prose is a human paste step.
- This feature advances NO readiness stage; it is DX/governance tooling. Final
  ledger id / roadmap placement is a human decision (DEC-3).
- The two golden regenerations already exist as commands in the kit; this feature
  only PRINTS them, never re-implements or runs them.
- "Generic placeholder logic" means a minimal, always-safe stub (e.g., a rule
  body that yields no findings) that a human replaces -- it carries no domain
  facts.
- Scope is the first step only (YAGNI): author the seam (a declared, guarded
  five-place model + a scaffold writer + a read-only doctor), not a dynamic
  repo-introspecting place-discovery engine.

## Out of Scope

- Auto-editing prose in the glossary (strictly print-only).
- Running the golden regenerations (strictly print-only).
- Deciding a rule's intent, logic, family, or whether its wiring "passes"
  (human/gate authority).
- Deriving the five-place list dynamically from the repo (the declared+guarded
  list is the seam; dynamic discovery is deferred).
- Any database, network, Power BI, or rule-execution behavior.
- Advancing or scoring any readiness stage.
