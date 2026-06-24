# Implementation Plan: dashboard design skill -- design a report FROM approved metric contracts

**Branch**: `012-dashboard-design-skill` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/012-dashboard-design-skill/spec.md`

## Summary

Add one governed agent skill, `.claude/skills/dashboard-design/SKILL.md`, that designs a
dashboard FROM approved metric contracts (F009) bound by a governed PBIP model (F010).
It is hard-gated on `semantic_model_ready: pass` (roadmap rule 5), authors reviewable
design guidance only (a layout plan, a visual list, a visual->contract binding map), and
STOPS at the publish boundary -- it never calls pbi-cli/PBIP authoring automation (rule
6, F016 owns that). Docs/skill-first (rule 8), generic (rule 7). No code, no codegen
engine, no CLI subcommand, no new `retail check` rule -- it consumes existing rule R1.

## Technical Context

**Language/Version**: N/A -- agent-procedure Markdown (`SKILL.md` front-matter + body).
The agent is the runtime, same posture as `source-mapping` and `retail-build-warehouse`.

**Primary Dependencies**: none new. Reads the readiness status
(`templates/readiness-status.yaml` instances), approved metric contracts (F009 artifact,
PLANNED), and the governed PBIP model (F010, `powerbi/<Model>.SemanticModel/`). Relies on
existing `retail check` rule R1 (relative model reference). No `pbi-cli`, no Power BI
Desktop, no network, no DB driver.

**Storage**: committed text only. Outputs are reviewable design artifacts (layout plan,
visual list, visual->contract binding map) plus a `dashboard_ready` stage entry in the
subject area's readiness status. No DB writes, no PBIR generation by automation.

**Testing**: doc/fixture review -- a generic fixture subject area exercising each
`semantic_model_ready` status (the gate) and a contracts-present happy path (the binding
map). `retail check` exit 0 on any committed PBIR text the design run touches (R1). No new
unit-test surface required for a skill; the binding map is the auditable artifact.

**Target Platform**: the Claude Code agent in this repo (Windows; 260-char path limit ->
keep the skill dir/name short: `dashboard-design`).

**Project Type**: agent skill (Layer 6 design verb), single repo.

**Performance Goals**: N/A (an authoring procedure, not a runtime service).

**Constraints**: ASCII + UTF-8 no BOM; generic (no C086/pharmacy specifics); no real
host/secret in any output (G6 + repo secret rule); never crosses the author/publish
boundary (rule 6); never self-grants `dashboard_ready: pass` (needs an `approvals[]`
design-review entry).

**Scale/Scope**: one skill file + (optional) a generic design-artifact template scaffold.
One worked instance is a per-subject-area working set, not part of this slice's commit.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this feature complies |
|-----------|---------------------------|
| I. Agent-First, Gate-Enforced | A skill (agent verb); the gate is `retail check` R1 + the readiness `semantic_model_ready: pass` precondition. The agent proposes the design; the gate + the human review dispose. |
| II. Depend, Never Fork | No fork, no vendored engine. pbi-cli stays the LATER adapter (F016); this skill never invokes it. No new codegen surface. |
| III. Medallion, Postgres-First, Gold-Only | Unaffected -- design reads the gold-bound semantic model; no new read surface. |
| IV. Source Mapping Before Silver | Unaffected and reinforced by analogy: the same author-then-stop posture, one stage later. |
| V. Agent Stops at Judgment Calls | The skill STOPS at the business-question choice, the grain-fit judgment, and the design-review sign-off -- it never self-answers them. |
| VI. Defaults Then Deviations | Grain-appropriate visual is the default; a grain-mismatch deviation must be recorded with a reason. |
| VII. C086 Is An Example | The skill text + any template are generic; worked values live only in a per-subject-area instance. |
| VIII. Static-First, Live Deferred | Docs/skill-first (rule 8); the only check is the existing static R1. Publishing (live) is deferred to F016. |
| IX. Secrets and Reproducibility | No real host/secret in any output (G6); ASCII + UTF-8 no BOM. |

**Roadmap hard rules**: rule 5 (no design before contracts) = FR-001/FR-003;
rule 6 (no pbi-cli/PBIP before semantic-model readiness) = FR-004/User Story 3;
rule 7 (generic) = FR-009; rule 8 (docs/templates first) = the whole skill-first shape.

**Result**: PASS. No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/012-dashboard-design-skill/
|-- spec.md       # the feature spec (committed)
|-- plan.md       # this file
|-- tasks.md      # the task list (speckit-tasks output)
`-- analysis.md   # cross-artifact consistency findings (speckit-analyze output)
```

No `research.md` / `data-model.md` / `contracts/` / `quickstart.md`: there is no
unknown to research (the stage doc `docs/readiness/dashboard-ready.md` already specifies
the gate, artifacts, and checks), no data model (the entities are the contracts/model
this feature consumes, owned by F009/F010), and no API contract (a skill, not a service).

### Source (repository root)

```text
.claude/skills/dashboard-design/
`-- SKILL.md      # the design verb: gate-check -> author guidance -> stop at publish boundary

templates/                              # OPTIONAL, generic scaffolds (no C086 values)
|-- dashboard-layout.md                 # blank layout-plan + visual-list scaffold
`-- visual-contract-binding-map.md      # blank visual->contract binding map scaffold
```

**Structure Decision**: Pure skill at `.claude/skills/dashboard-design/SKILL.md`,
matching the existing all-skills verb architecture (`source-mapping`,
`retail-build-warehouse`, `retail-validate`, `retail-orchestrate`, `pbip-workflow`). The
two `templates/` scaffolds are generic blanks (rule 7) the skill copies into a
per-subject-area working set; whether to ship them in this slice or inline their shape in
the skill body is a tasks-level call (kept minimal -- YAGNI). No code, no `src/` change,
no new `retail check` rule (R1 already covers the relative model reference).

## Phasing

- **Phase 0 (research)**: none required -- the stage doc + readiness model + R1 rule are
  the authoritative inputs and already exist. Recorded as "no open unknowns."
- **Phase 1 (design)**: author `SKILL.md` (front-matter `name`/`description`; body:
  scope boundary, the hard gate, preconditions, the procedure, what-the-agent-must-NOT-do,
  see-also) and, if kept, the two generic template scaffolds. Re-run Constitution Check
  (still PASS -- no new surface).
- **Phase 2 (tasks)**: enumerated in `tasks.md`.

## Complexity Tracking

> No Constitution Check violations. This table is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none)    | --         | --                                  |
