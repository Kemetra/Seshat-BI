# Architecture -- Core Authority vs Modules and Adapters (the authority boundary, in prose)

- **Status:** Authored (the F024 enumerated narrative; docs/templates, no runtime code).
- **Roadmap feature:** F024 (on-disk spec `018-companion-tools-architecture`). When the
  spec-dir number and the F-number disagree, the roadmap F-number wins.
- **Read with:** `product-modules.md` (the normative reference -- the five categories, the
  authority matrix, the two sub-vocabularies), `docs/decisions/0008-core-authority-vs-product-modules.md`
  (the decision record).

## Why this document exists

The normative reference (`product-modules.md`) is the checkable spine: five categories, a
matrix, two sub-vocabularies. This document is its prose companion -- it explains WHY the
authority boundary is drawn where it is, walks the module-vs-adapter seam through worked
examples, and shows the shipped surfaces being classified so a reader can apply the
contract to a new tool with confidence. The reference says WHAT; this says WHY and HOW.

## The one rule everything reduces to

> **Core Authority owns truth. Everything else is downstream of it.**

The kit has grown a dozen surfaces -- a conductor, gate verbs, read-only viewers,
artifact-writing helpers, a deferred publish adapter. The roadmap's Six product layers
describe WHICH part of the pipeline each touches. But "which part of the pipeline" never
answers the question that actually governs safety: **what is this surface allowed to do to
truth -- create it, approve it, or only read and summarize it?**

That is the authority axis. It is ORTHOGONAL to the functional (layer) axis. A tool has
two coordinates: its product LAYER (functional) and its authority CATEGORY (this
contract). The control room is product LAYER 4 AND authority CATEGORY "Product Module /
`read-only`". F016 is product LAYER 6 AND authority CATEGORY "Execution Adapter /
`publish-capable`". Neither coordinate replaces the other.

## Truth, and what it means to "create" it

"Truth" in this kit is a specific, enumerable set of artifacts -- the Core Authority:

- a readiness status (`readiness-status.yaml`: `current_stage`, per-stage status,
  `approvals[]`, `blocking_reasons[]`),
- a source map (`source-map.yaml`: declared grain, PK, PII, placement),
- a metric contract (the approved definition + binding of a measure),
- the human-owned narrative artifacts: `approvals[]`, `assumptions.md`,
  `unresolved-questions.md`.

To **CREATE truth** is to do one of: define business meaning, approve a metric or a
mapping, or move a readiness stage to `pass`. The matrix gives `yes` on those two rows
(create-truth, grant-approval) to Core Authority alone -- and grant-approval is always a
NAMED HUMAN action. No skill, module, adapter, or scheduled job may do either. They may
read it, summarize it, visualize it, derive new evidence from it, and execute a step that
was already approved -- but the truth itself, and the approval that blesses it, belong to
a named human via Core Authority.

This is not new authority invented by F024. It is the existing architectural rule woven
through Principles I and V and features F005-F016, made concrete and checkable.

## The four downstream categories, and why each is bounded the way it is

**Official Workflow Skill.** Drives a step of the spine (profile -> map -> validate ->
check). It reads Core Authority and writes into it ONLY through the named-human approval
boundary -- it routes a judgment call to a human and transcribes the answer; it never
self-grants the approval it routes. The conductor and the gate verbs live here. The
boundary: a workflow skill orchestrates the path to approval; it is not itself the
approver.

**Product Module.** Consumes Core Authority and presents, summarizes, or derives from it.
It declares one capability level -- `read-only`, `artifact-writing`, or
`execution-capable` -- and never creates truth. A `read-only` module (the control room,
the grain reviewer) reads and presents. An `artifact-writing` module (the handoff pack,
dashboard design) derives a committed artifact from committed evidence -- but the artifact
is DERIVED, never a new approval and never a new metric definition. An `execution-capable`
module runs an approved step, but only against the local committed working set (see the
seam).

**Execution Adapter.** Crosses an external trust/connectivity boundary to MATERIALIZE or
PUBLISH an already-approved artifact. It declares one connectivity level -- `local-only`,
`DB-connected`, `external-service-connected`, or `publish-capable`. It is execution-only
and gated: it never defines metrics, mappings, semantic logic, or dashboard design. The
definition it executes must already exist in Core Authority. F016 (the Power BI execution
adapter) is the canonical example: it materializes/publishes an already-approved model and
cannot invent a measure.

**Maintenance Automation.** The novel category. Runs WITHOUT a per-invocation human
trigger -- on a schedule or in CI. It emits ONLY derived evidence (a report, a drift
signal, a recomputed index) and never creates truth or self-approves. It is distinguished
from a human-invoked Module by exactly one thing: the absence of a per-run human trigger.
That absence is a DISCRIMINATOR, not a relaxation of Principle V -- the schedule itself,
and the evidence the job runs on, are prior named-human actions. A nightly job that
recomputes a drift signal is Maintenance Automation; the same logic invoked by a human at
a prompt is a Module. F031 (adapter-maintenance policy) and F033 (release-maturity) slot
into this category.

## The module-vs-adapter seam, worked through

This is the single biggest ambiguity in the contract, so it is worth walking concretely.
Both an `execution-capable` Module and an Execution Adapter "run a step". The seam is the
**external trust/connectivity boundary**:

- **Tool A -- rewrites a committed local index file from approved evidence.** It executes
  (it changes a file), but it touches only files the repo owns; it opens no DB connection
  and publishes nothing. -> **Product Module / `execution-capable`.** Not an adapter.
- **Tool B -- connects to a live Postgres to materialize gold.** It crosses an external
  connectivity boundary (a database the repo does not own). -> **Execution Adapter /
  `DB-connected`.**
- **Tool C -- publishes a Power BI report.** It crosses to a published artifact. ->
  **Execution Adapter / `publish-capable`.**
- **Tool D -- "executes", but its only side effect is reading and summarizing.** No file
  written, no boundary crossed. -> **Product Module / `read-only`.** Summarizing is not
  executing.

The rule: if it connects out or publishes, it is an Adapter and declares a connectivity
level. If it executes only against the local committed working set, it is an
`execution-capable` Module. The two categories never overlap.

## When a tool seems to fit two categories

Classify by the HIGHEST authority capability it actually uses, then take the most
restrictive matching sub-axis:

- A viewer that also writes a cache file is not `read-only` -- writing derived evidence
  makes it at least `artifact-writing`. It is still a Module, never Core Authority.
- A tool that would CREATE truth (define a metric, approve a mapping) cannot be a
  Module/Adapter/Maintenance tool at all -- the matrix forbids it. Either a named human
  owns it as Core Authority, or the proposal is rejected (Principle V; surface as a
  stop-and-ask, never auto-resolve).
- An adapter asked to define what it executes (e.g. F016 asked to invent a measure) is
  forbidden -- adapters are execution-only. Surface the missing definition as a blocker.
- A module asked to "approve" a stage so a pipeline can proceed is forbidden -- only the
  named human via Core Authority approves. The module surfaces the missing approval as a
  blocker.

## What this contract deliberately does NOT do

- It adds no `seshat check` rule, no CLI verb, no readiness stage, and no conformance
  checker. Enforcement of "every tool declares its category" is enumerated as a FUTURE
  deliverable's job (docs-first, hard rule #8). A tool with no declared category is a
  review finding today, not a runtime error.
- It emits no numeric or maturity score. Categories are names; the matrix is yes/no/n/a.
  A maturity-level concept is deferred to F033.
- It does not replace, renumber, or merge the Six product layers.
- It contains zero worked-example specifics. C086 / retail_store_sales may be cited as a
  filled reference; their values are never inlined (Principle VII).

## See also

- The normative reference (categories, matrix, sub-vocabularies): `product-modules.md`.
- The decision record: `docs/decisions/0008-core-authority-vs-product-modules.md`.
- The functional axis: `docs/roadmap/roadmap.md` (Six product layers).
- The constitution: `.specify/memory/constitution.md` (Principles I, V, VII, VIII, IX).
- The copy-me declarations: `templates/module-contract.md`, `templates/adapter-contract.md`.
- The spec: `specs/018-companion-tools-architecture/spec.md`.
