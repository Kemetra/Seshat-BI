---
name: readiness-viewer
description: >-
  Show the stage-centric readiness lens across the kit's sources / tables /
  reports -- one per-stage status MATRIX over the seven readiness stages, each
  stage's evidence rendered as NAVIGABLE REFERENCES, and an approvals TIMELINE,
  read from each item's readiness-status.yaml. Use when someone asks "show the
  readiness viewer", "which stage is each table at", "what evidence backs Gold
  Ready", or "who approved this gate, and when". READ-ONLY and invoke-and-present
  only: it RENDERS the recorded state (it never recomputes a status, advances a
  stage, writes a pass, infers/back-fills an approval, or fabricates evidence),
  it runs NO validator and opens NO DB connection, and it emits NO numeric
  health / confidence / percent-ready score (hard rule #9). It is the stage-lens
  sibling of the F012 control room: same inputs, different view.
---

# readiness-viewer

The F012 control room answers "what is broken, how badly, worst-first". The
Readiness Viewer answers a different question over the SAME inputs: "which of the
seven stages has each item reached, with what evidence, and who approved the gate
that let it advance". It is a read-only stage-progression LENS over evidence that
already exists per item -- it introduces no new validator and no new gate
(roadmap rule #8; Principle VIII). It renders, then STOPS.

## Module contract (this skill IS a filled Product Module declaration)

This skill declares its authority category up front, per the F024 Companion Tools
Architecture contract (`templates/module-contract.md`).

- **Authority category:** Product Module
- **Capability level:** `read-only`  *(exactly one)*
- **Product layer:** `4`  *(the functional axis -- see docs/roadmap/roadmap.md; orthogonal to category; matches the F012 control-room sibling)*
- **Roadmap feature:** `F026`  **On-disk spec:** `specs/020-readiness-viewer/` *(roadmap F-number is authoritative when the two disagree)*
- **Owner:** `the readiness / data-quality lead`  *(a named role -- never "the agent")*
- **Status:** `Authored`

### What it does (one line)

> Reads each item's `readiness-status.yaml` (Core Authority) and presents the
> seven-stage status matrix, each stage's `evidence[]` as navigable references,
> and the `approvals[]` timeline -- creating no truth.

### Core Authority it READS

It reads these committed truth artifacts; it never writes them.

- `mappings/<item>/readiness-status.yaml` -- `current_stage`, per-stage `status`
  (the four words), `evidence[]`, `blocking_reasons[]`, `approvals[]`, `next_action`.
- the files each `evidence[]` entry references (to mark a reference "referenced
  file not found" when absent -- it reads them only to check existence, never edits).
- the "Required owner / approval" field of each `docs/readiness/<stage>-ready.md`
  (to know which gates require an approval before flagging a missing one).

### Derived evidence it WRITES

- none (read-only). A `read-only` module writes NOTHING -- no cache, no report,
  no per-item file.

### Approved step it EXECUTES

- none (read-only). It executes no step; it renders recorded state.

### Forbidden operations (the matrix says NO)

- MUST NOT create truth: no defining business meaning, no approving a metric/mapping.
- MUST NOT grant approval or move a readiness stage to `pass` (named-human / Core
  Authority only).
- MUST NOT connect to a DB or external service, and MUST NOT publish a Power BI
  artifact (those are Execution Adapter capabilities).
- MUST NOT emit a numeric / maturity / confidence score (hard rule #9).
- As a `read-only` module it additionally MUST NOT write any derived evidence or
  execute any step.

### How it handles a missing input

When a required Core Authority input is absent, the viewer SURFACES it as a flag
and renders the gap as a gap -- it never fabricates the input, self-approves, or
reads a missing-evidence stage as complete (Principle V; stop-and-ask).

- missing `readiness-status.yaml` -> the item's row is "no readiness file"
  (FR-009); a stage with empty `evidence[]` -> "evidence missing"; a `pass` gate
  whose required approval is absent -> "approval not recorded" -- never auto-resolved.

## Scope boundary (read first)

- **Renders, never re-derives.** Every cell is a value copied from the source: a
  per-stage `status` is shown EXACTLY as `readiness-status.yaml` records it. If the
  file says a stage is `pass`, the viewer shows `pass`; it never decides `pass`
  itself. Core Authority owns truth.
- **Read-only.** It never edits a `readiness-status.yaml` or any per-item artifact,
  never advances a stage, never writes a `pass`, never runs SQL, never opens a DB
  connection, never runs `seshat check` / `retail validate` as a new check.
- **Infers no approval.** It RENDERS recorded `approvals[]` (each a named owner +
  date already written by the approving human); it never establishes, fabricates,
  or back-fills an approval, and never treats an unapproved gate as approved.
- **Shows missing evidence AS MISSING.** When a stage's `evidence[]` is empty or a
  referenced file is absent, it renders "evidence missing" / "referenced file not
  found" -- it never invents a reference and never lets a missing-evidence stage
  read as complete.
- **No fake confidence.** Readiness is the four explicit statuses + evidence +
  blockers. The viewer MUST NOT emit a numeric health / confidence / percent-ready
  score (hard rule #9). A score is OPTIONAL and DEFERRED; the viewer is not where
  one appears.
- **Generic.** No worked-example specifics (billing codes, segments, PII column
  names, per-table grain keys). C086 / retail_store_sales are filled instances
  cited as references, never baked in (Principle VII).
- ASCII only, UTF-8 no BOM. The stage spine is written Source Ready -> ... ->
  Publish Ready (ASCII `->`); every dash is `--`.

## Relationship to F012 (same inputs, different lens)

F012 (Data Quality Control Room, shipped, skill
`.claude/skills/retail-control-room/`) is already a read-only cross-table roll-up
of findings + blockers, worst-first, reading the SAME per-item
`readiness-status.yaml`. F026 must be the DELTA, not a re-spec.

Both modules read the SAME Core Authority files; F026 introduces NO new input, NO
new measurement, and NO new pipeline. The difference is the lens:

| Dimension | F012 Control Room (shipped) | F026 Readiness Viewer (this skill) |
|-----------|-----------------------------|------------------------------------|
| Organizing question | "What is broken, how badly, worst-first?" | "Which of the 7 stages has each item reached, with what evidence and approvals?" |
| Stage rendering | `current_stage` + its one status, worst-first | a per-stage MATRIX across all 7 stages |
| `evidence[]` rendering | summarized as MEASURED COUNTS | rendered as NAVIGABLE REFERENCES (path/line per stage) |
| `approvals[]` rendering | not read by F012 | rendered as a chronological TIMELINE |
| Primary axis | severity (findings + blockers, descending) | the stage spine (Source Ready .. Publish Ready) |
| `next_action` | already surfaced | also surfaced (SHARED, NOT a delta) |

The three genuine deltas are exactly: (1) the per-stage status matrix across all
seven stages, (2) `evidence[]` rendered as references rather than counts, and (3)
the `approvals[]` timeline (F012 does not read `approvals[]`). `next_action` is
SHARED with F012 and is NOT a delta.

**Chosen shape: (a).** This ships as a SEPARATE `readiness-viewer` skill that
REUSES F012's existing read-fan-out over the per-item files (one aggregation, two
lenses) -- not a re-implemented scan. The merge fallback (b) is explicit: if the
three deltas ever reduce so that the only durable difference is sort order +
column labels, this should NOT ship as a separate module -- it should fold into
F012 as an optional stage-view section. Shape (a) holds because the stage matrix
reveals WHERE in the seven-stage progression an item sits, evidence-as-reference
lets a reviewer OPEN the backing file, and the approvals timeline answers "who let
this advance, when" -- each gives a reader something the control room cannot.

## Renders, never re-derives (the evidence chain)

Every rendered element traces back to a recorded field -- a re-render, not a
measurement. A rendered value with no traceable source is a defect.

| Rendered element | Source field it copies VERBATIM |
|------------------|---------------------------------|
| each matrix cell (per-stage status) | `readiness-status.yaml` `stages.<stage>.status` |
| the marked current stage | `readiness-status.yaml` `current_stage` |
| the single next action | `readiness-status.yaml` `next_action` |
| each evidence reference | `readiness-status.yaml` `stages.<stage>.evidence[]` (each entry as-recorded) |
| each timeline approval | `readiness-status.yaml` `approvals[]` ({stage, owner, at}) |
| which gates require an approval | `docs/readiness/<stage>-ready.md` "Required owner / approval" |

## Run it -- produce the stage-centric view

Render `templates/readiness-view.md` filled from the per-item evidence, reusing
F012's read-fan-out for discovery.

### 1. The seven-stage status matrix (the MVP)

Discover items exactly as F012 does: scan each `mappings/<item>/` directory for a
`readiness-status.yaml` (ADR 0004 canonical location); emit one matrix row per
discovered file. Add NO second discovery path and invent NO row for an item with no
file. For each item, emit a row x seven stage columns (Source Ready -> Mapping
Ready -> Silver Ready -> Gold Ready -> Semantic Model Ready -> Dashboard Ready ->
Publish Ready); each cell is the `stages.<stage>.status` copied VERBATIM (one of
`not_started` / `blocked` / `warning` / `pass`). Mark `current_stage`. Show the
single `next_action`. Never recompute or upgrade a status -- a stage the file
records as `not_started` shows `not_started`.

### 2. Evidence rendered as navigable references

For each stage, render every `evidence[]` entry as its committed reference, copied
VERBATIM: if the entry carries a line/section anchor, render it with that anchor;
if it is a bare committed path, render the bare path. NEVER synthesize a line
number or section anchor the source does not record (that is fabricated evidence).
A stage with empty `evidence[]` renders "evidence missing" and NAMES the expected
artifact; a `pass` stage with empty `evidence[]` renders "evidence missing for a
pass stage" as an explicit flag (a `pass` without evidence is surfaced, never
hidden). An `evidence[]` entry whose referenced file is absent on disk renders the
reference marked "referenced file not found" -- the entry is never dropped and
never replaced with an invented one.

### 3. The approvals timeline

Render `approvals[]` as a chronological timeline: each approval as {stage/gate,
named owner, date} in date order, copied VERBATIM. Flag a `pass` gate "approval not
recorded" ONLY when BOTH conditions hold: (a) that stage's
`docs/readiness/<stage>-ready.md` "Required owner / approval" field declares an
approver IS required, AND (b) no matching `approvals[]` entry exists. Where the
stage doc records NO required approver (e.g. a mechanical gate whose doc reads
"None -- mechanical ... No human approval is added at this stage"), an empty
`approvals[]` is NORMAL and MUST NOT be flagged. The viewer reads the requirement
from the stage doc; it NEVER decides the requirement itself and NEVER infers,
establishes, or back-fills an approver (no-self-approval; Principle V).

### 4. Surface conflicts (never resolve them)

Surface, as explicit flags, never reconciled: `current_stage` disagreeing with the
per-stage statuses (e.g. `current_stage: gold_ready` but Silver Ready recorded
`blocked`); a `pass` stage with empty `evidence[]`; an approval that references a
stage the matrix shows as `not_started`. The viewer is a lens, not an arbiter -- it
does NOT resolve a conflict by picking one side.

### 5. Traceability

For every rendered value, be able to name the exact committed source path (and
line/section where the source records it). If asked "where does this come from",
answer with the path -- not a recomputation.

## No fake confidence (the guardrail)

If asked for "one readiness score", "a percent-ready per item", or "a confidence
number", DECLINE: cite `docs/readiness/readiness-model.md` "No fake confidence (the
scoring rule)" -- readiness is explicit status + evidence + blockers, not a
confidence score -- and return the four explicit statuses across the seven stages
instead. A stage matrix is exactly where a tidy invented score is tempting; it is
forbidden (hard rule #9). Any future optional score is DEFERRED until scoring rules
exist in the readiness model.

## Honest-state rules (never invent, never silently resolve)

| Situation | What the viewer does |
|-----------|----------------------|
| Zero items with a readiness file | render an empty matrix + a clear "no items onboarded yet" note; do not error, do not invent rows |
| A `readiness-status.yaml` malformed / partial | show that item "readiness file incomplete: `<file>`" for the affected fields; do NOT guess the missing stage statuses or evidence (FR-009) |
| `current_stage` disagrees with per-stage statuses | SURFACE the conflict as a flag; do NOT resolve it by picking one (Principle V) |
| A stage is `pass` with empty `evidence[]` | surfaced as "pass without evidence", an explicit flag; never hidden |
| An approval references a `not_started` stage | shown as a conflict flag; the stray approval is not reconciled or deleted |
| A `pass` gate whose stage doc requires an approver, with no matching `approvals[]` entry | flagged "approval not recorded"; an approver is NEVER inferred |

## Read-only proof

The skill modifies nothing: after a run, `git status` shows zero modified
`mappings/<item>/readiness-status.yaml` or per-item artifact, and zero
`approvals[]` entries added by the viewer. It triggers no state-mutating
`seshat check` / `retail validate` run of its own.

## See also

- The output shape: `templates/readiness-view.md`; the usage + boundary doc:
  `docs/tools/readiness-viewer.md`.
- The headline overlap it is the delta of (F012): the skill
  `.claude/skills/retail-control-room/SKILL.md`, the template
  `templates/data-quality-control-room.md`.
- The Core Authority input it renders: `templates/readiness-status.yaml`
  (`current_stage`, per-stage `status`, `evidence[]`, `blocking_reasons[]`,
  `approvals[]`, `next_action`); ADR 0004 (canonical
  `mappings/<table>/readiness-status.yaml` location).
- The module category + read-only contract: `docs/architecture/product-modules.md`,
  `docs/architecture/core-vs-modules-and-adapters.md`,
  `templates/module-contract.md` (F024 Companion Tools Architecture,
  `specs/018-companion-tools-architecture/`).
- The model + no-fake-confidence rule: `docs/readiness/readiness-model.md`; the
  stage sequence: `docs/readiness/readiness-pipeline.md`; the "Required owner /
  approval" field per stage: `docs/readiness/<stage>-ready.md`.
- The roadmap row + hard rules: `docs/roadmap/roadmap.md` (F026; rules #7/#8/#9);
  Principles V, VII, VIII, IX. retail_store_sales is a cited filled
  instance: `docs/worked-examples/retail-store-sales.md` (a filled worked
  example under `docs/worked-examples/`).

## Orchestration

When items are driven end-to-end, the `retail-orchestrate` conductor may invoke the
viewer as the stage-progression READ after sequencing an item -- to see where the
item sits across all seven stages, what backs each gate, and who approved it. This
skill reads state and reports; it advances no stage and clears no blocker. Moving a
stage to `pass`, recording an approval, and clearing a blocker all remain Core
Authority actions by the named owner, never the viewer (Principle V;
no-self-approval).
