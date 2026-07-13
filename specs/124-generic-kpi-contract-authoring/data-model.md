# Phase 1 Data Model: Generic KPI Knowledge Registry and Governed Project Metric-Contract Authoring

**Feature**: `124-generic-kpi-contract-authoring`

**Date**: 2026-07-13

This data model defines only the NEW shapes (the generic KPI registry entry and the answerability row) and the ADDITIVE fields layered onto already-shipped shapes (the F009 project metric-contract). Reused shapes -- the Decision Store record, the knowledge contract, the metric-contract base, the KPI pack -- are referenced by their owning spec and NOT restated. Concrete field names marked *(proposed)* are finalized at plan time (plan.md D-decisions); the spec fixes the behavior, not the byte.

## Status vocabularies (four distinct axes -- do NOT conflate)

This feature touches four separate status vocabularies. They are kept distinct on purpose; the `warning` (contract) vs `warn` (gate) spelling difference is real and preserved.

| Axis | Values | Owner / where defined | Used by |
| --- | --- | --- | --- |
| Answerability coverage (5) | `Covered`, `Blocked -- missing field`, `Blocked -- needs business definition`, `Planned`, `Out of scope` | `kpi-coverage-scorecard-template.md`; lintable by SL1 (spec 056) | KpiAnswerabilityRow (NEW) |
| Contract readiness (4) | `not_started`, `blocked`, `warning`, `pass` | `docs/readiness/readiness-model.md`; `templates/metric-contract.yaml` `readiness.status` | ProjectMetricContract (reused) |
| Decision lifecycle (9) | `proposed`, `approved`, `rejected`, `pending`, `needs_user_input`, `needs_sample`, `blocked`, `deferred`, `superseded` | `src/seshat/decision_store.py` `STATUS_VALUES` | ProjectKpiDecision (reused) |
| Gate verdict (3) | `pass`, `warn`, `blocked` | `src/seshat/decision_gate.py` `VERDICTS` | consumed, not authored here |

Note: the gate maps its `warn` to the contract's `warning` via the existing `project_to_spine()`; this feature adds no new mapping.

Registry lifecycle values (a fifth, entry-level axis distinct from the above): `seeded`, `planned` (matching the existing knowledge-contract Status semantics). Answerability derives `Planned` directly from a `planned` registry lifecycle.

---

## Entity: GenericKpiRegistryEntry (NEW -- US1)

**Owner of**: generic KPI identity + canonical metadata. This is the single authoritative inventory (FR-003); every other projection (INDEX, README, packs, candidates, source-field-requirements, derivation-lineage) becomes a consumer/view, not a source of truth.

**Location**: one product-level registry artifact under `skills/retail-kpi-knowledge/` (exact filename + wire-format = plan-time decision D1 in plan.md; the narrowest repo-consistent path). This feature's spec package defines the schema and one illustrative entry in `contracts/`; the populated product artifact is authored by a US1 task, not by this spec package.

**Format**: machine-readable (YAML or JSON per plan D1), a list of entries.

```yaml
# One GenericKpiRegistryEntry (illustrative; canonical schema in contracts/generic-kpi-registry.schema.md)
id: KPI-MC-01                 # stable, preserved; matches the knowledge-contract ID
slug: gross-sales             # stable machine slug (kebab-case); distinct from filename
canonical_name: "Gross Sales" # the one display name
aliases: []                   # alternate names; an alias NEVER creates a second entry
domain: sales-and-revenue     # one domain id from the domains catalog
metric_kind: base_metric      # base_metric | derived_metric | ratio | time_transform | snapshot | quality_metric | analytical_slice
lifecycle: seeded             # seeded | planned
knowledge_contract_ref: skills/retail-kpi-knowledge/contracts/gross-sales.md  # resolvable path
derives_from: []              # list of KPI-MC-NN ids (projected from spec 044 derives_from; NEVER a second graph)
required_concepts:            # LOGICAL concepts only -- never physical columns
  - sales_amount
required_decision_types:      # Decision Store decision types that MUST be approved to author a project contract
  - kpi_definition
  - policy_ruling             # only where a VAT/returns/discount/cost policy applies to this KPI
source_roles:                 # logical fact/source roles this KPI reads from (multi-fact KPIs list >1)
  - sales_fact
```

**Validation (FR / rule)**:
- Every `KPI-MC-NN` present exactly once; `id`, `slug`, `canonical_name` each unique across the registry (FR-005; US7 consistency rule).
- `metric_kind` in the closed 7-value set (FR-006).
- `lifecycle` in `{seeded, planned}`.
- `knowledge_contract_ref` resolves to a committed tracked file (US7 unresolved-reference rule).
- Each `derives_from` id resolves to another registry entry (US7 broken-edge rule).
- No physical table/column, client name, or worked-example token anywhere in the entry (FR-040; US7 leakage rule; SC-012).
- `required_concepts` are logical (no physical column names).

**State/lifecycle**: `seeded` (a knowledge contract exists and its meaning is owner-ruled) or `planned` (metadata + blockers recorded, no seeded contract). A registry entry advances no readiness stage and carries no numeric score.

---

## Entity: GenericKpiKnowledgeContract (REUSED -- US1/US6; spec 010/044/058)

**Owner of**: the rich business PROSE for one generic KPI. This is the existing per-KPI knowledge contract at `skills/retail-kpi-knowledge/contracts/<slug>.md` (13 files, `KPI-MC-01`..`KPI-MC-13`). The registry INDEXES it (via `knowledge_contract_ref`); it is NOT restated in the registry, and the registry never duplicates its prose or formula.

**Location**: `skills/retail-kpi-knowledge/contracts/<slug>.md`. **Format**: Markdown with labelled sections.

Existing section shape (reused as-is; the expansion wave US6 authors two NEW files in this shape):

| Section | Notes |
| --- | --- |
| `ID:` | the stable `KPI-MC-NN` (matches the registry `id`) |
| Business question | what the KPI answers |
| Business definition | the meaning (owner-ruled) |
| Formula in business terms | NOT DAX/SQL; business prose only |
| Derives from | parent `KPI-MC-NN` ids (spec 044); the registry's `derives_from` projects this, never a second graph |
| Required fields / concepts | logical concepts with confidence tags (`confirmed concept` / `assumption` / `derived`) |
| Grain / Additivity | stated as concepts (semi-additive snapshots flagged) |
| Filters / exclusions, Interpretation, Common mistakes | prose |
| Validation checks | expectations, not executable checks |
| Implementation handoff notes (SQL / DAX / Python) | handoff INTENT only |
| Priority / Owner / Status | free-text lifecycle (the registry `lifecycle` is the machine-readable source of truth) |

**Validation (FR / rule)**:
- The `ID:` matches its registry entry `id` (US7 unresolved-reference rule).
- Contains NO physical project binding (gold table/column), NO client token, NO worked-example value (FR-040, SC-012).
- A wave KPI (US6) describes required logical concepts + owner policy slots only; it bakes in no fiscal-year start, date column, YoY-vs-prior-period choice, discount denominator, or physical table/column (FR-024).

**State/lifecycle**: `Seeded` or `Planned` in the contract's free-text `Status`; the registry's `lifecycle` field is the authoritative machine value that answerability reads.

---

## Entity: KpiAnswerabilityRow (NEW -- US2)

**Owner of**: the per-source coverage verdict for one KPI. One row per (source scope x KPI request). The collection of rows for a source is an answerability artifact whose STRUCTURE is lintable by SL1 (spec 056); SL1 does not decide its truth.

**Location**: a per-table / per-subject-area answerability artifact under the project workspace (path pattern = plan D2; consistent with the coverage-scorecard placement).

**Format**: rows in the coverage-scorecard shape (Markdown table or YAML per plan D2).

| Field | Type | Notes |
| --- | --- | --- |
| `scope` | string | project/source scope (table or subject area); no physical value leakage |
| `kpi` | string | `generic_kpi_ref` (a `KPI-MC-NN`) OR a custom request label |
| `status` | enum(5) | exactly one of the five coverage statuses (ASCII `--`) |
| `blockers` | list | named blockers; non-empty and non-`--` when `status` begins `Blocked` |
| `evidence` | list | repo-relative references to source-profile / source-map evidence |
| `next_action` | string | the next allowed action (e.g. "request kpi_definition approval") |

**Validation (FR / rule)**:
- `status` in the closed 5-value set (FR-007; SL1 rule 1).
- A `Blocked -- ...` row names a blocker (FR-042; SL1 rule 2).
- No digit-immediately-followed-by-`%`, no ranking, no score (FR-008; SL1 rule 4; SC-003).
- `Covered` requires present + fresh evidence and a resolved governing policy; a lookalike-only column or unresolved policy -> `Blocked -- needs business definition` (FR-009); missing/stale evidence -> fail closed, never `Covered` (FR-041).
- A multi-fact KPI names every required `source_role` and blocks on any absent one (FR-042).

**State/lifecycle**: derived, not stored as truth. `Covered` grants NO readiness -- it means only "eligible to begin a Checkpoint-A draft." `Planned` mirrors the registry lifecycle; `Out of scope` marks a KPI whose domain the source cannot serve.

---

## Entity: ProjectKpiDecision (REUSED -- US3/US4/US5; spec 121)

**Owner of**: the approved business meaning and policy. This is an existing Decision Store record; this feature CONSUMES it and adds nothing to the decision schema.

Reference (not restated): `specs/121-business-knowledge-interview/contracts/decision-record.schema.json` and `src/seshat/decision_store.py`.

- `decision_type`: for this feature, `kpi_definition` (KPI meaning) and `policy_ruling` (VAT/returns/discount/cost); `missing_value_rule`, `pii_handling`, `data_exclusion` where a KPI depends on them.
- `status`: the 9-value lifecycle; only `approved` (with a valid `approval` block) authorizes a draft; `superseded`/stale block `pass` (FR-018).
- `approval`: the six required fields (`approved_by` as `Name (authority_class)`, `approved_at`, `source`, `evidence`, `evidence_identity`, `reviewed_scope`); authority for `kpi_definition`/`policy_ruling` is `metric_owner` (`contracts/knowledge/approval-authority.yaml`). No self-grant.
- staleness/supersession: computed by the existing gate via `evidence_identity` sha256 comparison and active-scope-conflict detection.

**This feature adds NO field to this entity.** It only references decision `id`s from the project contract (see below).

---

## Entity: ProjectMetricContract (REUSED + ADDITIVE fields -- US3/US4/US5; spec 010/087/103/058)

**Owner of**: the project-specific, governed metric definition and its readiness. This is the existing F009 contract at `mappings/<table>/metrics/<MetricName>.yaml`. This feature adds ONLY additive, optional fields; it does not re-define the base contract or change any existing field.

Existing base fields (reused as-is, NOT restated here): `name`, `grain`, `formula_intent`, `owner`, `binds_to` (`gold_table`, `columns`, `pii_sensitive`), `time_additivity`, `unit` (spec 103), `readiness` (`status`/`evidence`/`blocking_reasons`), `ambiguities[]` (spec 058), `direction_of_good`/`thresholds`/`action_on_breach` (spec 087), `definition` (F-DAXGEN).

Additive provenance fields *(proposed; finalized at plan D3)*:

```yaml
# ADDITIVE block on templates/metric-contract.yaml (all optional -> backward compatible)
generic_kpi_ref: KPI-MC-01     # present iff this realizes a known generic KPI; else omitted
custom: false                  # true iff this is a custom KPI with no generic entry (US5)
decision_refs:                 # structured links to the approved decisions that authorize this contract
  - kpi_definition.gross_sales # a Decision Store record id
  - policy_ruling.vat_treatment
source_evidence:               # structured links to the committed source/mapping evidence justifying the binding
  - mappings/<table>/source-map.yaml#<entry>
```

**Validation (FR / rule)**:
- Exactly one of `generic_kpi_ref` (resolves to a registry entry) or `custom: true` (FR-011, FR-021; SC-006).
- `decision_refs` and `source_evidence` present and structured (FR-014; SC-006).
- Draft requires an approved `kpi_definition` + applicable `policy_ruling` (FR-013).
- No Gold binding -> `readiness.status: blocked`, reason `physical gold binding is not materialized` (FR-016; SC-007).
- `pass` only with gold-only binding + valid non-superseded decisions + no stale evidence + empty blockers + named-human approval (FR-017, FR-044; SC-007).
- No DAX/SQL/visual/connection string/raw PII/unbacked gold path (FR-015; SEC-001/002/003).

**State/lifecycle**: the existing 4-value contract readiness (`not_started` -> `blocked`/`warning` -> `pass`). Checkpoint A produces a `blocked` (Gold absent) or `warning` draft; Checkpoint B may reach `pass`. This feature introduces NO new status word.

**Additive-field -> committed-artifact map** (what each new field points at; the contract stores references, not recomputed truth):

| New field | Points at | Read to verify |
| --- | --- | --- |
| `generic_kpi_ref` | GenericKpiRegistryEntry `id` | registry resolves; alias never used here |
| `custom` | (self) | mutually exclusive with `generic_kpi_ref` |
| `decision_refs` | Decision Store record `id`s | approved + not superseded + not stale (existing gate) |
| `source_evidence` | source-map / source-profile refs | evidence identity fresh (existing sha256 check) |

---

## Entity: KpiPack (REUSED -- US6; spec 010)

**Owner of**: a named rollup of KPIs. Reference: spec 010 pack shape; path pattern `metrics/packs/<pack_name>.yaml` (none exist yet).

- References member KPIs by `KPI-MC-NN` id ONLY -- never by alias, never by duplicated formula (FR-025).
- A pack's readiness is never greater than the least-ready member contract (rollup cannot outrank its members).
- This feature adds no field; the expansion wave (US6) only updates membership.

---

## Entity: WorkedExample (REFERENCE ONLY -- boundary; Constitution Principle VII)

**Owner of**: nothing product-level. A worked example (C086 pharmacy; retail_store_sales Kaggle) is an illustration that the generic system produced; it is NEVER a universal schema or a source of product defaults.

- Its physical table/column names (`gold.fct_sales_rss`, `total_spent`, ...), policies (Q1-Q4 rulings), numbers (12,575 transactions; 50.37% discount rate), client names, and named humans (e.g. the real `Ahmed Shaaban (data_owner / metric_owner)` in `readiness-status.yaml`) MUST NOT enter the registry or any generic content (SC-012; FR-040).
- It MAY be migrated as a fixture carrying the new additive provenance fields, purely to demonstrate the pattern -- but its values still never become product defaults (migration posture, plan.md).

---

## Shipped entities reused (referenced, not redefined)

- `templates/metric-contract.yaml` -- base F009 contract (spec 010; + spec 058 ambiguities; + spec 087 decision-aid; + spec 103 unit; + spec 044 derives_from).
- `specs/121-business-knowledge-interview/contracts/decision-record.schema.json` -- Decision Store record.
- `specs/121-business-knowledge-interview/contracts/knowledge-contract.schema.json` -- the `kpi_contracts` flow-stage contract.
- `contracts/knowledge/database-to-pbip-flow.yaml` -- the declared `kpi_contracts` stage.
- `contracts/knowledge/approval-authority.yaml` -- decision-type -> authority-class map.
- `skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md` -- the five coverage statuses (SL1-lintable).
- `docs/readiness/readiness-model.md` -- the 4-value contract readiness state machine.
