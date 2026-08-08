# Feature Specification: dbt evidence governance consumer

**Feature Branch**: `150-dbt-evidence-consumer`

**Created**: 2026-08-08

**Status**: draft

<!-- One of: draft | ratified | implemented | superseded (ADR 0019).
     draft       -- authored, not yet ratified by a named human
     ratified    -- a named human approved THE SPEC; record their name and the date
     implemented -- the capability exists on `main`; MUST name its artifact, e.g.
                    `**Status**: implemented -- artifact `src/seshat/foo.py``, and gets a
                    `spec-<NNN>-implemented` claim in docs/quality/status-claims.yaml
     superseded  -- replaced; name the superseding spec id
     When changing this value, move the previous text verbatim into a
     `**Status history**:` line rather than deleting it. -->

**Input**: Official-first roadmap Phase 7: connect upstream execution results to
Seshat governance evidence. Phase 4 (`specs/146-dbt-official-delegation`) placed
evidence-envelope work explicitly Out of Scope; this spec closes the one seam
that carve-out left open.

## Why this exists

Seshat already reads real dbt execution artifacts and already normalizes them
into a governance envelope. What it does not do is read that envelope back.

The chain is built up to its last link:

| Link | State on `main` | Artifact |
| --- | --- | --- |
| Official executor runs | present | `seshat dbt` invokes the real dbt executable (`src/seshat/dbt/runner.py`) |
| Native result parsed | present | `load_manifest()` / `load_run_results()` parse dbt's own `manifest.json` + `run_results.json` (`src/seshat/dbt/artifacts.py`) |
| Result proven against the accepted plan | present | `cross_check_execution()` raises `ArtifactIntegrityError` when executed nodes differ from the accepted plan |
| Thin normalization | present | `build_evidence()` returns `RunEvidence` (`src/seshat/dbt/contracts.py:324`) |
| Evidence committed | present | `write_evidence()` writes schema-validated JSON to `mappings/<table>/dbt-evidence/<invocation_id>.json` |
| **A governance surface reads it back** | **ABSENT** | **this spec** |

A repository sweep for `dbt-evidence` outside `tests/` finds exactly two
non-test consumers in `src/`: its writer (`src/seshat/dbt/evidence.py`) and
`src/seshat/reset.py`, which only deletes it. No readiness surface, evidence
pack, blocker explainer, or next-action surface reads a dbt evidence record.

The asymmetry with Dagster is the clearest statement of the gap, and it is also
the template for the fix. Dagster synthesizes its own record and that record
**is** consumed: `portfolio_watch.live_validation_state()` reads committed run
evidence and returns `verified` / `pending_live` / `stale` / `blocked` /
`uncommitted_evidence`, which `agent_next._live_validation_next_override()`
turns into a real next-action caveat. dbt parses richer, tool-native truth and
that truth reaches no reader.

The consequence is a governance blind spot in the honest direction: a governed
dbt build can fail, or be blocked, or record blocking reasons, and the agent's
next-action document does not mention it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A failed or blocked dbt build reaches the next-action surface (Priority: P1)

An agent asking for the next truthful action on a table whose governed dbt build
failed or was blocked is told so, and is told where the evidence is, instead of
being routed onward as though nothing had happened.

**Why this priority**: This is the whole delta. A recorded failure that no
surface reports is a failure nobody acts on.

**Independent Test**: Build the next-action document for a table fixture
carrying a committed dbt evidence record whose outcome is `failed`, and assert
the emitted caveat names the failure and cites the record path.

**Acceptance Scenarios**:

1. **Given** a table with a committed dbt record whose `outcome` is `failed`,
   **When** the next action is computed, **Then** the document carries a caveat
   naming the failed build and the record's relative path.
2. **Given** a record whose `outcome` is `blocked` with `blocking_reasons`,
   **When** the next action is computed, **Then** those reasons are surfaced.
3. **Given** a record whose `outcome` is `pass`, **When** the next action is
   computed, **Then** no caveat is emitted and the document is byte-identical to
   the same fixture with no dbt record present.

---

### User Story 2 - Execution success never becomes readiness (Priority: P1)

An agent reading readiness state for a table whose dbt build succeeded still
sees the recorded stage status and the outstanding named-human approval. The
dbt record informs; it never promotes.

**Why this priority**: Equal to US1. This is the risk that caused the seam to be
deferred. `RunEvidence.readiness_effect` already carries the literal
`"none; named-human approval required"`; a consumer that ignored it would turn
an executor's exit code into a governance verdict, breaching Principle V and the
readiness spine's rule that a stage's approval is a named human action the agent
cannot self-grant.

**Independent Test**: With a dbt record whose `outcome` is `pass`, assert the
table's recorded stage status and its approval requirement are identical to the
same fixture with no dbt evidence present.

**Acceptance Scenarios**:

1. **Given** a dbt record with `outcome: pass` and a stage recorded `blocked`,
   **When** readiness is projected, **Then** the stage remains `blocked`.
2. **Given** a dbt record with `outcome: pass` and an unmet approval, **When**
   the next action is computed, **Then** the approval remains outstanding.
3. **Given** any dbt record, **When** the state is classified, **Then** the
   classifier returns no readiness four-status token.

---

### User Story 3 - Unreadable or unknown evidence fails closed (Priority: P2)

A malformed, unparseable, or schema-invalid dbt evidence record produces a
visible defect caveat, not silence and not a pass.

**Why this priority**: Fail-open on an unreadable artifact is a documented
failure mode in this repository -- a degraded read that reports nothing reads as
"nothing to report".

**Independent Test**: Write a corrupt JSON file into `dbt-evidence/` and assert
the classifier returns the unreadable state and the caveat names the file.

**Acceptance Scenarios**:

1. **Given** a `dbt-evidence/<id>.json` that is not valid JSON, **When** the
   state is classified, **Then** it is `unreadable` and the file is named.
2. **Given** a record missing required envelope fields, **When** the state is
   classified, **Then** it is `unreadable` rather than partially trusted.
3. **Given** an unreadable record, **When** the state is classified, **Then**
   the result is never a success state.

---

### User Story 4 - Power BI absence is modelled truthfully (Priority: P3)

Anyone reading this spec or the resulting surface can tell that Power BI has no
execution-result seam today, and that this is a recorded architectural state
rather than an omission.

**Why this priority**: Documentary. It prevents a future reader from "fixing"
the asymmetry by inventing a Power BI normalizer for a runtime that does not
exist.

**Independent Test**: The spec and the adapter documentation state the absence
and cite the deferred capability entry.

**Acceptance Scenarios**:

1. **Given** the shipped capability manifest, **When** Power BI execution is
   inspected, **Then** it is `state: deferred` and no normalizer is added here.

## Requirements

- **FR-001**: A read-only classifier MUST read committed dbt evidence records
  from `mappings/<table>/dbt-evidence/` and return a state describing the latest
  governed build. It MUST mirror the *classifier* shape of
  `portfolio_watch.live_validation_state()` -- a pure function returning a bare
  state string. It MUST NOT mirror
  `_live_validation_next_override()`, which is a REPLACEMENT function; see
  FR-019. (Clarified 2026-08-08; corrected by adversarial review round 2.)
- **FR-002**: The next-action surface MUST surface a caveat when the classified
  state is not a clean success, naming the execution outcome, the originating
  `invocation_id`, and a relative path to the record. The caveat is emitted at
  every stage -- it is not gated to post-Gold stages -- which is safe only
  because it is additive per FR-019 and FR-020.
- **FR-003**: The caveat MUST report `blocking_reasons` when the record carries
  them.
- **FR-004**: The classifier and the caveat MUST NOT alter, upgrade, or derive
  any readiness stage status. Readiness remains owned by the recorded
  `readiness-status.yaml` and its existing authorities.
- **FR-005**: They MUST NOT satisfy, infer, or discharge any named-human
  approval.
- **FR-006**: An execution `outcome` of `pass` MUST NOT be rendered using the
  readiness vocabulary in a way that could be read as a stage verdict. The
  translation (`pass` -> `built`, `failed` -> `failed`, `blocked` -> `blocked`,
  `unavailable` -> `blocked`) MUST be defined ONCE as a public mapping in
  `src/seshat/dbt/`, and the orchestration package MUST import it from there in
  place of its private `_DBT_OUTCOME_TO_EXECUTION` copy, so the dependency runs
  orchestration -> seshat and not the reverse. (Clarified 2026-08-08.)
- **FR-007**: An absent `dbt-evidence/` directory MUST classify as an explicit
  absent state, never as success, and MUST emit no caveat -- a table that has
  never run dbt is not thereby defective.
- **FR-008**: An unreadable, non-JSON, or schema-invalid record MUST classify as
  unreadable, MUST emit a caveat, and MUST NOT classify as success.
- **FR-009**: When several records exist for a table, selection MUST be
  deterministic: lexicographic filename sort, taking the last. Records are named
  `<invocation_id>.json` and `invocation_id` is locked to
  `^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$` (`schemas/dbt-run-evidence.schema.json:37`),
  whose zero-padded timestamp prefix makes lexicographic order chronological.
  Sorting on filenames rather than parsed content means one corrupt record
  cannot prevent selection. (Clarified 2026-08-08.)
- **FR-010**: This spec MUST NOT change `RunEvidence`, its writer, or
  `schemas/dbt-run-evidence.schema.json`. It adds a reader only. (Inherited from
  `specs/146-dbt-official-delegation` FR-008.)
- **FR-011**: No new readiness state machine, execution engine, event bus, or
  second evidence envelope may be introduced.
- **FR-012**: The classifier MUST NOT open a database, invoke dbt, or execute
  any upstream tool. It reads committed artifacts only.
- **FR-013**: Reported content MUST NOT surface credentials, connection strings,
  tokens, or raw upstream logs. Records are already sanitized at write time by
  `seshat.dbt.redaction.sanitize()` and are schema-closed
  (`additionalProperties: false`), so the reader MUST NOT re-implement
  redaction. It MUST instead restrict itself to the named envelope fields in
  FR-002/FR-003 and MUST NOT echo arbitrary record content. (Clarified
  2026-08-08.)
- **FR-014**: No Power BI execution normalizer may be added; Power BI execution
  remains deferred and unconnected.
- **FR-015**: The new code MUST NOT declare an eleventh copy of `_STAGE_ORDER`.
  The constant is currently declared independently in ten modules; this spec
  does not deduplicate them (Out of Scope), but MUST NOT add to the count.
  (Clarified 2026-08-08.)
- **FR-016**: The evidence pack's documented fixed 10-section contract
  (`docs/tools/evidence-pack-generator.md`) MUST NOT be modified. No section is
  added, and `_build_section()`, `_section_blockers()`, and every existing
  section's output remain unchanged. (Clarified 2026-08-08.)
- **FR-017**: An informational dbt caveat MUST use a non-STOP prefix, mirroring
  the existing `CAUTION --` wording. `agent_next._is_stopped()` treats any
  ACTION string beginning with `STOP` as suppressing all downstream guidance.
  Under FR-019 the dbt caveat never becomes the action string, so this
  requirement is about honest wording rather than about controlling suppression:
  the caveat must not present itself as a stop it has no authority to impose.
  Conversely it MUST NOT be relied on to CREATE a stop -- a genuinely closed
  gate is the readiness spine's to declare, not this surface's. (Clarified
  2026-08-08; scope corrected by adversarial review round 2.)
- **FR-018**: The dbt caveat MUST NOT displace the existing live-validation or
  contract overrides. Their current precedence
  (`live_override or contract_override`) MUST be preserved and the dbt signal
  composed without reordering them. (Clarified 2026-08-08.)
- **FR-019**: The dbt signal MUST be additive and MUST NOT join the
  `next_override` replacement chain. `agent_next` line 871 computes
  `action = next_override or _next_allowed_action(response)`, which REPLACES the
  action string; line 862 sets `control_outcome = "next_action"` whenever
  `next_override` is not None, which feeds `stop_point`. A dbt caveat entering
  that chain would overwrite a blocked table's `STOP` sentence and suppress its
  blocked-specific stop point. The dbt signal MUST instead be appended to the
  existing additive `caveats` list (line 889). It MUST NOT modify
  `next_allowed_action`, `stop_point`, `control_outcome`, `control_stage`, or
  `forbidden_scope`. (Clarified 2026-08-08 by adversarial review round 2.)
- **FR-020**: Because the dbt signal is additive, it MUST NOT weaken any
  existing stop. For a table whose `outcome` is `stop_blocked` or
  `approval_required`, the emitted `next_allowed_action`, `stop_point`,
  `outcome`, and `forbidden_scope` MUST be byte-identical to the same fixture
  with no dbt record present. The only difference permitted anywhere in the
  document is the added `caveats` entry. (Clarified 2026-08-08.)
- **FR-021**: The classifier MUST NOT be added to `src/seshat/portfolio_watch.py`,
  which is already 1227 lines. It goes in a new sibling read-only module, so the
  change does not push an existing file further past the repository's ~800-line
  convention. (Clarified 2026-08-08.)

## Clarifications

### Session 2026-08-08

- Q: `_build_section()` emits only `pass`/`blocked` from file presence and
  cannot express a failed or corrupt record -- where should the consumer live?
  -> A: Initially a dedicated evidence-pack section. **Superseded** by the
  adversarial review below.
- Q: The adversarial plan review proved a new pack section is broken as
  specified -- `cli/commands/evidence_pack.py:21` reads `section['status']`
  unconditionally, `_section_blockers` reads `section['sources'][0]`,
  `tests/unit/test_evidence_pack.py:77` pins sections to `01`-`10`, and
  `docs/tools/evidence-pack-generator.md:79` documents a fixed 10-section
  contract. How should the spec proceed? -> A: Drop the evidence-pack section
  entirely. Mirror the shipped Dagster consumer instead: a read-only classifier
  feeding an `agent_next` caveat. No fixed contract is touched and no consumer
  breaks. The reviewer-facing pack section is deferred to a follow-on spec that
  can amend the 10-section contract on its own merits.
- Q: `_DBT_OUTCOME_TO_EXECUTION` lives in the orchestration package, which
  imports from `seshat`; reuse would invert the dependency. -> A: Define the
  mapping once as a public symbol in `src/seshat/dbt/` and have orchestration
  import it, correcting the direction and removing the private duplicate.
  Verified safe: `orchestration/dagster/pyproject.toml` already depends on the
  root package, and `src/seshat` imports nothing from `tower_bi_orchestration`.
- Q: How is the record selected when several exist? -> A: Lexicographic filename
  sort on the timestamp-prefixed `invocation_id`, tolerant of a corrupt sibling.
- Q: Is read-time redaction required? -> A: No; records are sanitized at write
  time and schema-closed. The reader restricts itself to named envelope fields.
- Q: Adversarial review round 2 -- how exactly does the dbt signal compose into
  the next-action document? `action = next_override or _next_allowed_action(...)`
  REPLACES the action string, and `control_outcome` flips to `next_action`
  whenever an override fires, which feeds `stop_point`. The two existing
  overrides are safe only because both are gated to `terminal_pass or
  post_gold_stage`; FR-002 gated the dbt caveat on nothing. -> A: The dbt signal
  is ADDITIVE ONLY. It appends to the existing `caveats` list and never joins
  the `next_override` chain, so it cannot displace a blocked table's `STOP`
  sentence or suppress its stop point. Recorded as FR-019/FR-020; FR-001 and
  FR-017 corrected accordingly. This defect runs opposite to the one originally
  guarded against: not execution granting readiness, but execution softening a
  stop.
- Q: Where does the classifier live? `portfolio_watch.py` is 1227 lines. -> A: A
  new sibling read-only module (FR-021).

## Success Criteria

- A table whose governed dbt build failed or was blocked produces a next-action
  caveat naming the outcome, the invocation, and the record path.
- A dbt record reporting execution success leaves every readiness status, every
  outstanding approval, and the whole next-action document exactly as recorded.
- A corrupt dbt record produces a visible unreadable-evidence caveat.
- The dbt evidence envelope, its schema, and its writer are unchanged.
- The evidence pack's 10-section contract and output are unchanged.
- Power BI gains no execution-result normalizer and no new write capability.

## Out of Scope

Any change to the dbt evidence schema, envelope, or writer. Any change to the
evidence pack, its sections, its consumers, or its documented contract -- the
reviewer-facing surface is deferred to a follow-on spec. Any new execution,
refresh, query, or publish capability for Power BI or Fabric. Any Dagster
normalization change -- its consumer already exists. Live database execution.
dbt activation (`docs/operations/dbt-activation-status.yaml` remains as
recorded). Deduplication of the pre-existing `_STAGE_ORDER` copies. Roadmap
Phase 8 and later. Push, PR, merge, or publication.

## Assumptions

- The dbt evidence record shape is stable as shipped; this spec reads the
  envelope fields it already guarantees.
- Reading committed evidence requires no optional dependency, so the static
  core's driver-free import path is unaffected.
- dbt activation remaining `blocked` does not prevent this reader from being
  correct: the reader's contract is over the record, not over a live run.
