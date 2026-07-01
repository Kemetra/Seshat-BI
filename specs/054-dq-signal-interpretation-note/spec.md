# Feature Specification: DQ-Signal Interpretation Note (-1 unknown-member counts as business caveat)

**Feature Branch**: `054-dq-signal-interpretation-note` (spec dir renumbered to `054-dq-signal-interpretation-note` to avoid the 053 collision across the parallel kraken runs; roadmap F-number wins on any disagreement)

**Created**: 2026-07-01

**Status**: Ratified (advisor-for-Ahmed-Shaaban, 2026-07-01)

**Ratification note**: Ratified by the advisor agent under the explicit, recorded
per-session delegated override granted by the repo owner (info@rahmaqanater.org) for the
2026-07-01 "release the kraken" session (the batch of seven idea-to-spec specs). Provenance:
this Ratified line is AI-authored under recorded human authority; it is NOT a human-typed
ratification and the git author identity does not by itself attest a human reviewer. The two
Principle-V open items are resolved as recorded rulings in FR-010 / FR-011 (stage of record =
Stage 7 Publish Ready, no F-number assigned; direction-of-distortion = totals preserved /
sliced views distorted, categorical only). The idea-premise error ("validate.py /
run_live_checks already tally the -1 count") is corrected in the spec: no such tally exists;
the count's home is a hand-filled data-issues.md row. Docs/template only -- no runtime code,
no new retail check rule (count stays 38). analyze=clean (0 critical/0 high); plan-review=
PASS-WITH-NOTES. Override is per-session/per-this-set only; it covers ratification, not merge
(normal CI gate still applies).

**Input**: User description: "DQ-Signal Interpretation Note (-1 unknown-member counts as business caveat)"

## Overview

A NEW generic authoring template `templates/handoff/dq-signal-interpretation.md`
that turns an already-recorded data-quality signal -- specifically the count of
fact rows routed to a dimension's `-1` unknown member (the ratified RC14 default:
FK `COALESCE(..., -1)`) -- into a plain-language business caveat an analyst can
hand to a consumer. It provides one interpretive row per signal:

```
signal -> which KPI it distorts -> direction (understate / overstate / none)
       -> plain-language caveat
```

The template READS the count from a table's `data-issues.md` (the single source of
truth for that number); it introduces NO new number and runs NO query. The
`signal -> KPI -> direction` mapping is a business-meaning judgment the analyst /
governance fills and confirms -- the template presents it as a fill-in and never
auto-decides it. The confirmed caveat then FEEDS the Stage-7 Publish Ready handoff
pack "Known data issues / caveats" section (`bi-handoff-pack.md` L59-73), for which
this note is the interpretive SOURCE, not a competing home.

This is a docs/template artifact only: no executor, no new validator, no live query,
no module-scope DB driver import.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Analyst interprets a recorded -1 signal into a caveat (Priority: P1)

An analyst has a table whose `data-issues.md` already records a `warning` row of
the form "N rows map to the -1 unknown member of dim_<x>" with a measured count
and an "accepted gap" disposition. Before assembling the Stage-7 handoff pack, the
analyst copies the generic `dq-signal-interpretation.md` template per table, fills
one interpretation row per recorded -1 signal by transcribing the count from
`data-issues.md` (never re-measuring), and confirms the KPI it distorts + the
direction of distortion. The filled caveat text is then carried verbatim into the
handoff pack's Known-gaps section.

**Why this priority**: This is the whole feature -- the interpretive layer that
converts a bare count into a consumer-readable caveat. Without it there is no
artifact.

**Independent Test**: Copy the template, transcribe a count from an existing
`data-issues.md` row, fill the KPI + direction + caveat, and confirm the caveat can
be pasted into the handoff pack Known-gaps section unchanged. Delivers a
publish-safe, single-sourced caveat.

**Acceptance Scenarios**:

1. **Given** a `data-issues.md` row recording a measured `-1` unknown-member count,
   **When** the analyst fills one interpretation row referencing that count,
   **Then** the note carries the SAME number (no new/re-measured number) and links
   back to `data-issues.md` as the source.
2. **Given** a filled interpretation row, **When** the Stage-7 handoff pack Known-
   gaps section is assembled, **Then** the caveat text is carried verbatim and the
   note is cited as the interpretive source (not duplicated as a second home for
   the count).

---

### User Story 2 - No content when there is no recorded signal (Priority: P2)

An analyst opens the template for a table that has NO recorded `-1` unknown-member
count (e.g. no live validate run has produced one yet). The template gives the
analyst nothing to interpret: it records "no recorded -1 signal for this table"
and produces no caveat. It never fabricates a count or a caveat.

**Why this priority**: The anti-fabricated-confidence invariant. A table with no
recorded signal must yield an empty note, not an invented one.

**Independent Test**: Open the template against a table with an empty / absent
`data-issues.md` -1 row; confirm the note explicitly records "none recorded" and
emits no caveat.

**Acceptance Scenarios**:

1. **Given** a table with no recorded `-1` unknown-member count, **When** the
   template is filled, **Then** it records "none recorded -- nothing to interpret"
   and produces zero caveats.

---

### User Story 3 - Analyst-judgment fills are visibly gated, never auto-filled (Priority: P3)

The template must make plain that the `KPI` and `direction-of-distortion` columns
are analyst / governance judgment fill-ins, not machine-derivable, and that a
person/customer dimension triggers a PII publish-safety review before the caveat is
published.

**Why this priority**: Principle V (Agent Stops at Judgment Calls). The mapping and
PII safety are human calls; the template must present them as unfilled prompts a
named owner confirms.

**Independent Test**: Inspect the template; confirm the KPI + direction cells are
blank prompts with an owner field, and that a PII-review gate is present for
person/customer dims.

**Acceptance Scenarios**:

1. **Given** the blank template, **When** an analyst reads the KPI / direction
   columns, **Then** each is an explicit fill-in with a named-owner field and no
   pre-decided value.
2. **Given** a signal on a person/customer dimension, **When** the analyst reaches
   the publish step, **Then** the template requires a governance PII publish-safety
   confirmation before the caveat is carried to the pack.

---

### Edge Cases

- What happens when the affected dimension is a person/customer entity? -> a
  PII publish-safety gate (Principle V) must be satisfied before the caveat text is
  published; the default is to defer to governance.
- What happens when the count is recorded but no KPI mapping is known? -> the row
  stays as an unconfirmed fill-in (owner: analyst); it is NOT published as a
  confirmed caveat until the mapping is ratified.
- What happens when `data-issues.md` and this note disagree on the count? -> this
  note is NOT a source of truth for the number; it MUST be reconciled to
  `data-issues.md` (single source), never overriding it.
- What happens when the caveat concerns a measure TOTAL vs a SLICED view? -> the
  direction-of-distortion semantics must be stated precisely (see Clarifications) so
  the caveat neither overstates nor understates impact.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The artifact MUST be a single generic authoring template at
  `templates/handoff/dq-signal-interpretation.md`, copied per table into
  `mappings/<table>/handoff/` -- carrying zero pharmacy/C086 specifics (no
  `salesperson_sk`, no fixed count, no `ezaby_demo` / pharmacy dims, no fixed
  measure list).
- **FR-002**: The template MUST source the `-1` unknown-member count by reference
  from the table's `data-issues.md` and MUST NOT introduce, re-measure, or invent
  any number.
- **FR-003**: The template MUST provide, per signal, a row expressing
  `signal -> affected KPI -> direction-of-distortion -> plain-language caveat`,
  where the KPI and direction cells are analyst/governance fill-ins with a named-
  owner field, never auto-decided.
- **FR-004**: The template MUST record "none recorded -- nothing to interpret" and
  produce zero caveats for a table with no recorded `-1` unknown-member count (no
  fabrication).
- **FR-005**: The template MUST frame itself as the interpretive SOURCE that feeds
  the Stage-7 Publish Ready handoff pack Known-gaps/caveats section
  (`bi-handoff-pack.md` L59-73), NOT as a competing second home for the count;
  `data-issues.md` remains the single source of truth for the number.
- **FR-006**: The template MUST cite the ratified RC14 `-1` unknown-member + FK
  `COALESCE` default (constitution Principle VI) as the accepted default whose
  consequence it interprets; it MUST NOT re-litigate the default.
- **FR-007**: The template MUST include a PII publish-safety gate for signals on a
  person/customer dimension, deferring the publish-safety decision to governance
  (Principle V).
- **FR-008**: The template MUST cite C086 only as a linked filled instance
  (`docs/worked-examples/c086-pharmacy.md`, `docs/c086-adr0002-compliance.md`),
  never inlining its specifics.
- **FR-009**: The template MUST be ASCII, UTF-8 without BOM, use `--` and `->` (no
  glyphs), and emit no numeric confidence/health/readiness score.
- **FR-010** (human-ruled 2026-07-01): The template's **stage of record is Stage 7
  (Publish Ready)** -- it is the caveat/stakeholder-communication surface that CONSUMES
  the signal. The `-1` count is **NOT produced by the Stage-4 `retail validate` run** (that
  run only flags hard orphan FKs; rows coalesced to the `-1` member pass validate silently);
  it comes from a separate analyst query and is recorded in `data-issues.md`. The template is
  authored generically now, filled once that count is recorded in `data-issues.md`, and read
  as a Stage-7 caveat. **No roadmap F-number is assigned** (the idea bank is not the roadmap;
  Principle V / roadmap prose). The template states this recorded-source -> consumer framing.
- **FR-011** (human-ruled 2026-07-01): The `direction-of-distortion` semantics are fixed
  to this precise, observed correctness claim: the `-1` unknown member **preserves measure
  TOTALS** (the row is absorbed into the `-1` bucket, so grand totals still reconcile) but
  **distorts any view SLICED / grouped by the affected dimension** (the `-1` bucket steals
  share from the real members, understating them and overstating "unknown"). The template
  states this categorical total-vs-sliced claim only -- it names no magnitude and forecasts
  nothing (stays clear of the F5/F6 ML boundary); attributing the distortion to a specific
  business KPI remains an analyst (Principle V) fill.

### Key Entities *(include if feature involves data)*

- **DQ signal (input)**: a recorded data-quality finding in `data-issues.md` --
  here specifically an "N rows on the `-1` unknown member of dim_<x>" row with a
  measured count and disposition. Read-only input; not owned by this artifact.
- **Interpretation row (new)**: the analyst-confirmed mapping of one signal to its
  affected KPI, direction-of-distortion, and plain-language caveat. The one genuinely
  new thing this artifact adds.
- **Caveat (output)**: the plain-language sentence carried verbatim into the Stage-7
  handoff pack Known-gaps section.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An analyst can produce a publish-ready caveat for one recorded `-1`
  signal by filling exactly one interpretation row, without measuring any new number
  (100% of the count comes by reference from `data-issues.md`).
- **SC-002**: The template contains zero pharmacy/C086 specifics (no fixed count, no
  named dim, no measure list) -- verifiable by inspection / grep.
- **SC-003**: For a table with no recorded `-1` signal, the filled note contains
  zero caveats and one explicit "none recorded" statement.
- **SC-004**: Every KPI + direction cell in the blank template is an unfilled prompt
  with a named-owner field (0 pre-decided judgment values).
- **SC-005**: The caveat produced is carried into the Stage-7 handoff pack Known-
  gaps section without a second copy of the count being created (single source of
  truth preserved).

## Assumptions

- The `-1` unknown-member count already lives (when it exists) as a hand-filled row
  in the table's `data-issues.md`, produced by a separate analyst query -- NOT by
  `validate.py` / `run_live_checks`, which tally hard orphan FKs (Severity.ERROR)
  and reconciliation gaps only and never count rows routed to `-1` (they pass
  silently under the RC14 COALESCE default). This artifact therefore reads an
  existing recorded number and never depends on a tooling-emitted `-1` tally.
- A live validate run for the target table is deferred (needs the optional db extra
  + read-only `.env` creds); the template is authorable now, but its filled value is
  gated on that deferred live run -- for a table with no live run the note has no
  content to interpret.
- The Stage-7 handoff pack Known-gaps behavior already exists (`bi-handoff-pack.md`
  L70-71 already mandates surfacing "<N> rows land on the -1 unknown member of
  dim_<x>" with the count); this note complements it as the interpretive source and
  does not duplicate or replace it.
- Scope discipline (YAGNI, CLAUDE.md): this adds the seam (a template), not an
  implementation -- no executor, no validator change, no live consumer (F016 Power
  BI execution adapter is verified absent and is NOT leaned on).

## Clarifications

### Session 2026-07-01

Advisor-resolved (non-Principle-V) ambiguities:

- **Q1 (scope of "signal")**: Does the template interpret ALL data-quality signals
  in `data-issues.md`, or only the `-1` unknown-member count?
  - **Recommended answer**: Only the `-1` unknown-member count (the RC14-default
    consequence). Reasoning: YAGNI / scope discipline (CLAUDE.md) -- this idea is
    scoped to the one signal the bank adopted; a general "any DQ signal" interpreter
    is a broader artifact not chartered here. Reversible: easy (a later spec can widen
    scope). Integrated: FR-001/FR-002/FR-003 already bound the artifact to the `-1`
    signal.
- **Q2 (single-source-of-truth boundary)**: Is the count duplicated here, or does
  the note reference `data-issues.md`?
  - **Recommended answer**: Reference only -- `data-issues.md` stays the single
    source of truth for the number; this note carries the interpretation and cites
    the count by reference, and feeds (does not duplicate) the Stage-7 pack.
    Reasoning: grounding confirms `bi-handoff-pack.md` L70-71 already surfaces the
    count; a second home would create a reconciliation hazard. Reversible: costly
    (a duplicated number is a divergence risk). Integrated: FR-002, FR-005, and the
    Edge Cases reconciliation rule.

Principle-V judgment calls -- REFUSED here, recorded for a human (workflow does not answer):

- **Stage of record / roadmap ownership (FR-010)**: which readiness stage this
  artifact is formally filed under, and whether an F-number is assigned. Recommended
  framing (authored generically now, filled after the Stage-4 live run, consumed at
  Stage 7) is stated in FR-010 but the stage-of-record + F-row assignment is a
  roadmap/governance call left OPEN for a human. Not build-blocking (the template is
  authorable generically regardless).
- **Direction-of-distortion correctness claim (FR-011)**: the precise business-meaning
  ruling on whether the caveat's claim is about a measure TOTAL (unaffected) vs a
  SLICED/grouped view (distorted). This is the load-bearing correctness question and a
  Principle-V business-rollup judgment reserved for a human/analyst; the template
  presents it as a fill-in, so it is not build-blocking, but the ruling itself stays
  OPEN.
- **PII publish-safety (FR-007)**: whether surfacing "N rows unattributed" as a
  published caveat is itself a PII-adjacent disclosure when the dim is a
  person/customer entity. Deferred to governance (Principle V default). OPEN.
- **KPI-mapping ownership**: WHO owns the `signal -> affected KPI` ruling (analyst vs
  governance) must be named per table. OPEN.
