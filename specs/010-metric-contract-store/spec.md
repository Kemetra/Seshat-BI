# Feature Specification: Metric Contract Store + Retail KPI Packs

**Feature Branch**: `010-metric-contract-store` (work per session convention; located via `.specify/feature.json`)

**Created**: 2026-06-24

**Status**: Draft

**Input**: "Roadmap F009 (Layer 5 Metrics & Semantic Model). Advances readiness stage Semantic Model Ready. A STORE/template of metric definitions (name, grain, formula INTENT, owner, the gold columns it binds to) plus GENERIC retail KPI packs (the pack schema + example generic KPIs, not C086 numbers). This is the metric-DEFINITION layer (F009): it defines contracts; it does NOT itself check a PBIP model (that is F010 / on-disk 011). No dashboard design here (hard rule #5). Docs/templates first (#8). Generic (#7). No fake confidence (#9)."

## Why this feature exists

The Semantic Model Ready stage (`docs/readiness/semantic-model-ready.md`) requires
that "every measure traces to a metric contract owned by the metric owner." But it
also records, explicitly, that **the metric-contract artifact does not yet exist**:

> Note: metric-contract artifacts (F009/F010) are PLANNED, not yet built. Until
> they exist, this stage is `not_started` for any new table -- there is nothing for
> a measure to bind to.

This feature builds the missing artifact: the **metric contract** -- a committed,
reviewable DEFINITION of a metric (its name, grain, formula intent, owner, and the
`gold` columns it binds to) -- plus **generic retail KPI packs** that group related
metric contracts (the pack schema + example generic KPIs). It is the
metric-DEFINITION layer of Layer 5.

It is the F009 half of the roadmap's Layer 5 pair. Per the roadmap, F010
("Semantic Model Readiness", on-disk feature 011) is the SEPARATE half that adds
readiness CHECKS over an actual PBIP model -- relationships, date table, and
measures binding to these contracts. Keeping the boundary clean is itself a
requirement of this feature (see Scope boundary below).

## The define/check boundary (the load this feature respects)

- **DEFINING contracts is in-scope.** Authoring committed, reviewable metric-contract
  and KPI-pack TEXT (templates + the store layout + an authoring guide + the generic
  example pack) is the same category as `source-mapping` authoring `mappings/`
  artifacts and `assumptions.md`: no side effects, no PBIP read, no DB connection.
  This is the metric-DEFINITION layer.
- **CHECKING a PBIP model is OUT of scope (it is F010 / on-disk 011).** Reading
  `powerbi/<Model>.SemanticModel/`, asserting a measure exists, asserting relationships
  or the marked date table, or running `retail check`'s D1-D8 over TMDL -- all of that
  belongs to Semantic Model Readiness (the checking half). This feature MUST NOT
  author a checker, a CLI verb, or a `retail check` rule. It produces the contracts a
  later check will read; it does not do the checking.
- **No dashboard design (hard rule #5).** Contracts come BEFORE dashboards. This
  feature defines metrics; it MUST NOT design visuals, pages, or a report. Dashboard
  design (F011) is gated on approved contracts existing -- which is exactly what this
  feature produces.

## Architecture (docs/templates only; no runtime code)

Per roadmap hard rule #8 ("Docs/templates/checklists first; automate only after
artifacts prove useful") and Principle VIII (static-first; the shippable core is
already the existing `retail check` -- this feature adds NO rule), this feature ships as
**templates + docs only**:

- A generic metric-contract TEMPLATE (`templates/metric-contract.yaml`) -- the
  machine-readable shape of one metric definition, in the same authoring style as
  `templates/source-map.yaml`.
- A generic KPI-pack TEMPLATE (`templates/kpi-pack.yaml`) -- the shape of a named
  group of metric contracts, plus an EXAMPLE generic retail pack (generic KPI names
  only; NO C086 / pharmacy values).
- A store layout + authoring guide doc (`docs/metrics/metric-contract-store.md`) --
  where filled contracts live, the lifecycle (draft -> reviewed -> approved), and how
  the Semantic Model Ready stage will read them.
- A pointer added from `docs/readiness/semantic-model-ready.md` resolving the
  "artifacts PLANNED, not yet built" note to "the contract template now exists".

There is NO Python, NO CLI subcommand, NO `retail check` rule, NO PBIP read. The
agent is the runtime that authors a filled contract from this template, exactly as it
authors a filled `source-map.yaml`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define a metric contract from the template (Priority: P1)

An analyst (or the agent on their behalf) takes the generic `metric-contract.yaml`
template and fills it for one metric: a stable name, the grain the metric is valid
at, the formula INTENT in plain language (not DAX), the named owner, and the `gold`
table/columns it binds to. The filled contract is committed and reviewable.

**Why this priority**: a single filled metric contract is the atomic unit the whole
Semantic Model Ready stage depends on -- without one, a measure has nothing to trace
to. This is the MVP.

**Independent Test**: take the template, fill it for a GENERIC metric (e.g. a
"total of an additive money column at line grain"), and confirm every required field
is present, the formula is INTENT not implementation, the owner is named, and the
bound columns reference a `gold` table/column -- with no pharmacy/C086 specifics.

**Acceptance Scenarios**:

1. **Given** the `metric-contract.yaml` template, **When** an analyst fills it for one
   metric, **Then** the result carries name, grain, formula intent, owner, and bound
   `gold` columns, and reads as a definition (no DAX, no visual, no PBIP path).
2. **Given** a metric whose grain differs from the fact's base grain (e.g. a
   ratio valid only at a rollup), **When** the contract is filled, **Then** the grain
   field states the grain the metric is valid at and flags grain mismatch for review.
3. **Given** a metric whose business-rollup or segment mapping is not analyst-supplied,
   **When** the contract is filled, **Then** the formula-intent field STOPS and records
   an open question rather than inventing the rollup (Principle V).

---

### User Story 2 - Group metric contracts into a generic KPI pack (Priority: P2)

An analyst groups related metric contracts into a named KPI pack (e.g. a generic
"sales overview" pack) using `kpi-pack.yaml`. The pack lists which contracts it
includes and what the pack is for. The feature ships ONE example generic pack so the
schema is demonstrated -- using generic KPI names only, no C086 numbers.

**Why this priority**: packs make contracts reusable and discoverable across tables;
they are the unit a future dashboard-design feature (F011) would request. Valuable,
but a single contract (US1) is already a usable MVP.

**Independent Test**: fill `kpi-pack.yaml` for a generic pack that references two or
more metric contracts by name; confirm the pack validates (every referenced contract
name resolves), is generic (no pharmacy values), and carries an owner + purpose.

**Acceptance Scenarios**:

1. **Given** two filled metric contracts, **When** an analyst authors a KPI pack
   referencing them, **Then** the pack lists both by stable name, states its purpose,
   and names a pack owner.
2. **Given** the shipped EXAMPLE pack, **When** it is read, **Then** it contains only
   generic retail KPI names and placeholders -- zero C086 / pharmacy specifics
   (Principle VII).
3. **Given** a pack that references a contract name that does not exist, **When** it is
   reviewed, **Then** the dangling reference is a defect the review must catch.

---

### User Story 3 - The store records contract readiness with evidence, never a score (Priority: P1)

The store layout + authoring guide define a contract's lifecycle as the four explicit
readiness statuses (`not_started` / `blocked` / `warning` / `pass`) plus evidence and
blocking reasons -- never a fabricated confidence number. A contract is `pass` only
when its owner has approved it, recorded as evidence (owner + date).

**Why this priority**: the whole point of a contract is that a downstream measure can
TRUST it; trust requires explicit approval-as-evidence, not a number. This enforces
Principle IX / roadmap rule #9 and is what lets the Semantic Model Ready stage cite a
contract as `pass`.

**Independent Test**: read the store guide; confirm it defines exactly the four
statuses, requires `evidence[]` for a `pass`, requires `blocking_reasons[]` for a
`blocked`, forbids a numeric confidence score, and names the metric owner as the
approver.

**Acceptance Scenarios**:

1. **Given** an unreviewed filled contract, **When** its status is recorded, **Then**
   it is `not_started` or `blocked` (one of the four spine statuses) with the missing
   approval listed -- never `pass`. ("draft" is lifecycle prose, never a status value.)
2. **Given** an owner-approved contract, **When** its status is recorded, **Then** it
   is `pass` with evidence = owner name + approval date, and no score field is emitted.
3. **Given** any attempt to record a numeric confidence on a contract, **When** the
   guide is followed, **Then** that is forbidden -- status is one of the four words.

---

### Edge Cases

- **A metric with no clean `gold` column to bind to**: the contract STOPS and records
  a blocking reason ("no bound gold column"); it is not approvable until gold provides
  the column. (Semantic Model Ready is downstream of Gold Ready.)
- **Two contracts with the same name**: stable names must be unique within the store;
  a duplicate is a defect the review catches.
- **A formula intent that requires a business rollup the analyst has not supplied**:
  the contract STOPS for a human (Principle V); the agent never invents the rollup.
- **A metric defined at a grain finer than the bound fact provides**: flagged as a
  grain conflict for human review; not auto-resolved (Principle V -- grain).
- **A PII-derived metric**: the contract records that its bound column is PII-sensitive
  and defers publish-safety to governance sign-off (Principle V -- PII); it is not
  auto-approved.
- **Someone tries to put a DAX expression or a visual spec in the contract**: rejected
  -- the contract is INTENT + binding, not implementation (define/check boundary).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add `templates/metric-contract.yaml` -- a GENERIC, copy-me template for
  one metric definition, ASCII + UTF-8 no BOM, valid YAML, in the authoring style of
  `templates/source-map.yaml` (header explaining what it is, which principles it
  instantiates, and a NAMESPACE / generic-placeholder note).
- **FR-002**: The metric-contract template MUST carry these required fields: a stable
  `name` (PascalCase, matching the DAX measure-naming convention), `grain` (the grain
  the metric is valid at), `formula_intent` (plain-language INTENT, explicitly NOT
  DAX), `owner` (a named metric owner), and `binds_to` (the `gold` table + column(s)
  the metric reads).
- **FR-003**: The template MUST record contract readiness using ONLY the four explicit
  statuses (`not_started` / `blocked` / `warning` / `pass`) plus `evidence[]` and
  `blocking_reasons[]`. It MUST NOT contain a numeric confidence/score field
  (roadmap rule #9; readiness-model "no fake confidence").
- **FR-004**: Add `templates/kpi-pack.yaml` -- a GENERIC template for a named group of
  metric contracts, carrying `pack_name`, `purpose`, `owner`, and a list of included
  contract names, plus ONE example generic retail pack (generic KPI names only).
- **FR-005**: Add `docs/metrics/metric-contract-store.md` -- the store layout +
  authoring guide: where filled contracts live, the draft -> reviewed -> approved
  lifecycle mapped to the four statuses, the owner-approval-as-evidence rule, and how
  the Semantic Model Ready stage reads contracts. It MUST state the define/check
  boundary (this feature defines; F010/on-disk-011 checks).
- **FR-006**: All artifacts MUST be GENERIC -- no C086 / pharmacy specifics (billing
  codes, segment rollups, insurance PII, per-table grain keys). Placeholders MUST be
  obvious; C086 may be CITED as the filled-instance reference but its values MUST NOT
  be inlined (Principle VII).
- **FR-007**: The feature MUST NOT add any Python, any CLI subcommand, any
  `retail check` rule, or any PBIP read. It is templates + docs only (Principle VIII;
  roadmap rule #8). `retail check` MUST stay green and at its current rule count.
- **FR-008**: The formula-intent field MUST be INTENT, not implementation: it
  describes WHAT the metric means, not the DAX/SQL that computes it. The template MUST
  make this explicit and give a generic example of intent vs implementation.
- **FR-009**: A contract MUST stop-and-ask (record a `blocking_reason`, never invent)
  for any Principle-V judgment call surfaced while defining it: a business rollup /
  segment mapping not analyst-supplied, a grain ambiguity, or a PII publish-safety
  question. The agent recommends; the named owner decides.
- **FR-010**: A contract reaches `pass` ONLY with owner-approval recorded as evidence
  (owner name + date). A `pass` with no evidence is a defect (readiness-model).
- **FR-011**: Resolve the "metric-contract artifacts PLANNED, not yet built" note in
  `docs/readiness/semantic-model-ready.md` by pointing its "Required artifacts" row at
  the new `templates/metric-contract.yaml`, WITHOUT changing that stage's gates or
  asserting any PBIP check (that stays F010's job).
- **FR-012**: `binds_to` MUST reference the `gold` schema only (Principle III:
  Power BI reads `gold` only). A contract that binds to `silver`/`bronze` is a defect.

### Key Entities *(include if feature involves data)*

- **Metric contract**: the atomic definition of one metric. Attributes: stable `name`,
  `grain`, `formula_intent` (plain language), `owner`, `binds_to` (gold table +
  columns), readiness `status` (one of four), `evidence[]`, `blocking_reasons[]`. It
  is a DEFINITION, not an implementation, and not a check.
- **KPI pack**: a named, owned group of metric contracts with a stated `purpose` and a
  list of included contract names. Reusable across tables; the unit a future
  dashboard-design feature would request.
- **Metric owner**: the named human who approves a contract. Approval (owner + date) is
  the evidence that promotes a contract to `pass`. The agent never self-approves.
- **The store**: the committed location + lifecycle for filled contracts and packs, and
  the rules (four statuses, evidence-for-pass, no score) the Semantic Model Ready stage
  reads. Defined by the authoring guide; it does not itself read or check a PBIP model.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new metric can be fully defined from `templates/metric-contract.yaml`
  with every required field (name, grain, formula intent, owner, bound gold columns)
  present and no field left as an unfilled placeholder -- verifiable by reading one
  filled instance.
- **SC-002**: 100% of shipped artifacts are generic: a reader finds ZERO C086 /
  pharmacy specifics (billing codes, segment rollups, insurance/PII columns, pharmacy
  grain keys) in any template or doc this feature adds (Principle VII).
- **SC-003**: Adding this feature changes the `retail check` rule count by 0 and keeps
  its exit code at 0 -- this feature ships no checker and no rule (Principle VIII).
- **SC-004**: The Semantic Model Ready stage's "metric contracts PLANNED, not yet
  built" gap is closed: its "Required artifacts" row resolves to a real, committed
  template, with its gates unchanged and no PBIP check introduced.
- **SC-005**: A contract's readiness is expressible using ONLY the four words plus
  evidence/blockers: a reviewer can determine `pass` vs `blocked` from the recorded
  status + evidence with no numeric score anywhere in the artifacts (rule #9).
- **SC-006**: The define/check boundary holds: a reader of the spec + artifacts can
  state, unambiguously, that this feature DEFINES contracts and that CHECKING a PBIP
  model against them is a separate later feature (F010 / on-disk 011) -- no artifact
  here reads `powerbi/`.

## Assumptions

- **Generic templates, C086 cited not inlined** (Principle VII): the worked example is
  referenced as the filled instance; its specifics never enter the templates. Auto-
  adopted default for this repo.
- **Filled-contract storage location**: filled metric contracts live alongside the
  table working set under `mappings/<table>/metrics/` (parallel to the five mapping
  gate artifacts, per ADR 0003's "cohesive per-table working set" rationale), with the
  reusable KPI-pack store under `metrics/packs/` (top-level). This is the recommended
  default; the authoring guide records it and it is cheaply reversible (a path move).
  See open question O-1.
- **Name convention**: contract `name` is PascalCase to match the existing DAX
  measure-naming convention (`docs/conventions.md`: "Measures in PascalCase"), so a
  measure and its contract share a name. Auto-adopted from conventions.
- **`binds_to` targets `gold` only** (Principle III). Auto-adopted.
- **No numeric score** (rule #9 / readiness-model). Auto-adopted; the four explicit
  statuses are the only readiness vocabulary.
- **Docs/templates first** (rule #8): no automation in this slice. A future feature may
  add a checker that reads these contracts (that is F010/on-disk-011, out of scope).

## Dependencies

- **Upstream**: the readiness spine (feature 005: `docs/readiness/`,
  `templates/readiness-status.yaml`) and the constitution (Principles III, V, VII,
  VIII, IX) -- both already committed. Gold Ready is the data prerequisite for any
  contract to bind to a real `gold` column (a contract is a definition, so it can be
  drafted earlier, but it cannot reach `pass` against a column gold has not built).
- **Downstream**: F010 / on-disk feature 011 (Semantic Model Readiness) reads these
  contracts to check a PBIP model; F011 (Dashboard Design) is gated on approved
  contracts existing. Neither is in scope here.

## Out of scope (this feature)

- Any `retail check` rule, Python module, or CLI verb (Principle VIII; rule #8).
- Reading, validating, or asserting anything about a PBIP model in
  `powerbi/<Model>.SemanticModel/` (that is F010 / on-disk 011).
- Authoring DAX measures or TMDL (the contract is intent + binding, not DAX).
- Any dashboard, visual, page, or report design (hard rule #5; that is F011).
- Filling contracts with C086 / pharmacy values (Principle VII).
- Defining numeric scoring rules for readiness (deferred; rule #9).
