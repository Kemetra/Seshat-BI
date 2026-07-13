# Research: Generic KPI Knowledge Registry and Governed Project Metric-Contract Authoring

**Feature**: `124-generic-kpi-contract-authoring`

**Date**: 2026-07-13

This research establishes the no-duplicate boundary and records the plan-time decisions the spec deferred. Every claim is anchored to a committed path. The governing rule: **add only what is genuinely absent; reuse everything already shipped.**

## R1. No-duplicate / reuse matrix (required coverage)

| Existing capability | Reuse as-is | Exact remaining gap | Change allowed |
| --- | --- | --- | --- |
| **Retail KPI Knowledge** (`skills/retail-kpi-knowledge/`: 13 knowledge contracts `KPI-MC-01..13`, domains, packs, candidates, references) | YES -- prose meaning, additivity, grain, required concepts, ambiguity codes stay here | No single machine-readable inventory; identity/lifecycle/kind/aliases/required-decisions are inferred or scattered and have DRIFTED (10-vs-13, 3 seeded-vs-"planned") | ADD one registry that indexes them (US1); DOCUMENT/RECONCILE drift. No prose rewrite. |
| **F009 metric-contract store + template** (`templates/metric-contract.yaml`, `docs/metrics/metric-contract-store.md`, spec 010) | YES -- base contract is the authoring target; store rules unchanged | No structured `generic_kpi_ref`, `custom`, `decision_refs`, `source_evidence` fields | ADD four optional additive fields (US3/US4/US5). No base re-definition. |
| **Business Knowledge Interview** (spec 121, `.claude/skills/business-knowledge-interview/`) | YES -- it PRODUCES the `kpi_definition`/`policy_ruling` decisions this feature consumes | none for this feature (it is upstream) | none -- out of scope; consume only. |
| **Decision Store** (`src/seshat/decision_store.py`: `kpi_definition`+`policy_ruling` types, 9-status lifecycle, approval-authority, staleness/supersession) | YES -- the ONLY decision store | none -- it already has the types, statuses, approval, staleness this feature needs | none -- reference decision `id`s from the contract; add no store logic (FR-032). |
| **`kpi_contracts` stage Knowledge Contract** (`contracts/knowledge/database-to-pbip-flow.yaml`, spec 121 stage enum) | YES -- the stage is already declared (inputs = approved `kpi_definition`+`policy_ruling`; gate = `[kpi_definition, policy_ruling, missing_value_rule]`; handoff = `silver_gold_model_planning`) | The stage declares outputs but nothing PRODUCES them yet | PRODUCE the stage's `required_outputs` (US3). Add NO new stage; maps to `semantic_model_ready` via existing `_FLOW_TO_SPINE`. |
| **KPI Coverage Scorecard** (`references/kpi-coverage-scorecard-template.md`, 5 statuses) | YES -- the five statuses verbatim | No per-source answerability that binds those statuses to committed evidence + decisions with a fail-closed rule | ADD the answerability artifact (US2) in the scorecard shape. |
| **SL1 scorecard linter** (spec 056, rule `SL1`, structure-only) | YES -- lints answerability structure (status enum, blocker presence, contract-path resolves, no `%`) | none -- SL1 already covers the structural checks | none -- SL1 stays structural; this feature adds at most two NEW narrow rules for the registry/provenance (US7), not a change to SL1. |
| **Semantic / DAX handoff** (spec 010 handoff notes; `semantic_model_dax` stage consumes contracts) | YES -- handoff notes are prose only; DAX is downstream | none | none -- this feature writes handoff intent, never DAX/SQL (Non-Goals). |
| **Worked examples** (`mappings/retail_store_sales/metrics/`, `docs/worked-examples/`) | REFERENCE only | Legacy project contracts lack the new provenance fields | MAY migrate as fixtures (additive fields), never as product defaults (SC-012). |

Supporting reuse (also cited, not rebuilt): spec 044 `derives_from` (lineage), spec 058 `ambiguities[]` (A1-A11 ledger), spec 087 `direction_of_good`/bands/action, spec 103 `unit`/`HR11` (currency/units).

## R2. Where this feature plugs into the flow (boundary confirmation)

- It IS the `kpi_contracts` flow stage. It is spec 121's Future Slice #2 ("KPI contract production at flow scale") and the direct downstream of spec 122's declared `kpi_contracts` handoff (122 explicitly "stops before KPI contract authoring").
- It consumes approved `kpi_definition`/`policy_ruling` decisions (produced by the interview) and produces governed metric contracts (010 template). It stops before `silver_gold_model_planning` and `semantic_model_dax`.

## R3. Decision D1 -- registry format and path (spec deferred this)

**Decision**: ONE machine-readable registry file under `skills/retail-kpi-knowledge/`, adjacent to the knowledge it indexes, in the repo-consistent format used by the existing patterns files (`patterns/*.json`) OR a single YAML (the packs/domains idiom). **Recommendation: a single YAML** (e.g. `skills/retail-kpi-knowledge/registry.yaml`) -- YAML matches the pack/domain/contract idiom the skill already uses, stays human-diffable, and is trivially loadable by a stdlib static rule. Rationale: narrowest repo-consistent path; one file = one source of truth (FR-003); avoids a JSON/YAML split with the existing `metric-contract-candidates.json`.

**Not chosen**: (a) extending `INDEX.md` (prose, not machine-readable -> fails FR-003 "machine-readable"); (b) a new top-level `docs/` inventory (splits truth from the skill it indexes); (c) per-domain registry files (multiplies sources of truth, complicates the uniqueness invariant).

## R4. Decision D2 -- answerability artifact path/shape

**Decision**: per-table/per-subject-area answerability in the coverage-scorecard shape, at the project-workspace scorecard location the scorecard template already implies (a filled scorecard under the mapping/subject-area working set). Shape = the scorecard's status table so SL1 applies unchanged. No new location convention is invented.

## R5. Decision D3 -- provenance field names + additivity

**Decision**: four OPTIONAL additive fields on the F009 contract: `generic_kpi_ref` (registry id), `custom` (bool), `decision_refs` (list of Decision Store ids), `source_evidence` (list of repo-relative refs). All optional -> legacy contracts remain valid (migration posture). Rationale: additive is the smallest backward-compatible change (Section 10 requirement); it wires the two ends of each currently-prose-only provenance link without a schema rewrite or a second contract format.

## R6. Decision D4 -- the (at most two) static consistency rules

**Decision**: at most two NEW `retail check` rules (agent-first; no CLI family), following the SL1/PP1 pattern (stdlib-only, static, `Severity.ERROR`, `tests/` fixtures excluded):
- **Rule A -- registry consistency**: duplicate `id`/`slug`/`canonical_name`; an alias equal to a canonical name; a `derives_from`/`knowledge_contract_ref` that does not resolve; a lifecycle value outside `{seeded, planned}`; a physical binding or client token in the product-level registry (leakage).
- **Rule B -- provenance/traceability**: a project contract with neither `generic_kpi_ref` nor `custom: true` (or both); a `generic_kpi_ref` that does not resolve to a registry entry; a `decision_refs`/`source_evidence` that is malformed (not that a decision is *approved* -- that is the existing gate's job, not a structural rule).

Both validate STRUCTURE and TRACEABILITY only; neither decides business meaning or grants readiness (FR-030). If one rule can cover both cleanly at plan time, ship one; the cap is two.

## R7. Faithful D10 status (ground-truth correction)

Research found the four wave KPIs are NOT uniform:
- **Discounted Transaction Rate** -- absent from the generic library entirely (net-new generic contract). NOTE: a *project* `DiscountedTransactionRate.yaml` exists in the retail_store_sales worked example; that is project-specific (`gold.fct_sales_rss`, 50.37%, Q2 blanks-excluded denominator) and MUST NOT seed the generic contract, whose denominator is an owner policy slot.
- **Average Basket Size (Units)** -- Planned, no contract, not even a candidate (new generic contract).
- **Net Sales Growth %** (`KPI-MC-11`) -- Seeded contract already exists; wave work = registry drift reconciliation.
- **YTD Net Sales** (`KPI-MC-13`) -- Seeded contract already exists; wave work = registry drift reconciliation.

This is faithful to D10 ("keep X honestly Planned"; describe concepts + policy slots, bake in nothing), not a contradiction of it.

## R8. Open items requiring human judgment (Principle V seams)

None block the spec. The following are approval seams the flow surfaces, not decisions the agent makes:
- Any `kpi_definition` / `policy_ruling` approval (authority: `metric_owner`).
- Any PII-handling ruling for a customer/identity KPI (authority: `data_owner`/`governance`).
- Checkpoint-B `pass` (named-human approval; no self-grant).
