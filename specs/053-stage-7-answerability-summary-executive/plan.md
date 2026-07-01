# Implementation Plan: Stage 7 Answerability Summary (executive-readable)

**Branch**: `053-stage-7-answerability-summary-executive` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/053-stage-7-answerability-summary-executive/spec.md`

## Summary

Author one new generic handoff template, `templates/handoff/answerability-summary.md`, and
add one non-gating reference to it from `docs/readiness/publish-ready.md` (in the existing
"See also" list). The template presents three executive/sponsor-readable lists --
answerable-today, blocked-pending-decision, out-of-scope -- composed strictly from shipped
F7 domain decision questions and F8 coverage statuses, expressed as status + named blocker
(never a number). No runtime code, no new `retail check` rule, no execution path. This is a
docs/templates-first artifact (hard rule #8) that is a readability layer over the human
publish-approval seam (Principle V) and self-grants nothing.

## Technical Context

**Language/Version**: N/A -- Markdown documentation/template only (no code).

**Primary Dependencies**: Existing committed artifacts only --
`skills/retail-kpi-knowledge/domains/*.md` (F7, 12 files),
`skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md` (F8),
`skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md` (A1-A11),
`templates/handoff/bi-handoff-pack.md` (sibling pack, referenced not restated),
`docs/readiness/publish-ready.md` (edited: one non-gating reference),
`docs/worked-examples/c086-pharmacy.md` (cited by reference for any concrete example).

**Storage**: N/A (tracked Markdown files under version control).

**Testing**: Manual/checklist review of the two authored files against spec Success
Criteria; no automated test harness is introduced (no new `retail check` rule -- count
stays 38). The requirements checklist and plan-review provide the verification pass.

**Target Platform**: Repository documentation (Windows dev host; MAX_PATH-aware short
paths).

**Project Type**: Documentation / template artifact (single-repo, docs-first).

**Performance Goals**: N/A.

**Constraints**: ASCII, UTF-8 without BOM (`--` and `->`, no glyphs; rule IX). Short paths
(Windows MAX_PATH). Generic-only (no C086/pharmacy specifics; rule #7). No numeric
confidence/coverage figure anywhere (rule #9). No stage self-granted to `pass` (Principle
V). Compose-not-invent: every list row resolves to an existing F7/F8 artifact.

**Scale/Scope**: Two files touched -- one new template, one one-line doc edit.

## Constitution Check

*GATE: docs-only artifact; the binding gates are the READ-ONLY / no-self-grant / no-fake-
confidence principles rather than data-migration gates.*

| Gate | Status |
|------|--------|
| Principle I (agent-first, gate-backed) | PASS -- presentation the agent produces; explicitly non-gating, becomes no `retail check` rule. |
| Principle V (Agent Stops at Judgment Calls) | PASS -- readability layer over the human publish seam; grants no approval, moves no stage; PII (FR-014) and rollup/severity ordering (FR-015) are left as open human rulings in `## Clarifications`, never answered. |
| Principle VII (C086 is a worked example, not the schema) | PASS -- template is generic placeholders; any pharmacy instance cited by reference to `docs/worked-examples/c086-pharmacy.md`. |
| Hard rule #6 (no publish/execution before F016) | PASS -- no live publish path assumed; "answerable today" is paper-answerable, not live-validated; F016 treated as absent. |
| Hard rule #8 (docs/templates/checklists first) | PASS -- a template + a doc edit; no runtime code. |
| Hard rule #9 (no fabricated confidence) | PASS -- status + named blocker only; a percentage/score is forbidden and the template states so, inheriting the F8 no-score discipline. |
| Rule IX (ASCII, UTF-8 no BOM) | PASS -- enforced in both authored files. |

No violations -> Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/053-stage-7-answerability-summary-executive/
├── spec.md              # Stage 2 output
├── plan.md              # This file (Stage 4)
├── tasks.md             # Stage 4 output (/speckit-tasks)
├── analysis.md          # Stage 5 output (/speckit-analyze report, repo convention)
├── plan-review.md       # Stage 6 output (adversarial review)
└── checklists/
    └── requirements.md  # Stage 2 quality checklist
```

### Source (repository root) -- files this feature touches

```text
templates/handoff/
├── answerability-summary.md      # NEW -- the deliverable (generic template)
├── bi-handoff-pack.md            # READ -- sibling engineer pack (referenced, not restated)
└── handoff-review-checklist.md   # READ -- existing sibling

docs/readiness/
└── publish-ready.md              # EDIT -- one non-gating reference in "See also"

skills/retail-kpi-knowledge/      # READ ONLY -- the composed sources
├── domains/*.md                  # F7 decision questions (12 files)
├── references/kpi-coverage-scorecard-template.md   # F8 coverage statuses
└── knowledge/kpi-ambiguities.md  # A1-A11 named blockers

docs/worked-examples/
└── c086-pharmacy.md              # READ -- cited by reference for any concrete example
```

**Structure Decision**: No `src/` or `tests/` tree -- this is a documentation/template
artifact. The only writes are the new `templates/handoff/answerability-summary.md` and a
one-line non-gating edit to `docs/readiness/publish-ready.md`. All other listed paths are
read-only sources the template composes from.

## Design notes (what the template contains)

The template ships as a copy-per-table generic file structured as:

1. **Header block** -- `<schema>.<table>`, source family, assembled-on/by, and an explicit
   audience line ("sponsor / finance companion to the engineer handoff pack; not a Stage 7
   required artifact").
2. **What this is / is not** -- states: presentation over the human publish seam; grants no
   approval; moves no stage; status + named blocker only, never a percentage (rule #9);
   generic, C086 by reference only.
3. **Answerable today** list -- decision questions whose F8 coverage status is "Covered".
4. **Blocked -- pending decision** list -- each row names its missing field or its A1-A11
   undecided policy (the named blocker), never softened.
5. **Out of scope** list -- decision questions whose KPI domain this table cannot serve.
6. **Planned / not yet contracted** note -- Planned KPIs parked here (FR-013), outside the
   three headline lists.
7. **Principle-V open items** -- the PII posture (FR-014) and any severity/priority ordering
   (FR-015) marked as human rulings, not resolved in the template.
8. **See also** -- points back at `publish-ready.md`, the F7 domains, the F8 scorecard, the
   sibling `bi-handoff-pack.md`, and the worked example.

The `publish-ready.md` edit adds ONE bullet under "See also" only.

## Deferred / not-in-scope (do NOT assume these exist)

- **F016 Power BI execution adapter** -- verified absent; no live publish path.
- **F031-F033 spec-only runtimes** -- not consumed here.
- Any validator, linter, or `retail check` rule over filled instances -- explicitly NOT this
  feature (that is a separate idea; this feature stays presentation-only, YAGNI).

## Complexity Tracking

No constitution violations; section intentionally empty.
