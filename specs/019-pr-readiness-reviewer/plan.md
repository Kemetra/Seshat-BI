# Implementation Plan: PR Readiness Reviewer

**Branch**: `019-pr-readiness-reviewer` | **Roadmap feature**: F025 | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

**Numbering note**: the roadmap F-number (F025) is the authoritative identity; the spec-dir
number (`019`) is the next free on-disk slot. When they disagree, the roadmap F-number wins.

**Input**: Feature specification from `specs/019-pr-readiness-reviewer/spec.md`

## Summary

Plan a read-only **Product Module** (F024 category) that turns the manual PR review pattern
into a repeatable skill: it OBSERVES one PR's state (open/draft, mergeable, CI/workflow
conclusions, open review threads, unresolved Codex/GitHub review comments) and READS the
committed readiness evidence the PR touches (`readiness-status.yaml`, `source-map.yaml`
approval metadata, declared-vs-run tests, no-raw-data / no-secrets / no-local-paths), then
emits ONE structured verdict: `merge_ready` (yes/no), `blockers[]`, `warnings[]`,
`required_human_decisions[]`, `evidence[]`, `next_action`. This is **docs/templates/skill
only** (Principle VIII; hard rule #8): no Python, no CLI verb, no `retail check` rule, no CI
workflow. `merge_ready` is a DERIVED BOOLEAN ("no blocker and no open required-human-decision
found in evidence"), never a score and never an approval. The module reports readiness from
evidence only -- it cannot merge, approve, resolve a thread, or move a stage (F024 Core
Authority; Principle V). This spec-only slice writes the five Spec-Kit files and ENUMERATES
the three future deliverables; it creates none of them.

## Technical Context

**Language/Version**: None (this slice is planning/docs only -- the future deliverables are a
Markdown skill, a Markdown template, and a Markdown doc; the agent is the runtime).

**Primary Dependencies**: None at runtime. The future skill borrows the read-and-interpret
posture from `.claude/skills/retail-control-room` (F012) and `.claude/skills/retail-validate`
("invoke-and-interpret only"); the verdict vocabulary borrows from
`docs/readiness/readiness-model.md` (status + evidence + blockers; no score). PR facts are
observed through read-only `gh` / git reads the agent already performs.

**Storage**: Committed text files. This slice: the five files under
`specs/019-pr-readiness-reviewer/`. The future deliverables (NOT created here):
`.claude/skills/pr-readiness-reviewer/SKILL.md`, `templates/pr-readiness-report.md`,
`docs/tools/pr-readiness-reviewer.md`.

**Testing**: No code this slice, so no unit tests. Verification of the future deliverables
(recorded in tasks.md, not run now): the verdict separates blocker from warning per the
gating rule; every verdict line is source-traceable; a score request is declined; read-only
holds (no merge/approve/resolve/edit/stage-move); no new `retail check` rule added and no
CI workflow added.

**Target Platform**: Repo text artifacts consumed by an agent + reviewed by a human; the
future skill is invoked against a single PR.

**Project Type**: Documentation/planning feature (no source tree change this slice).

**Performance Goals**: N/A (static text + a read-fan-out the agent performs on demand).

**Constraints**: ASCII + UTF-8 no BOM; generic (no C086 / `retail_store_sales` values);
Windows path budget (`<= 200` chars repo-relative -- keep names short); no numeric merge/
confidence score anywhere; read-only (no GitHub write, no commit, no stage move); no new
gate / rule / CI workflow.

**Scale/Scope**: 5 Spec-Kit files this slice; 3 future deliverables enumerated. The module is
per-PR (a portfolio PR roll-up is deferred).

## Constitution Check

*GATE: must pass before and after design. Constitution at `.specify/memory/constitution.md`.*

| Principle | How this feature complies |
|-----------|---------------------------|
| I. Agent-First, Gate-Enforced | The module is an agent skill that READS the gate's recorded results; it adds no gate and is not the authority on rule-pass. The `retail check` exit code and the human reviewer remain the authorities; the module proposes a verdict, the human disposes (merges/approves). |
| II. Depend, Never Fork | No engine, no execution adapter, no fork. The module observes `gh`/git read-only state and reads committed text; it integrates no Power BI adapter and is not the execution adapter (F016). |
| III. Medallion, Gold-Only | Not triggered (no SQL, no warehouse read, no Power BI read). The module reads readiness metadata, not data. |
| IV. Source Mapping Before Silver | Reinforced read-only: the module READS `source-map.yaml` approval metadata to check a PR's mapping-approval claim; it never approves or clears the mapping gate (that stays a named human action). |
| V. Agent Stops at Judgment Calls | FR-005/FR-008/FR-009: publish-too-early, PII publish-safety, grain/sentinel/rollup calls are `required_human_decisions[]` routed to a named owner; the module flags and recommends, never rules. An open required-decision gates `merge_ready: yes`. No self-approval, no stage move. |
| VI. Defaults Then Deviations | The verdict's severity defaults (the evidence-chain table) are the starting rule; a deviation in classification is recorded with its reason (FR-006 / US2 scenario 3), never silent. |
| VII. C086 Is An Example | FR-014/SC-001: all planned artifacts generic; C086 / `retail_store_sales` cited as filled instances, never inlined. Obvious placeholders (`<table>`, `<source>`, `<PR#>`). |
| VIII. Static-First, Live Deferred | FR-013/SC-006: NO Python, NO rule, NO CLI, NO CI workflow; no new `retail check` rule added (checker stays exit 0). Reading PR/CI/git state is read-only OBSERVATION, not a new gate. Docs/skill/templates only (rule #8). |
| IX. Secrets & Reproducibility | No secrets, no DSN, no token, no local path in any artifact. The module FLAGS a secret-shaped string in a diff as a blocker (and recommends STOP-rotate-sweep) but never edits it. ASCII + UTF-8 no BOM; short paths. |

**Result**: PASS. No violations; Complexity Tracking left empty.

### Boundary gate (feature-specific, load-bearing)

The two biggest design risks are (a) the module crossing from REPORTING into ACTING
(merge/approve/resolve/stage-move), and (b) `merge_ready` reading as a confidence score. The
plan holds both boundaries explicitly:

- The module OBSERVES and REPORTS. No artifact here, and no future deliverable, may merge a
  PR, submit a review/approval, resolve a thread, edit a PR body, push a commit, or move a
  readiness stage. Every state change stays a named human action (F024 Core Authority).
- `merge_ready` is a DERIVED BOOLEAN with one definition: `no` while any blocker OR any open
  required-human-decision exists; `yes` otherwise. It is NOT a number and NOT an approval.
  The module declines any request for a numeric score (rule #9).
- The module adds NO new gate: it READS recorded `retail check` / `retail validate` / CI
  results as evidence; it never re-runs them as its own check and adds no rule or workflow.

## Project Structure

### Documentation (this feature)

```text
specs/019-pr-readiness-reviewer/
|-- spec.md              # feature spec (this slice)
|-- plan.md              # this file
|-- tasks.md             # task list (this slice)
\-- checklists/
    |-- acceptance.md    # specification quality + acceptance checklist
    \-- governance.md    # Core-Authority / Principle-V / no-fake-confidence gate
```

No `research.md` / `data-model.md` / `contracts/` directory is generated: there is no code to
research, no DB model to design, and no API to contract. The "contract" this feature plans is
the verdict TEMPLATE, a FUTURE deliverable under `templates/` (not a Spec-Kit `contracts/`
dir).

### Repository artifacts this feature PLANS (not created this slice)

```text
.claude/skills/pr-readiness-reviewer/
\-- SKILL.md                       # PLANNED -- the read-only Product Module skill (procedure)

templates/
\-- pr-readiness-report.md         # PLANNED -- generic verdict shape (merge_ready, blockers[],
                                   #            warnings[], required_human_decisions[],
                                   #            evidence[], next_action)

docs/tools/
\-- pr-readiness-reviewer.md       # PLANNED -- when to run, field meanings, blocker-vs-warning
                                   #            rule, read-only boundary
```

These three are ENUMERATED as future outputs only. This spec-only slice creates exactly the
five Spec-Kit files above and none of the three deliverables.

**Structure Decision**: planning/docs feature -- no `src/` or `tests/` change. The future
skill lives under `.claude/skills/` (alongside the shipped read-only verbs like
`retail-control-room` and `retail-validate`); the verdict template joins the existing
`templates/` home (alongside `data-quality-control-room.md`); the narrative doc lives under a
`docs/tools/` dir (the Product-Module doc home introduced by the F024 batch).

## Phase 0 -- Research (no external research needed)

No unknowns requiring external research. The reference shapes are already in-repo: the
read-only aggregator posture (`specs/013-data-quality-control-room/`, the
`retail-control-room` skill), the invoke-and-interpret posture (`retail-validate`), and the
readiness vocabulary (`docs/readiness/readiness-model.md` + `templates/readiness-status.yaml`
-- four statuses + evidence + blockers, no score). The one design choice (verdict field set
+ gating rule) is resolved in this plan, not deferred: the six fields and the
"blocker-OR-open-required-decision flips to no; warnings do not" rule are fixed here.

## Phase 1 -- Design (the artifact shapes -- future deliverables)

**`templates/pr-readiness-report.md`** (generic verdict template). Header block in the
control-room template style: what it is, which principles it instantiates (V stop-and-ask,
VII generic, VIII no-new-gate, IX no-BOM), the no-score rule (#9), the read-only boundary, and
a generic-placeholder note (C086 / `retail_store_sales` cited, never inlined). Fields:
`merge_ready` (yes/no), `blockers[]`, `warnings[]`, `required_human_decisions[]` (each with a
named owner), `evidence[]` (each line: a source -- PR fact or committed path+field), and one
`next_action`. The template includes the evidence-chain severity table (which observed input
defaults to blocker vs warning) so a filled verdict is reproducible.

**`.claude/skills/pr-readiness-reviewer/SKILL.md`** (read-only Product Module). Procedure: (1)
identify the target PR; (2) OBSERVE PR facts read-only (state, mergeable, CI/workflow
conclusions, review threads, review comments); (3) READ the committed readiness evidence the
PR touches (`readiness-status.yaml`, `source-map.yaml`, declared test plan, recorded gate/CI
results, diff for raw-data/secret/path scan); (4) cross-check PR-body claims against that
evidence (stage consistency, approvals consistency, source-map approval metadata, drift); (5)
classify each finding blocker/warning/required-decision per the evidence-chain table; (6)
apply the gating rule to derive `merge_ready`; (7) fill the template; (8) STOP -- report and
recommend `next_action`, take no action. Frontmatter carries the read-only / no-merge /
no-approve / no-stage-move boundary and a no-fake-confidence note. An `## Orchestration`
pointer lets `retail-orchestrate` invoke the reviewer as the pre-merge read; the reviewer
reports, it does not advance any stage.

**`docs/tools/pr-readiness-reviewer.md`** (tool doc). Sections: purpose; when to run it (on
any PR proposing a promotion); each verdict field's meaning; the explicit blocker-vs-warning
gating rule (blocker OR open required-decision -> `merge_ready: no`; warnings surface only);
the `required_human_decisions[]` class and Principle-V routing; the read-only boundary
(cannot merge/approve/resolve/edit/move-stage); the no-fake-confidence rule; and how the
verdict maps to the readiness spine (cross-cutting -- guards promotions at every stage).

## Phase 1 -- Constitution re-check

Re-checked after design: still PASS. The design adds only generic planning text plus three
enumerated future deliverables that READ state and READ committed evidence; it reads no data,
adds no gate/rule/CI, defines no business meaning, takes no GitHub/stage action, and emits no
score. The boundary gate holds (report-not-act; boolean-not-score; read-not-re-run).

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.
