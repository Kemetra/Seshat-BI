# Feature Specification: Land bi-python's Planned Cleaning Artifacts

**Feature Branch**: `067-bi-python-cleaning-artifacts`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "I2. Land bi-python's Planned Cleaning Artifacts"

## Overview

The `skills/bi-python-knowledge` layer ships one LIVE cleaning route
("Clean / standardize strings, categories, currency, units, sentinels, or
duplicates") that routes to `knowledge/cleaning-and-standardization.md`. That
knowledge file, its `INDEX.md` route, and three inline notes (PY-CN-033,
PY-CN-036, and the "Ends on" block) all declare the route's TRUE terminal
artifact -- `checklists/cleaning-review-checklist.md` -- as "planned / not yet
implemented". A live route therefore dead-ends on a promised-but-absent
artifact.

This feature lands exactly that one terminal checklist and flips its route
status from planned to live. It is targeted content completion, not an
open-ended build: it distils reasoning that ALREADY exists in
`cleaning-and-standardization.md` (the row-count ledger, the 8-step cleaning
order-of-operations, the human-reserved decisions) into a checkbox-plus-verdict
review artifact that mirrors the SHAPE of the already-shipped
`checklists/aggregation-grain-checklist.md`. It adds NO runtime code, NO new
static-analysis rule, and NO new metric or gating logic.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cleaning route ends on a real artifact (Priority: P1)

An agent (or reviewer) follows the live "clean / standardize" route into
`knowledge/cleaning-and-standardization.md`, reaches the "Ends on" block, and is
sent to a checklist that actually exists. The agent walks the checklist against a
cleaned dataframe and produces a categorical cleaning verdict plus the row-count
ledger, then hands off.

**Why this priority**: This is the entire point of I2 -- it removes the one
concrete live-route-ends-on-planned-artifact dead-end in the layer. Without it,
the layer's own stop rule ("if you cannot name the artifact you will end on, you
are not ready to start") is violated by a shipped route.

**Independent Test**: Open `INDEX.md`, follow the cleaning task route, follow the
"Ends on" pointer, and confirm it resolves to a shipped file whose sections cover
the cleaning concerns the knowledge file raises (string/category standardization,
currency/numeric coercion, sentinels/out-of-range, deduplication, grain and
row-count accountability, source-value traceability) and ends on a verdict.

**Acceptance Scenarios**:

1. **Given** the cleaning knowledge file's "Ends on" block, **When** a reader
   follows the checklist pointer, **Then** the file
   `checklists/cleaning-review-checklist.md` exists and is reachable.
2. **Given** a cleaned dataframe and its cleaning steps, **When** the reviewer
   walks the checklist, **Then** every checklist item traces to an existing
   PY-CN-* / PY-BP-* / PY-AP-* ID already defined for cleaning, and the review
   ends on one categorical verdict plus an attached row-count ledger.

---

### User Story 2 - Router honestly reflects the flip (Priority: P1)

A reader consulting `INDEX.md` sees the cleaning-review checklist listed as a
LIVE artifact (not under "Planned routes"), and every inline "planned" note that
pointed at the endpoint (the cleaning route note, PY-CN-033, PY-CN-036, the
"Ends on" block, the README "Not yet complete" claim) now reflects that the
checklist has landed -- while every OTHER planned sibling stays marked planned.

**Why this priority**: A half-flip (file lands but the router still says
"planned", or the router flips but stale inline notes still say "not yet
implemented") is a new integrity gap, arguably worse than the original honest
dead-end. The flip must be complete and must NOT over-claim by flipping unrelated
siblings.

**Independent Test**: Grep the skill for the checklist's path and for "planned /
not yet implemented"; confirm no surviving reference calls the cleaning-review
checklist planned, and confirm the untouched planned siblings
(`profiling-and-source-inspection.md`, `pandas-dtypes-and-schema.md`,
`validation-and-reconciliation.md`, `groupby-aggregation-and-grain.md`, the other
planned checklists) are STILL marked planned.

**Acceptance Scenarios**:

1. **Given** `INDEX.md`, **When** the reader scans the Planned-routes table,
   **Then** the "Cleaning review checklist" row is gone from it and the checklist
   appears in the live tables / file map instead.
2. **Given** the inline notes in `cleaning-and-standardization.md` (PY-CN-033,
   PY-CN-036, "Ends on") and the README "Not yet complete" list, **When** the
   reader checks each, **Then** none of them still describe the cleaning-review
   checklist as planned, and none of the aggregation/profiling/dtype/validation
   siblings were flipped.

---

### User Story 3 - Fork boundaries stay intact (Priority: P2)

A reader comparing the new cleaning checklist to the shipped aggregation-grain
checklist and to the big-data sibling finds no duplicated ownership: the cleaning
checklist REFERENCES the aggregation-grain checklist for groupby/additivity/grain
rather than restating it, and stays single-node (routes distributed cleaning to
`skills/bi-bigdata-knowledge/`).

**Why this priority**: The idea explicitly requires keeping the
"aggregation-grain-checklist fork boundary intact". Duplicating grain/additivity
content into the cleaning checklist would fork ownership of a concern the
aggregation checklist already owns, creating drift risk. This is a boundary
guarantee, not new content, so P2.

**Independent Test**: Read the new checklist; confirm any groupby/grain/
additivity concern is a one-line reference to
`checklists/aggregation-grain-checklist.md` (not a restated checklist section),
and confirm any large-data / distributed concern is a one-line handoff to
`skills/bi-bigdata-knowledge/` (not an absorbed section).

**Acceptance Scenarios**:

1. **Given** the new checklist, **When** grain/additivity is relevant, **Then**
   it cites the aggregation-grain checklist as the owner and does not re-own it.
2. **Given** the new checklist, **When** scale/distribution is relevant, **Then**
   it hands off to the big-data sibling and does not absorb distributed concerns.

---

### Edge Cases

- What happens when a cleaning decision is one the layer already RESERVES for a
  human (sentinel-vs-null meaning, category-domain updates, deduplication
  keep-policy, out-of-range keep-vs-flag)? The checklist item MUST be phrased as
  a "recorded by a human" checkbox, never an instruction the agent auto-resolves
  (Principle V analog).
- What happens if a checklist author reaches for concrete C086 pharmacy
  specifics (billing codes, insurance/PII columns) to illustrate an item? The
  checklist MUST use only the fictional retail schema
  (`references/retail-dataframe-schema.md`); C086 may be cited at most as an
  external worked example (`docs/worked-examples/c086-pharmacy.md`), never with
  inline pharmacy values (Principle VII / hard rule 7).
- What happens if a reader wants a numeric "cleanliness score"? The verdict MUST
  be a categorical status set (mirroring the aggregation checklist's four
  verdicts), never a numeric score (IL1 / no-fake-confidence, hard rule 9).
- What happens to the route flip if the paired I1 "route-honesty" static rule
  never ships? The flip is a hand-edit, unenforced until (if) I1 lands; I2 does
  not depend on I1 and must not assume an I1 guard exists.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The layer MUST ship a new file
  `skills/bi-python-knowledge/checklists/cleaning-review-checklist.md` as the
  terminal artifact for the cleaning route.
- **FR-002**: The checklist MUST mirror the SHAPE of the shipped
  `aggregation-grain-checklist.md` (lettered sections of checkbox items, each
  citing existing IDs, ending on a small set of named categorical verdicts, with
  an "Attach:" line naming what evidence accompanies the verdict).
- **FR-003**: The checklist's content MUST cover the cleaning concerns the
  knowledge file already raises -- string standardization (PY-CN-031), category
  convergence to a known domain (PY-CN-032), currency / numeric-as-text coercion
  and coerced-null counting (PY-CN-033), invalid / out-of-range / sentinel
  handling (PY-CN-034), declared-key deduplication (PY-CN-035, guarding
  PY-AP-001), grain and row-count accountability (PY-CN-036), and source-value
  traceability (PY-CN-037), enforcing PY-BP-005 (clean only what profiling
  flagged).
- **FR-004**: Every checklist item MUST cite ONLY IDs that already exist in the
  cleaning content or `references/id-conventions.md`; the checklist MUST NOT mint
  new IDs (a new ID is a content act outside this distillation's scope).
- **FR-005**: The checklist's "Attach" evidence MUST include the row-count ledger
  already defined in PY-CN-036 (rows in -> altered -> coerced-null -> dropped ->
  out).
- **FR-006**: The checklist MUST end on a small set of CATEGORICAL cleaning
  verdicts (mirroring the aggregation checklist's four-state shape); it MUST NOT
  emit a numeric cleanliness score. The exact verdict vocabulary and each
  verdict's pass criteria are recorded in Clarifications
  [NEEDS CLARIFICATION: canonical cleaning-verdict status set + pass criteria --
  a definitional call reserved for a human ratifier so it does not smuggle a
  threshold / score].
- **FR-007**: For any cleaning decision the knowledge file reserves for a human
  (sentinel meaning, category-domain update, dedup keep-policy, out-of-range
  keep-vs-flag), the corresponding checklist item MUST be a "recorded by a human"
  checkbox and MUST NOT auto-resolve the decision.
- **FR-008**: `INDEX.md` MUST be updated so the cleaning-review checklist is a
  LIVE artifact: its row MUST be removed from the "Planned routes" table, the
  cleaning task/symptom routes MUST end on the checklist, the cleaning-route
  endpoint note MUST stop saying the checklist is planned, and the "File map"
  MUST list the checklist under shipped `checklists/`.
- **FR-009**: `knowledge/cleaning-and-standardization.md` MUST be updated so the
  "Ends on" block and the PY-CN-033 / PY-CN-036 inline notes no longer describe
  the cleaning-review checklist as "planned / not yet implemented" but point to
  the now-live checklist.
- **FR-010**: `README.md` MUST be updated so its coverage claim reflects the
  landed checklist (the cleaning route's endpoint is no longer listed among
  not-yet-built items), without claiming any other planned slice is complete.
- **FR-011**: The change MUST NOT flip any OTHER planned route or file to live
  (specifically NOT `groupby-aggregation-and-grain.md`,
  `profiling-and-source-inspection.md`, `pandas-dtypes-and-schema.md`,
  `validation-and-reconciliation.md`, nor the other planned checklists).
- **FR-012**: The checklist MUST keep the aggregation-grain fork boundary intact
  -- it MUST reference `checklists/aggregation-grain-checklist.md` for
  groupby/grain/additivity rather than restating that content.
- **FR-013**: The checklist MUST keep the single-node fork boundary intact -- it
  MUST hand distributed / large-data cleaning off to
  `skills/bi-bigdata-knowledge/` rather than absorbing scale concerns.
- **FR-014**: All examples in the checklist MUST use ONLY the fictional retail
  schema (`references/retail-dataframe-schema.md`); no C086 / pharmacy specifics
  may appear inline (C086 may be cited only as an external worked example).
- **FR-015**: All authored / edited files MUST be UTF-8 without BOM, ASCII-only
  (use `--` and `->`, no Unicode glyphs), with short repo-relative paths
  (Windows 260-char rule / reproducibility).
- **FR-016**: This feature MUST NOT self-assign a roadmap F-row or readiness
  stage; the idea-bank record keeps `f_row: none`
  [NEEDS CLARIFICATION: whether I2 maps to any roadmap F-row or stays off-spine
  -- a human mapping decision the ledger never self-assigns].

### Key Entities *(include if feature involves data)*

- **Cleaning-review checklist**: The new terminal artifact. Attributes: lettered
  sections of checkbox items; each item cites existing PY-CN-* / PY-BP-* /
  PY-AP-* IDs; a categorical verdict set; an "Attach" line (row-count ledger +
  recorded human decisions). Relationship: it is the endpoint of the live
  cleaning route defined in `INDEX.md` and `cleaning-and-standardization.md`;
  it REFERENCES (does not re-own) the aggregation-grain checklist.
- **Row-count ledger**: The existing accountability artifact (PY-CN-036), rows
  in -> altered -> coerced-null -> dropped -> out. It is the evidence the
  checklist verdict attaches; not newly invented here.
- **Cleaning verdict**: A CATEGORICAL status (not a score) the checklist ends on,
  mirroring the aggregation checklist's four-state verdict shape. Exact
  vocabulary reserved for human ratification (see Clarifications).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Following the live cleaning route in `INDEX.md` and then the
  knowledge file's "Ends on" pointer resolves to an existing file in 100% of
  cases (zero dead-ends) -- the one advertised live cleaning dead-end is closed.
- **SC-002**: Zero surviving references in the skill describe the cleaning-review
  checklist as "planned / not yet implemented" after the change.
- **SC-003**: 100% of the cleaning knowledge file's cleaning concerns
  (PY-CN-031..037, PY-BP-005, PY-AP-001) are represented by at least one
  checklist item.
- **SC-004**: 100% of checklist items cite an ID that already exists (zero newly
  minted IDs).
- **SC-005**: Zero planned siblings other than the cleaning-review checklist are
  flipped to live (the set of remaining planned routes shrinks by exactly one).
- **SC-006**: Zero inline C086 / pharmacy specifics and zero numeric cleanliness
  scores appear in the new checklist.

## Assumptions

- The `checklists/` and `patterns/` directories already exist; the new file lands
  in the existing `checklists/` home (confirmed by grounding). No new directory is
  created.
- The cleaning IDs the checklist cites (PY-CN-031..037, PY-BP-005, PY-AP-001)
  already exist in `cleaning-and-standardization.md` and
  `references/id-conventions.md`; the checklist distils existing reasoning and
  does not author new reasoning content.
- The OPTIONAL 1-2 pattern files mentioned in the idea's first step are treated as
  OUT of the minimal scope: this feature lands ONLY the checklist plus the route
  flip (the single advertised dead-end). Adding pattern JSON files risks scope
  creep beyond the one route and is deferred (a human may request them
  separately). See Clarifications.
- I1 (the paired "route-honesty" static rule) has NOT shipped and is NOT a
  dependency; I2 stands alone. Landing I2 first is coherent -- if a future I1
  rule lands it would ERROR on exactly this gap, which I2 closes.
- This is a docs-only knowledge-skill change (Principle VIII / hard rule 8): no
  runtime Python, no new retail check rule, no executor. The agent is the runtime.
- Deferred capabilities (F016 Power BI Execution Adapter; F031-F033 spec-only
  runtimes) are NOT assumed to exist and are irrelevant to this docs-only change.

## Clarifications

### Session 2026-07-02

The following are RESERVED for a human ratifier and are intentionally NOT
answered by the planning agent (Principle V analog -- definitional / off-spine
calls the ledger and layer never self-resolve):

- **Cleaning-verdict vocabulary** (FR-006): the exact canonical categorical
  status set for the cleaning-review checklist (e.g. a "sound" state, an
  "unresolved findings" state, a "grain violated" state, a "blocked" state) and
  each status's pass criteria. Mirror the aggregation checklist's four-state
  shape, but the precise wording + pass criteria is a definitional call a human
  should ratify so it does not smuggle a hidden threshold or score.
- **Roadmap-stage mapping** (FR-016): whether I2 advances any roadmap F-row or
  stays off-spine as an idea-bank content-completion item (`f_row: none`). The
  ledger never self-assigns an F-row (Principle V / IL1 contract).
- **Optional pattern files**: whether the human wants ONLY the checklist (minimal,
  closes the exact dead-end) or ALSO 1-2 `patterns/*.json` files. Recommended
  default recorded in Assumptions is checklist-only; confirming the pattern-file
  scope is a human call to avoid scope creep beyond the single advertised route.
- **Unenforced-flip risk**: whether landing I2's route flip WITHOUT the I1 guard
  (the flip is a hand-edit, unenforced until I1 ships) is a stale-marker risk the
  human is comfortable accepting.
