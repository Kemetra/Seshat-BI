# Feature Specification: Companion Tools Architecture -- the normative category contract every tool around the core declares itself against

**Feature Branch**: `018-companion-tools-architecture`  **Roadmap feature**: F024

> Numbering note (spec-dir vs roadmap F-number): the roadmap F-number is the
> authoritative identity. The spec-directory number is the next free on-disk slot.
> This batch: F024=spec 018, F025=019, F026=020, F027=021, F028=022, F029=023,
> F030=024, F031=025, F032=026, F033=027. When the dir number and the F-number
> disagree, the roadmap F-number wins. This feature is roadmap F024, on-disk 018.

**Created**: 2026-06-25   **Status**: Planned (spec only -- no runtime code this slice)

**Input**: "Define the OFFICIAL architecture taxonomy for every tool/module/adapter
around the core. Five categories: Core Authority, Official Workflow Skill, Product
Module, Execution Adapter, Maintenance Automation. Every future tool MUST declare its
category; every module MUST declare read-only | artifact-writing | execution-capable;
every adapter MUST declare local-only | DB-connected | external-service-connected |
publish-capable. Only Core Authority holds truth. Modules/adapters operate only from
committed evidence or approved runtime evidence. This FORMALIZES the roadmap's informal
'Six product layers' framing into a normative category contract -- it cites it, it does
not reinvent it. It is the FOUNDATION feature that F025-F033 all declare against."

## Why this feature exists

The kit has grown a dozen surfaces -- the conductor (`retail-orchestrate`), validation
verbs (`retail-validate`, `retail-govern`, `retail-semantic-check`), read-only viewers
(the control room, the grain-confidence reviewer), artifact-writing helpers (the BI
handoff pack, dashboard design), and one deferred execution adapter (F016, official
Power BI MCP / connection). The roadmap describes these informally through its **Six
product layers** table, whose "What it is" column gestures at what each surface may do.
But that table is a FUNCTIONAL cut (what part of the pipeline a surface touches); it
never states, normatively, **what each surface is allowed to do to TRUTH** -- whether it
may create it, approve it, or only read and summarize it.

That gap is now load-bearing. Features F025-F033 add more tools: a PR-readiness reviewer,
a readiness viewer, an approval console, an evidence-pack generator, a dbt adapter, a
Dagster adapter, an adapter-maintenance policy, an adapter-compatibility matrix, and a
release-maturity manager. Some read evidence, some write derived evidence, some connect to
a database, some publish. Without a normative category contract, each new tool re-litigates
the same question -- "can this thing approve a stage / define a metric / publish?" -- and
the architectural rule binding all features (only Core Authority owns truth) stays
implicit and unenforceable.

This feature makes it explicit. It defines **five categories** for every tool/module/
adapter, an **authority matrix** that says exactly which capabilities each category holds,
and **sub-vocabularies** that pin a module's and an adapter's capability declaration. It is
the FOUNDATION contract: F025-F033 each open by declaring their category against it.

## What this feature is NOT (the scope wall)

This is the load-bearing constraint, stated up front so the spec cannot drift:

- **It writes NO code, NO UI, NO dbt, NO Dagster, NO Power BI execution.** It is a
  planning/architecture slice: five spec-kit files now, and an ENUMERATION of five future
  documentation/template deliverables it does NOT create.
- **It adds NO gate, NO `retail check` rule, NO readiness stage.** Enforcement of "every
  tool declares its category" is DEFERRED (docs-first, roadmap rule #8). This feature
  ENUMERATES a future conformance check; it does not ship one. `retail check` stays exit 0
  and no new rule is added.
- **It does NOT replace or renumber the Six product layers.** The layers are a functional
  cut and remain authoritative for "what part of the pipeline a surface touches". This
  feature adds an ORTHOGONAL authority cut. Every tool now carries TWO coordinates: its
  product LAYER and its authority CATEGORY. Claiming to merge 6 layers into 5 categories
  would be a misread (see Relationship to shipped features).
- **It grants NO tool any new power.** It DESCRIBES the authority each category already may
  hold and forbids the rest; it cannot upgrade F016 to define metrics or let a viewer
  approve a stage.
- **It emits NO score.** Categories are explicit names, not a maturity number. Readiness
  remains `status` + `evidence[]` + `blocking_reasons[]` (Principle IX / rule #9). A
  maturity/score concept is F033's deferred problem, not this feature's.
- **Generic.** No worked-example specifics. C086 / retail_store_sales are FILLED examples
  cited as references, never baked into the taxonomy (Principle VII).

## Relationship to shipped features (scope delta)

The roadmap already ships the **Six product layers** framing (Agent Experience / Source
Intelligence / Mapping Governance / Validation & Readiness / Metrics & Semantic Model /
Dashboard & Delivery) and the architectural rule that **Core Authority owns truth**
(woven through F005-F016 and the constitution's Principles I and V). This feature does
not reinvent either; it FORMALIZES the authority dimension the layer table only gestures
at, and turns it into a normative category contract.

The relationship is ORTHOGONAL, not a renumbering:

- The **six layers** answer "WHICH part of the pipeline does this surface touch?" (a
  functional axis). They are unchanged and remain authoritative.
- The **five categories** this feature defines answer "WHAT may this surface do to TRUTH?"
  (an authority/capability axis). This is the new normative cut.
- Every tool therefore carries TWO coordinates. Example: the control room is product LAYER
  4 (Validation & Readiness) AND authority CATEGORY "Product Module / read-only". F016 is
  product LAYER 6 (Dashboard & Delivery) AND authority CATEGORY "Execution Adapter /
  publish-capable".

Shipped features classified under the new taxonomy (the contract working, not new claims):

| Shipped surface | Product layer (existing) | Authority category (this feature) |
|-----------------|--------------------------|-----------------------------------|
| `readiness-status.yaml`, `source-map.yaml`, metric contracts, `approvals[]`, `assumptions.md`, `unresolved-questions.md` | 4 / 5 | **Core Authority** (the truth) |
| `retail-orchestrate` (the conductor) | 1 | **Official Workflow Skill** |
| `retail-validate`, `retail-govern`, `retail-semantic-check`, table onboarding wizard | 1-4 | **Official Workflow Skill** |
| control room (F012), grain-confidence reviewer (F008) | 3-4 | **Product Module / read-only** |
| BI handoff pack (F013), dashboard design (F011) | 6 | **Product Module / artifact-writing** |
| Power BI execution adapter (F016, official Power BI MCP / connection) | 6 | **Execution Adapter / publish-capable** |

F025-F033 each declare their category against this contract: F025 PR-readiness reviewer
and F026 readiness viewer as read-only Modules; F027 approval console and F028 evidence-pack
generator against the Module sub-axes; F029 (spec-dir 023) dbt and F030 (spec-dir 024)
Dagster as Execution Adapters; F031 adapter-maintenance policy and F033 release-maturity as
the Maintenance Automation category. This feature is their foundation.

## The five categories (the normative contract)

1. **Core Authority** -- the committed (or named-human-approved) artifacts that ARE the
   truth: readiness status, source maps, metric contracts, approvals, assumptions, and
   unresolved questions. Only Core Authority creates business meaning, approves a metric or
   mapping, or moves a readiness stage to `pass`. Everything else is downstream of it.
2. **Official Workflow Skill** -- an agent procedure that drives a step of the readiness
   spine (profile -> map -> validate -> check), READING Core Authority and WRITING into it
   only through the named-human approval boundary. The conductor and the gate verbs are
   here. A workflow skill orchestrates; it never self-grants the approval it routes to a
   human.
3. **Product Module** -- a focused tool that consumes Core Authority and presents,
   summarizes, or derives from it. A module MUST declare exactly one capability level:
   `read-only` | `artifact-writing` | `execution-capable`. It never creates truth.
4. **Execution Adapter** -- a tool that crosses an external trust/connectivity boundary to
   MATERIALIZE or PUBLISH an already-approved artifact. An adapter MUST declare exactly one
   connectivity level: `local-only` | `DB-connected` | `external-service-connected` |
   `publish-capable`. It is execution-only and gated; it never defines metrics, mappings,
   semantic logic, or dashboard design.
5. **Maintenance Automation** -- a tool that runs WITHOUT a per-invocation human trigger
   (scheduled / CI), emits ONLY derived evidence (a report, a drift signal, a recomputed
   index), never creates truth, and never self-approves. This is the novel category: it is
   distinguished from a human-invoked Module by the absence of a per-run human trigger.

### Authority matrix (the spine -- each row is checkable)

| Capability | Core Authority | Workflow Skill | Product Module | Execution Adapter | Maintenance Automation |
|------------|:--:|:--:|:--:|:--:|:--:|
| Reads committed evidence | yes | yes | yes | yes | yes |
| Summarizes / visualizes evidence | yes | yes | yes | yes | yes |
| Writes DERIVED evidence (report, signal) | n/a | yes | only if `artifact-writing` | yes (the run record) | yes |
| Executes an APPROVED step | n/a | yes | only if `execution-capable` | yes (its sole purpose) | yes (scheduled) |
| Connects to a DB / external service | no | no | no | only if its connectivity level allows | only if its connectivity level allows |
| Publishes a Power BI artifact | no | no | no | only if `publish-capable` | no |
| **CREATES truth** (business meaning, metric, mapping) | **yes** | no | no | no | no |
| **GRANTS approval** / moves a stage to `pass` | **yes (named human)** | no | no | no | no |

Only Core Authority gets `yes` on the last two rows. Every other category reads, summarizes,
visualizes, may write derived evidence, and may execute an approved step -- but MUST NOT
create truth or grant approval. This is the architectural rule binding all ten features,
made concrete.

### The module-vs-adapter seam (the discriminator)

"Executes things" alone does NOT make a tool an adapter -- an `execution-capable` Product
Module also executes. The discriminator is the **trust/connectivity boundary**:

- An **Execution Adapter** crosses an EXTERNAL trust or connectivity boundary: it is
  `DB-connected`, `external-service-connected`, or `publish-capable`. It touches something
  the repo does not own (a live database, an external service, a published report).
- An **execution-capable Product Module** stays WITHIN committed evidence + local-repo
  operations (`local-only` in adapter terms). It runs an approved step that touches only
  files the repo owns; it never opens a DB connection or publishes.

If a tool needs to connect out or publish, it is an Adapter and MUST declare a connectivity
level. If it executes only against the local committed working set, it is an
`execution-capable` Module. This keeps the two categories disjoint.

## Architecture (planning posture: pure documentation + templates; no runtime code)

Consistent with features 005/010/013 (docs/templates-first, Principle VIII, roadmap rule
#8): this feature ships as **planning artifacts now** and ENUMERATES future documentation +
template deliverables. The agent is the runtime that classifies a tool against the contract;
no Python, no CLI verb, no `retail check` rule is added in this slice.

Future deliverables this feature PLANS (enumerated, NOT created now):

- `docs/architecture/product-modules.md` -- the five categories + the authority matrix +
  the two sub-vocabularies, as the normative reference.
- `docs/architecture/core-vs-modules-and-adapters.md` -- the prose narrative of the
  authority boundary and the module-vs-adapter seam, with the shipped-feature
  classification worked through.
- `docs/decisions/0006-core-authority-vs-product-modules.md` -- the ADR recording WHY the
  authority cut is orthogonal to the six layers and WHY only Core Authority owns truth.
- `templates/module-contract.md` -- the copy-me declaration every future Module fills
  (category = Product Module; capability = read-only | artifact-writing | execution-capable;
  what Core Authority it reads; what derived evidence it writes; its forbidden operations).
- `templates/adapter-contract.md` -- the copy-me declaration every future Adapter fills
  (category = Execution Adapter; connectivity = local-only | DB-connected |
  external-service-connected | publish-capable; the gate it is downstream of; its
  execution-only / no-truth forbidden operations).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Classify any tool into exactly one category (Priority: P1)

An architect (or the agent on their behalf) takes any existing or proposed tool and
classifies it into exactly one of the five categories, then -- if it is a Module or an
Adapter -- pins its sub-axis. The classification is unambiguous: the authority matrix and
the module-vs-adapter seam decide it.

**Why this priority**: a taxonomy that cannot classify a real tool is useless. The atomic
unit of value is "given this tool, what is its category and what may it do?" This is the MVP.

**Independent Test**: take three shipped surfaces (the control room, the BI handoff pack,
the F016 Power BI adapter) and one proposed surface (a scheduled drift recomputation);
confirm each lands in exactly one category, each Module/Adapter carries its sub-axis, and
the authority matrix says what each may and may not do -- with no overlap and no tool
landing in two categories.

**Acceptance Scenarios**:

1. **Given** the control room, **When** it is classified, **Then** it is a Product Module /
   `read-only` -- it reads Core Authority and presents, it writes no derived artifact, it
   creates no truth.
2. **Given** the BI handoff pack, **When** it is classified, **Then** it is a Product
   Module / `artifact-writing` -- it derives a bundle from committed evidence but approves
   nothing and defines no metric.
3. **Given** the F016 Power BI execution adapter, **When** it is classified, **Then** it is
   an Execution Adapter / `publish-capable`, downstream of semantic-model readiness, and
   the matrix forbids it from defining a metric or granting approval.

---

### User Story 2 - Distinguish an execution-capable Module from an Execution Adapter (Priority: P1)

A reviewer is handed a proposed tool that "runs a step" and must decide whether it is an
`execution-capable` Product Module or an Execution Adapter. The module-vs-adapter seam (the
trust/connectivity boundary) decides it deterministically.

**Why this priority**: this is the single biggest ambiguity in the contract -- without the
seam, the two categories overlap and the declaration is meaningless. Resolving it is what
makes the taxonomy normative rather than suggestive.

**Independent Test**: present two tools -- (a) one that rewrites a committed local index
file from approved evidence, (b) one that connects to a live Postgres to materialize gold;
confirm (a) classifies as Product Module / `execution-capable` and (b) classifies as
Execution Adapter / `DB-connected`, on the trust-boundary discriminator alone.

**Acceptance Scenarios**:

1. **Given** a tool that executes only against the local committed working set, **When** it
   is classified, **Then** it is a Product Module / `execution-capable` (`local-only` in
   adapter terms) -- never an Adapter.
2. **Given** a tool that opens a DB connection or publishes a report, **When** it is
   classified, **Then** it is an Execution Adapter and MUST declare a connectivity level.
3. **Given** a tool that "executes" but its only side effect is reading and summarizing,
   **When** it is classified, **Then** it is `read-only` -- summarizing is not executing.

---

### User Story 3 - Maintenance Automation is its own category, not a Module (Priority: P2)

An architect proposes a tool that runs on a schedule / in CI without a per-invocation human
trigger (e.g. nightly drift recomputation, a CI compatibility recheck). The contract places
it in Maintenance Automation, distinct from a human-invoked Module, and pins that it emits
only derived evidence and never self-approves.

**Why this priority**: Maintenance Automation is the novel category that lets F031
(adapter-maintenance policy) and F033 (release-maturity) slot in. Defining it sharply now
prevents those features from mis-declaring as Modules. Valuable, but US1/US2 are the
classification MVP.

**Independent Test**: take a scheduled nightly recomputation tool; confirm it classifies as
Maintenance Automation (not a Module), that the matrix grants it read / summarize / derived-
evidence / scheduled-execute but forbids truth-creation and self-approval, and that the
distinguishing feature recorded is "no per-invocation human trigger".

**Acceptance Scenarios**:

1. **Given** a tool with no per-invocation human trigger, **When** it is classified, **Then**
   it is Maintenance Automation, not a Product Module.
2. **Given** a Maintenance Automation tool, **When** the matrix is applied, **Then** it may
   emit derived evidence but MUST NOT create truth or move a stage to `pass`.
3. **Given** a Maintenance Automation tool that would publish Power BI, **When** it is
   classified, **Then** that capability is forbidden -- publishing is an Adapter capability,
   not a Maintenance one.

---

### Edge Cases

- **A tool that seems to fit two categories** (e.g. a viewer that also writes a cache file):
  classify by its HIGHEST authority capability used -- writing derived evidence makes it at
  least `artifact-writing`; it is still a Module, never Core Authority. The contract records
  the tie-break: pick the category whose forbidden list it does not violate, then the most
  restrictive matching sub-axis.
- **A proposed tool that would create truth** (define a metric, approve a mapping): it cannot
  be a Module/Adapter/Maintenance tool -- the matrix forbids it. Either it is Core Authority
  (a named human owns it) or the proposal is rejected (Principle V).
- **An adapter asked to define what it executes** (e.g. F016 asked to invent a measure):
  forbidden -- adapters are execution-only; the definition must already exist in Core
  Authority. Surface as a stop-and-ask, never auto-resolve.
- **A Module asked to "approve" a stage so a pipeline can proceed**: forbidden -- only the
  named human via Core Authority approves. The Module surfaces the missing approval as a
  blocker.
- **A tool with no declared category** (a future tool that skipped the contract): flagged as
  a defect by the (deferred, enumerated) conformance check; until that check exists, it is a
  review finding, not a runtime error.
- **Sub-axis ambiguity** (an adapter that is both DB-connected and publish-capable):
  declare the strongest connectivity it uses and enumerate every boundary it crosses;
  `publish-capable` implies the publish gate applies.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Define exactly FIVE tool categories -- Core Authority, Official Workflow Skill,
  Product Module, Execution Adapter, Maintenance Automation -- as a normative, closed set.
  Every tool/module/adapter MUST declare exactly one.
- **FR-002**: Define the AUTHORITY MATRIX (categories x capabilities) such that ONLY Core
  Authority may CREATE truth (business meaning, metric, mapping) or GRANT approval / move a
  stage to `pass`. Every other category MUST NOT do either.
- **FR-003**: Every Product Module MUST declare exactly one capability level from the closed
  set `{ read-only, artifact-writing, execution-capable }`. No other level is valid.
- **FR-004**: Every Execution Adapter MUST declare exactly one connectivity level from the
  closed set `{ local-only, DB-connected, external-service-connected, publish-capable }`.
  No other level is valid.
- **FR-005**: Define the module-vs-adapter SEAM: a tool that crosses an external trust /
  connectivity boundary (DB / external service / publish) is an Execution Adapter; a tool
  that executes only against the local committed working set is an `execution-capable`
  Module. The two categories MUST be disjoint.
- **FR-006**: Define Maintenance Automation as the category for tools that run WITHOUT a
  per-invocation human trigger (scheduled / CI), emit ONLY derived evidence, and never create
  truth or self-approve -- distinct from a human-invoked Module.
- **FR-007**: State that the five categories are ORTHOGONAL to the roadmap's Six product
  layers: a tool carries TWO coordinates (its layer AND its category). The taxonomy MUST NOT
  replace, renumber, or merge the layers.
- **FR-008**: Modules and Adapters MUST operate only from COMMITTED evidence or named-human-
  APPROVED runtime evidence. They MAY read, summarize, visualize, write derived evidence, and
  execute an approved step; they MUST NOT self-grant approval, define business meaning,
  approve a metric/mapping, publish (unless `publish-capable` adapter), or move a stage to
  `pass`.
- **FR-009**: Enumerate (do NOT create) the five future deliverables: `docs/architecture/
  product-modules.md`, `docs/architecture/core-vs-modules-and-adapters.md`,
  `docs/decisions/0006-core-authority-vs-product-modules.md`, `templates/module-contract.md`,
  `templates/adapter-contract.md`.
- **FR-010**: This feature MUST add NO runtime code, NO UI, NO dbt, NO Dagster, NO Power BI
  execution, NO `retail check` rule, and NO readiness stage. `retail check` stays exit 0 and
  no new rule is added.
- **FR-011**: This feature MUST emit NO numeric/maturity score for a tool. Category is an
  explicit name; readiness stays `status` + `evidence[]` + `blocking_reasons[]` (rule #9). A
  maturity-level concept is DEFERRED to F033.
- **FR-012**: Enforcement of "every tool declares its category" is DEFERRED (docs-first, rule
  #8): this feature ENUMERATES a future conformance check (e.g. a later `retail check` rule or
  a CI lint), it does NOT ship one. A tool with no declared category is a review finding now,
  not a runtime error.
- **FR-013**: All artifacts MUST be GENERIC: zero C086 / retail_store_sales specifics
  (billing codes, segment rollups, PII columns, per-table grain keys). The worked example may
  be CITED as a filled reference; its values MUST NOT be inlined (Principle VII).
- **FR-014**: The contract MUST classify the SHIPPED surfaces (Core Authority artifacts; the
  conductor + gate verbs as Workflow Skills; the control room + grain reviewer as read-only
  Modules; the handoff pack + dashboard design as artifact-writing Modules; F016 as a
  publish-capable Adapter) to demonstrate the taxonomy is real, citing existing features.

### Key Entities *(include if feature involves data)*

- **Tool category**: one of the five closed-set names every tool declares. Carries the
  authority the matrix assigns; only Core Authority creates truth.
- **Authority matrix**: the categories x capabilities table that decides, for any category,
  which of {read, summarize, derive, execute, connect, publish, create-truth, grant-approval}
  it holds. The checkable spine of the contract.
- **Module capability level**: one of `{ read-only, artifact-writing, execution-capable }`;
  the mandatory sub-axis a Product Module declares.
- **Adapter connectivity level**: one of `{ local-only, DB-connected,
  external-service-connected, publish-capable }`; the mandatory sub-axis an Execution Adapter
  declares.
- **Module/adapter contract (future deliverable)**: the copy-me template a future tool fills
  to declare its category, sub-axis, the Core Authority it reads, the derived evidence it
  writes, and its forbidden operations. Enumerated here, authored later.
- **Six product layers (existing, unchanged)**: the functional axis the categories are
  orthogonal to. An INPUT reference, not redefined.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Any tool can be classified into EXACTLY ONE of the five categories with no
  overlap -- verifiable by classifying three shipped surfaces + one proposed surface and
  showing each lands in one category with its sub-axis (where applicable).
- **SC-002**: The authority matrix shows ONLY Core Authority with `yes` on the create-truth
  and grant-approval rows; every other category is `no` on both -- verifiable by reading the
  matrix.
- **SC-003**: The module-vs-adapter seam classifies a local-only executor as a Module and a
  DB-connected / publishing executor as an Adapter on the trust-boundary discriminator alone,
  with the two categories provably disjoint.
- **SC-004**: 100% of shipped artifacts are generic: a reader finds ZERO C086 /
  retail_store_sales specifics in any of the five files (Principle VII).
- **SC-005**: Adding this feature adds no new `retail check` rule and keeps its
  exit code at 0 -- no checker, no rule, no readiness stage (Principle VIII; rule #8).
- **SC-006**: A reader of the spec can state, unambiguously, that the five categories are
  ORTHOGONAL to the six layers (a tool has two coordinates) and that the layers are not
  replaced -- demonstrating "formalize, do not reinvent".
- **SC-007**: F025-F033 can each declare a category against this contract with no gap: every
  one of those features maps to a defined category + (for Modules/Adapters) a defined
  sub-axis -- verifiable by walking the F025-F033 list against the five categories.

## Human approval boundary

This is an architecture-definition feature; the human approval it governs is structural,
not per-table. A named human (the architecture owner) approves the category contract itself
and any later change to the five categories, the authority matrix, or the two sub-axes. No
tool may self-classify into Core Authority, and no tool may grant itself a capability the
matrix denies. Moving any readiness stage to `pass`, defining business meaning, and
approving a metric/mapping remain Core Authority operations owned by a named human
(Principle V) -- this feature reaffirms that boundary, it does not relax it.

## Allowed operations

- Author the five spec-kit planning files (this slice's only writes).
- READ the roadmap, the constitution, and the shipped feature specs to classify them.
- DEFINE the five categories, the authority matrix, and the two sub-vocabularies as text.
- ENUMERATE the five future deliverables as planned outputs.
- CITE C086 / retail_store_sales as a filled reference (never inline its values).

## Forbidden operations

- Writing any runtime code, UI, dbt, Dagster, or Power BI execution code.
- Creating any of the five future deliverables (`product-modules.md`,
  `core-vs-modules-and-adapters.md`, ADR 0006, `module-contract.md`, `adapter-contract.md`)
  in this slice -- they are enumerated, not authored.
- Adding a `retail check` rule, a CLI verb, a readiness stage, or a conformance checker.
- Emitting a numeric/maturity score for any tool (rule #9).
- Granting any non-Core-Authority category the power to create truth or grant approval.
- Inlining C086 / retail_store_sales specifics into the taxonomy (Principle VII).
- Replacing, renumbering, or merging the Six product layers.

## Evidence required

- The five committed spec-kit files (spec, plan, tasks, acceptance checklist, governance
  checklist), ASCII + UTF-8 no BOM.
- The authority matrix present and showing only Core Authority with create-truth / grant-
  approval.
- The shipped-feature classification table (proof the taxonomy is real).
- The enumerated (not created) list of the five future deliverables.
- A record that no new `retail check` rule was added (verified by the diff).

## Readiness stage affected

**None directly.** This is a cross-cutting governance / architecture definition. It advances
no single stage; it constrains how every tool around the spine declares its authority. The
seven stages and their gates are unchanged.

## Dependencies

- **Upstream**: the roadmap (`docs/roadmap/roadmap.md`, the Six product layers + hard rules),
  the constitution (Principles I, V, VII, VIII, IX), and the shipped F005-F016 specs -- all
  committed. This feature reads them to classify; it changes none of them.
- **Downstream**: F025-F033 each declare their category against this contract. F031
  (adapter-maintenance policy) and F033 (release-maturity) depend specifically on the
  Maintenance Automation category and the deferred maturity concept this feature parks.

## Non-goals

- Any runtime code, UI, dbt, Dagster, or Power BI execution (that is F029/F030/F016).
- A conformance CHECK that enforces the contract (enumerated, deferred -- rule #8).
- A numeric maturity score (deferred to F033).
- Redefining or replacing the Six product layers.
- Filling any artifact with C086 / retail_store_sales values (Principle VII).

## Assumptions

- The Six product layers are authoritative for the functional axis and are CITED, not
  reinvented (Principle VII / "formalize, do not reinvent"). Auto-adopted default.
- The five categories are a CLOSED set for this slice; a sixth would be a future spec, not a
  silent addition (Principle VI: defaults then deviations).
- Docs/templates-first (rule #8): no automation, no checker this slice. A future feature may
  add the enumerated conformance check.
- "Core Authority owns truth" is the existing architectural rule (Principles I, V); this
  feature makes it concrete via the matrix, it does not invent new authority.

## Deferred decisions

- **A conformance check** that asserts every tool declares a category (a future `retail
  check` rule or CI lint): DEFERRED (rule #8). Enumerated here, not built.
- **A numeric maturity level** per tool/adapter: DEFERRED to F033 (release-maturity). The
  category contract is names + matrix only; no score.
- **Whether a sixth category is ever needed**: DEFERRED. The closed set of five covers
  F025-F033; a sixth requires its own spec.
- **The exact storage path of filled module/adapter contracts**: DEFERRED to the future
  `module-contract.md` / `adapter-contract.md` deliverables (recommended `templates/` for the
  copy-me shapes; per-tool filled instances alongside the tool).

## See also

- The functional axis this is orthogonal to: `docs/roadmap/roadmap.md` (Six product layers).
- The authority rule it makes concrete: `.specify/memory/constitution.md` (Principles I, V).
- The shipped surfaces it classifies: `specs/008` (grain reviewer), `specs/010` (metric
  contracts -- Core Authority), `specs/012` (control room), `specs/013` (handoff pack),
  the F016 Power BI execution adapter (parked).
- The features that declare against it: `specs/019`-`specs/027` (F025-F033).
- The no-fake-confidence rule: `docs/readiness/readiness-model.md`; hard rules #7, #8, #9.
