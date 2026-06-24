# Feature Specification: source drift detector -- shape/semantic drift as Source-Ready evidence + blockers

**Feature Branch**: `015-source-drift-detector` (work on the worktree branch per session convention; located via `.specify/feature.json`)

**Created**: 2026-06-24

**Status**: Draft

**Input**: "Roadmap F014 (Layer 2 Source Intelligence, 'Later' tier). Advances the Source Ready stage. Detect when a source's SHAPE or semantics DRIFT from its recorded source profile (new/removed/retyped columns, distribution shift), surfaced as readiness EVIDENCE + blockers that can move a table's Source Ready status to warning/blocked. 'Later' tier: spec the DESIGN (docs/templates/checklist) per hard rule #8; do not assume an ingestion runtime exists (scope discipline). Drift judgment that affects grain/identity/PII is a Principle-V human seam. Generic (#7). No fake confidence -- measured drift signal + blockers, not a score (#9)."

## Naming note (numbering vs roadmap)

This feature IS the roadmap's **F014 "Source Drift Detector"** (Layer 2 Source
Intelligence, "Later" tier, advances **Source Ready**). It is filed under spec
directory `015-source-drift-detector/` to avoid a numbering collision between
parallel worktrees; the roadmap's own F015 slot ("Reconciliation Ledger",
Gold Ready) is a DIFFERENT, later feature and is NOT specified here. All
roadmap/feature references below mean the Source Drift Detector. When this
slice's docs land, the roadmap row may be cross-referenced as
"F014 (spec 015)".

## Why this feature exists

Source Ready (stage 1) certifies a source ONCE: a `source-profile.md` records the
shape, the candidate grain/PK proof, the returns rule, and the PROPOSED semantics
that a human confirmed (see `docs/readiness/source-ready.md`). But a source is a
moving target. The same `<schema>.<table>` re-landed next month can gain a column,
drop a column, retype a column from `TEXT` to something narrower, shift its
missingness, fan out a previously-1:1 code/label pair, or change which billing
code marks a return. None of that is visible to the one-time profile -- yet every
one of those changes can silently invalidate a downstream mapping, silver cast, or
gold star that was built against the OLD shape.

The `source-profile.md` template already names the symptom in one narrow place:
its **"Cross-file schema drift"** semantic check (a column-order change across
folded source files that misaligns values). This feature **generalizes that idea
across time/versions**: it makes "the source no longer matches its recorded
profile" a first-class, measurable readiness signal -- surfaced as **evidence +
blockers** that can move a table's Source Ready status from `pass` to `warning` or
`blocked`, exactly like the rest of the spine.

It exists because re-certifying drift by re-reading two prose profiles by eye does
not scale and is not auditable. A drift report is the artifact that makes "has this
source changed in a way that breaks my build?" answerable with numbers, not vibes.

## What "drift" means here (the taxonomy this feature defines)

Drift = a measured difference between a **baseline source profile** (the committed
`source-profile.md` that earned `pass`) and an **observed re-profile** of the same
`<schema>.<table>` taken later. The taxonomy this slice defines, each as a
recordable drift CLASS with its own severity default:

| Class | What changed | Default severity | Why |
|-------|--------------|------------------|-----|
| **Column added** | a column present now, absent in baseline | `warning` | new signal may be wanted, may be noise; never auto-adopted |
| **Column removed** | a baseline column now absent | `blocked` | a mapping/silver cast may reference it; build breaks |
| **Column retyped** | landed type differs (e.g. now parses as numeric where baseline was free TEXT, or vice versa) | `warning` (auto) / `blocked` (if it touches a key/measure) | a cast may now lose data or fail |
| **Missingness shift** | `'' OR NULL` rate moved beyond a recorded tolerance | `warning` | population change can break grain or measure totals |
| **Cardinality shift** | distinct count moved beyond tolerance (e.g. a near-constant column fanned out) | `warning` | drop/keep + dimension-build decisions hinge on this |
| **Grain/PK drift** | the recorded candidate PK is no longer unique on the data, OR the row-vs-entity ratio moved | `blocked` | **Principle-V human seam** -- grain is never auto-rejudged |
| **Returns-rule drift** | the authoritative returns column changed population/meaning, or disappeared | `blocked` | **Principle-V human seam** -- returns identity is a judgment call |
| **Semantic-pair drift** | a baseline 1:1 code/label (or id->name) pair is no longer 1:1 on the data | `warning` (auto) / `blocked` (if it underpins identity) | dimension build + identity may be wrong |
| **PII surface drift** | a column now appears that looks like PII, or a dropped-PII column reappeared | `blocked` | **Principle-V human seam** -- PII publish-safety is never auto-decided |

Two firm rules over the whole taxonomy:

1. **No fake confidence (#9).** A drift report carries the **measured signal**
   (the before/after numbers and the class) plus a **status** + **blocking
   reasons**, never a single drift "score" that reads as confidence. A numeric
   magnitude per class (e.g. "missingness 3.1% -> 11.7%") is a MEASUREMENT and is
   allowed; a rolled-up "drift score: 0.62" is forbidden until scoring rules are
   defined (`docs/readiness/readiness-model.md`).
2. **Drift that touches grain, identity, returns, or PII is a Principle-V human
   seam.** The detector MEASURES and CLASSIFIES it and raises a blocker; it does
   NOT re-decide grain, re-rule PII, or re-pick the returns column. Those land in
   `unresolved-questions.md` for the named owner, exactly as in mapping.

## The measure/judge boundary (the load this feature respects)

This is a "Later" / Layer-2 feature. Per hard rule #8 (docs/templates/checklists
first; automate only after artifacts prove useful) and scope discipline (do not
assume an ingestion runtime exists), the boundary is:

- **DESIGN is in-scope (this slice).** A drift taxonomy, a `source-drift-report.md`
  template, a re-profile/compare checklist, the readiness-status wiring (how a
  drift outcome maps to Source Ready `pass`/`warning`/`blocked`), and the
  forbidden-actions list. These are reviewable text with no side effects -- the
  same category as the existing readiness docs and the five mapping templates.
- **A drift-detection RUNTIME is OUT of scope (deferred seam).** Opening a
  connection, re-profiling live rows, diffing two profiles programmatically, and
  emitting the report mechanically ALL require live data + the optional `db` extra
  (Principle VIII). This slice does NOT build a `retail drift` CLI, a comparator in
  `src/retail/`, or any code. It defines WHAT a drift report records and WHEN it
  changes readiness; the mechanical re-profile reuses the existing (deferred-live)
  `profile.py` path when that seam is built.
- **JUDGING drift is always a human seam where it touches grain/identity/returns/
  PII** (Principle V) -- true now and after a runtime exists. Automation may
  MEASURE and CLASSIFY; it may never self-grant a re-`pass` on a Principle-V class.

## Architecture (a doc + a template + a checklist; no runtime, no CLI)

Following the readiness-stage pattern (every stage is "a doc + a status entry
before it is code", hard rule #8), this feature ships:

1. **`docs/readiness/source-drift.md`** -- the design doc: the drift taxonomy
   above, the baseline-vs-observed model, how each class maps to a Source Ready
   status transition, the Principle-V seams, and the forbidden-actions list. It is
   a Source-Ready COMPANION doc (Source Ready certifies once; this re-certifies
   over time), cross-linked from `source-ready.md`.
2. **`templates/source-drift-report.md`** -- the committed BLANK a (future) drift
   run fills: header (baseline profile ref + observed re-profile date/by), a
   per-class findings table with before/after measured cells, the resulting Source
   Ready status + blocking reasons, and the open-questions handoff for Principle-V
   classes. Mirrors the `source-profile.md` / `reconciliation-report.md` template
   posture ("cite numbers, not adjectives"; ASCII; secrets only in `.env`).
3. **`docs/checklists/source-drift.md`** (or the repo's checklist home) -- the
   re-profile/compare checklist an operator (or a future runtime) follows: pin the
   baseline, re-profile with the SAME measures (`'' OR NULL`, candidate-PK
   uniqueness, returns from the authoritative column), classify each diff, set the
   status, hand Principle-V classes to a human.

No new Python, no `.sql`, no CLI subcommand, no schema in `src/retail/`. The agent
(or a later runtime) is the executor of the checklist; the templates are the
contract for what gets recorded. This matches the all-skills/all-docs posture of
the kit and adds no new gate (the "gate" is the existing Source Ready review,
now able to read a drift report as evidence).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detect and record shape drift as Source-Ready evidence (Priority: P1)

A source previously `pass` at Source Ready is re-landed. An operator (or future
runtime) re-profiles it and compares against the committed baseline profile,
producing a `source-drift-report.md` that lists each shape change (added/removed/
retyped column, missingness/cardinality shift) with before/after numbers, and sets
the table's Source Ready status accordingly (`pass` if no material drift,
`warning` for non-fatal drift, `blocked` for a fatal class).

**Why this priority**: shape drift is the most common and most mechanical drift,
and it is the case the one-time profile is blindest to. A column removed or
retyped silently breaks a downstream cast; catching it as a Source-Ready blocker
is the core value and the MVP.

**Independent Test**: take any committed `source-profile.md` as baseline and a
modified copy as the "observed" re-profile (one column removed, one added, one
missingness rate moved past tolerance); fill `source-drift-report.md` from the
two; assert each change is classified to the right class + default severity, and
the resulting Source Ready status is `blocked` (because of the removed column),
with `blocking_reasons` naming the removed column. No live DB required -- two
profiles are the only inputs.

**Acceptance Scenarios**:

1. **Given** a baseline profile and an observed re-profile that differ only by a
   NEW column, **When** the report is filled, **Then** the class is `column added`,
   severity `warning`, Source Ready becomes `warning` (not `blocked`), and the new
   column is recorded as "not yet mapped -- review for adoption", never auto-adopted.
2. **Given** an observed re-profile MISSING a baseline column, **When** the report
   is filled, **Then** the class is `column removed`, severity `blocked`, and
   `blocking_reasons` names the column and warns that any mapping/silver reference
   to it is now broken.
3. **Given** a column whose landed type changed but which is NOT a key/measure,
   **When** the report is filled, **Then** the class is `column retyped`, severity
   `warning`, with the before/after type recorded; **and** if the retyped column IS
   a candidate-PK part or a money/qty measure, severity escalates to `blocked`.
4. **Given** no material drift (every class within recorded tolerance), **When** the
   report is filled, **Then** Source Ready stays `pass`, evidence cites the drift
   report, and `next_action` is "no re-mapping needed; baseline still valid".

### User Story 2 - Grain / identity / returns / PII drift hard-stops for a human (Priority: P1)

When the comparison shows the candidate PK is no longer unique on the data, the
returns column changed, a previously-1:1 identity pair fanned out, or a PII-looking
column appeared / a dropped-PII column reappeared, the detector MEASURES and
CLASSIFIES it, sets Source Ready `blocked`, and raises the question to
`unresolved-questions.md` for the named owner -- it NEVER re-decides grain, re-rules
PII, or re-picks the returns column.

**Why this priority**: these are the Principle-V judgment classes. Auto-resolving
any of them would let the detector silently re-invent the exact grain/PII/identity
rulings the constitution reserves for a human. Getting the STOP right is as
load-bearing as the detection itself.

**Independent Test**: present a baseline+observed pair where the recorded candidate
PK's uniqueness proof now fails (`COUNT(*) != COUNT(DISTINCT pk)` on the observed
data); assert the report records `grain/PK drift = blocked`, the report does NOT
propose a new grain, and an `unresolved-questions.md` row is raised naming the
owner (analyst / governance / data-owner).

**Acceptance Scenarios**:

1. **Given** the recorded candidate PK is no longer unique on the observed data,
   **Then** class `grain/PK drift`, severity `blocked`, NO new grain proposed, an
   open question raised for the analyst.
2. **Given** the authoritative returns column changed population/meaning or
   disappeared, **Then** class `returns-rule drift`, severity `blocked`, NO new
   returns rule proposed, an open question raised.
3. **Given** a column appears that pattern-matches PII (or a baseline
   `decision: drop` PII column reappears), **Then** class `PII surface drift`,
   severity `blocked`, NO publish-safety ruling made, an open question raised for
   governance (default remains drop).
4. **Given** a baseline 1:1 code/label pair that is no longer 1:1, **Then** class
   `semantic-pair drift`, severity `warning` by default, escalating to `blocked`
   when the pair underpins entity identity -- and identity escalation is a human
   judgment, never auto-asserted.

### User Story 3 - Drift outcome wires cleanly into the readiness spine (Priority: P2)

A filled drift report updates the table's `readiness-status.yaml` (canonical path
`mappings/<table>/readiness-status.yaml`, ADR 0004): it sets the
`source_ready` stage status, lists the drift report under `evidence[]`, populates
`blocking_reasons[]` from the fatal classes, and -- if any stage was downstream of
the drifted source -- records that those stages must be RE-checked (a drift at
Source Ready can invalidate a Mapping/Silver/Gold that was built on the old shape).

**Why this priority**: the value of drift detection is realized only when it moves
readiness state the agent reads. But it is P2 because US1/US2 already deliver the
report; this story is the wiring that makes the report actionable.

**Independent Test**: given a `blocked` drift report for a table whose
`mapping_ready` was previously `pass`, assert the status model says Source Ready is
now `blocked` AND a note is recorded that `mapping_ready` (and any further `pass`
stages) are now SUSPECT and must be re-confirmed against the new shape -- without
the detector itself silently flipping the downstream stages to `pass`/`blocked`
(it flags; the human/agent re-runs the stage gate).

**Acceptance Scenarios**:

1. **Given** a `warning` drift report, **Then** Source Ready becomes `warning`,
   evidence cites the report, downstream stages are left as-is with an advisory note.
2. **Given** a `blocked` drift report, **Then** Source Ready becomes `blocked`,
   `blocking_reasons` come from the fatal classes, and downstream `pass` stages are
   flagged SUSPECT (re-check required) rather than auto-demoted.
3. **Given** the spine, **Then** no drift "score" is written; only the four
   explicit statuses + measured per-class magnitudes + blocking reasons.

### Edge Cases

- **No baseline.** If `<table>` has no committed `source-profile.md`, there is
  nothing to drift FROM: the detector does NOT run; the table is simply
  `not_started`/awaiting first profile (Source Ready stage 1), not "drifted".
- **Re-profile unavailable (deferred-live boundary).** If the DSN / `db` extra is
  absent, the observed re-profile cannot be taken: mark the report
  `[PENDING LIVE RE-PROFILE]` and record a `warning` (not a fabricated comparison),
  mirroring `source-ready.md`'s `[PENDING LIVE PROFILE]` posture.
- **Tolerances not set.** Missingness/cardinality "shift" needs a recorded
  tolerance. If none is recorded on the baseline, any movement is reported as an
  observation at `warning` (never silently treated as zero-drift), and a follow-up
  to record tolerances is raised.
- **Cosmetic-only diff.** A column RENAME that is provably the same column (same
  semantics, same measures) is recorded as an observation, not a removal+add, but
  the rename itself is a mapping concern flagged for review -- the detector does not
  auto-equate two names.
- **Both directions of PII drift.** Both a NEW PII-looking column and the
  REAPPEARANCE of a previously-dropped PII column are `blocked` -- the dropped-PII
  reappearance is the more dangerous and is called out explicitly.
- **Profile schema version skew.** If the baseline profile predates the current
  `source-profile.md` template shape, the comparison runs on the fields both carry
  and records which fields were uncomparable, rather than reporting false drift.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add `docs/readiness/source-drift.md` (ASCII, UTF-8 no BOM) defining
  the drift taxonomy (the nine classes above), the baseline-vs-observed model, the
  per-class default severity, and the Source Ready status mapping. It is a
  Source-Ready companion doc, cross-linked both ways with `source-ready.md`.
- **FR-002**: Add `templates/source-drift-report.md` (ASCII, UTF-8 no BOM) -- the
  committed blank a drift run fills. It MUST carry: a header (baseline
  `source-profile.md` ref + commit/date, observed re-profile date/by, connection is
  read-only with secrets only in `.env`), a per-class findings table with
  before/after MEASURED cells, the resulting Source Ready status, the
  `blocking_reasons`, and a Principle-V handoff section listing open questions.
- **FR-003**: Add a re-profile/compare checklist (`docs/checklists/source-drift.md`
  or the repo's checklist home if one exists) enumerating the ordered steps: pin
  baseline -> re-profile with the SAME measures as the baseline (`'' OR NULL`
  missingness, candidate-PK uniqueness on the data, returns from the authoritative
  column) -> classify each diff -> set status -> hand Principle-V classes to a human.
- **FR-004**: The design MUST reuse the EXISTING Source Ready measures, not invent
  new ones: missingness is `'' OR NULL` (RC5), PK uniqueness is
  `COUNT(*) = COUNT(DISTINCT pk)` with `0` NULL PK (RC2), returns are from the
  authoritative billing/transaction column (RC8), never a measure sign. Drift is a
  DIFF of these same measures across two points in time.
- **FR-005**: The drift report MUST carry NO fabricated confidence score (#9).
  Per-class measured magnitudes (before/after counts, %, type strings) are required
  MEASUREMENTS; any rolled-up single "drift score" is forbidden until scoring rules
  exist, and the template MUST state this.
- **FR-006**: A fail-loud Principle-V seam table: `grain/PK drift`, `returns-rule
  drift`, `PII surface drift`, and identity-bearing `semantic-pair drift` are
  HARD-STOPS that set `blocked`, raise an `unresolved-questions.md` entry naming the
  owner, and are NEVER auto-resolved by proposing a new grain/returns/PII/identity
  ruling. The default on PII stays `drop`.
- **FR-007**: Source Ready status mapping MUST be explicit: no material drift ->
  `pass` (evidence = the drift report); only non-fatal classes present ->
  `warning`; any fatal class present -> `blocked` (`blocking_reasons` enumerate the
  fatal classes). Map to the four spine statuses only; never a number.
- **FR-008**: Downstream-invalidation rule: a `blocked`/`warning` drift at Source
  Ready MUST be recorded as making downstream `pass` stages (Mapping/Silver/Gold/
  ...) SUSPECT and requiring RE-confirmation; the detector FLAGS this and MUST NOT
  silently demote or auto-`pass` any downstream stage.
- **FR-009**: Deferred-runtime honesty: the docs MUST state that this slice is
  DESIGN ONLY -- no `retail drift` CLI, no comparator code, no DB connection here;
  the mechanical re-profile reuses the deferred-live `profile.py` seam (Principle
  VIII) when that seam is built. Absent the live boundary, a run is
  `[PENDING LIVE RE-PROFILE]` + `warning`, never a fabricated comparison.
- **FR-010**: Generic only (#7, Principle VII): the taxonomy, template, and
  checklist carry NO worked-example specifics (no pharmacy columns, billing codes,
  segments, or PII column names). C086 may be CITED as the filled instance of the
  baseline profile that a drift run would compare against, never copied inline.
- **FR-011**: `readiness-status.yaml` wiring MUST be specified (not coded): how a
  filled drift report sets `source_ready.status`, appends the report to
  `evidence[]`, populates `blocking_reasons[]`, and records the downstream-suspect
  note + `last_checked_at`/`checked_by`. No change to the status schema is required;
  if one is, it is recorded as a deferred decision, not made here.
- **FR-012**: Cross-link the new doc into the spine: `source-ready.md` See-also ->
  `source-drift.md`; `source-drift.md` -> `readiness-model.md`,
  `readiness-pipeline.md`, `source-ready.md`, `templates/source-profile.md`,
  `templates/source-drift-report.md`, the checklist, and `docs/roadmap/roadmap.md`
  (F014). Update the roadmap row to note the spec dir (015) if edited.

### Key Entities

- **Baseline profile**: the committed `mappings/<table>/source-profile.md` that
  earned Source Ready `pass` -- the reference the observed re-profile is compared
  against. Immutable for the duration of a drift run.
- **Observed re-profile**: a later read-only re-profiling of the same
  `<schema>.<table>` using the SAME measures; the right-hand side of every diff.
  Deferred-live (needs the `db` extra); `[PENDING LIVE RE-PROFILE]` when absent.
- **Drift class**: one of the nine taxonomy classes, each with a default severity
  and a Principle-V flag (grain/returns/PII/identity = human seam).
- **Drift report** (`source-drift-report.md`): the committed artifact recording the
  per-class findings (before/after measured), the resulting Source Ready status,
  the blocking reasons, and the open-questions handoff. Evidence for the spine.
- **Source Ready status transition**: the mapping from a filled drift report to the
  four spine statuses (`pass`/`warning`/`blocked`), plus the downstream-suspect note.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The three artifacts exist and are ASCII + UTF-8 no BOM:
  `docs/readiness/source-drift.md`, `templates/source-drift-report.md`, and the
  drift checklist; each is cross-linked into the spine and carries no worked-example
  specifics.
- **SC-002**: `retail check` stays exit 0 with the new docs/templates added (this
  is a docs/templates slice; no rules change, no code added, `dependencies = []`
  unchanged), and the full unit suite stays green.
- **SC-003**: The baseline-vs-observed replay test passes: given two profiles
  (baseline + a modified copy), a human filling `source-drift-report.md` from the
  template classifies every diff to the correct class + default severity and lands
  the correct Source Ready status -- demonstrating the template is complete enough to
  drive a real comparison with no missing fields.
- **SC-004**: Every Principle-V class (grain/PK, returns, PII, identity-pair) is
  documented as a HARD-STOP that raises an `unresolved-questions.md` entry and is
  never auto-resolved; a reviewer can point to the exact forbidden-actions line for
  each. No drift "score" appears in any artifact (only statuses + measured
  magnitudes).

## Assumptions

- This is a "Later" / Layer-2 design slice: docs/templates/checklist only, per hard
  rule #8 and scope discipline. No drift runtime, no CLI, no comparator code, no DB
  connection is built here. (Auto-decision: design-only scope, the recommended
  default for a "Later"-tier roadmap row.)
- The mechanical re-profile, when built, reuses the existing deferred-live
  `profile.py` path (Principle VIII), not a new profiler. Drift is a diff of the
  same measures, not a new measurement family.
- The drift report lives next to the baseline it compares, under
  `mappings/<table>/` (ADR 0003 -- per-table working set), as
  `mappings/<table>/source-drift-report.md`. (Auto-decision: co-locate with the
  baseline profile, consistent with ADR 0003; recorded as reversible.)
- No change to the `readiness-status.yaml` schema is needed; the existing
  `evidence[]` / `blocking_reasons[]` / status fields carry a drift outcome. If a
  schema field turns out to be needed, it is a deferred decision, not made here.
- Tolerances for missingness/cardinality "shift" are recorded ON the baseline
  profile (or default to "any movement is an observation at `warning`"); defining a
  numeric global tolerance policy is deferred (it would otherwise become a fake-
  confidence knob).
- C086 is cited as the filled-baseline example only; the kit's drift artifacts stay
  generic (Principle VII / #7).

## Deferred decisions (future specs / issues -- recorded, not built)

- **The drift-detection runtime** (`retail drift` or a `src/retail/` comparator):
  re-profile live, diff two profiles mechanically, emit the report -- needs creds +
  the `db` extra (Principle VIII). Designed here; built later, after the templates
  prove useful (hard rule #8).
- **A static `retail check` rule for drift hygiene** (e.g. a baseline profile must
  carry recorded tolerances before a drift run is meaningful) -- a checker change
  for a later slice; recorded, not added (keeps this a docs slice; rule count
  unchanged).
- **A numeric drift-magnitude / scoring policy** -- forbidden as a confidence score
  now (#9); if ever defined, it MUST cite the evidence it derives from and live in
  `readiness-model.md`'s scoring rules. Deferred.
- **Tolerance policy** for what counts as a material missingness/cardinality shift
  (global default vs per-column) -- deferred; until set, movement is an observation
  at `warning`.
- **Scheduled / continuous drift watch** (re-profile on a cadence, alerting) -- an
  orchestration concern beyond this design slice; deferred to a later orchestration
  feature.
- **`readiness-status.yaml` schema extension** for an explicit `drift` sub-record,
  if the `evidence[]`/`blocking_reasons[]` carry proves insufficient in practice --
  deferred; not made here.

## See also

- The stage this advances: `docs/readiness/source-ready.md` (Source Ready, stage 1);
  the spine model `docs/readiness/readiness-model.md`; the sequence
  `docs/readiness/readiness-pipeline.md`.
- The baseline artifact this drifts FROM: `templates/source-profile.md` (its
  "Cross-file schema drift" check is the narrow seed this generalizes over time).
- The Principle-V handoff surface: `templates/unresolved-questions.md`.
- The defaults the measures reuse: `docs/decisions/0002-retail-cleaning-defaults.md`
  (RC2 PK-on-data, RC5 `'' OR NULL` missingness, RC8 returns from authoritative
  column).
- The deferred-live profiler the runtime will reuse: `src/retail/profile.py`;
  the live-surface posture: `specs/004-retail-validate/spec.md`, Principle VIII.
- Artifact location: `docs/decisions/0003-mapping-artifact-location.md` (ADR 0003,
  `mappings/<table>/`).
- The roadmap row: `docs/roadmap/roadmap.md` -- F014 "Source Drift Detector"
  (Layer 2, "Later" tier), filed under spec dir 015.
- C086 is the first filled baseline, an example not the schema:
  `docs/worked-examples/c086-pharmacy.md` (Principle VII / #7).
