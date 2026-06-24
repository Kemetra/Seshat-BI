# Implementation Plan: grain confidence + mapping diff reviewer

**Branch**: `009-grain-confidence-reviewer` | **Date**: 2026-06-24 | **Spec**:
`specs/009-grain-confidence-reviewer/spec.md`

**Input**: Feature specification from `specs/009-grain-confidence-reviewer/spec.md`

## Summary

Add one pure agent-procedure skill, `grain-confidence-reviewer`, that DEEPENS the
already-shipped Mapping Ready gate by (1) surfacing grain-uniqueness CONFIDENCE as
evidence -- the measured `PkProof` (`total` / `distinct_pk` / `null_pk` /
`is_unique` from `src/retail/profile.py`) mapped to one of the four readiness
statuses with `evidence[]` + `blocking_reasons[]`, never a fabricated number -- and
(2) rendering a semantic DIFF between two `source-map.yaml` versions that foregrounds
the load-bearing fields (grain, PK, `pii:` flags, `gold_placement`) and flags
re-approval. The skill reuses existing measurement code, reads two committed files,
renders for a human, and STOPS at the Principle-V human seam. No new Python, no new
CLI subcommand, no new gate.

## Technical Context

**Language/Version**: Markdown skill text (agent is the runtime). The only code it
TOUCHES is the existing `src/retail/profile.py` (Python 3.11+, stdlib-only core),
which it CALLS at the deferred live boundary but does not modify.

**Primary Dependencies**: none new. Static core stays `dependencies = []`; the live
profile path reuses the OPTIONAL `db` extra (psycopg2), imported lazily, exactly as
`source-mapping` / `retail-validate` already do.

**Storage**: N/A. Inputs are committed text (`mappings/<table>/source-profile.md`,
two `source-map.yaml` versions via git) and, at the live boundary, a read-only
Postgres connection. The skill writes nothing except the rendered review output it
hands back; it does not persist new artifacts in this slice.

**Testing**: the existing pytest suite must stay green; `retail check` must stay
exit 0 (27 rules). The acceptance evidence is the rendered card/diff inspected
against the spec's FRs (SC-003/SC-004/SC-005) on generic fixtures -- no new code to
unit-test in this slice.

**Target Platform**: the Claude Code agent harness on Windows (repo convention);
ASCII + UTF-8 no BOM, short paths (Windows 260-char limit, repo CLAUDE.md).

**Project Type**: single repo; an agent-skill addition under `.claude/skills/`.

**Performance Goals**: N/A (a one-table-at-a-time human-review aid; no throughput
target).

**Constraints**: no fabricated confidence number (hard rule #9); no auto-resolution
of grain/PII/rollups (Principle V); generic only (Principle VII); live DB read is
deferred and user-supplied (Principle VIII); reuse `PkProof`, do not re-implement
the uniqueness query.

**Scale/Scope**: one new skill file (~one focused SKILL.md), one `## Orchestration`
pointer, and a one-line seam reference from `retail-orchestrate`. No schema, no code,
no migration.

## Constitution Check

*GATE: must pass before and after design. This feature is docs/skill-only and adds
no gate, so the check is about what it MUST NOT do.*

| Principle | How this plan complies |
|-----------|------------------------|
| I. Agent-First, Gate-Enforced | The skill is an agent verb; it does not become a rule authority. The gate exit code (`retail check`) and the human `approvals[]` action remain the authorities -- the skill proposes/surfaces, it never disposes. |
| II. Depend, Never Fork | No pbi-cli, no engine fork; reuses the existing `profile.py`. |
| III. Medallion, Postgres-First, Gold-Only | The live profile reads bronze/landed data read-only via the existing host-agnostic DSN path; no new read surface, no Parquet copy. |
| IV. Source Mapping Before Silver | Reinforced: the reviewer is a Mapping Ready aid; it adds NO new gate and writes NO silver. It helps the existing gate be reviewed, never bypasses it. |
| V. Agent Stops at Judgment Calls | Central design constraint: grain ambiguity, PII publish-safety, and business rollups HARD-STOP and route to `unresolved-questions.md` with a named owner. The skill never auto-resolves grain or self-grants approval (FR-007/FR-008). |
| VI. Defaults Then Deviations | A data-justified, human-recorded deviation maps to `warning`, never auto-`pass` (FR-004); the skill records, it does not invent deviations. |
| VII. C086 Is An Example | All skill text is generic placeholders; C086 cited as the filled instance only (FR-010). |
| VIII. Static-First, Live Deferred | The live profile re-run is the deferred DB-read boundary; without DSN/`db` extra the skill reads committed numbers or reports `[PENDING LIVE PROFILE]` and never fabricates (FR-002/FR-004 scenario 4). The static core's import path stays driver-free. |
| IX. Secrets and Reproducibility | No DSN written to any tracked file; ASCII/UTF-8-no-BOM; short paths. |
| Readiness spine | Reinforced, not extended: the card maps to the four existing statuses + `evidence[]` + `blocking_reasons[]`; "No fake confidence" is honored (FR-003/FR-009). No new state field; any numeric `score` stays OPTIONAL + evidence-citing (default omitted). |

**Result**: PASS. No violation; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/009-grain-confidence-reviewer/
|-- spec.md        # the feature spec (done)
|-- plan.md        # this file
|-- tasks.md       # the task list (/speckit-tasks output)
`-- analysis.md    # the cross-artifact analyze findings
```

No `research.md` / `data-model.md` / `contracts/` are produced: there is no new code
surface, data model, or API to research or contract. (The kit's prior skill-only
slices -- 005, 006 -- likewise carried spec-only design; this one adds plan/tasks/
analyze per the chain but keeps the same lean, no-new-code posture.)

### Source Code (repository root)

```text
.claude/skills/
|-- grain-confidence-reviewer/
|   `-- SKILL.md                 # NEW: the pure reviewer verb (this feature)
|-- source-mapping/SKILL.md      # sibling verb (reads the same profile/map)
|-- retail-orchestrate/SKILL.md  # EDIT: one seam pointer at the Mapping Ready review
|-- retail-validate/SKILL.md     # live sibling (cited)
`-- retail-build-warehouse/SKILL.md

src/retail/profile.py            # REUSED unchanged (PkProof is the measured signal)
templates/source-map.yaml        # the diff input shape (unchanged)
templates/source-profile.md      # the grain/PK evidence source (unchanged)
templates/readiness-status.yaml  # where the card's evidence/blockers are recorded (unchanged)
docs/readiness/mapping-ready.md  # the stage this advances (unchanged; cited)
```

**Structure Decision**: a single new skill file plus a one-line orchestration seam
edit. The agent is the runtime (the kit's all-skills verb architecture); no new
module, package, or CLI is introduced. This mirrors features 005/006, which added
verbs as skills, not code.

## Phases

### Phase 0 - Confirm the reused signal and inputs (no code)

Confirm (already verified in research): `PkProof(total, distinct_pk, null_pk,
is_unique)` is the measured grain signal; `source-profile.md` carries the committed
numbers; `source-map.yaml` carries `meta.grain`, `meta.primary_key`, per-column
`pii:`, and `gold_placement` -- the load-bearing diff fields. No open unknowns; the
live boundary (DSN/`db` extra) is the only deferred dependency and is already a
documented, user-supplied seam.

### Phase 1 - Author the reviewer skill

Write `.claude/skills/grain-confidence-reviewer/SKILL.md` with: a scope-boundary
header (surface + stop; never approve, never edit the map, never fabricate a score);
a grain-confidence procedure (read the measured signal -> map to one of four
statuses with cited evidence + blockers -> STOP); a mapping-diff procedure (read two
`source-map.yaml` versions -> group changes by grain/PK/pii/gold_placement -> flag
re-approval); a fail-loud judgment-stop table (Principle V); a deferred/live-boundary
mode (Principle VIII); a generic-only rule (Principle VII); and the `## Orchestration`
pointer. Add the one seam reference in `retail-orchestrate`.

### Phase 1 re-check (Constitution)

Re-run the table above against the authored text: confirm no number is emitted, no
approval is written, all judgment calls hard-stop, all examples are generic, and the
live boundary degrades safely. PASS expected; record any deviation as Complexity
Tracking (none anticipated).

## Complexity Tracking

> No Constitution Check violations. No entries.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | -- | -- |
