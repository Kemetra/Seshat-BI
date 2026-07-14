# Phase 1 Data Model: Portfolio Watch

Read-only. No database. No new gate. All shapes are LOCAL artifacts or in-memory
composition results. No numeric health/confidence/priority/quality score anywhere
(FR-020, hard rule #9). Shapes below are logical contracts; the concrete
serialization (field casing, file split) is a tasks-level detail.

---

## Entities

### 1. Governed Scope (reused -- no new unit)

The existing per-table/per-report unit the readiness spine + committed
readiness-status paths already track (FR-002). Identified by its committed
readiness-status source path -- exactly as `status_surface` / `readiness_projection`
identify a table today.

| Field | Meaning | Source |
|---|---|---|
| `scope_id` | the table/report id (e.g. `bronze.orders`) | `readiness_projection` `table_id` |
| `source_path` | committed readiness-status path | `readiness_projection` `source_path` |
| `current_stage` | one of the seven spine stages | `readiness_projection` `current_stage` |

No scope unit is invented; Watch enumerates from the committed readiness paths (research D6).

### 2. Covered Dimension Finding (reused surface output, joined)

One per (scope, dimension). Each is SOURCED from one shipped surface (research D5)
and never re-derived (FR-003).

| Field | Meaning |
|---|---|
| `dimension` | `source_drift` \| `contract_metric_drift` \| `dashboard_intent_divergence` \| `readiness` \| `approvals` \| `review` |
| `state` | the truthful availability state (see Degradation State set below) |
| `class` | the shipped categorical class for the finding when `state=covered` (e.g. a drift class, a `semantic_audit` enum value, a readiness status) -- never a score |
| `measured` | optional measured magnitude already committed as evidence (e.g. "missing 3.1% -> 11.7%", "1 orphan") -- a MEASUREMENT, allowed; a rolled-up score, forbidden |
| `evidence` | committed source path (+ row/line where applicable) -- required when `state=covered` (FR-004) |
| `owner` | responsible owner when the finding is a relayed named-human seam (FR-006) |
| `source_surface` | the shipped module/skill the finding came from (citation) |

### 3. Portfolio Watch Summary (NEW artifact)

The one read-only, local, machine-readable + human-readable record spanning all
governed scopes.

```text
schema_version: <string>               # so a future reader can mark an old summary unreadable
generated_at_revision: <git HEAD sha>  # the current source_revision (for staleness compare)
scopes:
  - scope_id, source_path, current_stage
    dimensions: [ Covered Dimension Finding, ... ]   # one per covered dimension
    open_blockers: [ <string>, ... ]                 # relayed from readiness blocking_reasons
    requires_human_attention: <bool>                 # FR-006: unmet approval or relayed Principle-V drift
    prioritized_next_action:
      category: approval|grain|live_validation|artifact|readiness   # from readiness_classify rank (D4)
      action: <string>                               # RELAYED next_action; never synthesized
    change_labels: [ Condition Change, ... ]         # from the diff against the snapshot (entity 5)
portfolio:
  scope_count, scopes_requiring_attention_count      # measured counts (allowed), never a score
  scopes_with_no_evidence: [ scope_id, ... ]         # partial-portfolio honesty (FR-017)
disclosure: { status, findings }                     # reuse the shipped disclosure scan shape
```

Invariant: no field is a numeric health/confidence/priority score (FR-020). Counts are
measured facts, not scores.

### 4. Prior-Run Snapshot / Baseline (NEW entity)

The local artifact each run writes so the next run can diff (FR-007). Modeled on
`drift.py`'s baseline (research D3).

```text
schema_version: <string>
captured_at_revision: <git HEAD sha at capture>
conditions: [ Condition Key, ... ]     # the stable keys present this run (magnitude-free)
```

Local only (research D2). Carries no secret/DSN (SEC-002) and no fabricated data (SEC-003).

### 5. Condition Key + Condition Change (NEW; deterministic)

**Condition Key** -- a stable, magnitude-free tuple that identifies a standing
condition so a magnitude wiggle does not churn as new/resolved:

```text
(scope_id, dimension, class, subject_locator)
# e.g. (bronze.orders, source_drift, column_removed, order_note)
```

**Condition Change** -- the label from diffing the current keys against the snapshot keys:

| Label | Rule |
|---|---|
| `new` | key present now, absent in snapshot (only when a usable snapshot exists) |
| `resolved` | key absent now, present in snapshot |
| `unchanged` | key present in both (magnitude may differ -- reported once, not re-alerted) |
| `current_condition_no_baseline` | first run OR unreadable snapshot -- explicitly NOT `new` (FR-009) |

Determinism: a sorted set-diff over stable keys -> identical inputs + snapshot yield
identical labels (FR-012, SC-006).

### 6. Scope-Set Change (NEW; from the same diff)

A scope present in one run's snapshot but not the other is reported as a scope-level
change (`scope_added` / `scope_removed`), NOT misattributed to condition changes inside a
missing scope (FR-011).

---

## Degradation State set (the closed, truthful set)

| State | When | Rule |
|---|---|---|
| `covered` | evidence read cleanly | must carry a citation (FR-004); may carry `class` + `measured` |
| `[PENDING LIVE]` | the dimension's evidence needs a live re-profile/DB leg and none is configured | never a fabricated comparison (FR-013); per `source-drift.md` |
| `stale` | evidence captured at a revision older than current HEAD/source_revision | cite captured-at vs current; not shown as a current condition (FR-014) |
| `not_applicable_with_reason` | no shipped producer for the scope, or no evidence produced yet | name the reason; not counted covered/clean (FR-015) |
| `unreadable` | evidence declares a schema version this feature cannot parse | name the unknown version; excluded from any pass/clean claim; never guessed (FR-016) |

No state is ever silently upgraded to `covered`. A per-scope read error degrades that
dimension to `unreadable`, never a fabricated pass (FR-022).

---

## Dimension -> shipped source map (verified against `main`)

| Dimension | Shipped source | Live leg -> state |
|---|---|---|
| `source_drift` | `drift.py`, `drift_semantics.py` (committed source-drift findings) | re-profile needs DSN -> `[PENDING LIVE]` |
| `contract_metric_drift` | `metric_drift.py` verdicts over committed contracts + TMDL | static compare (no DB); ESCALATE relayed |
| `dashboard_intent_divergence` | `semantic_audit.py`, `report_intent.py`, `rules/report_intent.py` | committed only (no DB) |
| `readiness` | `readiness_projection.py`, `readiness_classify.py` | committed only (no DB) |
| `approvals` | `approval_inbox.py` | committed only (no DB) |
| `review` | `review_integration.py`, `review_pack_export.py` | committed only (no DB) |
| scope enumeration | committed readiness-status paths (NOT `portfolio_enumerate` live path) | no DB (research D6) |

---

## What Watch NEVER does (structural, not prose)

- Never opens a DB connection in the MVP (SEC-001) -- no `Dialect`/DSN import on its path.
- Never writes a per-scope artifact, records an approval, or moves a stage to `pass`
  (SC-008) -- the only writes are the summary + the local snapshot under `.seshat/watch/`.
- Never emits a numeric health/confidence/priority/quality score (FR-020) -- statuses,
  shipped categorical enums, and measured magnitudes only.
- Never originates a Principle-V ruling (FR-021) -- relays grain/returns/PII/approval
  conditions with a named owner and decides none.
- Never re-derives a shipped surface's own check (FR-003) -- it joins their outputs.
