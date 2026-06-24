# Implementation Plan: table onboarding wizard -- the Source -> Mapping readiness workflow

**Branch**: `007-table-onboarding-wizard` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/007-table-onboarding-wizard/spec.md`

## Summary

Ship the **table onboarding wizard** (roadmap F006, Layers 1-2): an agent-first
workflow that walks a NEW raw table across the first readiness transition,
**Source Ready -> Mapping Ready**, and STOPS at Mapping Ready. It is a thin
COMPOSITION layer -- a pure SKILL plus a committed CHECKLIST plus a readiness-status
seed -- over pieces that already exist: the `source-mapping` skill (which authors
the five mapping artifacts) and `templates/readiness-status.yaml` (the state model).
The wizard's own surface is the stage-transition walk, the readiness-status
bookkeeping, the four Principle-V human-seam hard-stops (grain, PII, business
rollup, product identity), and the hard boundary that it never writes silver. No
new Python, no CLI, no codegen (hard rule #8; constitution Principle I).

## Technical Context

**Language/Version**: None added. Markdown + YAML artifacts only (skill text,
checklist, readiness-status seed). The existing static core stays Python 3 stdlib.

**Primary Dependencies**: None added. `dependencies = []` unchanged. The wizard
reuses the existing `source-mapping` skill and (in live mode) the existing
read-only profile path (`retail.profile` + the optional `db` extra), neither of
which this feature modifies.

**Storage**: Committed text only -- `mappings/<table>/` artifacts (produced by the
delegated mapping leg) and the per-table readiness-status YAML. No database writes;
the profile connection is READ-ONLY and is the deferred live boundary.

**Testing**: The existing `retail check` gate (must stay exit 0) + the existing unit
suite (must stay green). The feature adds NO new Python and therefore no new Python
tests; its acceptance is the generic onboarding dry-run + the four human-seam
hard-stop checks described in the spec (SC-003, SC-004), verified as text review.

**Target Platform**: The Claude Code agent harness on Windows (the repo's primary
platform); ASCII + UTF-8 no BOM; short repo-relative paths (Windows MAX_PATH,
Principle IX).

**Project Type**: Agent-skill + docs feature (no application code) -- same posture
as features 004/005/006's skill surfaces.

**Performance Goals**: N/A (a human/agent-paced onboarding walk; no throughput target).

**Constraints**: Agent-first, not CLI-first (hard rule #1). Ends at Mapping Ready;
never silver (hard rule #2). Generic, no C086 specifics (hard rule #7). Docs/
templates/checklist first (hard rule #8). No fake confidence (Principle VIII spine).

**Scale/Scope**: One table per wizard run; the first two readiness stages only.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | This plan |
|-----------|------|-----------|
| I. Agent-First, Gate-Enforced | the agent is the interface; the gate is the contract | PASS -- the wizard is a SKILL the agent performs; `retail check` / the read-only profile are gates it CALLS; no CLI verb added. |
| II. Depend, Never Fork | no vendoring/forking pbi-cli | PASS -- not touched; pbi-cli remains the later adapter. |
| III. Medallion, Postgres-First, Gold-Only | bronze->silver->gold; PBI reads gold only | PASS -- wizard operates at bronze->source-mapping only; writes nothing downstream. |
| IV. Source Mapping Before Silver | map reviewed/approved before any silver | PASS (load-bearing) -- the wizard's terminal state IS Mapping Ready; it hard-stops before silver and never self-grants `Gate status: CLEARED`. |
| V. Agent Stops at Judgment Calls | grain/PII/rollup/identity reserved for a human | PASS (load-bearing) -- the four seams are HARD-STOPS raised as `unresolved-questions.md` rows; the wizard proposes, a human decides (open_for_human). |
| VI. Defaults Then Deviations | start from RC1-RC16; record deviations w/ data fact | PASS -- the delegated `source-mapping` leg authors `assumptions.md` from the RC defaults; the wizard does not bypass it. |
| VII. C086 Is An Example, Not The Schema | templates stay generic | PASS -- skill/checklist/status seed carry placeholders only; C086 cited as the filled instance, never copied. |
| VIII. Static-First, Live Deferred / no fake confidence | static gate ships; live deferred; no confidence number | PASS -- no live run required to ship; readiness is the four explicit statuses + evidence + blockers; deferred-boundary mode marks `[PENDING LIVE PROFILE]` and records `warning`. |
| IX. Secrets and Reproducibility | secrets in `.env`; ASCII/UTF-8 no BOM; short paths | PASS -- prints enable steps, never commits a DSN; artifacts ASCII + UTF-8 no BOM; short paths. |

**Result**: No violations. No entries in Complexity Tracking. The feature adds a
composition skill over existing gates; it weakens none and adds no new gate.

## Project Structure

### Documentation (this feature)

```text
specs/007-table-onboarding-wizard/
|-- spec.md        # the feature specification (done)
|-- plan.md        # this file
|-- tasks.md       # the task breakdown (/speckit-tasks output)
`-- analysis.md    # the cross-artifact analyze findings (/speckit-analyze output)
```

This feature follows the 004/005/006 precedent of a lean spec set (spec + plan +
tasks + analyze); no `research.md` / `data-model.md` / `contracts/` are needed --
there is no new data model or API, only an agent procedure and committed text.

### Source / artifacts touched (repository root)

```text
.claude/skills/<wizard-skill-name>/
`-- SKILL.md                      # NEW: the agent-first onboarding workflow
                                  #   (frontmatter + the Source->Mapping walk +
                                  #   the human-seam stop table + Orchestration
                                  #   pointer). ASCII, UTF-8 no BOM.

docs/readiness/
`-- onboarding-checklist.md       # NEW: the text-first, reviewable definition-of-done
                                  #   for each Source->Mapping step (home settled below).

.claude/skills/retail-orchestrate/SKILL.md   # EDIT (small): reciprocal pointer so the
                                  #   conductor invokes the wizard as its Source->Mapping leg.

# REUSED, NOT MODIFIED:
.claude/skills/source-mapping/SKILL.md        # delegated mapping-artifact authoring
templates/readiness-status.yaml               # the readiness-status seed source
docs/readiness/source-ready.md, mapping-ready.md   # the stage definitions-of-done
```

**Structure Decision**: An agent-skill + docs feature. The wizard's normative
surface is `.claude/skills/<wizard-skill-name>/SKILL.md`; the reviewable
definition-of-done is `docs/readiness/onboarding-checklist.md` (kept beside the two
stage docs it spans). One small reciprocal edit to `retail-orchestrate`. No
`src/` change, no migration, no template engine. This matches the all-skills verb
architecture (features 004-006) and the hard-rule-#8 "docs/checklist first" posture.

### Phase 0 -- research (decisions, no code)

The few open choices are NOT NEEDS-CLARIFICATION blockers; they are auto-defaulted
here (reversible) and recorded in the decision record:

- **Skill name**: default `retail-onboard-table` (verb-noun, parallels
  `retail-build-warehouse` / `retail-validate`). Reversible: a rename touches only
  the skill dir + two pointers.
- **Checklist home**: default `docs/readiness/onboarding-checklist.md` (beside
  `source-ready.md` / `mapping-ready.md`, the two stages it spans), not `templates/`
  (which holds copy-me blanks, not process docs). Reversible: a `git mv` + one link.
- **Readiness-status file home / naming**: the wizard WRITES a per-table status from
  `templates/readiness-status.yaml`; its committed location (e.g.
  `mappings/<table>/readiness-status.yaml` vs a central `readiness/` index) is a
  spine-level convention -- default to `mappings/<table>/readiness-status.yaml` so a
  table's full working set is co-located (parallels ADR 0003). Reversible.

### Phase 1 -- design (the skill + checklist shape)

- **SKILL.md** frontmatter (name + a precise `description` that triggers on
  "onboard a new table" / "walk a table from source to map"), then: scope boundary
  (read first) -> run-state-from-disk rule -> Stage 1 (profile, PROPOSE semantics)
  -> Stage 2 (delegate to `source-mapping`) -> readiness-status bookkeeping -> the
  four human-seam HARD-STOP table -> the Mapping-Ready terminal + next-action ->
  deferred-boundary mode -> See also -> Orchestration pointer.
- **onboarding-checklist.md**: a numbered, reviewable checklist mapping each step to
  its definition-of-done in `source-ready.md` / `mapping-ready.md`, with the four
  human seams called out as explicit STOP rows.
- **Re-check Constitution**: after drafting, confirm no C086 leakage, no silver
  authoring, no self-granted approval, no numeric confidence -- all PASS by design.

## Complexity Tracking

> No Constitution Check violations -- this section is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| (none) | -- | -- |
