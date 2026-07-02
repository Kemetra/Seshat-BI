# Implementation Plan: Design-Foundation Idea Lane + Backlog Seed (G1)

**Branch**: `066-design-foundation-idea-lane` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/066-design-foundation-idea-lane/spec.md`

## Summary

Give the Power BI design layer a first-class home in the idea backlog and the
same shipped-row->roadmap link the knowledge layers already have via IL1. The
approach is the smallest viable seam: a design-foundation grouping in
`docs/roadmap/idea-backlog.md`, the existing shipped-ideas ledger contract
extended to accept a design-layer ship, a small routing/rendering edit in
`.claude/workflows/idea-engine.js` so the existing `design` lens and
`design-foundation` reviewer land under the grouping, and a "See also" pointer in
the design skill. Documentation plus a small JavaScript edit only -- NO
static-check rule module, NO auto-reconciler (deferred HORIZON). The lane records
and routes; it never promotes an idea onto the roadmap and never self-assigns an
F-number (Principle V, roadmap hard rules #8/#9, IL1 read-only ledger contract).

## Technical Context

**Language/Version**: Markdown + YAML (docs); Node ESM JavaScript (the existing
`.claude/workflows/idea-engine.js` render/routing code). No Python change.

**Primary Dependencies**: None new. Reuses the existing idea-engine design lens,
design-foundation panel reviewer, and `strengthens_layer = design-system` enum.

**Storage**: Plain-text repo files: `docs/roadmap/idea-backlog.md` (rendered
prose), `docs/roadmap/shipped-ideas.yaml` (human-curated ledger).

**Testing**: Read-inspection of the rendered backlog and the design skill; the
existing `retail check` governance gate (must stay green). No new pytest module
(no `src/retail` change). The idea-engine's own render is a pure-JS function
whose output is inspected; no new runtime is added.

**Target Platform**: The idea-engine workflow + the docs/roadmap governance
surface. Off-spine (no roadmap readiness stage).

**Project Type**: Docs + governance workflow edit (single repo).

**Performance Goals**: N/A -- documentation and a small deterministic render edit.

**Constraints**: ASCII + UTF-8 without BOM (constitution rule IX: use `--` and
`->`, no glyphs). Generic-only (no c086/pharmacy specifics; rule 7). No numeric
score (rule 9). No executor / no report authoring (rule 8). Windows 260-char path
limit -- names stay short. Line endings via `.gitattributes` (`core.autocrlf`).

**Scale/Scope**: Four files touched (backlog, ledger, engine, skill). No schema
migration unless a human rules FR-012 that way; default is reuse the existing
3-field ledger shape unchanged.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle V (Agent Stops at Judgment Calls)**: PASS. The three human-owned
  decisions (lane grain FR-011, ledger schema change FR-012, roadmap F-row) are
  left OPEN in the spec's Clarifications block and this plan does not resolve
  them. The lane records/routes and never promotes an idea onto the roadmap.
- **Roadmap hard rule #8 (docs is not runtime)**: PASS. Docs + small-JS render
  edit only; no `src/retail` change and no retail-check rule module.
- **Roadmap hard rule #9 (never a numeric score)**: PASS. The grouping is
  categorical (section/tag/status); no computed or ranked score is attached.
- **IL1 read-only ledger contract**: PASS. `shipped-ideas.yaml` stays
  human-curated and engine-read-only; no entry is fabricated (Clarify Q2:
  shape-only, no design entry added now). Ground remains the single owner of
  git-derived ship-status.
- **Four-surface / never-author discipline**: PASS. No PBIP/PBIR authored, no DAX
  generated, no metric invented, no data baked into a theme/background.
- **Generic-only (rule 7)**: PASS. No worked-example paths/hexes/metrics baked in.
- **No deferred-capability assumption**: PASS. F016 and spec-only runtimes are not
  relied on; the feature executes nothing.

No violations. Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/066-design-foundation-idea-lane/
├── spec.md              # /speckit-specify output (+ clarify session)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (ledger entry + grouping shapes)
├── quickstart.md        # Phase 1 output (how to verify the lane)
├── contracts/
│   └── design-lane.md   # Phase 1 output (the lane + ledger contract, prose)
├── tasks.md             # /speckit-tasks output
└── checklists/
    └── requirements.md  # spec quality checklist
```

### Source Code (repository root)

This feature touches existing governance/docs surfaces only; it creates no new
source tree. The four touched paths:

```text
docs/roadmap/idea-backlog.md          # add the design-foundation grouping
docs/roadmap/shipped-ideas.yaml       # extend to accept a design-layer ship (shape only)
.claude/workflows/idea-engine.js      # route design lens + reviewer output under the grouping
.claude/skills/powerbi-dashboard-design/SKILL.md   # "See also" pointer to the lane
```

**Structure Decision**: No new module or directory. The change is additive edits
to four existing files plus this feature's own spec artifacts. Explicitly NO
`src/retail/rules/` module and NO reconciler script (HORIZON, out of scope).

## Complexity Tracking

No constitution violations. Table intentionally empty.
