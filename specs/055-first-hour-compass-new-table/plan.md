# Implementation Plan: First-Hour Compass / New-Table Author Onboarding Cockpit

**Branch**: `055-first-hour-compass-new-table` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/055-first-hour-compass-new-table/spec.md`

## Summary

Author a READ-ONLY, docs-first, single-table "you-are-here" orientation surface -- the
stateful single-table sibling of the shipped readiness-viewer (F026) and the stateful
counterpart to the static F006 onboarding-checklist. The MVP is docs/template/skill ONLY
(Principle VIII; hard rule #8): a generic orientation-card template, a read-only skill,
a usage+boundary doc, and a generic stage -> authoring-skill cross-walk. No runtime code,
no DB, no live recompute; `next_step.py` is deferred and enumerated-not-built.

## Technical Context

**Language/Version**: N/A this slice (docs / Markdown authoring only; no runtime code).

**Primary Dependencies**: None. Reads committed `mappings/<table>/readiness-status.yaml`
and `docs/readiness/<stage>-ready.md`; the agent is the runtime (invoke-and-present).

**Storage**: N/A. Reads committed files; writes no state (read-only module).

**Testing**: Static review against the requirements checklist + the adversarial
plan-review (no pytest target this slice; there is no code). The read-only proof is
`git status` clean after a render.

**Target Platform**: The kit's agent surface (a skill invoked by a human/agent operator).

**Project Type**: Docs/template/skill authoring artifact (F024 Product Module,
`read-only` capability level) -- the same shape as the readiness-viewer sibling.

**Performance Goals**: N/A (single-file read + render).

**Constraints**: ASCII only, UTF-8 no BOM (`--`, `->`). Generic-only placeholders
(`<table>`, `<stage_key>`, `<skill>`); Windows 260-char path limit (short names).

**Scale/Scope**: Four authored files + one generic cross-walk table. One table per card.

## Constitution Check

*GATE: must pass before authoring; re-checked in plan-review (stage 6).*

- **Principle I (Agent-First, Gate-Enforced)**: PASS -- the card is a read/present
  surface; the gate exit code stays the authority; the card is never a new gate
  (FR-013).
- **Principle V (Agent Stops at Judgment Calls)**: PASS by construction -- the card
  surfaces the recorded STOP (blocking_reasons, required-owner flag) and never
  populates an approval, clears a blocker, advances a stage, or resolves a seam
  (FR-006, FR-007, FR-008, FR-012, FR-014). The four human seams stay OPEN in the spec.
- **Principle VII (C086 Is An Example, Not The Schema)**: PASS -- every artifact is
  generic; C086/retail_store_sales cited only as a filled instance (FR-005, FR-017).
- **Principle VIII / hard rule #8 (Static-First, Live Deferred)**: PASS -- docs/
  template/skill only; no validator, no DB, no live recompute; `next_step.py` deferred
  (FR-015, FR-016).
- **Hard rule #9 (No Fake Confidence)**: PASS -- no numeric/percent/confidence score;
  a score request is declined (FR-009).
- **Readiness-pipeline ordering**: PASS -- next artifact is the FIRST non-pass stage;
  no downstream stage presented as reachable when an upstream gate is not `pass`
  (FR-003, FR-012).
- **Renders-never-re-derives**: PASS -- every value copies a recorded field; git status
  clean after a run (FR-008, FR-010, SC-003).

No constitution violation. No deferred capability assumed (F016 Power BI Execution
Adapter and F031-F033 spec-only runtimes are NOT referenced; the Compass reads static
files only).

## Project Structure

### Documentation (this feature)

```text
specs/055-first-hour-compass-new-table/
|-- spec.md              # stage 2 (done)
|-- plan.md              # this file (stage 4)
|-- tasks.md             # stage 4 (/speckit-tasks)
|-- analysis.md          # stage 5 (/speckit-analyze, repo convention)
|-- plan-review.md       # stage 6 (adversarial skeptic)
`-- checklists/
    `-- requirements.md   # stage 2 quality checklist
```

### Authored artifacts (repository, the MVP deliverables)

```text
templates/first-hour-compass.md            # generic single-table orientation-card template
                                           #   (mirrors templates/readiness-view.md)
.claude/skills/first-hour-compass/SKILL.md # read-only skill (mirrors readiness-viewer contract)
docs/tools/first-hour-compass.md           # usage + boundary doc (mirrors docs/tools/readiness-viewer.md)
```

The generic stage -> authoring-skill cross-walk table is authored INSIDE these
artifacts (the template + the skill + the tools doc); it is not a separate file this
slice.

### Deferred (enumerated, NOT built this slice)

```text
src/retail/tools/next_step.py    # OPTIONAL future read-only resolver/scaffolder.
                                 #   Enumerated only; nothing in this slice creates it.
                                 #   If ever built: still read-only, stdlib, no new gate,
                                 #   no DB read (mirrors readiness_viewer.py deferral).
```

## Design approach (mirror the shipped sibling)

The readiness-viewer (F026) is the proven pattern; the Compass reuses it verbatim where
possible and states only its deltas:

- **Reuse**: the read-only contract (creates no truth, changes no state, infers no
  approval, fabricates no evidence, runs no validator, opens no DB, emits no score);
  the honest-state rules (missing file, malformed file, pass-without-evidence,
  referenced-file-not-found); the approval-flag two-condition rule read from the stage
  doc; the module-contract declaration (F024 Product Module / `read-only`); the
  renders-never-re-derives evidence-chain table.
- **Deltas from readiness-viewer** (the reason it is a separate module, not a re-spec):
  (1) SINGLE table, not the multi-table matrix; (2) a NEXT-ARTIFACT pointer (the
  artifact of the first non-pass stage) -- readiness-viewer has none; (3) an
  AUTHORING-SKILL route via the generic cross-walk -- readiness-viewer has none;
  (4) the you-are-here orientation framing for a new-table author.
- **Delta from F006 onboarding-checklist**: stateful (reads readiness-status.yaml) vs
  static definition-of-done.

## Phasing

- **Phase 0 (research)**: none required beyond the grounding already done; the sibling
  pattern (readiness-viewer skill + template + tools doc) is the design source. No
  research.md needed.
- **Phase 1 (author the artifacts)**: write the three files + embedded cross-walk,
  generic and ASCII, mirroring the sibling.
- **Phase 2 (tasks)**: `/speckit-tasks` enumerates the authoring + verification tasks.

## Complexity / risk notes

- **C086 leak (MODERATE, guardable)**: the only filled `readiness-status.yaml` is
  retail_store_sales. Mitigation exactly as readiness-viewer: template + cross-walk stay
  generic (`<table>`/`<stage_key>`/`<skill>`); C086 cited only as a filled instance.
- **Scope creep to a gate/executor (guarded)**: FR-013 forbids the card becoming a gate;
  FR-015/FR-016 keep this docs-only and defer `next_step.py`.
- **Roadmap provenance (open)**: no F-number is minted; roadmap admission is a human
  decision (Clarifications Q1).
