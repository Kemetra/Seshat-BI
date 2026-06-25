# Implementation Plan: Evidence Pack Generator

**Branch**: `022-evidence-pack-generator` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

**Roadmap feature**: F028 (dir 022 == F028; F-number is authoritative when dir and
F-number disagree).

**Input**: Feature specification from `specs/022-evidence-pack-generator/spec.md`

## Summary

Plan the **Evidence Pack Generator** (F028): a product MODULE that, when built,
COMPOSES a single readable 10-section evidence pack for a table/report at the late
readiness stages, assembling already-committed evidence across the whole spine
(source -> publish) and EMBEDDING the shipped F013 handoff pack as section 08. The
module writes DERIVED evidence only -- it summarizes and links existing artifacts,
records any missing source as a BLOCKER (never invents), surfaces (never asserts)
the `publish_ready` state, and moves no stage to `pass`. This slice is
**planning-only**: the deliverable is the 5 spec-kit files. The generator skill, its
tool doc, and its two templates are ENUMERATED as future outputs, not created now.

## Technical Context

**Language/Version**: None -- docs/planning this slice (Markdown spec-kit artifacts).
The future module is a skill (invoke-and-compose) over committed text artifacts; no
new language/runtime is introduced by this spec.

**Primary Dependencies**: F024 (Companion Tools Architecture) for the product-module
posture and Core-vs-Module authority vocabulary. Consumes the OUTPUTS of F008, F009,
F010, F011/F011A, F012, F013, F014, F015 and reads the Core Authority
`readiness-status.yaml`. No new engine; depends-never-forks.

**Storage**: This slice writes 5 committed text files under
`specs/022-evidence-pack-generator/`. The FUTURE module (not built here) would write
a derived pack (index + summary) per table and read the existing section-source
artifacts; it stores no new truth.

**Testing**: No code this slice, so no unit tests. Verification is doc-level: (1) the
5 files exist and match house style; (2) the 10-section contract is complete and each
section is mapped to a committed source; (3) the F013 scope delta is explicit and
one-directional (F028 consumes F013); (4) the publish-ready guardrail (surface, never
assert) is an FR + edge case; (5) ASCII + UTF-8 no-BOM + short-path check on all files.

**Target Platform**: Repo text artifacts consumed by an agent + reviewed by a human;
the late readiness stages read/compose them later.

**Project Type**: Documentation/planning feature (no source tree change this slice).

**Performance Goals**: N/A (static planning text).

**Constraints**: ASCII + UTF-8 no BOM; generic (no C086 / retail_store_sales values);
Windows path budget (short repo-relative names); no numeric confidence/health score;
no live DB / PBIP read; no publish; no new `retail check` rule or readiness stage.

**Scale/Scope**: 5 spec-kit files this slice. The module's future contract is a fixed
10-section pack + 4 planned deliverables (1 skill, 1 doc, 2 templates).

## Constitution Check

*GATE: must pass before and after design. Constitution at `.specify/memory/constitution.md`.*

| Principle | How this feature complies |
|-----------|---------------------------|
| I. Agent-First, Gate-Enforced | Adds no gate and grants the module no authority over pass/fail. The pack COMPOSES evidence and SURFACES the recorded `publish_ready` state; the gate stays `retail check` + the recorded human approval. The module moves no stage to `pass`. |
| II. Depend, Never Fork | No engine, no Power BI MCP, no fork. The module reads committed artifacts and writes a derived pack -- pure local composition. |
| III. Medallion, Gold-Only | Not triggered (writes no SQL). Section 04/06 summarize gold-bound contracts/model already authored upstream; the pack adds no binding. |
| IV. Source Mapping Before Silver | Not triggered (no silver SQL). The pack sits at the LATE stages, far downstream of mapping; it records the ordering, builds nothing. |
| V. Agent Stops at Judgment Calls | FR-005/FR-006/FR-009: publish authorization, source disagreements, and grain/PII/rollup/sentinel ambiguities surfaced in the pack are stop-and-ask -- the pack RECORDS them as `warning`/`blocked` for the named human; it never resolves or self-approves. |
| VI. Defaults Then Deviations | The 10-section order is the default contract; the pack starts from existing artifacts and records gaps rather than silently substituting. Deferred decisions (tally indicator, storage path) are recorded, not silently chosen. |
| VII. C086 Is An Example | FR-011 / SC-006: skill, doc, and templates stay generic; the worked example is cited by reference only, never inlined. |
| VIII. Static-First, Live Deferred | This slice is planning-only (5 files). The FUTURE module reads ONLY committed artifacts -- no live DB, no PBIP read, no publish, no Power BI execution (F016). FR-010 / FR-013. |
| IX. Secrets & Reproducibility | No secrets, DSNs, or local paths. ASCII + UTF-8 no BOM; short repo-relative paths; the pack is reproducible composition of committed inputs. FR-012. |

**Result**: PASS. No violations; Complexity Tracking left empty.

### Boundary gate (feature-specific, load-bearing)

The two biggest scope risks and how the plan holds them:

- **Bleed into F013.** F028 COMPOSES the full pack and EMBEDS F013 as section 08; it
  never re-authors the handoff template and never records the publish approval. The
  relationship is one-directional (F028 consumes F013). The plan repeats this in the
  spec scope-delta, FR-004, and the section-08 source mapping.
- **Manufacturing publish authority.** "Generator" must not become "approver." The
  pack SURFACES `publish_ready` from `readiness-status.yaml` and prints a publish-
  ready claim ONLY when `pass` + a recorded named approval exist (FR-005/FR-006). It
  writes no approval and moves no stage. This is both an FR and an edge case.
- **"Generator" leaking into building now.** This is a PLANNING slice. The module is
  a future deliverable; nothing is built here beyond the 5 files. The 4 future
  artifacts are enumerated as PLANNED outputs, not created.

## Project Structure

### Documentation (this feature)

```text
specs/022-evidence-pack-generator/
|-- spec.md                 # /speckit-specify output (this slice)
|-- plan.md                 # This file (/speckit-plan output)
|-- tasks.md                # /speckit-tasks output
`-- checklists/
    |-- acceptance.md       # specification quality + acceptance checklist
    `-- governance.md       # Core-vs-Module authority / no-self-approval gate
```

No `research.md` / `data-model.md` / `contracts/` directory: there is no code to
research, no DB model, and no API. The pack "contract" this feature defines (the 10
sections + source map) lives INSIDE spec.md and is realized later as the two
`templates/` artifacts -- not as a speckit `contracts/` dir.

### Repository artifacts this feature PLANS (not created)

These are FUTURE outputs ENUMERATED by this spec; this slice does NOT create them.

```text
.claude/skills/evidence-pack-generator/
`-- SKILL.md                          # PLANNED: invoke-and-compose verb (read sources,
                                      #   render 10-section pack, record per-section
                                      #   status + blockers, surface publish state, STOP)

docs/tools/
`-- evidence-pack-generator.md        # PLANNED: tool doc -- 10-section contract, the
                                      #   source-artifact map, allowed/forbidden ops,
                                      #   missing-source-is-a-blocker rule, F013 delta

templates/
|-- evidence-pack-index.md            # PLANNED: ordered 10-section index, each row ->
                                      #   source artifact + status + blocker
`-- evidence-pack-summary.md          # PLANNED: one-page readiness summary (surfaces
                                      #   stage + publish_ready + recorded approval +
                                      #   rolled-up blockers; asserts nothing)
```

**Structure Decision**: Planning/docs feature -- no `src/` or `tests/` change. The
future templates live in the existing `templates/` dir (alongside `templates/handoff/`
from F013) so all copy-me artifacts share one home; the tool doc lives under
`docs/tools/` (the established tool-doc home); the skill lives under `.claude/skills/`
(alongside the shipped readiness skills). Per-table FILLED pack placement is a
deferred decision (spec "Deferred decisions"; cheaply reversible).

## Phase 0 -- Research (no external research needed)

No unknowns requiring external research. The reference shapes are all in-repo: F013's
`templates/handoff/bi-handoff-pack.md` (the composes-existing-evidence + completeness-
checklist idiom to embed as section 08), `templates/readiness-status.yaml` +
`docs/readiness/readiness-model.md` (the four-status / no-score vocabulary the pack
reuses), and the shipped section-source artifacts (F008-F015). The one open item is
the 10-to-source mapping, resolved in Phase 1 below, not deferred to research.

## Phase 1 -- Design (the pack contract)

**The 10-section contract (fixed, ordered) and its committed source map:**

1. **01-source-profile** <- the table's source-profile.md (Source Ready).
2. **02-source-map-summary** <- `source-map.yaml` (the Principle-IV mapping-gate artifact;
   F008 Grain Confidence + Mapping Diff Reviewer consumes it, does not produce it).
3. **03-assumptions-and-decisions** <- `assumptions.md` + `unresolved-questions.md`
   + relevant ADRs.
4. **04-metric-contracts** <- `mappings/<table>/metrics/` filled contracts (F009/F010).
5. **05-validation-summary** <- recorded `retail check` + `retail validate` results +
   the F012 data-quality roll-up.
6. **06-semantic-model-summary** <- F010 / `retail semantic check` recorded output.
7. **07-dashboard-summary** <- F011 dashboard design + F011A visual foundation.
8. **08-handoff-pack** <- the table's FILLED F013 `templates/handoff/bi-handoff-pack.md`
   instance (EMBEDDED / referenced; never re-authored).
9. **09-known-limitations** <- `data-issues.md` + recorded caveats.
10. **10-release-notes** <- F015 reconciliation ledger (+ F014 drift signals +
    `readiness-status.yaml` `approvals[]`), so even release notes COMPOSE, never invent.

**Per-section record shape** (planned for `evidence-pack-index.md`): section id +
title, `status` (one of `not_started` / `blocked` / `warning` / `pass`), source
artifact path(s), `evidence[]`, `blocking_reasons[]`, and a one-line summary. A
missing/unfilled/blank-template source -> `blocked` + a blocker naming the source;
no fabricated content.

**Pack summary shape** (planned for `evidence-pack-summary.md`): current readiness
stage; `publish_ready` status (SURFACED from `readiness-status.yaml`); recorded
approval (owner + date) when `pass`; rolled-up open blockers across sections; an
explicit "in-progress" marker when composed before Publish Ready. The summary prints
a publish-ready claim ONLY when `publish_ready: pass` + a named approval is recorded.

**The F013 delta wiring**: section 08 references the filled handoff instance and links
to it; the doc states verbatim that F028 consumes F013, embeds it, and never edits or
redefines it, and never records the publish approval (F013 / Core Authority owns it).

**Skill posture** (planned `SKILL.md`): HARD on the allowed/forbidden ops -- read
committed sources, render the pack, record status, surface (not assert) publish state,
STOP at any judgment call (publish authorization, source disagreement, grain/PII).

## Phase 1 -- Constitution re-check

Re-checked after design: still PASS. The design adds only a fixed section contract +
a committed-source map + the four-status/no-score record shape. The module reads only
committed artifacts, writes a derived pack, surfaces (never asserts) publish state,
re-authors nothing (esp. F013), adds no rule, and moves no stage. Boundary gate holds
(no live read; no approval write; no F013 redefinition; planning-only this slice).

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.
