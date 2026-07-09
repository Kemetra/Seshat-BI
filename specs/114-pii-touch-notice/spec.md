# Feature Specification: Personal-Data-Touch Notice -- per-column PII disclosure from committed flags

**Feature Branch**: `114-pii-touch-notice`

**Created**: 2026-07-09

**Status**: Draft

**Input**: User description: "Personal-Data-Touch Notice -- a read-only, no-gate, no-score sibling composer of F040 consumer-data-dictionary. For each PII-flagged column in a table's source-map.yaml, emit exactly one disclosure sentence that ECHOES the committed pii: flag and its recorded keep/drop disposition string verbatim, and emit an explicit GAP sentence for any pii:true column with NO recorded governance decision. Writes an optional post-publish companion artifact; adds NO blocking reason to any stage; renders NO publish-safety judgment of its own."

## Clarifications

### Session 2026-07-09

- Q: Which committed file(s) are authoritative inputs for a PII column's governance disposition? -> A: `source-map.yaml` ONLY. The notice reads the column's `pii:` flag and `decision`, and echoes the disposition from the column entry plus its cross-referenced `defaults.deviations` (RC4) block, all from `source-map.yaml`. `unresolved-questions.md` is NOT parsed (it is only cited via the RC4 `detail_in` pointer). A `pii: true` column is "undecided" (-> GAP) exactly when `source-map.yaml` records no disposition string for it. A cross-FILE disagreement cannot arise (single authoritative file); FR-010 therefore covers only an INTRA-file disagreement.
- Q: Where is the composed PII Notice written? -> A: `mappings/<table>/pii-touch-notice.md` -- table-co-located, mirroring F040's `mappings/<table>/consumer-data-dictionary.md`. It is the ONLY file the notice writes; regenerating overwrites only this path; the filename collides with no shipped artifact (dictionary, handoff pack, evidence pack).

## Why this feature exists

Whether a published table still touches personal data -- and what a named human
already decided about each such column -- is real information that today lives
scattered and unrendered. In a table's `mappings/<table>/source-map.yaml`, a
column carries a `pii: true`/`false` flag, and the governance decision about a
KEPT PII column lives elsewhere in the same file: inside a `defaults.deviations`
RC4 block (e.g. `customer_id`: `pii: true` at the column, with the disposition
"Q1 RESOLVED 2026-06-25 (data owner): keep, no raw PII" recorded in the RC4
deviation and cross-referenced to `unresolved-questions.md`). No shipped surface
brings the flag and its disposition together into one reader-facing sentence:

- The **BI Handoff Pack** (F013) PII-exclusion item lists only columns DROPPED
  for PII safety -- a KEPT `pii: true` column is never mentioned by it.
- The **consumer-data-dictionary** (F040) omits PII as a disclosure fact BY
  DESIGN (its FR-010: a dropped `pii:true` column is "not even a gap"); it lists
  a kept PII column for its business MEANING only, never surfacing its `pii:`
  flag or governance disposition.
- The **dq-signal-interpretation** note's PII gate is scoped to the `-1`
  unknown-member DQ signal, not a per-column PII inventory.
- The **answerability-summary** explicitly disclaims publish-safety.

So a governance reviewer, downstream consumer, or auditor who asks "which
columns in this table touch personal data, and what was decided about each?"
must open `source-map.yaml` and hand-parse column flags, deviation blocks, and
`unresolved-questions.md` themselves. This feature composes that scattered,
already-committed information into one ordered, plain notice -- one sentence per
PII-flagged column, kept or dropped, echoing the recorded decision verbatim, and
an explicit GAP line for any `pii: true` column whose governance decision has
not been recorded. It ORIGINATES no judgment; it echoes what a named human
already decided, or marks the absence of a decision.

## What this feature is NOT (the scope wall)

This is the load-bearing constraint, stated up front so the spec cannot drift:

- **It renders NO publish-safety verdict of its own.** It never emits "safe to
  publish", "no PII risk", "cleared", or any equivalent evaluative claim. The
  only evaluative content it may show is a VERBATIM echo of a disposition string
  a named human already committed. Composing a new judgment is a Principle-V
  violation this module must be structurally incapable of.
- **A kept-and-undecided PII column is a GAP, never implied clearance.** A
  `pii: true` column with no recorded governance decision MUST render as an
  explicit GAP marker. It MUST NOT be silently omitted (which would read as "no
  PII here") and MUST NOT be phrased so that the absence of a decision reads as
  a decision to keep.
- **It emits NO score and NO count** (hard rule #9): no numeric PII risk level,
  no confidence value, no "N of M PII columns cleared" tally. The notice is a
  categorical echo (flagged / kept / dropped / undecided) only.
- **It adds NO gate.** No new `retail check` rule that blocks a stage, no
  `blocking_reasons[]` entry, no `approvals[]` entry, no readiness-stage move.
  Its presence or absence is never a gate requirement (the
  `answerability-summary` optional-companion precedent).
- **It writes NO upstream artifact and opens NO connection.** It reads only
  committed on-disk artifacts; it never edits `source-map.yaml`,
  `unresolved-questions.md`, `readiness-status.yaml`, or any handoff artifact,
  and never opens a DB / Power BI / network connection.
- **It is generic (Principle VII).** No hardcoded column names, PII category
  labels, or table-specific values baked into the composer; it operates per
  table over the committed `pii:` flags and recorded dispositions it finds.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Governance reviewer sees every PII-touching column and its recorded decision (Priority: P1)

A governance reviewer preparing to authorize (or having already authorized) a
table's release wants a single place that answers: which columns in this table
were flagged as personal data, and for each, what did the named human decide?
Today they must hand-parse `source-map.yaml` column flags and its RC4 deviation
block. With this feature, they read one notice: one sentence per PII-flagged
column, echoing the committed decision verbatim (kept vs dropped, with the
recorded disposition), so they can confirm at a glance that every PII touch has
a named-human decision behind it.

**Why this priority**: This is the whole feature -- enumerating PII-flagged
columns with their verbatim recorded disposition is the net-new capability no
shipped surface provides. Without it there is no MVP.

**Independent Test**: Run the notice against a committed table whose
`source-map.yaml` has at least one `pii: true` KEPT column with a recorded
disposition (e.g. `retail_store_sales` / `customer_id`); confirm the output
contains exactly one disclosure sentence for that column that quotes the
recorded disposition verbatim, and contains no evaluative claim the composer
authored.

**Acceptance Scenarios**:

1. **Given** a table whose `source-map.yaml` marks a column `pii: true`,
   `decision: keep`, with a recorded governance disposition in its RC4 deviation
   block, **When** the notice is composed, **Then** the output contains exactly
   one disclosure sentence for that column that echoes the `pii: true` flag and
   quotes the recorded disposition string verbatim, citing its source path.
2. **Given** a table whose `source-map.yaml` marks a column `pii: true` and
   `decision: drop` for PII safety, **When** the notice is composed, **Then** the
   output contains one disclosure sentence naming that column as PII-flagged and
   dropped, echoing the recorded drop reason verbatim.
3. **Given** a table with columns that are all `pii: false`, **When** the notice
   is composed, **Then** the output states plainly that no column is flagged as
   personal data, and emits no score, count, or evaluative claim.

---

### User Story 2 - Undecided PII column is surfaced as an explicit GAP, never as clearance (Priority: P1)

A reviewer must be able to trust that if a PII-flagged column has NOT yet had its
governance decision recorded, the notice says so loudly -- rather than omitting
the column (which would read as "no PII") or phrasing its kept state as if it
were a decision. This is the safety-critical half of the feature: an undecided
PII touch must never masquerade as a cleared one.

**Why this priority**: Equal-P1 with Story 1. A feature that surfaces decided
PII columns but silently drops undecided ones would be actively misleading -- a
Principle-V hazard. The GAP behavior is what makes the notice safe to rely on.

**Independent Test**: Construct a table fixture with a `pii: true` column that
has NO recorded governance disposition anywhere (no RC4/deviation entry, no
recorded decision); confirm the notice renders an explicit GAP line naming that
column, and that the line cannot be read as implied clearance.

**Acceptance Scenarios**:

1. **Given** a table whose `source-map.yaml` marks a column `pii: true` but
   records NO governance disposition for it, **When** the notice is composed,
   **Then** the output contains an explicit GAP marker naming that column and the
   path(s) checked, and the GAP line contains no clearance language.
2. **Given** the same undecided PII column, **When** the notice is composed,
   **Then** the column is NOT omitted from the notice and its kept/undecided
   state is not phrased as a decision to keep.

---

### User Story 3 - Missing or unreadable source input is surfaced, never fabricated (Priority: P2)

A reviewer running the notice against a table that has no committed
`source-map.yaml`, or an unreadable one, must get an honest signal -- a
document-level GAP naming the path checked -- rather than an empty notice that
reads as "no PII in this table".

**Why this priority**: Robustness. It protects the trust guarantee at the
input-absence boundary, but is secondary to the core decided/undecided behavior.

**Independent Test**: Point the notice at a table directory with no
`source-map.yaml`; confirm it emits one document-level GAP naming the missing
path and composes no fabricated column list.

**Acceptance Scenarios**:

1. **Given** a target table with no committed `source-map.yaml`, **When** the
   notice is composed, **Then** the output is a single document-level GAP naming
   the path pattern checked, with no fabricated PII findings.

---

### Edge Cases

- A `pii: true` column whose disposition is recorded not on the column entry but
  only in a table-level deviation block (RC4) cross-referenced by id -> the
  notice MUST join the column flag to the deviation disposition and echo it, not
  report the column as undecided.
- A column with a recorded disposition whose text itself contains an evaluative
  phrase (e.g. "no raw PII") -> permitted, because it is a VERBATIM echo of a
  named human's committed words, not a claim the composer authored; the notice
  must attribute it (who/when) as recorded, never restate it as the module's own
  finding.
- A table where `source-map.yaml` exists but has no `columns` block, or an empty
  one -> a document-level GAP, not an empty "no PII" notice.
- Conflicting signals WITHIN `source-map.yaml` (a column both `pii: true` and
  listed among PII drops but also `decision: keep`) -> surface the disagreement
  as a GAP naming both in-file locations; never silently pick one.
- The RC4 deviation's `detail_in` pointer references `unresolved-questions.md`,
  but per Clarification Q1 that file is NOT parsed for content -- the notice
  echoes the disposition string as recorded in `source-map.yaml` and cites its
  in-file location. It never opens `unresolved-questions.md` to reconcile.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The notice MUST enumerate every column in the target table's
  committed `source-map.yaml` that is flagged `pii: true`, and MUST also report
  when no column is flagged as personal data.
- **FR-002**: For each `pii: true` column, the notice MUST emit exactly one
  disclosure sentence that echoes the committed `pii:` flag and the column's
  recorded keep/drop decision.
- **FR-003**: Where a governance disposition is recorded for a PII column
  (whether on the column entry or in a cross-referenced table-level deviation
  block), the notice MUST quote that disposition string VERBATIM and cite its
  source location. It MUST NOT paraphrase, simplify, or generate a substitute.
- **FR-004**: For any `pii: true` column with NO recorded governance disposition,
  the notice MUST render an explicit GAP marker naming the column and the
  path(s) checked, and MUST NOT omit the column and MUST NOT phrase its state as
  implied clearance.
- **FR-005**: The notice MUST NOT emit any evaluative publish-safety claim of its
  own (e.g. "safe to publish", "no PII risk", "cleared"). The only evaluative
  text permitted is a verbatim, attributed echo of a committed disposition.
- **FR-006**: The notice MUST NOT emit a numeric score, risk level, confidence
  value, or completeness/"N of M" count anywhere (hard rule #9).
- **FR-007**: The notice MUST NOT add a `retail check` rule that blocks a stage,
  add a `blocking_reasons[]` or `approvals[]` entry, or move any readiness stage;
  its presence or absence MUST NOT be a gate requirement.
- **FR-008**: The notice's sole committed input is the target table's
  `mappings/<table>/source-map.yaml` (Clarification Q1); it reads no other
  artifact for content. It MUST NOT write to, modify, or append to
  `source-map.yaml`, `unresolved-questions.md`, `readiness-status.yaml`, or any
  handoff artifact, and MUST NOT open a DB, Power BI, or network connection. The
  ONLY file it writes is `mappings/<table>/pii-touch-notice.md` (Clarification
  Q2); regenerating overwrites only that path.
- **FR-009**: When the target table has no committed `source-map.yaml` or it is
  unreadable, the notice MUST emit one document-level GAP naming the path
  checked, and MUST NOT fabricate a PII finding or an empty "no PII" result.
- **FR-010**: When `source-map.yaml` is internally inconsistent about a column's
  PII state or disposition (e.g. a column is `pii: true` and `decision: keep`
  yet also appears among the PII drops), the notice MUST surface the
  disagreement as a GAP naming both in-file locations, and MUST NOT silently
  prefer one. (Because the disposition source is `source-map.yaml` ONLY per
  Clarification Q1, this is an INTRA-file consistency check, not a cross-file
  reconciliation.)
- **FR-011**: Every disclosure sentence and GAP line MUST be traceable to the
  committed field(s) in `source-map.yaml` it was composed from -- the content
  MUST be 100% derived from named committed fields (the column's `pii:` flag,
  its `decision`, and its recorded disposition string from the column entry or
  its cross-referenced `defaults.deviations` block), with no other source of
  content. (This is the mechanically-enforceable guarantee that distinguishes
  this notice from a free-composed summary.)
- **FR-012**: The notice MUST be generic across tables (Principle VII): no
  hardcoded column names, PII category labels, or table-specific values; it
  operates over whatever `pii:` flags and recorded dispositions the target
  table's committed artifacts contain.
- **FR-013**: The notice MUST cover a PII-flagged column regardless of its
  keep/drop decision (unlike the drops-only handoff-pack item) -- kept, dropped,
  and undecided PII columns all appear (decided ones as echoed sentences,
  undecided ones as GAP).
- **FR-014**: Output MUST be ASCII-only, UTF-8 without BOM, using `--` and `->`
  (no glyphs), with short repo-relative paths (Windows 260-char budget).

### Key Entities *(include if feature involves data)*

- **PII-flagged column**: a column in `mappings/<table>/source-map.yaml` whose
  `pii:` field is `true`. Attributes the notice reads (all from
  `source-map.yaml`, per Clarification Q1): source name, `pii:` flag, `decision`
  (keep/drop), and the recorded disposition (on the column entry or in a
  cross-referenced `defaults.deviations` block within the same file).
- **Recorded governance disposition**: the committed, named-human decision about
  a PII column (who/what/when), e.g. an RC4 deviation string. The notice echoes
  it verbatim; it never authors one.
- **PII Notice document**: the composed output at
  `mappings/<table>/pii-touch-notice.md` (Clarification Q2) -- one ordered set of
  disclosure sentences (one per PII-flagged column) plus GAP lines for undecided
  columns and any document-level gap. An optional, post-publish companion
  artifact; the only file the notice writes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a table with at least one kept, decided PII column, a reviewer
  can identify every PII-flagged column and its recorded decision from the notice
  alone, without opening `source-map.yaml` or `unresolved-questions.md`.
- **SC-002**: Every disclosure sentence for a decided PII column reproduces the
  recorded disposition string with 100% verbatim fidelity (character-for-
  character match against the committed source), and every such sentence cites
  its source path.
- **SC-003**: For a table containing a `pii: true` column with no recorded
  disposition, the notice always renders that column as an explicit GAP; in no
  case is an undecided PII column omitted or shown as cleared.
- **SC-004**: The notice contains zero numeric scores, risk levels, or counts,
  and zero evaluative publish-safety claims authored by the composer (verifiable
  by inspection: the only evaluative text is verbatim-quoted, attributed
  disposition strings).
- **SC-005**: After composing the notice, `git status` shows the ONLY new/
  modified file is `mappings/<table>/pii-touch-notice.md`; no upstream source
  artifact (`source-map.yaml`, `unresolved-questions.md`, `readiness-status.yaml`,
  handoff artifacts) is modified and no readiness stage moved; the run opened no
  DB/Power BI/network connection.
- **SC-006**: The composer produces a correct notice for any conformant table
  with no code change (generic), demonstrated on at least two distinct tables.

## Assumptions

- The `pii:` flag and each PII column's governance disposition are already
  recorded in committed artifacts before the notice is composed; this feature
  surfaces them, it never originates them. (Grounded: `retail_store_sales/
  source-map.yaml` records `customer_id` as `pii: true`, `decision: keep`, with
  the RC4 deviation "Q1 RESOLVED 2026-06-25 (data owner): keep, no raw PII".)
- The notice is an OPTIONAL companion consumed AFTER a table is published,
  following the `answerability-summary` precedent; it is never a prerequisite for
  any readiness stage.
- This feature mirrors the F040 consumer-data-dictionary as an `artifact-writing`
  Product Module sibling (read-only inputs, one derived output, no gate, no
  score, generic), and fills F040's own declared PII exclusion (its FR-010)
  rather than competing with it.
- The precise output VEHICLE (a standalone skill like F040, versus a runtime
  module) and the exact enforcement mechanism for FR-011 (the derived-from-named-
  fields lint) are implementation decisions deferred to the plan phase; the spec
  fixes only the behavior, not the mechanism. (The disposition SOURCE and the
  output PATH are no longer deferred -- fixed by Clarifications Q1 and Q2.)
- The disposition source is `source-map.yaml` only (Clarification Q1). Within
  that single file, a disposition may be recorded on the column entry or in a
  cross-referenced `defaults.deviations` block; the notice echoes what is
  recorded and GAP-marks an internal inconsistency (FR-010) rather than ranking.
