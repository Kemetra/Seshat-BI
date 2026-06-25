# Implementation Plan: Dagster Orchestration Adapter

**Branch**: `024-dagster-orchestration-adapter`  **Roadmap feature**: F030  | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

> Numbering note: roadmap F-number (F030) is the authoritative identity; the spec-directory
> number (024) is the next free on-disk slot. When they disagree, the roadmap F-number wins.

**Input**: Feature specification from `specs/024-dagster-orchestration-adapter/spec.md`

## Summary

Plan the entry of Dagster as an ORCHESTRATION ADAPTER -- the unattended/CI sibling of the
`retail-orchestrate` conductor. Dagster RUNS approved steps (load bronze, profile, build
silver/gold via dbt or SQL, run `retail check` / `retail validate`, run the semantic check,
generate the handoff pack) and WRITES derived run-evidence; it DECIDES no readiness stage and
authors no truth. This slice is **planning artifacts only** (Principle VIII; roadmap rule #8):
it writes the five Spec-Kit files and creates NO Dagster code. The asset graph, the project
layout, the run-evidence template, the adapter doc, the ADR, and the adapter skill are
ENUMERATED below as FUTURE outputs a later slice will author -- the shape this spec commits to,
not code this slice ships. The load-bearing design decision is the derived-evidence vs
authored-truth boundary: Dagster writes evidence ABOUT runs and READS committed approvals; it
never writes a `pass`, a `Gate status: CLEARED`, an approval, or a metric/mapping/grain ruling.

## Technical Context

**Language/Version**: None -- docs/planning this slice (Markdown Spec-Kit artifacts). The
PLANNED future project would be Python (Dagster + dagster-dbt), but no code is written now.

**Primary Dependencies**: None at runtime this slice. The planned future project would depend
on `dagster` and `dagster-dbt` (pinned TOGETHER, FR-009), consumed as external upgradeable
dependencies (Principle II -- depend, never fork). Authoring style borrows from `specs/010`
and `specs/013` (house style) and from `.claude/skills/retail-orchestrate/SKILL.md` (the gate-
read + human-seam posture Dagster reuses).

**Storage**: Committed text -- the five planning files under
`specs/024-dagster-orchestration-adapter/`. The PLANNED future project would live under
`orchestration/dagster/` with run evidence recorded from a `templates/dagster-run-evidence.md`
template; none of that is created this slice.

**Testing**: No code, so no unit tests this slice. Verification is: (1) the five files exist
and only those; (2) ASCII + UTF-8 no-BOM on every file; (3) no Dagster file / pyproject /
module / doc / ADR / template / skill was created; (4) `retail check` stays exit 0 and
no new rule is added (this slice adds no rule). For the PLANNED project, the named minimum CI
gate is a definitions-load smoke test plus (once impl exists) a small orchestration smoke test.

**Target Platform**: Repo text artifacts consumed by an agent + reviewed by a human; the
planned adapter would run unattended/CI against the Postgres medallion.

**Project Type**: Documentation/planning feature (no source tree change this slice).

**Performance Goals**: N/A (static planning text).

**Constraints**: ASCII + UTF-8 no BOM (`->` arrows, `--` dashes, no box-drawing / smart quotes
/ em-dashes); generic (no worked-example specifics baked in); Windows path budget
(`<= 200` chars repo-relative -- keep names short); no numeric confidence score anywhere; no
Dagster file created; Dagster decides no stage.

**Scale/Scope**: 5 planning files. One enumerated asset graph (11 assets), one enumerated
project layout, and one enumerated set of future deliverables.

## Constitution Check

*GATE: must pass before and after design. Constitution at `.specify/memory/constitution.md`.*

| Principle | How this feature complies |
|-----------|---------------------------|
| I. Agent-First, Gate-Enforced | The gate exit code stays the SOLE pass authority. Dagster's asset success means "the command ran and returned this exit," never "the stage passed." The orchestrator proposes and runs; the gate disposes. No new gate is added. |
| II. Depend, Never Fork | The planned Dagster project is a SEPARATE, upgradeable external dependency (`dagster` + `dagster-dbt`, pinned together). The kit depends on Dagster, never forks it; upgrading needs no local-patch reapply. The orchestrator is an adapter at the bottom of the stack, not the product core. |
| III. Medallion, Gold-Only | Dagster orchestrates `bronze -> silver -> gold` one way; Power BI still reads gold only. The publish trigger is gated downstream of gold + validate + semantic + publish-ready. No silver/bronze read by Power BI is introduced. |
| IV. Source Mapping Before Silver | The `silver_tables` asset is a STOP/HUMAN-SEAM edge: it cannot materialize until the mapping is CLEARED in the committed gate artifacts. Dagster READS that approval and never self-grants it (FR-006, US2). |
| V. Agent Stops at Judgment Calls | Every Principle-V judgment call (grain, PII, rollup, segment, sentinel-vs-null) HALTS the affected asset and escalates to the named owner; the orchestrator never resolves one to make a finding go away (FR-004, US4). |
| VI. Defaults Then Deviations | The planned project starts from the conductor's existing gate-read posture and the medallion defaults as defaults; any deviation would be recorded, not silent. This slice introduces no deviation. |
| VII. C086 Is An Example | All five files are generic with placeholders (`<table>`, `<source>`); the C086 / retail_store_sales worked examples are cited as references only, never inlined (FR-010, SC-007). |
| VIII. Static-First, Live Deferred | NO Dagster code, NO new `retail check` rule, NO new validator this slice -- planning only (roadmap rule #8). The live `retail validate` asset stays gated on creds; a failed/unconnectable validate never fabricates a pass. |
| IX. Secrets & Reproducibility | No secrets, no DSNs, no tokens, no machine paths in any file. ASCII + UTF-8 no BOM; short repo-relative paths. Run evidence carries measured numbers + statuses, never a fabricated confidence score (FR-007, FR-011). |

**Result**: PASS. No violations; Complexity Tracking left empty.

### Authority gate (feature-specific, load-bearing)

The single biggest design risk is an orchestrator silently becoming Core Authority. The plan
holds the boundary explicitly:

- Dagster WRITES derived run-evidence (what happened) and READS committed approvals (the GO
  signal). It NEVER writes a readiness `pass`, a `Gate status: CLEARED`, an approval, or a
  metric/mapping/grain/rollup/PII ruling.
- For mechanical stages (Silver/Gold Ready) Dagster writes the CHECK evidence; whether that
  evidence MARKS the stage `pass` is Core Authority's record, not Dagster's write.
- For human-seam stages (Mapping, Semantic publish-safety, Publish) Dagster reads the
  committed approval and HALTS if absent.
- The publish asset only TRIGGERS the parked F016 adapter, and only when `publish_ready` is
  `pass`; Dagster opens no Power BI connection and publishes nothing.

## Project Structure

### Documentation (this feature)

```text
specs/024-dagster-orchestration-adapter/
  spec.md                    # /speckit-specify output (this feature)
  plan.md                    # This file (/speckit-plan output)
  tasks.md                   # /speckit-tasks output
  checklists/
    acceptance.md            # spec quality + acceptance checklist
    governance.md            # Core-Authority / no-self-approval governance gate
```

No `research.md` / `data-model.md` / `contracts/` is generated: there is no code to research
this slice, no DB model to design, and the "contracts" are the gate/authority boundaries stated
in the spec, not API contracts. This slice writes exactly the five files above.

### Repository artifacts this feature PLANS (not created)

These are the FUTURE outputs a later implementation slice will author. This planning slice
ENUMERATES them and creates NONE of them:

```text
orchestration/dagster/
  README.md                                  # PLANNED -- how to run the adapter, the human seams, the gate-read posture
  pyproject.toml                             # PLANNED -- pins dagster + dagster-dbt TOGETHER (FR-009)
  src/tower_bi_orchestration/
    definitions.py                           # PLANNED -- the Definitions object (assets/jobs/sensors/schedules)
    assets/                                   # PLANNED -- the 11 assets (raw_source_file .. publish_execution_evidence)
    jobs/                                     # PLANNED -- the full-sequence + partial jobs
    sensors/                                  # PLANNED -- event triggers (deferred specifics)
    schedules/                                # PLANNED -- cadence (deferred specifics)

docs/integrations/
  dagster-adapter.md                         # PLANNED -- the adapter integration doc (allowed/forbidden, seams, asset graph)

docs/decisions/
  0008-dagster-is-orchestration-adapter.md   # PLANNED -- the ADR: Dagster runs steps, decides no stage

templates/
  dagster-run-evidence.md                    # PLANNED -- the generic derived run-evidence record shape

.claude/skills/dagster-orchestration-adapter/
  SKILL.md                                   # PLANNED -- the agent-side companion skill (when/how to invoke; seams)
```

**Structure Decision**: planning feature -- no `src/` or `tests/` change this slice. The
PLANNED Dagster project is a SEPARATE top-level `orchestration/dagster/` project (keeps the
adapter an upgradeable external dependency, Principle II; keeps `src/retail/` the static gate,
unchanged). The run-evidence template joins the existing `templates/` home; the adapter doc
joins `docs/integrations/`; the ADR joins `docs/decisions/`; the companion skill joins
`.claude/skills/`. None is created now.

## Phase 0 -- Research (no external research needed)

No unknowns requiring external research. The reusable shapes are already in-repo: the gate-read
+ human-seam posture in `.claude/skills/retail-orchestrate/SKILL.md`, the four-status/no-score
vocabulary in `docs/readiness/readiness-model.md` + `templates/readiness-status.yaml`, and the
house style in `specs/010` / `specs/013`. The two adapter dependencies cited (F024 category,
F029 dbt) are referenced by ROLE from the roadmap/brief, not researched -- their specs (018,
023) own their internals. The Dagster + dagster-dbt pin-together posture is a stated policy
need, deferred to F031/F033 for the shared cross-adapter rule.

## Phase 1 -- Design (the artifact shapes this feature commits to)

**The asset graph** (enumerated in the spec; gate semantics fixed here). Eleven assets:
`raw_source_file -> bronze_<table> -> source_profile -> source_map -> silver_tables ->
gold_tables -> metric_contracts -> semantic_model -> dashboard_blueprint -> handoff_pack ->
publish_execution_evidence`. Each dependency edge is classified: STOP edges (a failed gate
halts all downstream assets) at the check/validate/semantic-check nodes; HUMAN-SEAM edges
(read a committed approval, halt if absent) at `source_map` (mapping gate), `semantic_model`
(publish-safety / metric approval), and `publish_execution_evidence` (publish approval). The
terminal asset is gated on `publish_ready = pass` and only TRIGGERS the parked F016 adapter.

**The run-evidence record** (`templates/dagster-run-evidence.md`, planned). Generic shape:
run id, commit sha, timestamp, per-asset {gate command, exit code, measured numbers,
status}, and for each blocked/skipped asset {concrete blocking_reason, named owner}. NO score
field; NO readiness-status write; NO Gate-status write. It is the live-filled DERIVED evidence
of a run -- the same category as `reconciliation-report.md` being filled by a live run.

**The ADR** (`docs/decisions/0008-dagster-is-orchestration-adapter.md`, planned). Records the
decision: Dagster is an orchestration adapter that runs approved steps and decides no stage;
the derived-evidence vs authored-truth boundary; the F005 conductor-sibling relationship; the
pin-together auto-update posture; the F016 publish-trigger-only constraint.

**The adapter doc + skill** (planned). `docs/integrations/dagster-adapter.md` is the human-
facing integration guide (allowed/forbidden ops, the human seams, the asset graph).
`.claude/skills/dagster-orchestration-adapter/SKILL.md` is the agent-side companion (when to
invoke, where the seams are, the gate-read posture mirrored from `retail-orchestrate`).

**Auto-update posture** (stated, shared policy deferred). Pin `dagster` + `dagster-dbt`
together (no independent bumps); updates via PR only; a definitions-load smoke test as the
minimum CI gate; a small orchestration smoke once impl exists; NO automerge for Dagster MAJOR
versions. The SHARED cross-adapter policy lives in F031 (spec 025) / F033 (spec 027); this
spec states only Dagster's adapter-specific needs and defers the rest.

## Phase 1 -- Constitution re-check

Re-checked after design: still PASS. The design adds only generic planning text, creates no
Dagster code, adds no `retail check` rule, keeps the gate exit code + named human as the sole
authorities, holds the source-map gate (Principle IV) and the judgment-call seam (Principle V),
keeps the publish trigger gated on `publish_ready` (Principle II + hard rule #6), and emits no
numeric score (Principle IX). The authority gate holds: Dagster writes evidence, never truth.

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.
