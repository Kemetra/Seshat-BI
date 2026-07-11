# Data Model: Agent Ecosystem Growth

The feature stores no service-side database state. These entities are versioned local
documents or immutable in-memory models derived from committed repository artifacts.

## 1. Shared Readiness Projection

The single disclosure-safe input to the demo HTML view, review integration, governor,
passport, and explorer.

| Field | Type | Rules |
|-------|------|-------|
| `schema_version` | string | `MAJOR.MINOR`; unknown major fails closed. |
| `workspace` | object | Public label and source revision only; no absolute path. |
| `tables` | ordered array | Stable order by normalized table ID. |
| `generated_at` | timestamp or null | Optional; excluded from deterministic digest. |
| `disclosure` | object | Check status and redaction/block reasons. |

Each table contains `table_id`, seven ordered stage records, `current_stage`,
`next_action`, `forbidden_scope`, evidence references, blockers, approval receipts, and
metric-lineage references when available. It never contains source row values.

### Stage record invariants

- Status is exactly `not_started`, `blocked`, `warning`, or `pass`.
- `pass` requires non-empty evidence.
- `blocked` requires non-empty blocking reasons.
- Stage order is fixed and cannot be supplied by a pack.
- A later stage cannot be presented as actionable while a prior required stage is not
  pass.

## 2. Evidence Reference

| Field | Type | Rules |
|-------|------|-------|
| `artifact_id` | string | Stable within one projection/passport. |
| `kind` | enum | Known artifact category or `other`. |
| `path` | string | Repository-relative POSIX path; cannot escape root. |
| `sha256` | string or null | Lowercase content hash when readable. |
| `verification` | enum | `verified`, `changed`, `missing`, `incompatible`, `unavailable`. |
| `note` | string or null | Disclosure-safe explanation. |

## 3. Approval Receipt

Records an existing human action; never authorizes one.

| Field | Type | Rules |
|-------|------|-------|
| `stage` | stage token | Must name an existing stage. |
| `owner` | string | Existing named-human owner validation applies. |
| `at` | timestamp or null | Passed through from authoritative artifact. |
| `source_artifact` | relative path | Required and included in evidence identity. |
| `valid_shape` | boolean | Structural observation only, not approval judgment. |

## 4. Review Result

Contains `schema_version`, source revision, normalized findings, stage changes, blockers,
next actions, run boundary, and `result_digest`. It has human Markdown and machine JSON
renderings plus optional SARIF. The digest excludes timestamps and ordering noise.

Lifecycle: `inputs_loaded -> checks_complete -> rendered`; malformed authoritative input
terminates as `input_defect`, never pass.

## 5. Agent Governance Request and Response

### Request

Contains `operation`, explicit local `workspace_root`, optional `table_id`, and
operation-specific parameters. The root must resolve to the selected workspace and every
derived read path must remain within it.

### Response

Contains `schema_version`, `operation`, `outcome`, structured content, evidence,
blockers, required authority, next action, forbidden scope, `read_only_proof: true`, and
sanitized errors. Outcomes are `ok`, `blocked`, `input_defect`, or `unavailable`.

No request or response contains an execution command that bypasses the named stop point.

## 6. Readiness Passport

| Field | Type | Rules |
|-------|------|-------|
| `schema_version` | string | Compatibility contract. |
| `passport_id` | string | Digest-derived, not random authority. |
| `source_revision` | string or null | Git revision when available. |
| `scope` | table ID array | One or more explicit tables. |
| `readiness` | projection subset | Status/evidence/blockers only. |
| `artifacts` | evidence array | Canonical relative paths + hashes. |
| `approvals` | receipt array | Existing receipts only. |
| `validation_boundary` | object | Static/live facts and unavailable checks. |
| `generated_at` | timestamp | Informational. |
| `authority_disclaimer` | fixed string | Required no-grant statement. |

Verification derives a separate result and does not rewrite the passport.

## 7. Extension Pack

### Pack manifest

Contains `schema_version`, `pack_id`, `version`, `category`, `owner`, `description`,
`core_compatibility`, `provides`, `requires`, `conflicts`, `artifacts`,
`human_decisions`, `fixtures`, `verification`, and `non_goals`.

`pack_id` uses a reverse-domain-like or owner-qualified lowercase namespace. Every
provided ID becomes `<pack_id>:<local_id>`. Category is one of `kpi`, `source_vocabulary`,
`warehouse_compatibility`, `regional_policy`, `accessibility`, or
`dashboard_blueprint`.

### Selection graph

Nodes are explicitly selected packs; edges are declared requirements. Invalid states:
missing dependency, cycle, explicit conflict, duplicate fully qualified ID, incompatible
core range, stage-order declaration, executable content, or authority escalation.

Packs have no activation lifecycle. A validated selection is an input to one projection;
it is never globally installed or enabled by hidden state.

## 8. Contribution Lane

Contains lane ID, intended contributor, owned files, forbidden files/scope, prerequisites,
acceptance scenarios, verification commands, expected evidence, difficulty label, and
maintainer response expectation. A starter issue instantiates one lane.

## 9. Benchmark Scenario

| Field | Type | Rules |
|-------|------|-------|
| `scenario_id` | string | Stable and globally unique. |
| `title` | string | Human-readable. |
| `principle` | string | One hard stop or declared semantic failure class. |
| `fixture` | relative path | Synthetic data only. |
| `prompt` | string | Disclosed participant input. |
| `expected_behavior` | enum | `proceed`, `refuse`, `block_for_evidence`, `request_human_decision`. |
| `observable_evidence` | array | Conditions for categorical comparison. |
| `vendor_neutral` | boolean | Must be true for accepted scenarios. |

## 10. Benchmark Run

Contains schema version, run ID, participant identity, model/version if applicable,
instructions digest, environment, repetition count, timestamps, per-scenario observations,
expected behavior, comparison result, evidence, and variation notes. There is no aggregate
score, percentage, rank, or winner.

Run states: `declared -> observations_recorded -> rendered`. Missing disclosure leaves the
run `incomplete`; it cannot be published as a comparable result.

## 11. Static Explorer Projection

Extends the shared readiness projection with navigation indexes and disclosure-safe
lineage edges. It contains no HTML. The renderer consumes only this contract and cannot
open arbitrary repository files.

Lineage nodes are source field, warehouse column, metric contract, semantic measure, and
dashboard visual references. An edge records relation kind and evidence path. Missing
lineage remains explicit; it is not inferred.

## 12. Disclosure Result

Contains `status` (`pass` or `blocked`), inspected artifact count, and findings with rule,
relative locator, and safe message. It detects or rejects secrets, DSNs, absolute paths,
raw value arrays, high-cardinality samples, unsafe embedded content, and PII-bearing
fields. A blocked disclosure result prevents the explicit publication step but does not
alter readiness.
