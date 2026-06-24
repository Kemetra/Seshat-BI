# Implementation Plan: Semantic Model Readiness -- the model-checking layer

**Branch**: `011-semantic-model-readiness` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/011-semantic-model-readiness/spec.md`

## Summary

Add one read-only agent skill, `retail-semantic-check`, that computes the Stage-5
(**Semantic Model Ready**) readiness verdict for a committed PBIP semantic model. It
runs the existing `retail check` gate (D1-D8 / C1 / R1 / G6) for the MECHANICAL half,
evaluates the CONTRACT-BINDING half against the F009 metric-contract store (every
measure binds to an approved contract, owner approval recorded), and emits exactly one
status (`not_started` | `blocked` | `warning` | `pass`) with `evidence[]` +
`blocking_reasons[]` -- then STOPS. No new Python, no new checker rule, no CLI
subcommand, no model authoring (pbi-cli / PBIP automation stays deferred to F016).

Technical approach: a pure SKILL.md procedure (the agent is the runtime), the same
posture as `retail-govern` / `retail-validate` / `retail-build-warehouse`. The skill
ORCHESTRATES the existing gate and PERFORMS the cross-artifact binding read; it
implements the procedure the stage doc (`docs/readiness/semantic-model-ready.md`)
already specifies, without redefining the stage or the contracts.

## Technical Context

**Language/Version**: None added. Skill is Markdown agent-procedure text. The gate it
calls is the existing Python `retail` package (Python 3.11+, stdlib-only core).

**Primary Dependencies**: None added. Reuses `retail check` (D1-D8 `dax.py`, C1/R1
`pbir.py`, C2 `git_meta.py`, G6 `g6.py`). `dependencies = []` stays unchanged.

**Storage**: Reads committed text only -- `powerbi/<Model>.SemanticModel/definition/`
(TMDL), the F009 metric-contract store (when it exists), and a
`templates/readiness-status.yaml` instance. Writes nothing under `powerbi/`.

**Testing**: Existing pytest unit suite must stay green; `retail check` must stay
exit 0 with the new skill present. The skill's own behavior is verified by the
documented acceptance scenarios (the RetailGold-model read-only check, F009-absent).

**Target Platform**: Windows-first dev (the repo's Power BI Desktop host); the static
gate is CI-able and OS-agnostic. The skill runs wherever the agent + `retail check` run.

**Project Type**: Agent skill (docs/agent-procedure), not an application. Single repo.

**Performance Goals**: N/A -- a single read-only pass over committed text per invocation.

**Constraints**: ASCII + UTF-8 no BOM; generic (no C086 / pharmacy specifics in the
skill); short repo-relative paths (Windows `MAX_PATH`, Principle IX); read-only.

**Scale/Scope**: One skill file + one `## Orchestration` pointer wired into
`retail-orchestrate`; one fixture story (RetailGold model, F009 absent). One table /
one model at this volume.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Agent-First, Gate-Enforced)**: PASS. The skill is an agent procedure
  that CALLS the enforced gate (`retail check`); the checker exit code remains the
  authority, the skill interprets. It proposes a verdict; the gate disposes the
  mechanical half.
- **Principle II (Depend, Never Fork)**: PASS. No pbi-cli vendoring, no authoring; the
  skill READS an existing PBIP model. pbi-cli / PBIP automation stays the deferred F016
  adapter, gated on this stage being `pass` (hard rule #6).
- **Principle III (Medallion, Postgres-First, Gold-Only)**: PASS. The model under check
  binds to `gold` only; D8 (gold-only partitions) is part of the gate the skill calls.
  No new read surface introduced.
- **Principle IV (Source Mapping Before Silver)**: N/A to this stage (Stage 2 gate);
  not weakened. The skill never touches mapping artifacts.
- **Principle V (Agent Stops at Judgment Calls)**: PASS. Contract approval is a named
  human action the skill cannot self-grant; ambiguous measure<->contract mapping
  HARD-STOPS for a human. Grain, PII, business-rollup, product-identity are explicitly
  NOT decided here (left to the owner / F009).
- **Principle VI (Defaults Then Deviations)**: N/A (cleaning defaults are Stage 1-4);
  not touched.
- **Principle VII (C086 Is An Example, Not The Schema)**: PASS. The skill text is
  generic; the RetailGold model is cited as the available fixture instance, not baked
  into the procedure.
- **Principle VIII (Static-First Governance, Live Deferred)**: PASS. The skill enforces
  the hard gate that Gold Ready (live `retail validate`) is `pass` BEFORE Stage 5; it
  treats a clean static `retail check` as necessary-not-sufficient for `pass`.
- **Principle IX (Secrets and Reproducibility)**: PASS. Read-only; G6 (no real host)
  is part of the gate; the skill never writes a connection string. ASCII / UTF-8 no
  BOM / short paths observed.
- **Readiness System spine**: PASS. The skill computes one Stage-5 verdict with
  explicit status + evidence + blockers; no fabricated confidence number (hard rule
  #9). It implements `docs/readiness/semantic-model-ready.md`, redefining nothing.

**Result**: No violations. No entry in Complexity Tracking required.

## Project Structure

### Documentation (this feature)

```text
specs/011-semantic-model-readiness/
  spec.md         # Feature specification (done)
  plan.md         # This file
  tasks.md        # Task breakdown (/speckit-tasks output)
  analysis.md     # Cross-artifact analysis findings (/speckit-analyze output)
```

No `research.md`, `data-model.md`, `contracts/`, or `quickstart.md` are produced:
there is no new data model (the skill reads existing TMDL + the F009 store) and no
new code interface (no Python, no CLI). The "contract" of this feature is the SKILL.md
procedure + the stage doc it implements.

### Source Code (repository root)

```text
.claude/skills/retail-semantic-check/SKILL.md   # NEW: read-only Stage-5 checking verb

.claude/skills/retail-orchestrate/SKILL.md      # EDIT: reference retail-semantic-check
                                                #       at the Phase-7 model [SEAM] row

docs/readiness/semantic-model-ready.md          # READ-ONLY authority (already exists);
                                                #   skill cross-links it, does not edit it

# Reused unchanged (called, not modified):
src/retail/rules/dax.py                # D1-D8 (measures, relationships, date marker)
src/retail/rules/pbir.py               # C1 (connection params), R1 (relative ref)
src/retail/rules/g6.py                 # G6 (no real host in PBIP parameters)
powerbi/Retailgold.SemanticModel/      # the model under check (read-only fixture)
templates/readiness-status.yaml       # the verdict shape the skill emits
```

**Structure Decision**: Single agent-skill addition plus one orchestration-pointer
edit. No `src/` or `tests/` tree is created -- the feature adds no code, only an
agent procedure that reuses the shipped checker. This matches the repo's all-skills
verb architecture (feature 005/006 precedent) and the constitution's static-first,
depend-never-fork posture.

## Phasing (how the skill executes at runtime)

The skill itself encodes a fixed evaluation order (this is the procedure, not a build
plan):

1. **Ordering gate** -- read the readiness status; if Gold Ready != `pass`, emit
   `not_started` and STOP (Principle VIII hard gate).
2. **Mechanical gate** -- run `retail check`; any D1-D8 / C1 / R1 / G6 finding ->
   collect as `blocking_reasons`. Exit 0 recorded as MECHANICAL-pass-only.
3. **Structural facts** -- confirm relationships present + single-direction (D6), a
   marked date table (D7 marker), measures PascalCase (D1) in display folders (D2),
   all surfaced by step 2; interpret, do not re-implement.
4. **Contract-binding** -- read the F009 store; for each measure, confirm a matching
   APPROVED contract + recorded owner approval. Unmatched / unapproved -> a distinct
   `blocking_reason`. Store absent -> `blocked` ("nothing to bind to"). Ambiguous
   mapping -> HARD-STOP for a human.
5. **Verdict** -- combine into ONE status with `evidence[]` + `blocking_reasons[]`;
   `pass` only if steps 2-4 all clear AND owner approval recorded; never a fabricated
   number; then STOP.

## Complexity Tracking

> No Constitution Check violations. This section intentionally left empty.
