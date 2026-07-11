# Feature Specification: CVD (Colorblind) Simulation Evidence Aid -- read-only colour-vision-deficiency simulation evidence for the named-OPEN accessibility checkbox

**Feature Branch**: `118-cvd-simulation-evidence`

**Created**: 2026-07-10

**Status**: Draft

**Input**: User description: "CVD (Colorblind) Simulation Evidence Aid -- a read-only design-review evidence aid that, given a committed Power BI theme (its categorical dataColors palette + any sequential/diverging ramps), applies deterministic protanope/deuteranope/tritanope colour-vision-deficiency simulation transforms (beside the shipped delta_e76 in src/retail/color.py) and emits a read-only evidence markdown: the simulated swatches plus the under-simulation pairwise deltaE for each colour pair, so a NAMED human reviewer can fill the literal `- [ ] **CVD distinguishability** -- OPEN` checkbox that the shipped theme_gen.py renderer (theme_gen.py:569) itself leaves open. It emits EVIDENCE for a human, never a pass and never a score."

## Clarifications

### Session 2026-07-10

- Q: What EXACTLY is the input theme, and what colours are simulated? -> A: The
  input is ONE committed Power BI theme JSON at a caller-supplied path (the same
  `themes/*.theme.json` shape the shipped `theme-compile` / `pbir-apply-theme`
  verbs already read). The colours simulated are the theme's `dataColors` array
  (the categorical palette) plus, when present, any declared sequential/diverging
  ramp stops. Text/background foreground colours are NOT this aid's concern (that
  is CT1's normal-vision contrast lane). The aid reads the committed theme AS
  GIVEN and simulates the colours it declares; it invents no colour and edits no
  theme value.
- Q: What are the three simulations, and are they deterministic? -> A: Three fixed
  colour-vision-deficiency types -- protanope (no long-wave/red cones),
  deuteranope (no medium-wave/green cones), tritanope (no short-wave/blue cones).
  Each is a DETERMINISTIC, closed-form colour transform (a documented linear
  colour-space projection) that maps a normal-vision colour to how it appears
  under that deficiency. Same theme -> byte-identical evidence every run (no
  randomness, no data, no model). The transforms sit beside the shipped
  `delta_e76` perceptual-distance function in `src/retail/color.py`, and the
  evidence reuses `delta_e76` to measure pairwise distance AFTER simulation.
- Q: What is the evidence, and how is hard rule #9 (no fabricated confidence
  score) honoured? -> A: For each simulation type the aid emits (a) the simulated
  swatch value for every palette colour and (b) the pairwise `delta_e76` distance
  between every colour PAIR computed on the simulated colours -- i.e. "under
  deuteranope simulation, palette[1] and palette[4] are deltaE 4.2 apart". A
  per-pair deltaE is a MEASUREMENT of an already-shipped, already-used distance
  metric and is ALLOWED (the shipped CT2/CT3 rules already surface pairwise
  deltaE). What is FORBIDDEN (hard rule #9): any rolled-up single "CVD score", any
  pass/fail verdict on a threshold, any ranking of themes, any count presented as
  a quality index, and any statement that the palette IS or IS NOT colorblind-safe.
  The aid presents the measured pairs and NAMES which pairs collapse closest under
  each simulation as an ORDERED-BY-MEASURED-DISTANCE reading aid (the ordering is a
  presentation of the measured deltaE values, never a new computed rank); the human
  reviewer reads the evidence and decides.
- Q: What is the output vehicle -- printed or a written companion file, and WHERE
  is it written? -> A: A written companion evidence file, with an optional
  `--format json` machine shape, MIRRORING the shipped DL4 design-review-evidence
  precedent (which writes a review-evidence markdown a human cites), NOT the
  print-only posture of specs 115/116. Rationale: the CVD evidence is a DURABLE
  design-review artifact a named reviewer cites when filling the OPEN checkbox
  (exactly F035/DL4/spec-114 territory: durable disclosure -> companion file),
  whereas 115/116 are transient triage answers -> print-only. LOCATION: because the
  INPUT is a repo-global theme (`themes/*.theme.json`) and a theme is NOT 1:1 with a
  table -- a single theme (e.g. `themes/tower-retail.theme.json`) can back MANY
  tables, referenced by each table's design artifacts as `palette_source` -- there
  is NO deterministic theme -> table resolution, so the evidence MUST NOT default to
  a per-table path. The DEFAULT output is THEME-ADJACENT
  (`themes/<theme-name>.cvd-simulation-evidence.md`), matching the theme-scoped input
  and keeping the aid generic over any committed theme (Principle VII). A `--out
  <path>` override lets a reviewer place the evidence into a specific table's design
  review record (`mappings/<table>/design/`) WHEN they choose to; the aid never
  infers that table itself. The written file is EVIDENCE with a BLANK reviewer slot;
  it is never `readiness-status.yaml`, never the theme, and never the checkbox
  itself.
- Q: Does the aid check the OPEN box or advance any stage? -> A: NO. The literal
  `- [ ] **CVD distinguishability** -- OPEN` checkbox that `theme_gen.py:569`
  renders stays a BLANK human field. This aid produces the evidence a named
  reviewer needs to make that call; it never ticks the box, never sets
  `colorblind_considerate_categoricals: true`, never moves `dashboard_ready` or any
  stage, and adds NO `retail check` rule (Principle V, `never_self_grant_approval`).

## Why this feature exists

The shipped Power BI design foundation reasons about colour ONLY under normal
vision. Its three shipped colour rules all use normal-vision maths:
`CT1` (text/background contrast), `CT2` = `design_categorical_distinctness`
(adjacent/categorical deltaE), and `CT3` = `design_ramp_deltae` (whole-set
normal-vision deltaE) -- and `CT3`'s own docstring explicitly disclaims a
colorblind-safe claim. There is a real, named hole: the shipped theme renderer
`src/retail/theme_gen.py` emits, at line 569, a LITERAL unchecked review box
`- [ ] **CVD distinguishability** -- OPEN: ...`, and sets
`colorblind_considerate_categoricals: false` (line 470), leaving colour-vision
deficiency (CVD) as a checkbox no shipped surface can help a reviewer answer.

Colour-vision deficiency affects roughly 8% of male readers -- it is the single
accessibility class the foundation currently cannot reason about, and the renderer
itself flags it OPEN. Today a design reviewer asked to fill that box has no
evidence: they must eyeball the palette or reach for an external tool, exactly the
manual, drift-prone assembly the kit exists to remove.

This feature is the missing evidence aid. Given a committed theme, it applies three
deterministic CVD simulation transforms (protanope / deuteranope / tritanope) to
the palette, then reuses the SHIPPED `delta_e76` perceptual-distance function
(`src/retail/color.py:83`) to measure how far apart each colour PAIR sits AFTER
each simulation, and emits a read-only evidence markdown of simulated swatches +
under-simulation pairwise deltaE. The named human reviewer reads that evidence and
fills the OPEN checkbox. The aid ORIGINATES no verdict, computes no rolled-up
score, edits no theme, and moves no stage: it manufactures the evidence, the human
makes the call.

## What this feature is NOT (the scope wall)

The surface's subject (accessibility, "distinguishability") is itself the risk
flag; this wall is load-bearing and stated up front so the spec cannot drift.

- **It computes NO rolled-up score and asserts NO safe/unsafe verdict** (hard rule
  #9). A per-pair `delta_e76` measurement under a named simulation is a
  MEASUREMENT (the shipped CT2/CT3 rules already surface pairwise deltaE), and is
  ALLOWED. FORBIDDEN: any single "CVD score", any pass/fail threshold verdict, any
  ranking of themes, any count framed as a quality index, and any statement that a
  palette IS or IS NOT colorblind-safe. The aid presents measured pairs (optionally
  ordered by the measured distance as a reading aid); it never emits a new computed
  rank or a rolled-up number.
- **It does NOT tick the OPEN checkbox and moves NO readiness stage.** The
  `- [ ] **CVD distinguishability** -- OPEN` box (`theme_gen.py:569`) stays a BLANK
  human field; the aid never sets `colorblind_considerate_categoricals: true`,
  never touches `readiness-status.yaml`, and never moves `dashboard_ready` or any
  stage. `never_self_grant_approval` (Principle V) holds absolutely.
- **It is a SIMULATOR + MEASURER over a committed theme, never a theme author.** It
  reads the already-committed theme JSON and simulates the colours it declares. It
  invents no colour, edits no `dataColors`, authors no theme value, and writes back
  nothing to the theme. It generates no DAX and authors no PBIP/PBIR.
- **It adds NO `retail check` rule and is NOT a gate.** Its presence/absence is not
  a gate requirement; it neither enforces nor requires any readiness gate. It is an
  OPTIONAL design-review evidence companion (DL4/spec-114 posture), never a
  precursor to a stage `pass`.
- **It opens NO connection.** No DB, Power BI, or network connection; pure
  deterministic colour arithmetic over a committed on-disk theme JSON.
- **It is generic (Principle VII).** Operates over ANY committed theme's declared
  tokens; no hardcoded brand colours, palette values, table names, or C086/pharmacy
  specifics baked into the transforms or the evidence.
- **It is distinct from the shipped CT-family rules.** CT1/CT2/CT3 all operate on
  normal-vision colour maths and none simulates CVD confusion. This aid complements
  them by adding the one lens they lack; it restates none of them and adds no
  competing normal-vision check.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A reviewer gets CVD simulation evidence to fill the OPEN checkbox (Priority: P1)

A design reviewer asked to fill the `- [ ] **CVD distinguishability** -- OPEN`
checkbox for a committed theme runs the aid against that theme. The aid applies the
three deterministic CVD simulations to the palette, measures the pairwise
`delta_e76` distance between every colour pair under each simulation, and emits a
read-only evidence markdown: the simulated swatch values per simulation type and
the under-simulation pairwise deltaE for each pair, with the closest-collapsing
pairs surfaced (ordered by the measured distance) so the reviewer can see at a
glance which palette colours become hard to tell apart for each deficiency type.
The reviewer reads the evidence and fills the checkbox; the aid ticks nothing.

**Why this priority**: This is the whole feature -- the CVD simulation evidence
grounded in the committed theme is the net-new capability no shipped surface
provides, and it directly fills the named-OPEN hole the renderer itself flags.
Without it there is no MVP.

**Independent Test**: Run the aid against a committed theme whose palette contains
a red/green pair that is well-separated under normal vision; confirm the evidence
reports a materially smaller under-deuteranope `delta_e76` for that pair than its
normal-vision distance, that all three simulation types are present, that the
OPEN checkbox and `colorblind_considerate_categoricals` value are untouched, and
that no rolled-up "CVD score" or safe/unsafe verdict appears anywhere.

**Acceptance Scenarios**:

1. **Given** a committed theme JSON with a `dataColors` categorical palette,
   **When** the aid runs, **Then** the evidence contains, for EACH of the three
   simulation types (protanope, deuteranope, tritanope), the simulated swatch value
   for every palette colour and the pairwise `delta_e76` distance for every colour
   pair computed on the simulated colours.
2. **Given** the same theme, **When** the aid composes the evidence, **Then** it
   surfaces the closest-collapsing pairs per simulation type ordered by the measured
   `delta_e76` value (a presentation of the measured distances), and emits NO
   rolled-up score, NO pass/fail verdict, NO ranking of themes, and NO "is/ is not
   colorblind-safe" statement.
3. **Given** a run, **When** it completes, **Then** the theme JSON is unchanged, the
   `- [ ] **CVD distinguishability** -- OPEN` checkbox rendered by `theme_gen` is
   still unchecked, `colorblind_considerate_categoricals` is unchanged, and
   `readiness-status.yaml` is unchanged.

---

### User Story 2 - The evidence is a durable review artifact with a blank reviewer slot (Priority: P1)

The reviewer must be able to CITE the evidence when they fill the OPEN checkbox, so
the aid writes a durable companion evidence file (theme-adjacent by default, or at a
reviewer-supplied `--out` path) containing the simulated swatches, the
under-simulation pairwise deltaE, and a BLANK named-reviewer slot (mirroring the
shipped DL4 design-review-evidence artifact). Every measured value in the file must
be traceable to the committed theme colour it was computed from; the aid composes
nothing beyond the simulation maths and the reused `delta_e76`.

**Why this priority**: Equal-P1 with Story 1. A transient printed answer could not
be cited as design-review evidence; the durable, blank-slot companion file is what
makes the evidence usable in the review record and keeps the reviewer decision a
human action (the slot is theirs to fill, not the aid's).

**Independent Test**: Run the aid and confirm it writes exactly one companion file
at the theme-adjacent default path (or the `--out` path when supplied), that the
file carries a blank named-reviewer / decision slot (no pre-filled verdict), that
every reported deltaE is reproducible by re-computing `delta_e76` on the simulated
colours of the named theme pair, and
that a second run on the unchanged theme produces a byte-identical file.

**Acceptance Scenarios**:

1. **Given** a committed theme, **When** the aid runs, **Then** it writes exactly
   one durable companion evidence file (with an optional machine `--format json`
   shape) and that file contains a BLANK named-reviewer/decision slot with no
   pre-filled pass, verdict, or score.
2. **Given** the written evidence, **When** any reported under-simulation deltaE is
   audited, **Then** it is reproducible by applying the named simulation transform
   and `delta_e76` to the two named committed palette colours (100% derived from the
   committed theme; no fabricated value).
3. **Given** an unchanged theme, **When** the aid is run twice, **Then** the two
   evidence files are byte-identical (deterministic; no randomness, timestamp, or
   data-dependent content in the measured body).

---

### User Story 3 - A theme with no palette or an unreadable theme is surfaced, not fabricated (Priority: P2)

A reviewer running the aid against a theme that declares no `dataColors` palette
(or a malformed/unreadable theme) must get an honest signal -- "no palette to
simulate at <path>" -- rather than fabricated swatches or an empty verdict that
reads as "simulated and found distinguishable".

**Why this priority**: Robustness at the input boundary. It protects the trust
guarantee when the input is thin or malformed, but is secondary to the core
evidence behaviour.

**Independent Test**: Point the aid at a theme JSON with an empty/absent
`dataColors` array (and separately at a malformed JSON); confirm it names what was
checked, states plainly that there is no palette to simulate, fabricates no swatch
or deltaE, and never presents the absence as a distinguishability result.

**Acceptance Scenarios**:

1. **Given** a theme with no `dataColors` palette (or fewer than two colours to
   pair), **When** the aid runs, **Then** it names the theme path checked, states
   there is no palette (or no pair) to simulate, and fabricates no swatch, pair, or
   deltaE.
2. **Given** a malformed/unreadable theme JSON, **When** the aid runs, **Then** it
   reports the theme could not be read at the named path and produces no fabricated
   evidence, never presenting an unreadable input as a distinguishability result.

---

### Edge Cases

- A palette with a single colour (no pair to measure) -> the aid reports the
  simulated swatch for that one colour under each simulation type but states there
  is no colour PAIR to measure distance for; it fabricates no pair.
- Two palette colours that are IDENTICAL under normal vision -> their
  under-simulation deltaE is (correctly) ~0 for every simulation; the aid reports
  the measured value and does not treat "already identical" as a CVD finding of its
  own (it measures, it does not judge).
- A theme declaring sequential/diverging ramp stops in addition to the categorical
  palette -> ramp stops are simulated and measured the same way (pairwise deltaE
  along declared stops), reported in a distinct section from the categorical
  palette; the aid never conflates ramp stops with categorical colours.
- A colour value in a form the shipped colour parser cannot read (e.g. a named
  colour or an unsupported notation) -> the aid names the unreadable colour, skips
  it from the pairwise measurement, and never guesses a hex value to stand in for
  it (no fabrication).
- A very large palette (many pairs) -> the aid reports all measured pairs (it does
  not silently cap); if any presentation limit is applied it is stated explicitly
  and no pair is dropped from the machine `--format json` output.
- A reviewer expecting a yes/no answer -> the evidence explicitly states it is
  measured evidence for a human decision, names the OPEN checkbox it supports, and
  does NOT answer "safe/unsafe" itself.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The aid MUST accept a caller-supplied path to ONE committed Power BI
  theme JSON and read its declared `dataColors` categorical palette (and any
  declared sequential/diverging ramp stops) AS GIVEN, inventing and editing no
  colour value.
- **FR-002**: The aid MUST apply THREE deterministic colour-vision-deficiency
  simulation transforms -- protanope, deuteranope, tritanope -- each a documented
  closed-form colour-space transform with no randomness, so the same theme yields
  byte-identical simulated colours every run.
- **FR-003**: The aid MUST measure, for each simulation type, the pairwise
  perceptual distance between every colour pair computed on the SIMULATED colours,
  reusing the shipped `delta_e76` perceptual-distance function (a MEASUREMENT, per
  Clarification Q3), and MUST report the simulated swatch value for every palette
  colour under each simulation type.
- **FR-004**: The aid MUST NOT compute or emit any rolled-up "CVD score",
  pass/fail threshold verdict, ranking of themes, count framed as a quality index,
  or any statement that the palette IS or IS NOT colorblind-safe (hard rule #9). It
  MAY surface the closest-collapsing pairs ORDERED BY the measured `delta_e76`
  value as a presentation of the measured distances, which MUST NOT be a new
  computed rank or a rolled-up number.
- **FR-005**: The aid MUST NOT tick the `- [ ] **CVD distinguishability** -- OPEN`
  checkbox, MUST NOT set `colorblind_considerate_categoricals` or any theme value,
  MUST NOT edit the theme JSON, and MUST move no readiness stage or touch
  `readiness-status.yaml` (Principle V, `never_self_grant_approval`).
- **FR-006**: The aid MUST write exactly one durable companion evidence file (with
  an optional machine `--format json` shape) containing the simulated swatches, the
  under-simulation pairwise `delta_e76` values, and a BLANK named-reviewer/decision
  slot with no pre-filled pass, verdict, or score (DL4 design-review-evidence
  posture). The DEFAULT location MUST be theme-adjacent
  (`themes/<theme-name>.cvd-simulation-evidence.md`) because the theme input is
  repo-global and NOT 1:1 with a table (Clarification Q4); the aid MUST NOT infer a
  `<table>` from a theme path or default to a per-table location. A `--out <path>`
  override MUST be supported so a reviewer MAY place the evidence into a specific
  table's design review record; the aid writes only the one file (the chosen
  location), and no other.
- **FR-007**: Every reported simulated swatch and every reported under-simulation
  deltaE MUST be 100% derived from the committed theme colours it names -- auditably
  reproducible by applying the named simulation transform and `delta_e76` to the
  named committed colour(s) -- with no fabricated value and no other source of
  content.
- **FR-008**: When the theme declares no palette (or fewer than two colours to
  pair), or the theme JSON is malformed/unreadable, the aid MUST name the path
  checked and state plainly that there is no palette/pair to simulate (or that the
  theme could not be read), fabricating no swatch, pair, or deltaE, and never
  presenting the absence/unreadability as a distinguishability result.
- **FR-009**: The aid MUST add NO `retail check` rule and MUST be gate-agnostic:
  its presence/absence MUST NOT be a gate requirement and it MUST neither enforce
  nor require any readiness gate.
- **FR-010**: The aid MUST open no DB, Power BI, or network connection, author no
  PBIP/PBIR, and generate no DAX; it performs pure deterministic colour arithmetic
  over a committed on-disk theme JSON.
- **FR-011**: The aid MUST be generic across themes (Principle VII): no hardcoded
  brand colours, palette values, table names, page names, or C086/pharmacy
  specifics baked into the transforms or the evidence; it operates over whatever
  committed theme it is given.
- **FR-012**: The evidence MUST be deterministic and stable: re-running on an
  unchanged theme yields a byte-identical evidence file (no randomness, no wall-clock
  timestamp, no data-dependent content in the measured body). Every reported
  `delta_e76` value MUST be formatted at a FIXED decimal precision so byte-identical
  output holds across platforms (float formatting is pinned, not left to the
  platform default). Tie ordering among equal measured distances MUST use a fixed
  lexical secondary order so no computed value is needed to break ties.
- **FR-013**: The aid MUST be distinct from and additive to the shipped CT-family
  rules (CT1 contrast, CT2 categorical distinctness, CT3 ramp deltaE), all of which
  operate on normal-vision colour maths; it MUST NOT restate them or add a competing
  normal-vision check, and its evidence MUST make the CVD-simulation lens explicit.
- **FR-014**: Output MUST be ASCII-only, UTF-8 without BOM, using `--` and `->`
  (no glyphs), with short repo-relative paths (Windows 260-char budget); the
  evidence MUST name the OPEN checkbox and the theme path it supports.

### Key Entities *(include if feature involves data)*

- **Committed theme (input)**: one committed Power BI theme JSON at a
  caller-supplied path, whose declared `dataColors` categorical palette (and any
  declared ramp stops) are the colours simulated. Read AS GIVEN; never edited.
- **CVD simulation**: one of the three fixed deficiency types (protanope,
  deuteranope, tritanope), each a deterministic closed-form colour transform that
  maps a normal-vision colour to its appearance under that deficiency.
- **Under-simulation pairwise measurement**: for a simulation type and a pair of
  palette colours, the `delta_e76` perceptual distance between their SIMULATED
  values -- a measurement (allowed), never a rolled-up score.
- **Evidence artifact (output)**: the durable companion markdown (with optional
  JSON shape) written theme-adjacent by default
  (`themes/<theme-name>.cvd-simulation-evidence.md`), or at a reviewer-supplied
  `--out` path (e.g. into a table's `mappings/<table>/design/` review record):
  simulated swatches + under-simulation pairwise deltaE + a BLANK
  named-reviewer/decision slot. Never the theme, never `readiness-status.yaml`,
  never the checkbox itself.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer running the aid against a committed theme receives, for all
  three simulation types, the simulated swatches and the under-simulation pairwise
  `delta_e76` for every colour pair, WITHOUT opening any external colorblindness
  tool or hand-computing a transform.
- **SC-002**: The output contains zero rolled-up "CVD scores", pass/fail verdicts,
  theme rankings, quality-index counts, or "is/ is not colorblind-safe" statements
  (verifiable by inspection: only per-pair measured distances and simulated swatch
  values appear).
- **SC-003**: After a run, the theme JSON is unchanged, the
  `- [ ] **CVD distinguishability** -- OPEN` checkbox is still unchecked,
  `colorblind_considerate_categoricals` is unchanged, and `git status` shows no
  modification to any file other than the single companion evidence file the aid
  writes.
- **SC-004**: Every reported under-simulation deltaE is reproducible by applying the
  named simulation transform and `delta_e76` to the two named committed colours (no
  fabricated value), demonstrated by auditing at least one red/green pair whose
  under-deuteranope distance is materially smaller than its normal-vision distance.
- **SC-005**: For a theme with no palette (or an unreadable theme), the aid reports
  the absence/unreadability naming the path checked and fabricates no swatch, pair,
  or deltaE; in no case is the absence presented as "simulated and found
  distinguishable".
- **SC-006**: The aid produces correct evidence for any conformant theme with no
  code change (generic), demonstrated on at least two distinct committed themes.
- **SC-007**: Running the aid twice on an unchanged theme yields byte-identical
  evidence files (deterministic).

## Assumptions

- The committed theme JSON (`themes/*.theme.json` shape) is produced UPSTREAM by the
  shipped theme-authoring path (`theme-gen` / `theme-compile`) and is already
  committed before the aid runs; this feature READS that theme as its input and
  never authors, edits, or gates it. (Grounded: `src/retail/theme_gen.py:569`
  emits the literal `- [ ] **CVD distinguishability** -- OPEN` checkbox and line
  470 sets `colorblind_considerate_categoricals: false`; `src/retail/color.py:83`
  ships `delta_e76`.)
- The perceptual-distance MECHANISM is NOT invented here: the aid reuses the shipped
  `delta_e76` function (already used by CT2/CT3) applied to simulated colours. Only
  the three CVD simulation transforms are net-new colour maths, and they are
  standard documented closed-form transforms, not a model or a heuristic.
- Verified net-new against `main`: no shipped `src/retail` surface, CLI verb, or
  `retail check` rule performs CVD simulation. `CT1` (contrast),
  `CT2` = `design_categorical_distinctness`, and `CT3` = `design_ramp_deltae` all
  operate on normal-vision colour maths (CT3's docstring disclaims a colorblind-safe
  claim); none simulates CVD confusion. This aid is the missing lens.
- The aid is an OPTIONAL design-review evidence companion following the shipped DL4
  design-review-evidence and spec-114 durable-disclosure posture; it is never a
  prerequisite for any readiness stage and is gate-agnostic.
- The OUTPUT VEHICLE (a durable companion file, theme-adjacent by default with a
  `--out` override, NOT a per-table default -- there is no theme -> table
  resolution) is fixed by Clarification Q4; the EXACT surface mechanism (a
  standalone read-only runtime module + CLI verb beside the shipped design-evidence
  surfaces vs a skill), the exact theme-adjacent filename convention, and the exact
  machine `--format json` shape are implementation decisions for the plan phase. The spec fixes the BEHAVIOUR
  (three deterministic simulations, per-pair `delta_e76` measurement, no rolled-up
  score, no checkbox tick, durable blank-slot evidence, honest absence), not the
  mechanism.
- The three CVD simulation transforms are documented, deterministic colour-space
  projections; the specific published transform matrices are an implementation
  choice for the plan phase, constrained only by determinism (FR-002/FR-012) and by
  producing an auditable, reproducible result (FR-007).
