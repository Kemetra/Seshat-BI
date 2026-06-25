# Implementation Plan: Approval Console -- the human-in-the-loop decision package + decision recorder

**Branch**: `021-approval-console` | **Roadmap feature**: F027 | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

(Numbering note: the roadmap F-number is the authoritative identity; the spec-dir number
is the next free on-disk slot. On-disk dir `021-approval-console`; roadmap feature F027.
When they disagree, the roadmap F-number wins: this is F027.)

**Input**: Feature specification from `specs/021-approval-console/spec.md`

## Summary

Plan the Approval Console: the Product Module that turns a raised judgment call into a
reviewable DECISION PACKAGE (a request) and then RECORDS the named human's answer back
into the committed Core-Authority artifacts (a decision). It is the operational
realization of Principle V (stop-and-ask) and the write-back side of the `approvals[]`
slot in `readiness-status.yaml` + the `Resolution` column in `unresolved-questions.md`.

This slice is **planning artifacts only**: the five Spec-Kit files. The feature's runtime
shape is **a pure skill + two templates + one docs page** (the agent is the runtime),
enumerated here as PLANNED future deliverables and NOT created in this slice. The
load-bearing design rule is the transcribe-never-author boundary: the console writes INTO
Core-Authority artifacts but only transcribes a human decision and only executes an
already-approved step -- it never decides, never self-approves, and never moves a stage to
`pass` without the required evidence AND a named human approval. No Python, no CLI, no new
`retail check` rule (Principle VIII; roadmap rule #8).

## Technical Context

**Language/Version**: None -- docs/planning this slice (Markdown + YAML text artifacts when
the planned deliverables are later authored).

**Primary Dependencies**: None at runtime. Authoring style borrows from
`templates/source-map.yaml` (header + namespace/placeholder convention),
`templates/unresolved-questions.md` (the Open-questions table the request packages and the
Resolution column the decision writes), and `templates/readiness-status.yaml` (the
`approvals[]` slot the decision appends to, and the four-status vocabulary).

**Storage**: Committed text files: the planned `templates/` request + decision shapes, the
planned `.claude/skills/approval-console/SKILL.md`, and the planned
`docs/tools/approval-console.md`. Filled requests/decisions (a later, per-question
activity) are recorded alongside the table working set and written through to the table's
`unresolved-questions.md` + `readiness-status.yaml` (see Structure Decision + open
question O-1).

**Testing**: No code this slice, so no unit tests. Verification when the deliverables are
later authored: (1) `retail check` exit 0 with no new rule added, (2) templates parse /
are valid Markdown+YAML, (3) a manual generic request->decision walkthrough proves the
write-back lands in `unresolved-questions.md` + `approvals[]` and that self-approval /
no-evidence-pass are refused, (4) ASCII + UTF-8 no-BOM on every file.

**Target Platform**: Repo text artifacts consumed by an agent + reviewed by a human;
every stage's gate reads the `approvals[]` evidence the console records.

**Project Type**: Documentation/planning feature (no source tree change this slice).

**Performance Goals**: N/A (static text).

**Constraints**: ASCII + UTF-8 no BOM; generic (no C086/pharmacy values); Windows path
budget (`<= 200` chars repo-relative); no numeric confidence score anywhere; no deciding,
no self-approval, no stage flip without approval AND evidence; no checker/CLI/rule.

**Scale/Scope**: 5 planning files this slice. The enumerated future deliverables: 1 skill,
2 templates, 1 docs page.

## Constitution Check

*GATE: must pass before and after design. Constitution at `.specify/memory/constitution.md`.*

| Principle | How this feature complies |
|-----------|---------------------------|
| I. Agent-First, Gate-Enforced | Adds no gate and no agent authority over a decision. The agent packages a request and transcribes a human answer; the named human decides; the gate exit code stays the authority. The console executes an approved step, it does not dispose of judgment. |
| II. Depend, Never Fork | No engine, no Power BI execution adapter, no fork. Pure local opinion in a skill + templates + docs. The console never publishes Power BI (that is F016). |
| III. Medallion, Gold-Only | Not triggered (no SQL, no PBIP read). The console records decisions about stages; it reads/writes committed text only. |
| IV. Source Mapping Before Silver | Reinforced: the console is the mechanism that records the named-owner answer to a mapping-gate `unresolved-questions.md` row, so Mapping Ready can reach `pass` with recorded approval -- it never lets silver proceed on an unanswered question. |
| V. Agent Stops at Judgment Calls | This feature IS the operational realization of Principle V. FR-005..FR-010: the console transcribes, never decides; refuses self-approval; refuses the wrong authority class; refuses a no-evidence `pass`; surfaces conflicts. |
| VI. Defaults Then Deviations | A `recommended_default` is recorded as a default, but FR-006 forbids auto-accepting it -- accepting a default is an explicit named-owner decision, exactly as the source templates require. |
| VII. C086 Is An Example | FR-013/SC-004: all planned artifacts generic; C086 cited as the filled instance, never inlined. |
| VIII. Static-First, Live Deferred | FR-001/SC-005: NO Python, NO rule, NO CLI, NO PBIP/DB read; `retail check` exit 0 + no new rule added. Pure skill + templates + docs (rule #8). |
| IX. Secrets & Reproducibility | No secrets. ASCII + UTF-8 no BOM; short paths; the planned templates are reproducible copy-me text. |

**Result**: PASS. No violations; Complexity Tracking left empty.

### Boundary gate (feature-specific, load-bearing)

The single biggest design risk is that a module which WRITES into Core-Authority artifacts
slides into CREATING truth. The plan holds the boundary explicitly:

- The console TRANSCRIBES a human decision and EXECUTES an already-approved step. It does
  NOT pick the option, supply the owner, invent the rationale, accept a default, or self-
  grant a stage.
- It MAY flip a stage to `pass` ONLY when a named approval AND the stage's required
  evidence both already exist -- mechanically, never discretionarily.
- It WRITES (unlike F012's read-only roll-up): into `unresolved-questions.md` Resolution +
  status and `readiness-status.yaml` `approvals[]`. The write is a transcription, not a
  ruling.

## Project Structure

### Documentation (this feature)

```text
specs/021-approval-console/
|-- spec.md              # the feature spec (this slice)
|-- plan.md              # this file
|-- tasks.md             # the task list
`-- checklists/
    |-- acceptance.md    # spec quality checklist
    `-- governance.md    # Core-Authority / Principle V governance checklist
```

These five files ARE the deliverable of this slice. No `research.md` / `data-model.md` /
`contracts/` directory is generated: there is no code to research and no DB model to
design. The "contracts" this feature will later produce are the request + decision
TEMPLATES, which live under `templates/` (a planned deliverable), not under a Spec-Kit
`contracts/` dir.

### Repository artifacts this feature PLANS (not created in this slice)

```text
.claude/skills/approval-console/
`-- SKILL.md                      # PLANNED -- the console verb (package request; transcribe decision)

templates/
|-- approval-request.md           # PLANNED -- the decision-package shape (request fields)
`-- approval-decision.md          # PLANNED -- the recorded-decision shape (decision fields)

docs/tools/
`-- approval-console.md           # PLANNED -- operator guide + transcribe-never-author boundary
```

Filled instances (NOT created by this feature; their write targets are existing artifacts):

```text
mappings/<table>/unresolved-questions.md     # Resolution + answered status written here
mappings/<table>/readiness-status.yaml       # approvals[] entry (stage + owner + at) appended here
```

**Structure Decision**: planning feature -- no `src/` or `tests/` change this slice. The
planned skill lives under `.claude/skills/` (alongside the shipped skills); the request +
decision templates live in the existing `templates/` dir (alongside the mapping-gate
templates the console writes into); the operator guide lives in a new `docs/tools/` dir
(parallel to `docs/readiness/`, keeping `docs/` narrative-only). Per-question filled
requests/decisions write through to the EXISTING per-table `unresolved-questions.md` +
`readiness-status.yaml`; whether to also retain a standalone recorded copy under the
per-table working set is recorded as open question O-1 (cheaply reversible -- a path
choice; see Phase 0).

## Phase 0 -- Research (no external research needed)

No unknowns requiring external research. The write targets are already in-repo:
`templates/readiness-status.yaml` (the `approvals[]` shape: `stage` / `owner` / `at`) and
`templates/unresolved-questions.md` (the Open-questions table the request packages, the
`Who must answer` authority classes, and the `Resolution` column the decision writes). The
one open decision is O-1.

- **O-1 (recorded, not deferred research): where a standalone recorded request/decision
  copy lives.** Recommended default: the authoritative write-back is into the existing
  per-table `unresolved-questions.md` Resolution + `readiness-status.yaml` `approvals[]`;
  a standalone `approval-request.md` / `approval-decision.md` copy is OPTIONAL and, if
  retained, lives under the per-table working set (parallel to the five mapping-gate
  artifacts, per ADR 0003's cohesive-working-set rationale). Cheaply reversible (a path
  choice); the operator guide records it.

## Phase 1 -- Design (the planned artifact shapes)

**approval-request.md** (generic template). Header in the `source-map.yaml` style: what it
is, principles it instantiates (V stop-and-ask, VII generic, IX no-BOM), the no-score rule
(#9), the transcribe-never-author boundary, and a generic-placeholder note. Fields:
`question_id`, `stage` (one of the seven), `subject` (source/table/report),
`decision_needed` (one sentence), `evidence` (measured numbers + committed source paths),
`options`, `impact` (per option), `recommended_default` (optional; carries an explicit
"NOT auto-accepted" note), `owner_required` (analyst / governance / data-owner /
metric-owner), `artifacts_to_update_after_decision`. No `selected_option` -- a request
never answers itself.

**approval-decision.md** (generic template). Header in the same house style + the same
boundary text. Fields: `selected_option` (transcribed from the human), `owner` (the named
human), `date`, `rationale` (the human's), `artifacts_updated` (the committed paths the
decision was written through to), `remaining_blockers` (why a recorded decision does NOT
always mean `pass`). Authoring notes: the `pass`-needs-approval-AND-evidence rule, the
authority-class match rule, and the conflict-surfacing rule.

**docs/tools/approval-console.md** (operator guide). Sections: purpose; the
request->decision loop; the transcribe-never-author boundary (the console records, the
human decides); the four authority classes and how they match question classes; the
`pass`-needs-approval-AND-evidence rule; how a recorded decision maps to `approvals[]` +
the `unresolved-questions.md` Resolution; the no-self-approval / no-auto-accept-default /
no-fabricated-score guards; and how `retail-orchestrate` invokes it.

**.claude/skills/approval-console/SKILL.md** (the verb). The procedure: (1) package a
raised judgment call into a filled request; (2) on a named human's answer, transcribe it
into a filled decision and write through to the named artifacts; (3) refuse to self-
approve, to accept a default, to record under the wrong authority, or to flip a stage to
`pass` without approval AND evidence; (4) surface conflicts. Plus an `## Orchestration`
pointer.

## Phase 1 -- Constitution re-check

Re-checked after design: still PASS. The design adds only generic planned text artifacts,
reads no PBIP/DB, adds no rule, transcribes (never authors) decisions, and keeps the
four-status/no-score vocabulary. The boundary gate holds: the only writes are
transcriptions of a named human's decision into existing Core-Authority artifacts, and a
stage flip to `pass` is mechanical and gated on approval AND evidence.

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.
