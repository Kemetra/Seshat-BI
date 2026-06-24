# Feature Specification: Reconciliation Ledger -- a durable history of cross-layer reconciliation results

**Feature Branch**: `016-reconciliation-ledger` (work on the feature branch per session convention; located via `.specify/feature.json`)

**Created**: 2026-06-24

**Status**: Draft

**Input**: "Roadmap F015 (Layer 4 Validation & Readiness, 'Later' tier). Advances readiness stage: Gold Ready. A durable LEDGER of cross-layer reconciliation RESULTS over time (each entry: which reconciliation, when, measured penny/row deltas, pass/fail, the evidence) -- a history layer over the existing retail validate reconciliation check, NOT a new validator. Gold to Power BI requires validation (hard rule #4); the ledger records that validation's results durably. 'Later' tier: spec the design/template first (hard rule #8); do not build the storage runtime (scope discipline). Generic (#7). Entries carry measured numbers as evidence; no fabricated confidence (#9)."

## Why this feature exists

`retail validate` (feature 004) already runs the four live checks and, among them, the
**penny-exact cross-layer reconciliation** (RC16) that the Gold Ready gate depends on. But a
validate run is a **point-in-time event**: it proves the totals reconcile *right now* and then
its output evaporates unless someone pastes it into a `reconciliation-report.md`. The kit has no
**durable, append-only record of reconciliation results over time** -- no way to answer "did this
table's silver<->gold totals reconcile last month, and by how much did they drift since?", "when
did this measure last pass penny-exact?", or "show me the history of every reconciliation that
gated this table's Gold Ready status."

This feature defines that record: a **reconciliation ledger** -- one durable, append-only entry
per reconciliation result, each carrying the measured penny/row deltas, the pass/fail verdict,
the evidence, and provenance (which table, which run, when, by whom). It is a **history layer**,
not a validator. It does not re-prove anything; it **records** what `retail validate` already
proved, so the proof survives the run.

**This is a "Later"-tier feature (roadmap F015).** Per hard rule #8 (docs/templates/checklists
first; automate only after artifacts prove useful) this slice **specs the ledger design and its
entry template** -- it does **NOT** build a storage runtime, a database table, a writer, or a
query CLI. The shape is defined and proven by hand-filled example entries; wiring `retail
validate` to auto-append is a named, deferred follow-up.

## What it advances (readiness)

- **Stage: Gold Ready** (`docs/readiness/gold-ready.md`). Gold Ready's `pass` requires the live
  `retail validate` reconciliation to be penny-exact, with the figures **recorded as evidence**.
  Today that evidence is a single `mappings/<table>/reconciliation-report.md` snapshot. The
  ledger makes the evidence **durable and historical**: every Gold Ready re-validation appends
  an entry, so the stage's `evidence[]` can cite a ledger that shows the result held over time,
  not just once.
- It reinforces, and adds no new, gate. The gate is still `retail validate` (Principle VIII,
  hard rule #4). The ledger is downstream of the gate -- it records the gate's verdict.

## What this is (and is not)

| It IS | It is NOT |
|-------|-----------|
| A durable, append-only **history** of reconciliation **results** | A new validator or a new check (it adds no gate) |
| A **template + design** for a ledger entry (this slice) | A storage runtime, DB table, writer, or query tool (deferred) |
| A record of **measured** penny/row deltas + pass/fail + evidence | A confidence score or any fabricated number (forbidden, #9) |
| Generic -- placeholders, no worked-example specifics | C086/pharmacy-shaped (those live in the worked example) |
| The complement to the point-in-time `reconciliation-report.md` | A replacement for `reconciliation-report.md` or `retail validate` |
| A history layer for **Gold Ready** evidence | A change to the Gold Ready gate's pass/fail criteria |

## Relationship to existing artifacts

- **`retail validate` (src/retail/validate.py, feature 004)** -- the SOURCE of a ledger entry's
  numbers. The reconciliation check already computes per-measure source/silver/gold totals and a
  match verdict; an entry records exactly those, plus when/which/who. The ledger never recomputes.
- **`templates/reconciliation-report.md`** -- the point-in-time, per-table acceptance snapshot
  (one filled instance per table, the Gold Ready required artifact). The ledger is its **temporal
  complement**: the report answers "does this table reconcile?"; the ledger answers "has it kept
  reconciling, and how has the delta moved?". An entry MAY be derived from a report run, and an
  entry SHOULD cite the report it corresponds to as evidence.
- **`docs/readiness/gold-ready.md`** -- the stage the ledger serves. The ledger is a candidate
  member of Gold Ready's `evidence[]` (durable history) without changing the stage's gate.
- **`templates/readiness-status.yaml` / readiness-model** -- the ledger entry's verdict
  vocabulary aligns with readiness statuses where sensible (a `pass`/`fail` per entry; no score).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A reconciliation result is recorded as a durable, append-only entry (Priority: P1)

After a `retail validate` reconciliation runs for a table, its result -- the measured per-measure
and row-count deltas, the overall pass/fail, and the evidence -- is captured as **one immutable
ledger entry** appended to that table's ledger. Re-running validation later appends a **new**
entry; it never overwrites the prior one. The history accumulates.

**Why this priority**: this is the feature's entire reason to exist -- durability of the result
over time. Without an append-only entry that survives the run, there is no ledger.

**Independent Test**: hand-fill one ledger entry from a `retail validate` reconciliation result
(or a filled `reconciliation-report.md`), following the template; confirm it carries the
measured deltas, the verdict, the evidence, and the provenance, and that appending a second entry
for the same table leaves the first untouched. No runtime required -- the template + two example
entries prove the shape.

**Acceptance Scenarios**:

1. **Given** a reconciliation that passed penny-exact, **When** an entry is recorded, **Then** the
   entry carries each measure's source/silver/gold totals, the row-count line, a per-line delta of
   `0`, an overall verdict of `pass`, the run timestamp, the table id, the actor, and the evidence
   reference (the validate run and/or the `reconciliation-report.md`).
2. **Given** a later reconciliation for the same table, **When** a second entry is recorded,
   **Then** it is **appended** (the prior entry is unchanged and still present) -- the ledger is
   append-only, never mutated in place.
3. **Given** an entry, **When** it is read back, **Then** every number in it is a **measured**
   value (or a measured difference), never an estimate, rounding, or fabricated score (#9).

---

### User Story 2 - A reconciliation FAIL is recorded with its measured drift, not hidden (Priority: P1)

When a reconciliation does **not** reconcile penny-exact, the ledger entry records the **measured
non-zero delta** (which measure, by how much, in which direction) and an overall verdict of
`fail`. A failing result is first-class history -- it is recorded with the same rigor as a pass,
so drift is auditable rather than lost.

**Why this priority**: a ledger that only records passes is a vanity log. The auditable value is
in the failures and the drift over time -- this is why the entry carries measured deltas, not
just a boolean.

**Independent Test**: hand-fill an entry from a reconciliation where one measure differs by a
known amount; confirm the entry names the measure, the exact delta (e.g. `+0.03`), the layer pair
where the gap appears (e.g. silver->gold), and an overall `fail`, with no rounding-away.

**Acceptance Scenarios**:

1. **Given** a measure whose gold total differs from its silver total by `0.03`, **When** the
   entry is recorded, **Then** it records that measure with delta `0.03`, the layer pair, and an
   overall verdict `fail` -- the cent is recorded, never rounded to zero.
2. **Given** a NULL total on one layer for a measure, **When** the entry is recorded, **Then** the
   entry records it as a reconciliation defect (a `fail` line), not an omitted or zero line.
3. **Given** a `fail` entry exists, **When** Gold Ready evidence is assembled, **Then** the entry
   makes the stage `blocked` (reconciliation not penny-exact), not silently `pass`.

---

### User Story 3 - The ledger gives Gold Ready durable, historical evidence (Priority: P2)

A reader (agent or human) assembling a table's Gold Ready status can point `evidence[]` at the
ledger to show the reconciliation result **and its history** -- not just the latest snapshot.
"This table's silver<->gold totals reconciled penny-exact on these N dates" becomes a citable,
durable fact.

**Why this priority**: this is the readiness payoff (the stage this feature advances) but it
builds on US1/US2 -- the entry shape must exist before it can be cited.

**Independent Test**: given a table ledger with several entries, confirm the most recent `pass`
entry can be cited in `readiness-status.yaml`'s `gold_ready.evidence[]`, and that the history of
prior entries is visible alongside it -- the stage's pass is backed by durable evidence, not a
one-shot run.

**Acceptance Scenarios**:

1. **Given** a table ledger whose latest entry is `pass` with evidence, **When** Gold Ready is
   assessed, **Then** the ledger entry is a valid member of `gold_ready.evidence[]` (a `pass`
   carries evidence, per the readiness model).
2. **Given** a ledger with a mix of past `pass` and `fail` entries, **When** the history is read,
   **Then** the sequence of verdicts and deltas over time is legible (the durability/history
   value) without any entry being mutated to "clean up" the record.

---

### Edge Cases

- **Two runs same day** -- entries are distinguished by a precise timestamp (and, if needed, a run
  id), so same-day re-validations are both retained and ordered. The ledger is append-only; a
  same-day re-run never overwrites the earlier same-day entry.
- **Measure set changes between runs** -- a new measure appears, or one is removed, between two
  entries. Each entry records the measure set **as measured at that run**; the ledger does not
  retro-fit older entries. History reflects what was true then.
- **Reconciliation not run / deferred mode** -- when `retail validate` could not run (no DSN / no
  `db` extra; the Gold Ready blocked-deferred boundary), there is **no entry** -- the ledger never
  fabricates a "pass" or a "0 delta" for a run that did not happen (#9, and gold-ready.md "report
  the boundary, never fake a pass").
- **BI-layer total not yet available** -- the source/silver/gold deltas are recorded; the BI
  column is recorded as `n/a` (mirrors `reconciliation-report.md`), never as a guessed number.
- **Manual correction of a past mistake** -- a wrong entry is NOT edited in place; a new
  corrective entry is appended that references the superseded entry (append-only integrity).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Define a **ledger entry template** (a new generic template,
  `templates/reconciliation-ledger-entry.md` -- exact filename confirmed in plan) describing the
  fields of a single reconciliation result over time. It MUST be generic (placeholders only; no
  worked-example/pharmacy specifics, #7) and ASCII + UTF-8 without BOM.
- **FR-002**: Each entry MUST carry, at minimum: a **provenance block** (table id, run timestamp,
  actor [agent|analyst], DB cluster/database identifiers, and a reference to the source `retail
  validate` run and/or the `reconciliation-report.md` it derives from); a **per-measure result
  table** (measure name, source/silver/gold[/BI] totals, the measured delta, a per-line match
  verdict); a **row-count line**; and an **overall verdict** (`pass` | `fail`).
- **FR-003**: Every numeric field in an entry MUST be a **measured value or a measured
  difference**. The template MUST NOT contain, and an entry MUST NOT carry, any confidence score
  or fabricated number (Principle: no fake confidence, #9). A delta is recorded exactly (penny
  precision), never rounded to reach a verdict.
- **FR-004**: The ledger MUST be **append-only**: recording a new result for a table ADDS an entry
  and never mutates or deletes a prior entry. The template/design MUST state this invariant and
  the correction protocol (supersede-by-append, never edit-in-place).
- **FR-005**: A `fail` entry MUST record the **specific non-zero delta(s)** and the layer pair(s)
  where the gap appears, so drift is auditable. A NULL total on a layer MUST be recorded as a
  reconciliation defect (a `fail` line), not omitted.
- **FR-006**: The entry's verdict vocabulary MUST be **`pass` | `fail`** for the reconciliation
  result, consistent with the Gold Ready gate (penny-exact = pass). It MUST NOT introduce a
  `warning`/`score` middle value for the reconciliation number itself (a cent off is a `fail`).
- **FR-007**: The design MUST specify **where a table's ledger lives and how entries are
  organized** as a documented placement decision, consistent with the kit's existing per-table
  artifact convention (`mappings/<table>/`, ADR 0003) -- with the concrete path/format chosen in
  the plan, not invented here. (Recorded as a deferred placement decision below.)
- **FR-008**: The ledger MUST be positioned as a **history layer over** the existing `retail
  validate` reconciliation check -- it records that check's result. The spec MUST state it adds
  **no new validator and no new gate** (Principle VIII; hard rule #4 unchanged).
- **FR-009**: The design MUST cross-reference the temporal-complement relationship to
  `templates/reconciliation-report.md` (point-in-time snapshot) and the Gold Ready stage doc, and
  cite the worked example as the eventual filled instance source -- without copying any worked-
  example specifics into the generic template (#7).
- **FR-010**: A ledger entry MUST be citable as **Gold Ready evidence**: a `pass` entry is a valid
  member of `gold_ready.evidence[]`; a `fail` entry is a `gold_ready` blocking reason
  (reconciliation not penny-exact). The design MUST NOT change the Gold Ready gate criteria.
- **FR-011 (scope discipline, "Later" tier)**: This slice delivers the **design + template +
  hand-filled example entries ONLY**. It MUST NOT build a storage runtime, a database/ledger
  table, an auto-append writer, a query/report CLI, or any wiring from `retail validate` into the
  ledger. Those are named, deferred follow-ups (see Deferred decisions). No runtime code, no DB
  writes (Scope Boundaries; hard rule #8; CLAUDE.md YAGNI).
- **FR-012**: When a reconciliation **did not run** (deferred boundary, no DSN/`db` extra), a
  fabricated pass/zero-delta entry is forbidden (#9; gold-ready.md deferred-mode rule). HOW the
  ledger represents "did not run" is an **OPEN HUMAN DECISION** (see Deferred decisions), not
  settled here: (a) write **no entry** (the recommended default -- absence over fabrication), vs
  (b) write an explicit **no-figures `blocked-deferred` entry** (so an append-only audit log
  distinguishes "could not run" from "nobody tried"). Resolve this with the open ledger-grain
  question before the template is authored; either way, no figures are invented.

### Key Entities

- **Reconciliation ledger entry**: one immutable record of a single reconciliation result over
  time. Holds provenance (table, when, who, where), the per-measure measured totals + deltas, the
  row-count line, and the overall `pass`/`fail` verdict, plus evidence references. The atom of the
  ledger.
- **Ledger (per table)**: the append-only ordered collection of entries for one table -- the
  durable history. Defined as a design/template here; its concrete storage is deferred.
- **Reconciliation result (input)**: the per-measure source/silver/gold[/BI] totals + match
  verdict produced by the existing `retail validate` reconciliation check (or a filled
  `reconciliation-report.md`). The ledger records this; it does not compute it.
- **Evidence reference**: a pointer from an entry to its proof -- the `retail validate` run and/or
  the corresponding `reconciliation-report.md` -- so a reader can trace the entry to its source.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A generic ledger-entry template exists, is ASCII + UTF-8 without BOM, and contains
  **zero** worked-example/pharmacy specifics (all fields are placeholders) -- verifiable by
  inspection and by `retail check` staying green (no new violations).
- **SC-002**: The template + at least **two hand-filled example entries** (one `pass`, one `fail`)
  demonstrate the entry shape end-to-end, including a measured non-zero delta on the `fail`
  example -- proving the design without any runtime.
- **SC-003**: Every numeric field across the template and examples is a **measured value or
  measured difference**; a reviewer can confirm **no** confidence score or fabricated number
  appears anywhere (#9).
- **SC-004**: The append-only invariant and the supersede-by-append correction protocol are
  stated in the design and demonstrated by the two example entries coexisting (the first is not
  altered when the second is added).
- **SC-005**: The design explicitly states the ledger adds **no new validator and no new gate**,
  records the `retail validate` reconciliation result, and is the temporal complement to
  `reconciliation-report.md` -- with working cross-links to `gold-ready.md`,
  `templates/reconciliation-report.md`, and constitution Principle VIII.
- **SC-006**: A `pass` example entry is shown to be citable in a `readiness-status.yaml`'s
  `gold_ready.evidence[]`, and a `fail` entry as a `gold_ready` blocking reason -- without
  changing the Gold Ready gate criteria.
- **SC-007**: **No runtime artifact is added** -- no `src/` code, no migration, no DB write, no
  CLI subcommand. The deliverable is docs/templates only (verifiable by the changed-file set).
- **SC-008**: The deferred items (storage placement/format, auto-append wiring, query surface) are
  recorded as explicit future work with their triggering need, not built (scope discipline).

## Assumptions

- **"Later" tier, template-first (hard rule #8).** This slice delivers design + template + filled
  examples; the storage runtime and any `retail validate` -> ledger wiring are deferred. Chosen as
  the recommended default for a "Later"-tier roadmap feature; reversing it (building the runtime
  now) would violate scope discipline and hard rule #8. Reversible: easy (the deferred runtime is
  a clean follow-up spec).
- **The ledger records, never recomputes.** Entry numbers come from the existing `retail validate`
  reconciliation check (or a filled `reconciliation-report.md`). The ledger introduces no new
  computation, validator, or gate (Principle VIII; hard rule #4 unchanged).
- **Per-table organization, ADR 0003-aligned.** A table's ledger is assumed to live with the
  kit's other per-table artifacts (the `mappings/<table>/` convention, ADR 0003); the exact
  path/filename/format is a plan-phase decision, not fixed in this spec.
- **Generic only (#7).** The template carries placeholders; the C086 worked example is cited as
  the eventual filled-instance source but its specifics are never copied into the generic template.
- **Verdict is binary for the reconciliation number (#9 + Gold Ready).** Penny-exact = `pass`; any
  non-zero delta = `fail`. No score, no confidence, no `warning` middle value for the number.
- **Work on the feature branch; no constitution amendment is assumed required** (the ledger adds
  no gate/principle). If the plan finds an amendment is warranted (e.g. naming the ledger in
  Principle VIII or the readiness spine), that is raised in the plan, not pre-decided here.

## Deferred decisions (future specs / issues -- recorded, not built)

Per scope discipline and the "Later" tier, the following are named and parked, each its own
follow-up when prioritized:

- **[DEFERRED: ledger storage runtime]** A real store for entries (a `gold` ledger table, an
  append-only file format, or similar) plus a writer. This slice defines the entry shape only;
  building the store is a later spec, gated on the template proving useful (hard rule #8).
- **[DEFERRED: `retail validate` -> ledger auto-append]** Wiring the validate reconciliation check
  to emit a ledger entry automatically on each run. Named here; not built. The entry shape this
  spec defines is the contract that wiring would target.
- **[DEFERRED: ledger query / history surface]** A read surface ("show this table's
  reconciliation history / drift over time", a CLI or report). Deferred until entries accumulate.
- **[NEEDS CLARIFICATION -> resolve in plan, not human: concrete entry storage path + format]**
  Exact filename/path/format under the per-table convention (ADR 0003). A reversible plan-phase
  decision; flagged here, decided in plan.md.
- **[OPEN -- human, Principle V: ledger grain]** Whether a ledger entry's grain is one-row-per-
  reconciliation-run (recommended) versus one-row-per-measure-per-run, and whether multiple tables
  ever share a single ledger vs strictly one-ledger-per-table. This is a grain/identity decision
  reserved for a human (Principle V); the spec assumes one-entry-per-run-per-table as the working
  default but does NOT finalize the grain.

## See also

- **The check it records:** `src/retail/validate.py` (feature 004, reconciliation check, RC16);
  `specs/004-retail-validate/spec.md`.
- **The point-in-time complement:** `templates/reconciliation-report.md` (per-table snapshot).
- **The stage it advances:** `docs/readiness/gold-ready.md`; the spine
  `docs/readiness/readiness-model.md`; `templates/readiness-status.yaml`.
- **The roadmap entry:** `docs/roadmap/roadmap.md` (F015 Reconciliation Ledger, Layer 4, "Later").
  Note: F016 (pbi-cli / PBIP Adapter) is deliberately EXCLUDED from this batch (hard rule #6).
- **Governing principles:** constitution Principle VIII (static-first, live `retail validate`),
  the readiness-spine section, and hard rules #4 (no gold->Power BI before validation), #7
  (generic), #8 (docs/templates first), #9 (no fake confidence).
- **Defaults:** `docs/decisions/0002-retail-cleaning-defaults.md` -- RC16 (cross-layer
  reconciliation + 0 orphan FKs).
- **Per-table artifact placement:** ADR 0003 (`mappings/<table>/`).
