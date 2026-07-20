# Architecture -- the Companion Tools Taxonomy (the normative category contract)

- **Status:** Authored (the F024 enumerated normative reference; docs/templates, no runtime code).
- **Roadmap feature:** F024 (on-disk spec `018-companion-tools-architecture`). When the
  spec-dir number and the F-number disagree, the roadmap F-number wins.
- **Read with:** `core-vs-modules-and-adapters.md` (the prose narrative + the module-vs-adapter
  seam worked through), `docs/decisions/0008-core-authority-vs-product-modules.md` (why the
  authority cut is orthogonal to the six layers), `docs/roadmap/roadmap.md` (the Six product
  layers -- the functional axis this is orthogonal to).
- **Templates it governs:** `templates/module-contract.md`, `templates/adapter-contract.md`.

## One line

> Every tool around the core declares EXACTLY ONE of five authority categories; the
> authority matrix says what each category may do to TRUTH; only **Core Authority**
> creates truth or grants approval.

## What this is, and is not

- It **formalizes**, it does not reinvent. The roadmap's **Six product layers** answer
  "which part of the pipeline does this surface touch?" (a functional axis). This
  document adds an ORTHOGONAL **authority** axis: "what may this surface do to truth?"
  Every tool carries TWO coordinates -- its product LAYER and its authority CATEGORY.
- It **replaces, renumbers, and merges NOTHING.** The six layers stay authoritative for
  the functional axis. Claiming "6 layers became 5 categories" is a misread.
- It **grants no new power.** It DESCRIBES the authority each category already may hold
  and forbids the rest. It cannot upgrade an adapter to define a metric or let a viewer
  approve a stage.
- It **emits no score.** Categories are explicit names, never a maturity number.
  Readiness stays `status` + `evidence[]` + `blocking_reasons[]` (hard rule #9). A
  maturity-level concept is F033's deferred problem, not this contract's.
- It **adds no gate, no `seshat check` rule, no readiness stage.** Enforcement of "every
  tool declares its category" is a DEFERRED, enumerated future conformance check
  (docs-first, hard rule #8); a tool with no declared category is a review finding now,
  not a runtime error.

## The five categories (the closed set)

Every tool/module/adapter declares EXACTLY ONE. The set is closed: a sixth category
would require its own spec, never a silent addition (Principle VI).

1. **Core Authority** -- the committed (or named-human-approved) artifacts that ARE the
   truth: readiness status, source maps, metric contracts, approvals, assumptions, and
   unresolved questions. Only Core Authority creates business meaning, approves a metric
   or mapping, or moves a readiness stage to `pass`. Everything else is downstream of it.
2. **Official Workflow Skill** -- an agent procedure that drives a step of the readiness
   spine (profile -> map -> validate -> check), READING Core Authority and WRITING into
   it only through the named-human approval boundary. The conductor and the gate verbs
   are here. A workflow skill orchestrates; it never self-grants the approval it routes
   to a human.
3. **Product Module** -- a focused tool that consumes Core Authority and presents,
   summarizes, or derives from it. A module MUST declare exactly one capability level:
   `read-only` | `artifact-writing` | `execution-capable`. It never creates truth.
4. **Execution Adapter** -- a tool that crosses an external trust/connectivity boundary
   to MATERIALIZE or PUBLISH an already-approved artifact. An adapter MUST declare
   exactly one connectivity level: `local-only` | `DB-connected` |
   `external-service-connected` | `publish-capable`. It is execution-only and gated; it
   never defines metrics, mappings, semantic logic, or dashboard design.
5. **Maintenance Automation** -- a tool that runs WITHOUT a per-invocation human trigger
   (scheduled / CI), emits ONLY derived evidence (a report, a drift signal, a recomputed
   index), never creates truth, and never self-approves. This is the novel category: it
   is distinguished from a human-invoked Module by the absence of a per-run human
   trigger. The schedule itself -- and the evidence it runs on -- is a prior named-human
   action, so this does NOT relax Principle V.

## The authority matrix (the checkable spine)

Each row is a checkable statement. Only Core Authority gets `yes` on the last two rows.

| Capability | Core Authority | Official Workflow Skill | Product Module | Execution Adapter | Maintenance Automation |
|------------|:--:|:--:|:--:|:--:|:--:|
| Reads committed evidence | yes | yes | yes | yes | yes |
| Summarizes / visualizes evidence | yes | yes | yes | yes | yes |
| Writes DERIVED evidence (report, signal) | n/a | yes | only if `artifact-writing` | yes (the run record) | yes |
| Executes an APPROVED step | n/a | yes | only if `execution-capable` | yes (its sole purpose) | yes (scheduled) |
| Connects to a DB / external service | no | no | no | only if its connectivity level allows | no (if it must connect out, the seam makes it an Adapter) |
| Publishes a Power BI artifact | no | no | no | only if `publish-capable` | no |
| **CREATES truth** (business meaning, metric, mapping) | **yes** | no | no | no | no |
| **GRANTS approval** / moves a stage to `pass` | **yes (named human)** | no | no | no | no |

Every non-Core category reads, summarizes, visualizes, may write derived evidence, and
may execute an approved step -- but MUST NOT create truth or grant approval. This is the
architectural rule binding all the companion features, made concrete.

## The two closed sub-vocabularies

A Module pins a capability level; an Adapter pins a connectivity level. Both are closed
sets. The other three categories carry no parallel sub-axis (their boundary is prose).

**Module capability level** (a Product Module declares exactly one):

| Level | Means | May write derived evidence? | May execute? |
|-------|-------|:--:|:--:|
| `read-only` | reads + presents/summarizes Core Authority; writes no artifact | no | no |
| `artifact-writing` | derives a committed artifact from committed evidence | yes | no |
| `execution-capable` | runs an approved step against the LOCAL committed working set | yes | yes (local-only) |

**Adapter connectivity level** (an Execution Adapter declares exactly one):

| Level | Crosses which boundary | Example shape |
|-------|------------------------|---------------|
| `local-only` | none (local repo files only -- see the seam below) | rewrites a committed index from approved evidence |
| `DB-connected` | a live database | materializes gold against a live Postgres |
| `external-service-connected` | a non-DB external service | calls a remote API/runtime |
| `publish-capable` | a published artifact | publishes a Power BI report |

> Note on `local-only`: a purely local executor is normally an `execution-capable`
> Product Module (see the seam). `local-only` exists in the adapter vocabulary so an
> adapter that ALSO has a local mode can still name its weakest connectivity; it does not
> make every local executor an adapter.

## The module-vs-adapter seam (the discriminator)

"Executes things" alone does NOT make a tool an adapter -- an `execution-capable` Product
Module also executes. The discriminator is the **external trust/connectivity boundary**:

- An **Execution Adapter** crosses an EXTERNAL trust or connectivity boundary
  (`DB-connected`, `external-service-connected`, or `publish-capable`). It touches
  something the repo does not own -- a live database, an external service, a published
  report.
- An **execution-capable Product Module** stays WITHIN committed evidence + local-repo
  operations. It runs an approved step that touches only files the repo owns; it never
  opens a DB connection or publishes.

If a tool needs to connect out or publish, it is an Adapter and MUST declare a
connectivity level. If it executes only against the local committed working set, it is an
`execution-capable` Module. The two categories are disjoint by construction.

**Tie-breaks** (recorded so a borderline tool classifies deterministically):

- A tool that seems to fit two categories: classify by its HIGHEST authority capability
  used -- writing derived evidence makes it at least `artifact-writing`; it is still a
  Module, never Core Authority. Pick the category whose forbidden list it does NOT
  violate, then the most restrictive matching sub-axis.
- "Executes" but the only side effect is reading and summarizing -> `read-only`.
  Summarizing is not executing.
- An adapter that is both DB-connected and publish-capable: declare the STRONGEST
  connectivity it uses and enumerate every boundary it crosses; `publish-capable` implies
  the publish gate applies.

## The shipped surfaces, classified (proof the taxonomy is real)

This contract classifies the surfaces the kit already ships, citing existing features. No
new claim is made; this demonstrates the taxonomy decides real tools with no overlap.

| Shipped surface | Product layer | Authority category |
|-----------------|---------------|--------------------|
| `readiness-status.yaml`, `source-map.yaml`, metric contracts, `approvals[]`, `assumptions.md`, `unresolved-questions.md` | 4 / 5 | **Core Authority** (the truth) |
| the conductor (`retail-orchestrate`) | 1 | **Official Workflow Skill** |
| `retail-validate`, `retail-govern`, `retail-semantic-check`, table onboarding wizard | 1-4 | **Official Workflow Skill** |
| control room (F012), grain-confidence reviewer (F008), cross-table lineage (F036) | 3-6 | **Product Module / `read-only`** |
| BI handoff pack (F013), dashboard design (F011), consumer data dictionary (F037) | 6 | **Product Module / `artifact-writing`** |
| Power BI execution adapter (F016, official Power BI MCP / connection) | 6 | **Execution Adapter / `publish-capable`** |

## How F025-F033 declare against this contract

Each downstream companion feature opens by declaring its category here:

| Feature | Category | Sub-axis |
|---------|----------|----------|
| F025 PR Readiness Reviewer | Product Module | `read-only` |
| F026 Readiness Viewer | Product Module | `read-only` |
| F027 Approval Console | Product Module | `artifact-writing` |
| F028 Evidence Pack Generator | Product Module | `artifact-writing` |
| F029 dbt Transformation Adapter | Execution Adapter | `DB-connected` |
| F030 Dagster Orchestration Adapter | Execution Adapter | `DB-connected` |
| F031 Adapter Maintenance Policy | Maintenance Automation | -- |
| F032 Adapter Compatibility Matrix | Maintenance Automation | -- |
| F033 Release & Maturity Management | Maintenance Automation | -- |

Every one maps to a defined category and (for Modules/Adapters) a defined sub-axis, with
no gap -- the closed set of five covers the whole companion tier.

## See also

- The prose narrative + the seam worked through: `core-vs-modules-and-adapters.md`.
- The decision record: `docs/decisions/0008-core-authority-vs-product-modules.md`.
- The functional axis this is orthogonal to: `docs/roadmap/roadmap.md` (Six product layers).
- The authority rule it makes concrete: `.specify/memory/constitution.md` (Principles I, V).
- The copy-me declarations: `templates/module-contract.md`, `templates/adapter-contract.md`.
- The spec: `specs/018-companion-tools-architecture/spec.md`.
