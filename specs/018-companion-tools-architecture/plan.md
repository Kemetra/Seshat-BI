# Implementation Plan: Companion Tools Architecture

**Branch**: `018-companion-tools-architecture` | **Roadmap feature**: F024 | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

> Numbering note: roadmap F-number is authoritative; spec-dir number is the next free
> on-disk slot. This feature is roadmap F024, on-disk 018. When they disagree, F024 wins.

**Input**: Feature specification from `specs/018-companion-tools-architecture/spec.md`

## Summary

Define the OFFICIAL authority taxonomy for every tool/module/adapter around the core:
five categories (Core Authority, Official Workflow Skill, Product Module, Execution
Adapter, Maintenance Automation), an authority MATRIX (only Core Authority creates truth
or grants approval), and two closed sub-vocabularies (Module = read-only | artifact-writing
| execution-capable; Adapter = local-only | DB-connected | external-service-connected |
publish-capable). The taxonomy is ORTHOGONAL to the roadmap's Six product layers -- every
tool carries two coordinates (layer AND category). This slice is PLANNING ONLY: it writes
the five spec-kit files and ENUMERATES five future documentation/template deliverables; it
adds no runtime code, no gate, no readiness stage, and no `retail check` rule. It is the
FOUNDATION contract that F025-F033 each declare themselves against.

## Technical Context

**Language/Version**: None -- docs/planning this slice (Markdown text artifacts only).

**Primary Dependencies**: None at runtime. Authoring style borrows from the existing spec
house style (`specs/010`, `specs/013`) and reads the roadmap's Six product layers + the
constitution's Principles I/V/VII/VIII/IX as the inputs being formalized.

**Storage**: The five committed spec-kit text files under
`specs/018-companion-tools-architecture/`. The five FUTURE deliverables (docs/architecture,
docs/decisions, templates) are enumerated, NOT created this slice.

**Testing**: No code, so no unit tests. Verification is: (1) `retail check` exit 0 with
no new rule added, (2) every file ASCII + UTF-8 no BOM, (3) the authority matrix shows
only Core Authority with create-truth / grant-approval, (4) the five categories form a
closed set and classify the shipped surfaces with no overlap, (5) zero C086 /
retail_store_sales specifics leak.

**Target Platform**: Repo text artifacts consumed by an agent + reviewed by a named human
(the architecture owner); F025-F033 read the contract to declare their category.

**Project Type**: Documentation/architecture-definition feature (no source tree change).

**Performance Goals**: N/A (static text).

**Constraints**: ASCII + UTF-8 no BOM; generic (no C086 / retail_store_sales values);
Windows path budget (keep names short); no numeric/maturity score anywhere; no runtime
code; no gate/rule/stage; the Six product layers are cited, not replaced.

**Scale/Scope**: 5 spec-kit files now; 5 future deliverables enumerated. One authority
matrix; two closed sub-vocabularies; one shipped-feature classification table.

## Constitution Check

*GATE: must pass before and after design. Constitution at `.specify/memory/constitution.md`.*

| Principle | How this feature complies |
|-----------|---------------------------|
| I. Agent-First, Gate-Enforced | Adds no gate and no agent authority over truth. It makes the existing "Core Authority owns truth" rule concrete via the matrix; the agent CLASSIFIES tools, it does not approve. `retail check` stays the gate, untouched. |
| II. Depend, Never Fork | No engine, no fork, no pbi-cli. Pure local opinion in planning docs that enumerate future docs/templates. |
| III. Medallion, Gold-Only | Not triggered (no SQL, no schema). The taxonomy records that adapters connecting to a DB must declare connectivity; Power BI still reads gold only -- a fact cited, not changed. |
| IV. Source Mapping Before Silver | Not triggered (no silver/gold build). The contract preserves the spine ordering; it adds no stage. |
| V. Agent Stops at Judgment Calls | The matrix forbids every non-Core-Authority category from creating truth or granting approval; a proposed truth-creating tool is a stop-and-ask, never auto-classified into Core Authority. Reaffirms Principle V, does not relax it. |
| VI. Defaults Then Deviations | The five categories are a closed-set default; a sixth is a future deviation requiring its own spec, never a silent addition. |
| VII. C086 Is An Example | FR-013/SC-004: all artifacts generic; C086 / retail_store_sales cited as a filled reference, never inlined. |
| VIII. Static-First, Live Deferred | FR-010/FR-012/SC-005: NO code, NO rule, NO checker, NO stage; `retail check` exit 0 + no new rule added. Enforcement of "declare your category" is enumerated and deferred (rule #8). |
| IX. Secrets & Reproducibility | No secrets, no DSNs, no paths. ASCII + UTF-8 no BOM; short paths; no numeric/maturity score (rule #9). |

**Result**: PASS. No violations; Complexity Tracking left empty.

### Boundary gate (feature-specific, load-bearing)

The biggest design risks are (a) re-spec'ing the Six layers as a renumbering, (b) shipping a
checker, and (c) collapsing the module/adapter seam. The plan holds all three:

- The five categories are an ORTHOGONAL authority axis; the layers stay authoritative for
  the functional axis. The spec states a tool has TWO coordinates. No renumbering.
- No artifact this slice adds is executable: no `retail check` rule, no CLI verb, no
  conformance check. The conformance check is enumerated as a future deliverable's job.
- The module-vs-adapter discriminator (external trust/connectivity boundary) is stated
  explicitly so an `execution-capable` Module and an Execution Adapter are disjoint.

## Project Structure

### Documentation (this feature)

```text
specs/018-companion-tools-architecture/
|-- spec.md                  # /speckit-specify output (done)
|-- plan.md                  # This file (/speckit-plan output)
|-- tasks.md                 # /speckit-tasks output
`-- checklists/
    |-- acceptance.md        # spec quality checklist (done)
    `-- governance.md        # core-authority governance checklist (done)
```

No `research.md` / `data-model.md` / `contracts/` directory is generated: there is no code
to research and no DB model to design. The "contracts" this feature is ABOUT are the future
`module-contract.md` / `adapter-contract.md` templates, enumerated below, not a speckit
`contracts/` dir.

### Repository artifacts this feature PLANS (not created)

```text
docs/architecture/
|-- product-modules.md                     # FUTURE -- the five categories + authority matrix + two sub-axes (normative reference)
`-- core-vs-modules-and-adapters.md        # FUTURE -- prose narrative of the authority boundary + module-vs-adapter seam + shipped classification

docs/decisions/
`-- 0006-core-authority-vs-product-modules.md  # FUTURE -- ADR: why the authority cut is orthogonal to the six layers; why only Core Authority owns truth

templates/
|-- module-contract.md                     # FUTURE -- copy-me declaration every Module fills (category + capability level + reads + derived evidence + forbidden ops)
`-- adapter-contract.md                    # FUTURE -- copy-me declaration every Adapter fills (category + connectivity level + gate it is downstream of + forbidden ops)
```

**Structure Decision**: architecture-definition feature -- no `src/` or `tests/` change.
The normative reference + narrative live under a new/extended `docs/architecture/` (parallel
to `docs/readiness/`); the ADR under `docs/decisions/` (the existing ADR home); the two
copy-me contracts under `templates/` (alongside the existing mapping-gate templates). All
FUTURE; this slice writes only the five spec-kit files.

## Phase 0 -- Research (no external research needed)

No unknowns requiring external research. The inputs being formalized are all in-repo: the
roadmap's Six product layers (`docs/roadmap/roadmap.md`), the constitution's authority rules
(Principles I, V), and the shipped F005-F016 specs (the surfaces to classify). The one
non-obvious modelling decision -- that the five categories are an ORTHOGONAL authority axis,
not a 6->5 renumbering -- is resolved in the spec (Relationship to shipped features), not
deferred to research.

## Phase 1 -- Design (the contract shapes)

**The five categories**: a closed set with a one-paragraph definition each (Core Authority,
Official Workflow Skill, Product Module, Execution Adapter, Maintenance Automation). Core
Authority is the only truth-holder; the other four are downstream.

**The authority matrix**: rows = the five categories; columns = {reads evidence, summarizes/
visualizes, writes derived evidence, executes approved step, connects DB/external, publishes,
CREATES truth, GRANTS approval}. Only Core Authority is `yes` on the last two. Each row is a
governance CHK item.

**The two sub-vocabularies**: Module capability = `{ read-only, artifact-writing,
execution-capable }`; Adapter connectivity = `{ local-only, DB-connected,
external-service-connected, publish-capable }`. Both closed sets; no invented parallel axes
for the other three categories (their boundary is prose).

**The module-vs-adapter seam**: the discriminator is the external trust/connectivity
boundary. Local-only execution -> `execution-capable` Module; DB/external/publish -> Adapter.
Disjoint by construction.

**Maintenance Automation**: pinned by "no per-invocation human trigger" + "derived evidence
only" + "never creates truth / self-approves" -- the distinguisher from a human-invoked
Module.

**The shipped-feature classification table**: Core Authority = the truth artifacts;
Workflow Skills = conductor + gate verbs; read-only Modules = control room + grain reviewer;
artifact-writing Modules = handoff pack + dashboard design; publish-capable Adapter = F016.
Proof the taxonomy is real.

**The five enumerated future deliverables**: listed as planned outputs (FR-009), with one
line each on what they will contain. NOT authored this slice.

## Phase 1 -- Constitution re-check

Re-checked after design: still PASS. The design adds only generic planning text, defines the
authority matrix + closed sub-vocabularies, reaffirms that only Core Authority owns truth,
adds no rule/checker/stage, and emits no score. The boundary gate holds (layers cited not
replaced; no executable artifact; module/adapter seam disjoint).

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.
