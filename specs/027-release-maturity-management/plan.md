# Implementation Plan: Release & Maturity Management

**Branch**: `027-release-maturity-management` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

**Roadmap feature**: F033 (Numbering note: roadmap F-number is authoritative; spec-dir is
the next free on-disk slot. This batch: F024=018, F025=019, F026=020, F027=021, F028=022,
F029=023, F030=024, F031=025, F032=026, F033=027. Dir 027 = roadmap F033; when they
disagree, the F-number wins.)

**Input**: Feature specification from `specs/027-release-maturity-management/spec.md`

## Summary

Plan the kit's release + maturity record: a per-release **release note** (seven required
blocks: what became possible / what changed / readiness stages affected / new
modules+adapters / known limitations / migration notes / next best slice) and an
**evidence-gated maturity ladder** (L0 docs-only .. L6 official Power BI execution adapter)
whose reported level is the HIGHEST rung whose required evidence ALL exists. This is
**docs/templates + one skill, planned only** (Principle VIII; roadmap rule #8): no Python,
no CLI verb, no `retail check` rule. The defining design move is reconciling a numbered 0-6
ladder with hard rule #9 (no fake confidence): the ladder is an evidence-gated MILESTONE
ladder -- structurally the same as the seven numbered readiness stages, with a binary
"evidence exists or not" test per rung -- and emphatically NOT a score/percentage. The kit's
honest level today is L2 achieved (two worked examples) with L3 (repeatable silver/gold)
proven for those two tables; L4/L5/L6 are NOT BUILT and the model says so. This feature
CONSUMES the F028 evidence pack + the F032 compatibility matrix; it re-measures nothing.

## Technical Context

**Language/Version**: None (docs/planning this slice -- Markdown + YAML text artifacts only).

**Primary Dependencies**: None at runtime. Authoring borrows the read-and-present posture
from `.claude/skills/retail-control-room/SKILL.md` (F012) and the four-status / no-score
vocabulary from `docs/readiness/readiness-model.md`. Consumes (does not import) the F028
evidence pack and F032 compatibility matrix as evidence inputs.

**Storage**: Committed text. THIS slice writes only the five spec-kit files. The FUTURE
deliverables (planned, not created): `templates/release-notes.md`,
`templates/maturity-report.md`, `.claude/skills/release-notes-generator/SKILL.md`, and the
`docs/releases/` output dir. Filled, approved releases live under `docs/releases/<release>/`.

**Testing**: No code, so no unit tests. Verification is: (1) `retail check` exit 0 with rule
count unchanged, (2) the spec defines the ladder as evidence-gated milestones with NO numeric
score, (3) the honest current-state pin (L2 achieved, L4-6 not built) is present and
verifiable against the repo, (4) ASCII + UTF-8 no-BOM on every file.

**Target Platform**: Repo text artifacts consumed by an agent + reviewed by a named release
owner; the product-level release process reads them.

**Project Type**: Documentation/planning feature (no source tree change this slice).

**Performance Goals**: N/A (static text).

**Constraints**: ASCII + UTF-8 no BOM; generic templates (no per-table specifics); no numeric
maturity score anywhere; no re-measurement (no `retail check`/`validate`, no DB, no
`powerbi/` read); no self-approval / self-level-bump / publish; Windows path budget
(repo-relative <= 200 chars -- keep names short).

**Scale/Scope**: 5 spec-kit files this slice. The planned feature is 2 templates + 1 skill +
1 output dir. Seven maturity rungs; seven release-note blocks.

## Constitution Check

*GATE: must pass before and after design. Constitution at `.specify/memory/constitution.md`.*

| Principle | How this feature complies |
|-----------|---------------------------|
| I. Agent-First, Gate-Enforced | The generator is a skill the agent runs; it adds no gate and no authority over pass/fail. Release approval + level confirmation are the named release owner's, not the agent's. `retail check` stays the gate; this feature does not touch it. |
| II. Depend, Never Fork | No engine fork, no Power BI execution path. Pure local opinion in a skill + two templates. Consumes F028/F032 outputs; reproduces neither. |
| III. Medallion, Postgres-First, Gold-Only | Not triggered (no silver/gold SQL, no PBIP). The maturity rungs DESCRIBE the medallion capability (L3 repeatable silver/gold; L6 Power BI execution) but build none of it. |
| IV. Source Mapping Before Silver | Not triggered (no mapping/SQL authored). The ladder records that medallion repeatability is proven only for the two worked tables -- it does not skip the ordering, it reports on it. |
| V. Agent Stops at Judgment Calls | FR-010/FR-012: release approval, level confirmation, and conflicting evidence are stop-and-ask; the agent recommends + drafts, a named human decides. An over-claimed level is refused by the binary evidence test regardless of who asks. |
| VI. Defaults Then Deviations | The ladder + the seven note-blocks are the default record shape; any deviation (e.g. a release with no evidence pack) is recorded as "evidence not available", never silently filled. |
| VII. C086 Is An Example | Templates carry no per-table specifics. c086 + retail_store_sales are cited as the kit's real track record -- allowed evidence-citation FOR the ladder, distinct from baking per-table logic into a generic template. |
| VIII. Static-First, Live Deferred | FR-001/FR-009: NO Python, NO rule, NO CLI, NO live re-measurement (no `retail check`/`validate`, no DB, no `powerbi/` read). Docs/skill/templates only (rule #8); `retail check` exit 0 + no new rule added. |
| IX. Secrets & Reproducibility | No secrets, no DSNs, no local paths. ASCII + UTF-8 no BOM; short repo-relative paths; templates are reproducible copy-me text; `->` for arrows, `--` for dashes. |

**Result**: PASS. No violations; Complexity Tracking left empty.

### Boundary gate (feature-specific, load-bearing)

Two boundaries carry this feature; the plan holds them explicitly.

- **No-fake-confidence boundary (the crux).** The 0-6 ladder is the single biggest risk: a
  numbered ladder can read as a score. The plan fixes it as an evidence-gated milestone
  ladder -- a binary test per rung, level = highest all-evidence-present rung -- exactly the
  way the seven numbered readiness stages are legitimate milestones, not scores. NO artifact
  here emits a percentage, a 0-100 number, or an average. (Spec FR-005/FR-006; governance.md
  has a dedicated CHK.)
- **Consume-never-re-measure / never-self-approve boundary.** The generator READS the F028
  pack + F032 matrix + roadmap ledger and DRAFTS/ASSESSES; it never re-runs a validator,
  opens a DB, reads `powerbi/`, self-approves a release, self-confirms a level, or publishes.
  (Spec FR-009/FR-010; the planned skill carries this verbatim in its header.)

## Project Structure

### Documentation (this feature)

```text
specs/027-release-maturity-management/
|-- spec.md              # /speckit-specify output (done)
|-- plan.md              # This file (/speckit-plan output)
|-- tasks.md             # /speckit-tasks output
`-- checklists/
    |-- acceptance.md    # spec quality + acceptance checklist
    `-- governance.md    # Core-Authority / Principle-V / no-fake-confidence gate
```

No `research.md` / `data-model.md` / `contracts/` dir: there is no code to research, no DB
model, and no API contracts. The "contracts" this feature will later produce are the two
TEMPLATES, which live under `templates/` (a future deliverable), not under a speckit
`contracts/` dir.

### Repository artifacts this feature PLANS (not created this slice)

```text
templates/
|-- release-notes.md          # PLANNED -- generic per-release note (seven required blocks)
`-- maturity-report.md        # PLANNED -- generic point-in-time ladder snapshot (seven rungs)

.claude/skills/
`-- release-notes-generator/
    `-- SKILL.md              # PLANNED -- the draft-and-assess verb; agent is the runtime

docs/releases/                # PLANNED -- durable home for filled, approved releases
`-- <release>/                #   one set per release (note + maturity snapshot), human-approved
    |-- release-notes.md      #   filled from templates/release-notes.md
    `-- maturity-report.md    #   filled from templates/maturity-report.md
```

These are ENUMERATED here as future outputs; this slice creates NONE of them -- only the
five spec-kit files above are written.

**Structure Decision**: docs/templates + skill feature -- no `src/`/`tests/` change. The two
templates live in the existing `templates/` dir (alongside the other copy-me artifacts); the
skill lives under `.claude/skills/` (alongside `retail-control-room`); filled releases live
under a new `docs/releases/` dir (parallel to `docs/roadmap/`), keeping `docs/roadmap/` the
delivered ledger and `docs/releases/` the per-release record. Release-notes vs maturity-report
are kept as TWO files because they answer two questions (per-release "what became possible" vs
point-in-time "how mature, by evidence") and have two lifecycles.

## Phase 0 -- Research (no external research needed)

No unknowns requiring external research. The two reference shapes are in-repo: the
read-and-present posture of `.claude/skills/retail-control-room/SKILL.md` (F012 -- aggregate
committed evidence, present, stop) and the four-status / no-score vocabulary of
`docs/readiness/readiness-model.md` + `templates/readiness-status.yaml`. The honest current
level is verifiable against the repo today: `mappings/c086/` and `mappings/retail_store_sales/`
exist (two worked examples -> L2); no dbt adapter, no Dagster project, no Power BI execution
adapter exist (-> L4/L5/L6 not built). The one design decision (ladder-vs-score) is resolved
in Phase 1, not deferred.

## Phase 1 -- Design (the artifact shapes, planned)

**templates/release-notes.md** (generic). Header in the house style: what it is, principles
it instantiates (VII generic, VIII static, IX no-BOM), the no-unbacked-claim rule (FR-008),
the consume-never-re-measure note (FR-009). Body = the seven required blocks (FR-004), each
with a placeholder + an evidence-citation slot; plus `status` (`draft`/`approved`) and
`approvals[]` (named release owner + date). A "known limitations" block that MUST list the
unbuilt rungs.

**templates/maturity-report.md** (generic). Header same house style + the explicit
ladder-is-not-a-score reconciliation (FR-006). Body = the seven rungs, each row carrying:
rung id (L0..L6), the capability, the BINARY evidence test, the achieved/not-achieved
verdict, and the cited evidence (or named missing artifact). A "reported level" line = the
highest all-evidence-present rung. A standing note that L4/L5/L6 are unbuilt and that L3 is
caveated to the worked tables.

**.claude/skills/release-notes-generator/SKILL.md** (planned skill). Frontmatter (name +
gating description). Procedure: read inputs (F028 pack, F032 matrix, roadmap ledger) ->
draft the seven note-blocks with citations -> assess each rung by its binary test ->
report the level -> STOP for the named release owner. Carries the two boundaries verbatim
(no score; consume-never-re-measure; never self-approve/level-bump/publish). Ends with an
`## Orchestration` pointer for `retail-orchestrate`.

**docs/releases/** (planned dir). Holds one subdir per approved release; the generator drafts
into it, a human approves.

## Phase 1 -- Constitution re-check

Re-checked after design: still PASS. The design adds only planned generic text artifacts +
one skill, reads no PBIP, runs no validator, adds no rule, emits no score, and keeps the
ladder as evidence-gated milestones + the four-status/no-score vocabulary. Both boundary
gates (no-fake-confidence; consume-never-re-measure/never-self-approve) hold.

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.
