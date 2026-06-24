# Implementation Plan: source drift detector (F014, spec 015)

**Branch**: `015-source-drift-detector` | **Date**: 2026-06-24 | **Spec**: `specs/015-source-drift-detector/spec.md`

**Input**: Feature specification from `specs/015-source-drift-detector/spec.md`

## Summary

Ship the DESIGN of a source drift detector as docs/templates/checklist (no
runtime), advancing the **Source Ready** stage. The artifacts make "this source no
longer matches its recorded `source-profile.md`" a first-class, measured readiness
signal: a baseline-vs-observed comparison classified into nine drift classes, each
with a default severity, surfaced as `source-drift-report.md` evidence that moves a
table's Source Ready status to `pass`/`warning`/`blocked`. Grain/identity/returns/
PII drift are Principle-V human seams (measured + raised, never auto-rejudged). No
fake confidence (#9): measured per-class magnitudes + statuses + blocking reasons,
never a rolled-up drift score. Generic (#7): no worked-example specifics.

Technical approach: this is a "Later"-tier (#8) docs slice. It adds NO Python, NO
SQL, NO CLI, NO checker rule -- three prose/markdown artifacts plus cross-links and
a readiness-status wiring spec. The mechanical re-profile reuses the existing
deferred-live `profile.py` seam (Principle VIII) only when a runtime is built later.

## Technical Context

**Language/Version**: None (docs/templates/markdown only). The repo's runtime is
Python 3 (`src/retail/`, `dependencies = []`, stdlib-only static core) but this
slice adds no code.

**Primary Dependencies**: None added. The design REFERENCES (does not import) the
existing deferred-live `src/retail/profile.py` and the optional `db` extra for the
future runtime; this slice touches neither.

**Storage**: Committed text only. Drift reports live at
`mappings/<table>/source-drift-report.md` (co-located with the baseline profile per
ADR 0003). No database writes; the source substrate stays the deferred DO Postgres
medallion (Principle III), untouched here.

**Testing**: Documentation/replay validation, not code tests: (a) `retail check`
stays exit 0 over the new committed text; (b) the unit suite stays green (no code
changed); (c) a manual baseline-vs-observed replay (two profiles -> a filled
`source-drift-report.md`) proves the template is complete enough to classify every
diff and land the right status (SC-003).

**Target Platform**: Repo docs consumed by the agent + human reviewers on Windows
(MAX_PATH-aware short paths, UTF-8 no BOM, `core.autocrlf=true`), per Principle IX.

**Project Type**: Single repo, docs/templates slice (no src/ or tests/ changes).

**Performance Goals**: N/A (no runtime). The future comparator's perf is a deferred
concern; this slice has none.

**Constraints**: ASCII-only artifacts, UTF-8 no BOM; generic (no C086 specifics);
no fabricated confidence number; Principle-V classes hard-stop; no new gate, no new
checker rule, no DB connection. Repo-relative paths <= 200 chars.

**Scale/Scope**: One design doc, one template, one checklist, plus cross-link edits
to `source-ready.md` and (optionally) the roadmap row. Nine drift classes; one
readiness stage (Source Ready) wired.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate | This plan |
|-----------|------|-----------|
| I. Agent-First, Gate-Enforced | the enforced gate is the checker exit code, not prose | PASS -- adds no gate; the existing Source Ready review reads the drift report as evidence; `retail check` stays the authority and stays exit 0 |
| II. Depend, Never Fork | no pbi-cli fork; engine borrowed | PASS -- no pbi-cli touched; no engine added |
| III. Medallion, Postgres-First, Gold-Only | one substrate, gold-only read | PASS -- no DB writes, no new read surface; re-profile (deferred) reads the same landed source the baseline profiled |
| IV. Source Mapping Before Silver | map before build | PASS -- this is UPSTREAM of mapping (Source Ready, stage 1); a drift `blocked` correctly prevents trusting a stale map |
| V. Agent Stops at Judgment Calls | human decides grain/PII/returns/identity | PASS -- grain/PK, returns-rule, PII-surface, identity-pair drift are HARD-STOPS raised to `unresolved-questions.md`; never auto-rejudged (FR-006, US2) |
| VI. Defaults Then Deviations | start from RC defaults | PASS -- reuses RC2 (PK on data), RC5 (`'' OR NULL`), RC8 (returns column) as the drift measures; invents no new measure family (FR-004) |
| VII. C086 Is An Example | generic templates | PASS -- artifacts carry no worked-example specifics; C086 cited as the filled baseline only (FR-010) |
| VIII. Static-First, Live Deferred | static now, live deferred | PASS -- design only; the mechanical re-profile is the deferred-live seam; `[PENDING LIVE RE-PROFILE]` + `warning` when the boundary is absent (FR-009) |
| IX. Secrets and Reproducibility | secrets in `.env`; UTF-8 no BOM; short paths | PASS -- template states read-only connection, secrets only in `.env`, no inline DSN; ASCII/UTF-8 no BOM; `mappings/<table>/` paths short |
| Roadmap #9 No fake confidence | status + evidence + blockers, never a number | PASS -- measured magnitudes + four statuses + blocking reasons; no drift score (FR-005) |
| Roadmap #8 Docs first | a stage is a doc + status before code | PASS -- this slice IS the doc/template/checklist; runtime deferred |

No violations. No Complexity Tracking rows required.

## Project Structure

### Documentation (this feature)

```text
specs/015-source-drift-detector/
|-- spec.md        # the feature spec (done)
|-- plan.md        # this file
|-- tasks.md       # task breakdown (speckit-tasks output)
`-- analysis.md    # cross-artifact analyze findings
```

No `research.md` / `data-model.md` / `contracts/` / `quickstart.md`: this is a docs
slice with no novel technical unknowns, no data schema, and no API surface. The
"data model" is the drift taxonomy, which lives in the design doc itself, not a
separate `data-model.md`. (Consistent with sibling docs-slice specs 002-006 that
ship spec.md alone; this slice adds plan/tasks/analysis for chain completeness.)

### Source Code (repository root)

No `src/` or `tests/` changes. The deliverables are docs/templates:

```text
docs/
|-- readiness/
|   |-- source-drift.md         # NEW: the drift design doc (taxonomy, model, status mapping, Principle-V seams)
|   `-- source-ready.md         # EDIT: add a See-also link to source-drift.md
|-- checklists/
|   `-- source-drift.md         # NEW: the re-profile/compare checklist (or repo checklist home if one exists)
`-- roadmap/
    `-- roadmap.md              # EDIT (optional): note F014 is filed under spec dir 015

templates/
`-- source-drift-report.md      # NEW: the committed blank a drift run fills

mappings/<table>/
`-- source-drift-report.md      # (instance, authored per-table later by a drift run; ADR 0003 location)
```

**Structure Decision**: docs/templates slice, no source tree. New design doc under
`docs/readiness/` (it is a Source-Ready companion, so it belongs beside the stage
docs); new template under `templates/` beside `source-profile.md`; new checklist
under `docs/checklists/` (Phase 0 confirms whether a checklist home already exists
and adjusts the path). Drift report INSTANCES land at `mappings/<table>/` per ADR
0003, co-located with the baseline profile they compare against.

## Phase 0 -- Research (resolve the few open shape questions)

No deep unknowns; the few questions are repo-placement conventions, each
auto-answered with the recommended default (recorded in spec Assumptions):

1. **Checklist home.** Does a `docs/checklists/` (or equivalent) already exist?
   -> Confirm at task time; if not, create `docs/checklists/source-drift.md`. The
   speckit `checklist-template.md` is the shape to follow. Reversible (file move).
2. **Drift report location.** -> `mappings/<table>/source-drift-report.md` (ADR
   0003 per-table working set). Co-located with the baseline. Reversible.
3. **readiness-status wiring.** -> Reuse existing `evidence[]` / `blocking_reasons[]`
   / status fields; no schema change. A `drift` sub-record is a deferred decision.
4. **Tolerance policy.** -> Until a global policy is defined, any measured movement
   is an observation at `warning`; tolerances may be recorded on the baseline. A
   numeric tolerance/scoring policy is deferred (would be a fake-confidence knob).

These are recorded as auto-decisions; none is a Principle-V class, so none is
escalated. The Principle-V classes themselves (grain/returns/PII/identity) are
NOT auto-answered -- they are designed AS human seams.

## Phase 1 -- Design (the three artifacts)

1. **`docs/readiness/source-drift.md`** -- mirror the stage-doc shape
   (Purpose / model / taxonomy table / status mapping / blocking reasons /
   Principle-V seams / forbidden actions / See also). Generalize the
   `source-profile.md` "Cross-file schema drift" check across time/versions. State
   no-fake-confidence and the design-only / deferred-runtime boundary explicitly.
2. **`templates/source-drift-report.md`** -- mirror `source-profile.md` /
   `reconciliation-report.md` posture: top instructions ("copy to
   `mappings/<table>/source-drift-report.md`", ASCII, cite numbers not adjectives,
   secrets only in `.env`); a Header; a per-class findings table with before/after
   MEASURED cells; the resulting Source Ready status + blocking reasons; a
   Principle-V open-questions handoff; an exit-gate checklist.
3. **`docs/checklists/source-drift.md`** -- the ordered re-profile/compare steps,
   following the speckit `checklist-template.md` shape, reusing the SAME measures
   as Source Ready (RC2/RC5/RC8).

Cross-link all three into the spine and update `source-ready.md`'s See-also. Re-run
the Constitution Check (unchanged -- still all PASS, no new gate).

## Phase 2 -- Verify (no code; docs gates)

- `retail check` exit 0 over the new committed text (no rule change; the new files
  are markdown the SQL/TMDL/PBIR rules do not touch).
- Unit suite green (nothing in `src/` changed).
- ASCII / UTF-8-no-BOM check on the three new files.
- Cross-link existence check (every See-also target resolves).
- The baseline-vs-observed replay (SC-003): two profiles -> a filled report ->
  correct classes + status, no missing template fields.

## Complexity Tracking

No Constitution Check violations. No entries.
