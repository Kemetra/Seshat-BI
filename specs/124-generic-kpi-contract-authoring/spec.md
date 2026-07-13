# Feature Specification: Generic KPI Knowledge Registry and Governed Project Metric-Contract Authoring

**Feature Branch**: `124-generic-kpi-contract-authoring`

**Created**: 2026-07-13

**Status**: Draft

**Input**: Owner-directed specification input (2026-07-13): "Complete the already-declared `kpi_contracts` stage of the Database-to-PBIP flow for any retail user workspace. Introduce one authoritative generic KPI registry, produce source-to-KPI answerability using the existing five coverage statuses, and let any retail user author a project-specific F009 metric-contract from approved Decision Store decisions -- without creating a second stage, second Decision Store, second readiness engine, or client-specific KPI system."

> This is a SPECIFICATION-ONLY package. The product decisions below are recorded as
> owner-directed input dated 2026-07-13; the feature is NOT ratified by their presence.
> No runtime code, no CLI command, no production artifact under `skills/`, `templates/`,
> `mappings/`, `docs/metrics/`, or `contracts/knowledge/` is created or edited by this
> package. All authored bytes live under `specs/124-generic-kpi-contract-authoring/`.
> Status-header and tasks.md checkboxes are known-stale in this repo; the authoritative
> record of shipped truth is `docs/capabilities/capabilities.yaml` + git log + source paths.

---

## Overview

### Feature Summary

Seshat BI already ships (a) a generic Retail KPI **knowledge** layer (`skills/retail-kpi-knowledge/`, 13 per-KPI knowledge contracts numbered `KPI-MC-01`..`KPI-MC-13`), (b) an F009 **metric-contract** template and store (`templates/metric-contract.yaml`, filled instances under `mappings/<table>/metrics/`), and (c) a runtime **Decision Store** with a `kpi_definition` and `policy_ruling` decision type, a fail-closed loader, and a decision gate (spec 121). The Database-to-PBIP flow (`contracts/knowledge/database-to-pbip-flow.yaml`) already **declares** a `kpi_contracts` stage between `business_knowledge_interview` and `silver_gold_model_planning`.

What is missing is the connective tissue that turns "we have KPI knowledge, a contract template, and approved decisions" into "any retail user can reliably author a governed, traceable project metric-contract for the KPIs their source can actually answer." Today the KPI knowledge is smeared across six projections that have already drifted (three seeded contracts are still reported as "planned" elsewhere; seed counts say "10" while 13 files exist), there is no single machine-readable inventory, project contracts carry no structured link back to the decisions or evidence that authorize them, and there is no repeatable way to say "this KPI is answerable here, that one is blocked, and here is exactly why" without fabricating a score.

This feature specifies: **one authoritative generic KPI registry**, a **source-to-KPI answerability** artifact using the five existing coverage statuses, a **project metric-contract authoring** flow that draws its meaning and policy from approved Decision Store decisions and records structured provenance, a **custom-KPI** path, a **first generic expansion wave**, and a **routine extension protocol** with at most two narrow static consistency rules.

### Problem Statement

- There is no single source of truth for generic KPI metadata. Stable identity (`KPI-MC-NN`) exists, but slug, canonical name, aliases, domain, metric kind, lifecycle, derivation edges, required logical concepts, required owner decisions, and applicable source/fact roles are inferred or inline, and the INDEX, README, packs, candidates JSON, source-field-requirements, and derivation-lineage projections have already drifted from the contract files.
- A retail user cannot see, per source, which KPIs are answerable and which are blocked, in a way that is truthful (no fabricated coverage percentage), evidence-backed, and refuses to guess a mapping from a lookalike column name.
- A project metric-contract has no structured field tying it to the approved `kpi_definition` / `policy_ruling` decisions, the generic KPI it realizes (or a custom classification), or the source/mapping evidence that justifies its binding. Provenance exists only as prose comments and free-text evidence.
- There is no bounded, repeatable way to add the next generic KPI, and nothing statically guards against duplicate IDs, unresolved references, lifecycle drift, aliases mistaken for new KPIs, broken derivation edges, or product-level leakage of a project binding.

### Product Goal

Give any Seshat BI retail user a governed, reusable KPI-contract authoring flow: select a generic KPI or declare a custom one; assess answerability against committed source/mapping evidence and approved decisions; author a project-specific F009 metric-contract draft from approved meaning and policy; preserve traceable provenance end-to-end; stop truthfully when meaning, policy, source concepts, grain, unit/currency, PII ruling, or Gold binding is missing; and add future KPIs through a repeatable protocol -- all without a second Decision Store, a second readiness engine, a second contract format, a new CLI family, or any numeric confidence score.

### Primary Actors

- **Retail user / analyst** (agent-driven): selects candidate KPIs, requests answerability, drafts contracts.
- **Metric owner**: the only authority that can approve `kpi_definition` and `policy_ruling` decisions (`contracts/knowledge/approval-authority.yaml`).
- **Data owner / governance**: approve PII, exclusion, grain, and publish-safety decisions where a KPI depends on them.
- **The agent**: the runtime. It routes through `retail-kpi-knowledge`, reads committed state, proposes, and STOPS at judgment calls; it never self-grants an approval and never fabricates a confidence score.

### Relationship to Already-Shipped Capabilities (no-duplicate check)

This feature is the **`kpi_contracts` flow stage** (`contracts/knowledge/database-to-pbip-flow.yaml`), which maps to the `semantic_model_ready` readiness stage via the existing `_FLOW_TO_SPINE` projection. It is spec 121's declared Future Slice #2 ("KPI contract production at flow scale") and the direct downstream of spec 122's `kpi_contracts` handoff. It introduces **no new readiness spine stage.**

| Already on main (do NOT rebuild) | Where it lives (evidence) | This feature's relationship |
| --- | --- | --- |
| Generic Retail KPI knowledge (13 knowledge contracts, domains, packs, candidates, references) | `skills/retail-kpi-knowledge/` | REUSE as the prose source of truth. This feature adds ONE machine-readable registry that indexes them; it does not replace the prose contracts. |
| F009 metric-contract template + store rules | `templates/metric-contract.yaml`, `docs/metrics/metric-contract-store.md`, spec 010 | REUSE as the authoring target and store. This feature adds only additive fields (generic ref / custom classification, decision refs, source/mapping evidence refs); it does not re-define the base contract. |
| KPI derivation-lineage `derives_from` field | spec 044 | REUSE. The registry projects lineage from this field; it creates no second dependency representation. |
| Per-contract ambiguity ledger (`ambiguities[]`, A1..A11) | spec 058 | REUSE. KPI ambiguity rulings are recorded via this ledger, not a new mechanism. |
| Decision-aid fields (`direction_of_good`, threshold bands, action-on-breach) | spec 087 | REUSE where a KPI is decision-ready; this feature adds no threshold/direction field. |
| Currency / unit-of-measure (`unit`, `columns[].unit/currency`, rule `HR11`) | spec 103 | REUSE. Unit/currency lives there; this feature adds no unit field. |
| Decision Store + decision gate (`kpi_definition`, `policy_ruling`, 9-status lifecycle, approval-authority, staleness/supersession) | `src/seshat/decision_store.py`, `src/seshat/decision_gate.py`, spec 121 | REUSE as the ONLY decision store and the ONLY readiness engine. This feature records decisions there and reads the gate verdict; it adds no second store or engine. |
| `kpi_contracts` Knowledge Contract stage | `contracts/knowledge/database-to-pbip-flow.yaml`, spec 121 stage enum | REUSE. This feature PRODUCES the stage's declared `required_outputs`; it does not add a stage. |
| KPI Coverage Scorecard (five statuses) | `skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md` | REUSE the exact five statuses for answerability. |
| SL1 scorecard linter (structure only) | spec 056, rule `SL1` | REUSE. This feature does not re-adjudicate coverage; SL1 lints answerability structure. |
| Business Knowledge Interview | spec 121, `.claude/skills/business-knowledge-interview/SKILL.md` | REUSE as the producer of the `kpi_definition` / `policy_ruling` decisions this feature consumes; it is upstream and out of scope here. |
| Worked examples (C086 pharmacy; retail_store_sales Kaggle) | `docs/worked-examples/`, `mappings/retail_store_sales/metrics/` | REFERENCE only, as illustrations. Their table/column names, policies, numbers, and named humans MUST NOT become product defaults or enter the registry. |

Genuinely NEW in this feature: (1) the single authoritative generic KPI **registry** artifact and format; (2) the per-source **answerability** artifact bound to committed evidence + decisions; (3) additive **provenance** fields on the project metric-contract; (4) the **custom-KPI** classification and its guardrails; (5) the **extension protocol** and at most two narrow static consistency rules. Everything else is reuse.

---

## Clarifications

### Session 2026-07-13 (owner-directed product decisions D1-D10)

- Q: Is this capability client-specific or generic? -> A: Generic for any Seshat BI retail user and any supported workspace; not tied to C086, retail_store_sales, Kaggle, a named customer, a named ERP, or a fixed physical schema. Seshat remains a Retail BI product, not a universal cross-industry KPI ontology. (D1; FR-001, FR-040)
- Q: How many layers, and who owns what? -> A: Three layers -- product (generic KPI knowledge + canonical metadata shipped with Seshat), project decision (approved meaning/policy in the existing Decision Store), project contract (filled F009 YAML under `mappings/<table>/metrics/`). SQL/DAX/Python/Big-data/Semantic/Dashboard/Publish remain downstream owners. (D2; FR-002)
- Q: How many authoritative generic inventories? -> A: Exactly one machine-readable registry; rich prose stays in the per-KPI knowledge contracts; INDEX/README/packs/candidates/field-requirements/derivation-lineage must not compete as sources of truth. (D3; FR-003, FR-004, FR-005)
- Q: Must a project contract name equal the generic canonical name? -> A: No. A project contract may use a project name but MUST carry a stable `generic_kpi_ref` when it realizes a known generic KPI; aliases never create duplicate generic contracts; a project metric is never forced to map to a generic KPI unless the approved definition proves it. (D4; FR-011, FR-012, FR-031)
- Q: Are custom KPIs allowed? -> A: Yes. A custom project KPI needs an approved `kpi_definition` decision plus applicable policy rulings, MUST be marked custom, and MUST NOT be silently promoted into the product registry; promotion is a separate contribution workflow. (D5; FR-020, FR-021, FR-022)
- Q: One contract or two (business vs technical)? -> A: One F009 project contract with two checkpoints -- Checkpoint A (meaning + policies approved -> contract may be drafted, and stays `blocked` if Gold binding is not materialized) and Checkpoint B (after Gold exists and validates -> actual Gold-only binding + named-human approval evidence -> may reach `pass`). No new readiness status vocabulary. (D6; FR-013, FR-016, FR-017, FR-018)
- Q: How is answerability expressed? -> A: Using the existing five KPI Coverage Scorecard statuses exactly (`Covered`, `Blocked -- missing field`, `Blocked -- needs business definition`, `Planned`, `Out of scope`); `Covered` means eligible to begin a draft, not approved/ready; no percentage, score, or ranking; SL1 stays a structural linter. (D7; FR-007, FR-008, FR-009)
- Q: Is "Net Sales by Branch" a separate KPI? -> A: No. Grouping-dimension variants are analytical slices of an existing metric, not new generic KPI contracts, unless the business formula is materially different. (D8; FR-010, FR-031)
- Q: CLI or agent? -> A: Agent-first. Reuse/extend the existing `retail-kpi-knowledge` routing; no broad CLI family, no new KPI CLI command, no new orchestration engine. The agent is the runtime; committed artifacts + static checks are the durable output. (D9; FR-035, FR-036)
- Q: Which KPIs are in the first expansion wave, and what must they not bake in? -> A: Discounted Transaction Rate, Average Basket Size (Units), Net Sales Growth %, YTD Net Sales -- describing required logical concepts and owner policy slots only, never a fiscal-year start, a date column, YoY-vs-prior-period as a universal choice, a discount denominator, a physical table/column, or any worked-example decision. Same-Store Sales Growth, Inventory Turnover, GMROI, Out-of-Stock Rate, Customer Retention, CLV, Net Sales vs Target, and Promotion Uplift stay honestly Planned (registry metadata + blockers only). (D10; FR-023..FR-027)

---

## User Scenarios & Testing *(mandatory)*

Actors: retail user/analyst (agent-driven), metric owner, data owner/governance, the agent.

### User Story 1 - Establish the authoritative generic KPI registry (Priority: P1 -- MVP)

A maintainer needs one machine-readable inventory that names every seeded and planned generic KPI exactly once, preserves the stable `KPI-MC-NN` IDs, and distinguishes canonical names from aliases and metric kinds (base metric, derived metric, ratio, time-transform, snapshot, quality metric, analytical slice). Where INDEX/README/packs/candidates/source-field-requirements/derivation-lineage currently disagree (three seeded contracts still reported "planned"; seed counts saying "10" while 13 files exist; the template/SL1 dash divergence), each divergence is either reconciled in the registry or explicitly documented as known drift. All registry metadata stays generic and client-free.

**Why this priority**: Every other story reads identity, lifecycle, required concepts, and required decisions from the registry. Without one source of truth, answerability and authoring inherit the existing drift. This is the smallest independently valuable and testable slice.

**Independent Test**: Load the registry alone; confirm every existing `KPI-MC-NN` appears exactly once with canonical name, slug, aliases, domain, metric kind, lifecycle, knowledge-contract reference, derivation refs, required logical concepts, required decision types, and applicable source/fact roles; confirm no client-specific token appears; confirm every documented drift item names the conflicting files and the reconciled or owner-flagged resolution.

**Acceptance Scenarios**:

1. **Given** the 13 shipped knowledge contracts and their scattered projections, **When** the registry is authored, **Then** each `KPI-MC-NN` is present exactly once and no two entries share an ID, slug, or canonical name.
2. **Given** Net Sales Growth % (`KPI-MC-11`) and YTD Net Sales (`KPI-MC-13`) are Seeded in their contract files but "planned" in README/packs/candidates, **When** the registry records their lifecycle, **Then** each carries a single lifecycle value and the drift is listed as a resolved or owner-flagged item that names every conflicting file.
3. **Given** the scorecard template uses em-dash status strings while this spec authors ASCII `--` (and SL1 normalizes both), **When** the registry documents drift, **Then** the dash divergence is recorded as a cosmetic (non-functional) drift item flagged for the owner (spec-only: not edited here).
4. **Given** an alias such as "average receipt value" for Average Transaction Value, **When** the registry records aliases, **Then** the alias is attached to the canonical entry and creates no separate entry.

---

### User Story 2 - Produce source-to-KPI answerability (Priority: P1 -- MVP)

Given committed source-profile / source-map evidence for a table or subject area, a selected domain/scope, the generic KPI requirements from the registry, and the Decision Store, the agent produces a per-table (or per-subject-area) answerability artifact using the five existing coverage statuses. It never infers a semantic mapping from a lookalike column name, treats a present physical field as insufficient while the governing policy is unresolved, fails closed on missing or stale evidence, and for a multi-fact KPI names every required source role/fact and blocks when one is absent.

**Why this priority**: Answerability is the gate that tells a user which KPIs are even eligible to draft. It is independently valuable (a truthful "what can this source answer" report) and independently testable against fixture evidence.

**Independent Test**: Provide fixture source evidence and a fixture Decision Store; request answerability for a set of registry KPIs; confirm each row carries exactly one of the five statuses, names its blockers, cites its evidence, states the next allowed action, and grants no readiness; confirm a lookalike-only column produces `Blocked -- needs business definition`, not `Covered`; confirm a missing required fact for a multi-fact KPI produces a `Blocked -- missing field` naming the absent role.

**Acceptance Scenarios**:

1. **Given** a column `total_sales` whose meaning is unresolved, **When** answerability runs for Gross Sales / Net Sales, **Then** the status is `Blocked -- needs business definition` and the blocker names the unresolved gross/net/tax-inclusive meaning -- never `Covered`.
2. **Given** a KPI requiring two facts (e.g. sales plus returns) where only one is present, **When** answerability runs, **Then** the status is `Blocked -- missing field` and every absent required role is named.
3. **Given** cited source evidence whose content hash no longer matches the recorded identity, **When** answerability runs, **Then** it fails closed (does not report `Covered`) and names stale evidence as the blocker.
4. **Given** a KPI whose contract is `Planned` in the registry, **When** answerability runs, **Then** the status is `Planned` and the row routes to the deferred note without fabricating a contract.
5. **Given** an inventory KPI requested against a sales-only fact, **When** answerability runs, **Then** the status is `Out of scope`.

---

### User Story 3 - Draft a project metric contract from approved decisions (Priority: P1 -- MVP)

From approved `kpi_definition` and applicable `policy_ruling` decisions, the agent drafts a project-specific F009 metric-contract. A known generic KPI carries a stable `generic_kpi_ref`; a custom KPI carries an explicit custom classification. The draft records machine-readable provenance to the decision IDs and the committed source/mapping evidence, states business intent, grain, additivity, unit/currency where applicable, required filters/exclusions, ambiguities, and intended implementation handoffs, and contains no DAX, SQL, visual spec, connection string, raw PII, or fabricated Gold path. If physical Gold binding does not yet exist, the contract is left `blocked` with a concrete next action.

**Why this priority**: This is the core deliverable of the `kpi_contracts` stage -- a governed, traceable contract. It completes the MVP triad (registry -> answerability -> draft) and is independently testable by drafting from fixture decisions.

**Independent Test**: Provide fixture approved decisions and fixture source/mapping evidence; draft a contract; confirm it carries `generic_kpi_ref` (or `custom: true`), structured `decision_refs`, structured `source_evidence`, `readiness.status: blocked` with a named `physical gold binding is not materialized` reason when Gold is absent, and contains none of the forbidden content (DAX/SQL/visual/connection string/raw PII/invented gold path).

**Acceptance Scenarios**:

1. **Given** an approved `kpi_definition` for a known generic KPI and no Gold table, **When** the draft is authored, **Then** it carries the matching `generic_kpi_ref`, links the decision IDs, and is `blocked` with reason `physical gold binding is not materialized`.
2. **Given** no approved `kpi_definition` for the requested KPI, **When** a draft is attempted, **Then** authoring stops and the next action names the missing approved decision.
3. **Given** an applicable VAT/returns/discount/cost `policy_ruling` is unresolved, **When** a draft is attempted, **Then** it is `blocked` and the blocker names the unresolved policy.
4. **Given** a draft is authored, **When** it is inspected, **Then** it contains no DAX/SQL/visual spec/connection string/raw PII and no Gold path that is not backed by committed evidence.

---

### User Story 4 - Complete Gold binding and hand off downstream (Priority: P2)

After Gold is materialized and validated, the same project contract is completed with actual Gold-only table/column binding. The flow detects stale or superseded decisions and changed evidence, refuses `pass` unless the binding exists, decisions remain valid, blockers are empty, and a named-human approval is recorded, and it produces clean handoffs to SQL/DAX/Python/Big-data per existing ownership boundaries. This feature implements none of that downstream work.

**Why this priority**: Checkpoint B depends on Gold existing (a later stage), so it is P2. It is independently testable: given a contract, a fixture Gold binding, valid decisions, and a named approval, the contract may reach `pass`; remove any one and it may not.

**Independent Test**: With a drafted contract plus fixture Gold binding, valid non-superseded decisions, empty blockers, and a recorded named-human approval, confirm the contract is eligible for `pass`; then independently (a) supersede a decision, (b) change evidence identity, (c) remove the binding, (d) remove the approval, and confirm each independently prevents `pass`.

**Acceptance Scenarios**:

1. **Given** a validated Gold binding, valid decisions, empty blockers, and a named-human approval, **When** the contract is finalized, **Then** it may reach `pass` with recorded evidence.
2. **Given** a decision was superseded after the draft, **When** finalization is attempted, **Then** `pass` is refused and the superseded decision is named.
3. **Given** cited evidence changed since approval, **When** finalization is attempted, **Then** `pass` is refused as stale.
4. **Given** a user attempts `pass` before any Gold binding exists, **When** finalization is attempted, **Then** it is refused with the binding-missing blocker.

---

### User Story 5 - Support custom KPIs safely (Priority: P2)

A retail user authors a project KPI absent from the generic registry. It requires an approved business definition, grain, additivity, unit, applicable policies, required fields, and a named eligible owner. It is marked custom, is not auto-added to the generic product knowledge, and the separate contribution path to promote it is explained but not performed here.

**Why this priority**: Custom KPIs are essential for real workspaces but sit on top of the generic machinery, so P2. Independently testable by authoring a custom contract and confirming it never mutates the registry.

**Independent Test**: Author a custom KPI draft with approved definition + policies + eligible owner; confirm `custom: true`, no `generic_kpi_ref`, no change to the generic registry, and a stated contribution path; then attempt a custom KPI with no eligible owner and confirm authoring stops.

**Acceptance Scenarios**:

1. **Given** a project KPI with no generic registry entry and an approved `kpi_definition` + policies + eligible owner, **When** it is authored, **Then** it is marked `custom: true`, carries no `generic_kpi_ref`, and the generic registry is unchanged.
2. **Given** a custom KPI request without an eligible human owner, **When** authoring is attempted, **Then** it stops and names the missing owner.
3. **Given** a completed custom KPI, **When** the user asks how to make it generic, **Then** the contribution/review workflow is explained and NOT executed automatically.

---

### User Story 6 - Add the first generic expansion wave (Priority: P3)

Specification-ready coverage is added for the four D10 KPIs. Faithful to ground truth: **Discounted Transaction Rate** is net-new (absent from the generic library today), **Average Basket Size (Units)** is promoted from Planned (no contract today), and **Net Sales Growth %** (`KPI-MC-11`) and **YTD Net Sales** (`KPI-MC-13`) already have Seeded contracts, so their expansion work is drift reconciliation in the registry, not new prose. Each updates registry metadata, the knowledge contract, relevant packs, field requirements, aliases, and derivation relationships without duplicating formulas. Each is independently testable and reviewable. None bakes in a fiscal-year start, a date column, YoY-vs-prior-period as a universal choice, a discount denominator, a physical table/column, or any worked-example decision.

**Why this priority**: Content expansion sits on top of the architecture (US1-US3), so P3. Each KPI is an independent, reviewable slice.

**Independent Test**: For each of the four, confirm the registry entry, knowledge-contract requirements, and derivation edges exist and describe only logical concepts + owner policy slots; confirm no prohibited baked-in value; confirm Discounted Transaction Rate is described from first principles (not the worked-example 50.37% / Q2 denominator); confirm MC-11 and MC-13 lifecycle is now consistent across the registry.

**Acceptance Scenarios**:

1. **Given** Discounted Transaction Rate is absent from the library, **When** its generic contract is authored, **Then** its discount denominator is an owner policy slot, not a value copied from any worked example.
2. **Given** Average Basket Size (Units) is Planned, **When** it is added, **Then** it references units (not currency) and its grain/additivity are stated as concepts, deriving from existing quantity/transaction metrics without duplicating their formulas.
3. **Given** MC-11 and MC-13 already have Seeded contracts, **When** the wave completes, **Then** their registry lifecycle is consistent and no duplicate contract is created.
4. **Given** any of the four, **When** its time or ratio behavior is described, **Then** YoY-vs-prior-period and fiscal-year start remain owner policy slots, not universal choices.

---

### User Story 7 - Make future KPI additions routine (Priority: P3)

A KPI contribution/extension checklist defines the bounded set of artifacts and validations required to add a future generic KPI. At most two narrow static consistency rules guard structure and traceability: duplicate IDs, unresolved references, lifecycle drift, aliases treated as new KPIs, broken derivation edges, and product-level leakage of project bindings. The static rules validate structure and traceability only; they never decide business meaning or grant readiness.

**Why this priority**: The extension protocol prevents the architecture from being reopened per KPI. It is valuable but sits atop everything else, so P3. Independently testable by running the checklist against a well-formed and a malformed addition.

**Independent Test**: Run the extension checklist and the (at most two) consistency rules against (a) a well-formed new registry entry -> pass, and (b) each malformed case (duplicate ID, dangling reference, lifecycle mismatch, alias-as-new-KPI, broken derivation edge, a project binding in a product-level file) -> a structural error naming the defect, with no business-meaning adjudication and no readiness granted.

**Acceptance Scenarios**:

1. **Given** a new registry entry that duplicates an existing `KPI-MC-NN`, **When** the consistency rule runs, **Then** it emits a structural error naming the duplicate ID.
2. **Given** a registry entry whose `generic_kpi_ref`/knowledge-contract reference does not resolve, **When** the rule runs, **Then** it emits an unresolved-reference error.
3. **Given** a product-level registry file that contains a physical Gold table/column binding, **When** the rule runs, **Then** it emits a leakage error.
4. **Given** a well-formed addition following the checklist, **When** the rule runs, **Then** it passes and grants no readiness.

---

### Edge Cases

- **Ambiguous `total_sales`**: a field whose meaning could be gross, net, tax-inclusive, or merely recorded value -> `Blocked -- needs business definition` until an approved `kpi_definition` resolves it; never auto-mapped to Gross/Net Sales.
- **Field present, policy unresolved**: a required VAT/returns/cost/date policy is undecided -> answerability is `Blocked -- needs business definition` even though the physical field exists.
- **No generic equivalent**: a project KPI with no registry entry -> the custom path (US5), not a forced mapping.
- **Same generic, different scopes**: two project contracts intentionally referencing the same `generic_kpi_ref` with different approved scopes -> both valid, distinguished by scope, not duplicates.
- **Alias/canonical collision**: an alias equal to another entry's canonical name -> a consistency error (US7), never two competing entries.
- **Slice, not a metric**: "KPI by branch/product/category/channel" -> recorded as a slice of an existing metric, not a new generic contract (D8).
- **Gold not yet materialized**: draft is `blocked` with `physical gold binding is not materialized`; never `pass`.
- **Gold column renamed/disappeared later**: a completed binding whose column later changes -> detected as changed evidence; `pass` is withdrawn/refused until rebound.
- **Decision superseded after draft**: the contract cannot reach `pass`; the superseded decision is named.
- **Decision approval stale**: cited source evidence changed after approval -> stale; blocks `pass`.
- **Multi-fact KPI**: sales+returns, sales+targets, or COGS+inventory snapshots -> every required role named; absent one blocks with `Blocked -- missing field`.
- **Customer/PII-dependent KPI**: depends on a customer-identity / PII ruling -> blocked until governance rules; raw PII never written into any artifact.
- **Semi-additive snapshot KPI**: additivity over time is stated as semi-additive (concept), never silently summed.
- **Ratio summed/averaged across groups**: recorded as non-additive with the anti-pattern noted; a ratio is never additively rolled up.
- **Multiple/incompatible currencies or units**: deferred to the spec 103 unit/currency contract; a summed measure with disagreeing units is a defect there (rule `HR11`), not re-solved here.
- **Custom KPI without eligible owner**: authoring stops; the missing eligible owner is named.
- **Legacy contracts lacking provenance**: existing project contracts without the new fields remain valid; the fields are additive/optional (migration posture below).
- **Bundled worked examples**: may be migrated as fixtures carrying the new provenance fields, but their values never enter the registry or become product defaults.
- **Decision Store absent/malformed/conflicting**: fail closed (the existing loader's behavior); answerability and authoring block with the store problem named; conflicting active decisions of the same type/scope block (existing DS4/gate behavior).
- **Planned KPI requested as seeded**: answerability returns `Planned`; no contract is fabricated.
- **`pass` attempted before Gold binding**: refused with the binding-missing blocker (D6).

---

## Requirements *(mandatory)*

### Functional Requirements -- Product scope and layering (D1, D2)

- **FR-001**: The registry, answerability, and authoring flow MUST be generic for any retail workspace and MUST NOT embed C086, retail_store_sales, Kaggle, a named customer, a named ERP, or a fixed physical schema.
- **FR-002**: The feature MUST preserve the three-layer boundary -- product (generic knowledge + registry), project decision (Decision Store), project contract (F009 YAML under `mappings/<table>/metrics/`) -- and MUST leave SQL/DAX/Python/Big-data/Semantic/Dashboard/Publish as downstream owners.

### Functional Requirements -- Generic KPI registry (US1; D3)

- **FR-003**: The system MUST provide exactly ONE machine-readable authoritative registry of generic KPI metadata; no other file (INDEX, README, packs, candidates, source-field-requirements, derivation-lineage) may act as a competing source of truth for that metadata.
- **FR-004**: Each registry entry MUST carry: stable id, slug, canonical name, aliases, domain, metric kind, lifecycle, knowledge-contract reference, derives-from references, required logical concepts, required decision/policy types, and applicable source/fact roles.
- **FR-005**: The registry MUST preserve existing stable IDs (`KPI-MC-01`..`KPI-MC-13`) and record each seeded and planned generic KPI exactly once.
- **FR-006**: Registry metric kind MUST distinguish base metric, derived metric, ratio, time-transform, snapshot, quality metric, and analytical slice.
- **FR-040**: All registry content MUST be client-free; a consistency rule (US7) MUST be able to detect a physical binding or client token in a product-level registry file.

### Functional Requirements -- Answerability (US2; D7)

- **FR-007**: Answerability MUST use exactly the five existing coverage statuses, spelled `Covered`, `Blocked -- missing field`, `Blocked -- needs business definition`, `Planned`, `Out of scope` (ASCII `--`).
- **FR-008**: Answerability MUST NOT emit any numeric coverage percentage, confidence score, or ranking, and MUST grant no readiness (`Covered` means eligible to begin a draft only).
- **FR-009**: Answerability MUST NOT infer a semantic mapping from a similar column name; a present physical field is insufficient while the governing business policy is unresolved.
- **FR-041**: Answerability MUST fail closed on missing or stale source/mapping evidence (it MUST NOT report `Covered` when required evidence is absent or its recorded identity no longer matches).
- **FR-042**: For a KPI requiring multiple source roles/facts, answerability MUST name every required role and MUST block when any one is absent.
- **FR-043**: Each answerability row MUST record: project/source scope, the generic KPI or custom request, the coverage status, named blockers, evidence references, and the next allowed action.

### Functional Requirements -- Project contract authoring, Checkpoint A (US3; D4, D6)

- **FR-010**: A grouping-dimension variant (by branch/product/category/channel/etc.) MUST be recorded as an analytical slice of an existing metric, not a new generic KPI contract.
- **FR-011**: A project contract that realizes a known generic KPI MUST carry a stable `generic_kpi_ref`; a project contract MUST NOT be forced to reference a generic KPI unless the approved definition proves the mapping.
- **FR-012**: A project contract name MAY differ from the generic canonical name; aliases MUST NOT create duplicate generic entries or duplicate project contracts.
- **FR-013**: Drafting a project contract MUST require an approved `kpi_definition` decision and every applicable approved `policy_ruling` decision; absent either, authoring MUST stop and name the missing approved decision.
- **FR-014**: A drafted contract MUST record machine-readable provenance: structured references to the approved decision IDs and to the committed source/mapping evidence it relies on.
- **FR-015**: A drafted contract MUST state business intent, grain, additivity, unit/currency where applicable, required filters/exclusions, ambiguities (via the spec 058 ledger), and intended implementation handoffs; it MUST contain no DAX, SQL, visual spec, connection string, raw PII, or Gold path unbacked by committed evidence.
- **FR-016**: If physical Gold binding does not exist, the contract MUST be left `readiness.status: blocked` with a concrete blocking reason (e.g. `physical gold binding is not materialized`) and a concrete next action; it MUST NOT reach `pass`.

### Functional Requirements -- Checkpoint B and downstream handoff (US4; D6)

- **FR-017**: A contract MUST reach `pass` only when a valid Gold-only binding exists, all referenced decisions remain valid (not superseded), no cited evidence is stale, blockers are empty, and a named-human approval is recorded.
- **FR-018**: The flow MUST detect superseded decisions and changed evidence and MUST refuse `pass` when either is present, naming the offending decision or evidence.
- **FR-019**: On reaching `pass`, the contract MUST present clean handoffs to SQL/DAX/Python/Big-data per existing ownership boundaries; this feature MUST NOT implement any of that downstream work.
- **FR-044**: Gold bindings MUST be gold-only; the flow MUST NOT bind a contract to a `silver`/`bronze` object.

### Functional Requirements -- Custom KPIs (US5; D5)

- **FR-020**: A custom project KPI (no generic registry entry) MUST require an approved `kpi_definition` decision plus applicable policy rulings, and MUST record grain, additivity, unit, required fields, and a named eligible owner.
- **FR-021**: A custom contract MUST be explicitly marked custom (e.g. `custom: true`), carry no `generic_kpi_ref`, and MUST NOT mutate the generic registry.
- **FR-022**: The system MUST describe the separate contribution/review workflow to promote a custom KPI into the generic library and MUST NOT perform that promotion automatically.

### Functional Requirements -- First expansion wave (US6; D10)

- **FR-023**: The system MUST add specification-ready coverage for Discounted Transaction Rate (net-new), Average Basket Size (Units) (from Planned), Net Sales Growth % (`KPI-MC-11`, reconcile existing), and YTD Net Sales (`KPI-MC-13`, reconcile existing).
- **FR-024**: Each wave KPI MUST be described by required logical concepts and owner policy slots only, and MUST NOT bake in a fiscal-year start, a date column, YoY-vs-prior-period as a universal choice, a discount denominator, a physical table/column, or any worked-example decision.
- **FR-025**: The wave MUST update registry metadata, the knowledge contract, relevant packs, field requirements, aliases, and derivation relationships WITHOUT duplicating any formula (derivation via the spec 044 `derives_from` field).
- **FR-026**: Each wave KPI MUST be independently testable and independently reviewable.
- **FR-027**: The following MUST remain honestly Planned (registry metadata + blockers only, no seeded contract authored here): Same-Store Sales Growth, Inventory Turnover, GMROI, Out-of-Stock Rate, Customer Retention, CLV, Net Sales vs Target, Promotion Uplift.

### Functional Requirements -- Metrics vs slices (US2/US6; D8)

- **FR-031**: A grouping variant MUST become a distinct contract only when its business formula is materially different, proven by an approved `kpi_definition`; the system MUST prevent contract proliferation caused solely by a different grouping dimension.

### Functional Requirements -- Extension protocol and consistency rules (US7; D3, D9)

- **FR-028**: The system MUST define a bounded KPI contribution/extension checklist listing the required artifacts and validations to add a future generic KPI.
- **FR-029**: The system MUST provide at most TWO narrow static consistency rules that detect duplicate IDs, unresolved references, lifecycle drift, aliases treated as new KPIs, broken derivation edges, and product-level leakage of project bindings.
- **FR-030**: The consistency rules MUST validate structure and traceability only; they MUST NOT decide business meaning, populate a status, or grant any readiness (Principle-V "slot present, never grant").

### Functional Requirements -- Provenance and reuse (all stories; D2)

- **FR-032**: The feature MUST reuse the existing Decision Store and decision gate as the ONLY decision store and the ONLY readiness engine; it MUST NOT introduce a second store, a second gate, or a second readiness engine.
- **FR-033**: The feature MUST realize the `kpi_contracts` Knowledge Contract stage's declared `required_outputs` and consume its declared `required_inputs`; it MUST NOT add a new flow stage or a new readiness spine stage.
- **FR-034**: Provenance MUST be traceable end-to-end: generic KPI (or custom definition) -> Decision Store decision IDs -> source/mapping evidence -> project contract -> Gold binding -> downstream handoff.

### Functional Requirements -- Agent-first delivery (D9)

- **FR-035**: The flow MUST be delivered by reusing/extending the existing `retail-kpi-knowledge` routing; it MUST NOT add a broad CLI family, a new KPI CLI command, or a new orchestration engine.
- **FR-036**: The durable output MUST be committed artifacts (registry, answerability, contracts) plus static checks; the agent is the runtime, not a persisted engine.

### Security / PII Requirements

- **SEC-001**: No artifact produced by this feature (registry, answerability, project contract) MAY contain raw PII; a PII-dependent KPI MUST block on an approved PII-handling decision (default drop) before any binding.
- **SEC-002**: No artifact MAY contain a connection string, credential, or DSN; connection details remain parameters per Constitution Principle IX.
- **SEC-003**: Evidence references MUST be repo-relative paths/ids (matching the Decision Store schema), never embedded secret or raw-PII values.

### Key Entities

- **GenericKpiRegistryEntry**: one generic KPI's canonical metadata. *(New.)*
- **GenericKpiKnowledgeContract**: the existing per-KPI prose contract (business question/definition/formula/grain/additivity/unit/required fields/filters/ambiguities/validation/handoff), referenced by the registry. *(Reused; spec 010/044/058.)*
- **ProjectKpiDecision**: an existing Decision Store record of type `kpi_definition` or `policy_ruling` (or another applicable existing type). *(Reused; spec 121.)*
- **KpiAnswerabilityRow**: one KPI's coverage status for a source scope, with blockers, evidence, and next action. *(New.)*
- **ProjectMetricContract**: the F009 contract, extended with additive provenance fields. *(Reused + additive fields; spec 010/087/103.)*
- **KpiPack**: a rollup referencing KPI IDs (never aliases or duplicated formulas), never more ready than its member contracts. *(Reused; spec 010.)*
- **WorkedExample**: an illustration referencing the generic system, never a universal schema or product default. *(Reference only.)*

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every shipped generic KPI (`KPI-MC-01`..`KPI-MC-13`) appears in the registry exactly once with all required metadata fields populated. *(Verify: load the registry; count entries and unique IDs; confirm no field missing.)*
- **SC-002**: Every current cross-file drift instance (three "planned"-vs-Seeded contracts; the "10"-vs-13 seed count; the template-vs-SL1 dash) is either reconciled in the registry or listed as a documented drift item naming the conflicting files. *(Verify: read the drift section; each item names files + resolution.)*
- **SC-003**: An answerability artifact for a given source uses only the five allowed status strings and contains no digit-immediately-followed-by-`%` token and no ranking. *(Verify: SL1-style structural scan.)*
- **SC-004**: A lookalike-only column (e.g. `total_sales` with unresolved meaning) yields `Blocked -- needs business definition`, never `Covered`, in the answerability artifact. *(Verify: fixture run.)*
- **SC-005**: A project contract draft authored without an approved `kpi_definition` is refused, and the refusal names the missing decision. *(Verify: fixture run.)*
- **SC-006**: Every authored project contract carries `generic_kpi_ref` OR `custom: true` (exactly one), structured `decision_refs`, and structured `source_evidence`. *(Verify: structural scan of the contract.)*
- **SC-007**: A contract with no Gold binding is `readiness.status: blocked` and never `pass`; a contract reaches `pass` only with binding + valid decisions + no stale evidence + empty blockers + a named-human approval. *(Verify: fixture matrix, removing one precondition at a time.)*
- **SC-008**: A custom KPI is authored with `custom: true` and no change to the generic registry; a custom KPI without an eligible owner is refused. *(Verify: fixture runs + registry diff = empty.)*
- **SC-009**: Each of the four expansion-wave KPIs has a registry entry and knowledge-contract requirements describing only logical concepts + owner policy slots, with no prohibited baked-in value and no duplicated formula. *(Verify: per-KPI review + no-leak scan.)*
- **SC-010**: At most two static consistency rules exist; each malformed-addition case (duplicate ID, dangling reference, lifecycle mismatch, alias-as-new-KPI, broken derivation edge, product-level binding leakage) produces a structural error, and a well-formed addition passes and grants no readiness. *(Verify: fixture matrix.)*
- **SC-011**: No artifact produced by this feature contains raw PII, a connection string, or a credential. *(Verify: secret/PII scan, reusing the existing C2/SEC posture.)*
- **SC-012**: No worked-example table name, column name, policy, number, client name, or named human appears anywhere in the product-level registry or generic knowledge content. *(Verify: no-leak scan against the enumerated worked-example token list.)*

---

## MVP Boundary and Delivery Slices

**MVP = US1 + US2 + US3** (all P1): one authoritative registry, truthful source-to-KPI answerability, and a governed project-contract draft from approved decisions with structured provenance and honest `blocked` when Gold is absent. This triad is independently valuable and testable without US4-US7.

Later slices: **US4** (Checkpoint B binding + downstream handoff, P2), **US5** (custom KPIs, P2), **US6** (first expansion wave, P3), **US7** (extension protocol + consistency rules, P3).

---

## Non-Goals

This feature MUST NOT:

- Generate or modify DAX.
- Generate SQL or implement any transformation.
- Execute Python or implement dataframe logic.
- Select or implement a Big-data runtime/engine.
- Author a semantic model.
- Design a dashboard.
- Generate PBIR.
- Publish or execute against Power BI.
- Do ML or forecasting.
- Build a universal ERP connector.
- Automatically map source columns or automatically approve a KPI.
- Introduce a second Decision Store.
- Introduce a second readiness/state engine or a new readiness spine stage.
- Add a new broad CLI command family.
- Emit a numeric confidence, KPI coverage percentage, ranking, or health score.
- Treat any worked example as a product default.
- Migrate Seshat from Retail BI into a universal cross-industry KPI product.
- Implement every planned KPI in this feature (only the four D10 wave KPIs get authored coverage; the eight named in FR-027 stay Planned).

---

## Repository Conflicts and Drift Found *(documented, not blocking; resolved or owner-flagged in US1)*

- **Seed-count drift**: `SKILL.md`, `INDEX.md`, and `README.md` say "10 seeded contracts"; 13 contract files exist (`KPI-MC-01`..`KPI-MC-13`).
- **Lifecycle drift**: Net Sales Growth % (`KPI-MC-11`) and YTD Net Sales (`KPI-MC-13`) are Seeded in their contract files but "planned"/"candidate" in README, packs, and `patterns/metric-contract-candidates.json`. Same-Store Sales Growth % (`KPI-MC-12`) is Planned in its contract but carries a different status string (`needs-business-definition`) in the candidates JSON.
- **ID-table drift**: `references/id-conventions.md` lists only `KPI-MC-01`..`KPI-MC-10` as assigned.
- **Lineage-scope drift**: `references/kpi-derivation-lineage.md` is scoped to only MC-01..MC-10; MC-11/12/13 derivation edges are absent from the central map.
- **Dash divergence (cosmetic, not functional)**: the shipped `kpi-coverage-scorecard-template.md` uses em-dash status strings (U+2014), while this spec's ASCII gate requires `--`. Verified in source: SL1 (`src/seshat/rules/scorecard.py:86`) normalizes both em-dash and en-dash to `--` before comparing, so SL1 lints BOTH dash forms correctly -- the divergence is a cosmetic/consistency inconsistency, NOT a functional linter mismatch. This spec authors ASCII `--` throughout; whether to normalize the shipped template's em-dashes to ASCII for consistency is flagged for the owner (spec-only: not edited here).
- **Status-header/checkbox staleness**: repo-wide, spec Status headers and tasks.md checkboxes are known-unreliable; capability truth is `docs/capabilities/capabilities.yaml`.

---

## Assumptions

- The exact registry file format, path, and wire-format (YAML vs JSON, single-file vs per-domain) are plan-time decisions (see plan.md); the spec fixes only that there is exactly one authoritative registry (FR-003).
- The precise additive field names on the F009 contract (`generic_kpi_ref`, `decision_refs`, `source_evidence`, `custom`) are proposed in data-model.md and finalized at plan time; the spec fixes only that provenance is structured and additive (FR-014, FR-021).
- The Business Knowledge Interview (spec 121) is the producer of the `kpi_definition` / `policy_ruling` decisions this feature consumes; it is upstream and out of scope here.
- Spec 122 hands off at `kpi_contracts`; this feature picks up exactly there.
- The Decision Store fail-closed loader, decision gate, approval-authority map, and staleness/supersession detection (spec 121) are reused as-is; this feature adds no decision-store logic.
- Unit/currency behavior is owned by spec 103; multi-currency conflicts are its concern (rule `HR11`), not re-solved here.
- The worked examples (C086 pharmacy; retail_store_sales Kaggle) are references; their specifics never enter product-level content and may only be migrated as fixtures.
- Answerability structure is lintable by the existing SL1 rule (spec 056); this feature does not re-adjudicate coverage truth.
