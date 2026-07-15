# Phase 1 Data Model: Decision Change Impact Map

**Feature**: `132-decision-change-impact-map` | **Date**: 2026-07-15

> Describes the projection dict shape (NEW) and the reused input record shapes (REUSE). No shape
> below changes any existing on-disk artifact. Field provenance is tagged: **[reuse]** (read
> verbatim from a shipped authority) or **[new]** (a projection field this feature adds).

## Reused input shapes (read-only — not modified)

### ChangedDecision — the impact-map subject *(reuse; spec 121 Decision Store)*

Read from `decision_store.load_store(...).decisions()`. Relevant fields:

| Field | Source | Use here |
| --- | --- | --- |
| `id` | Decision record | subject identity; supersession-chain node id |
| `decision_type` | Decision record | criticality (via `decision_store.is_critical`) → affects next-action category |
| `status` | Decision record | trigger leg (a): `superseded` (or is the target of another record's `supersedes`) |
| `scope{tables,columns,kpis,artifacts}` | Decision record | resolved via `decision_store.scope_keys(scope)` → `kind:value` keys to join to downstream artifacts |
| `approval.evidence` + `approval.evidence_identity` | Decision record | trigger leg (b): staleness via promoted `_evidence_stale` |
| `supersedes` / `superseded_by` | Decision record | supersession-chain pointers (read-only) |

**Invariant reused**: subject MUST be an *approved* decision (spec Edge Cases); a `proposed`/`pending`
record is reported "not a valid impact-map subject", not "no impact".

### Supersession pointer chain *(reuse; DS4 referential integrity)*

Two scalar string-id fields per record (`supersedes`, `superseded_by`). Presented in pointer order.
A pointer that does not resolve within the combined store id set → `IncompleteLineageWarning`
(kind `dangling_supersession_pointer`). No new history/version structure is created (spec D2/FR-006).

### Lineage edge *(reuse; explorer `_lineage`)*

`{from: node_id, to: node_id, relation: 'binds_to', evidence: <repo-relative path>}` with node ids
`metric:<table>:<name>` and `warehouse:<gold_table>` (explorer vocabulary — the one adopted scheme,
NFR-006). Hops beyond metric→gold follow the `cross-table-lineage` SKILL's hop definitions and
proven/unresolved/gap tiering.

### Affected readiness stage *(reuse; `readiness_projection` + `_FLOW_TO_SPINE`)*

Stage names and statuses are read from `build_readiness_projection(...)` and the flow→spine mapping;
no stage or status word is added (NFR-006 for stages; FR-017). Status vocabulary stays the shipped
four: `not_started | blocked | warning | pass`.

### Next review action *(reuse; `readiness_classify`)*

`classify(reason) -> (category, explanation, next_surface)` and `CATEGORY_RANK` (rank order:
approval > grain > live_validation > artifact > readiness). No category rule is re-derived (FR-018).

### Artifact identity *(reuse; `artifact_identity`)*

`{artifact_id: 'kind:path', kind, path (repo-relative posix), sha256|null, verification}`. The one
identity scheme for every resolved downstream artifact.

## New projection shape

### `ImpactMapProjection` *(new — the single composed dict)*

```text
{
  schema_version: "1.0",                         # [new] contract version
  # The map is SINGLE-SUBJECT: exactly one changed decision per run (loaded by decision_id).
  # `subject` is null iff `blocking_condition` is set (e.g. an invalid/non-approved subject);
  # otherwise `subject.trigger` is present.
  subject: null | {                              # [new] the single changed decision, read-only; null when blocking_condition is set
    decision_id: str,                            # [reuse] ChangedDecision.id
    decision_type: str,                          # [reuse]
    trigger: "superseded" | "evidence_stale"      # [new] which mode fired: committed legs (a)/(b) may
            | ["superseded","evidence_stale"]     #   fire together (list); OR the explicit
            | "preview",                          #   "preview" mode (c) — FR-003; present iff blocking_condition is null
    is_preview: bool,                            # [new] true iff trigger == "preview" (run against a not-yet-superseded, non-stale approved decision — FR-004)
    critical: bool                               # [reuse] via decision_store.is_critical
  },
  supersession_chain: [                          # [new view over reuse pointers], in pointer order
    { decision_id: str, relation: "supersedes"|"superseded_by", resolved: bool }
  ],
  affected: [                                    # [new] resolvable downstream artifacts, sorted (direct-first, artifact_id)
    {
      artifact_id: "kind:path",                  # [reuse] artifact_identity
      kind: str,                                 # [reuse] e.g. metric_contract | warehouse_table | dashboard_binding | readiness_evidence
      relation: "direct" | "transitive",         # [new] FR-009
      evidence_paths: [str, ...],                # [new] ordered repo-relative edge evidence chain (FR-008); one entry for direct, the full hop chain for transitive
      affected_stages: [str, ...],               # [reuse] stage names from readiness_projection + _FLOW_TO_SPINE (FR-017)
      next_actions: [                            # [reuse] readiness_classify outputs (FR-018)
        { category: str, explanation: str, next_surface: str }
      ]
    }
  ],
  incomplete_lineage: [                          # [new] FR-012/013/016; DISJOINT from affected[]; sorted (kind, locator)
    {
      kind: "unresolved_scope_tag"
          | "unfollowable_edge"
          | "dangling_supersession_pointer"
          | "missing_cited_evidence",
      locator: str,                              # the unresolved scope key / edge / pointer id / evidence path
      detail: str                                # why it could not resolve (no inferred substitute)
    }
  ],
  cycles: [                                       # [new] FR-014; named cycle conditions, sorted
    { nodes: [node_id, ...], detail: str }
  ],
  blocking_condition: null | {                    # [new] US4 fail-closed; set when the run cannot produce a truthful subject map. When non-null, `subject` is null and no `affected[]` is claimed.
    kind: "invalid_subject"                       #   subject is not an approved decision (proposed/pending/absent) — FR-003 approved-only
        | "absent_store"|"malformed_store"|"active_scope_conflict"|"unreadable_lineage_input",
    detail: str
  },
  generated_at: str                              # [new] EXCLUDED from any content digest (NFR-001)
}
```

### Field-level invariants (contract)

- **INV-1 (disjoint sets)**: an `affected[]` entry and an `incomplete_lineage[]` entry never describe
  the same reference; every reference resolves to exactly one of the two (FR-015).
- **INV-2 (direct dominates)**: an artifact reachable both directly and transitively appears once,
  `relation:"direct"`, with the transitive path(s) also recorded in `evidence_paths` (spec Edge Cases).
- **INV-3 (evidence-backed)**: every `affected[]` entry has a non-empty `evidence_paths` (FR-008).
- **INV-4 (no score)**: no key named `score`/`confidence`/`risk`/`risk_score`/`trust`/`completeness`/
  `blast_radius`/`weight` and no string value containing a digit-immediately-followed-by-`%` appears
  anywhere in the dict (FR-023, SC-005).
- **INV-5 (fail-closed)**: when `blocking_condition` is non-null, `affected` is NOT reported as an
  empty "no impact"; the condition is named and the write is refused where appropriate (FR-019, SC-008).
- **INV-6 (deterministic)**: for identical committed inputs, the dict is byte-identical modulo
  `generated_at` (NFR-001, SC-010).
- **INV-7 (disclosure-safe)**: the dict passes `disclosure.scan_disclosure` before any write; a
  finding blocks (NFR-003, SC-011). Only repo-relative posix paths / identities appear (SEC-003).

### Human-readable rendering

A deterministic textual/markdown rendering of the identical dict content (subject, supersession
chain, direct then transitive affected artifacts with evidence paths + affected stages + next
actions, incomplete-lineage warnings, cycles, blocking condition). No content present in one form is
absent from the other (SC-009). Rendering follows the `explorer` render pattern (pure templating over
the dict; HTML-escaped if HTML; no arbitrary file reads).

## Provenance summary

| Entity | Disposition | Authority |
| --- | --- | --- |
| ChangedDecision | reuse | `decision_store` |
| Supersession chain (pointers) | reuse pointers / new view | `decision_store` + DS4 |
| Staleness trigger | reuse | promoted `decision_gate._evidence_stale` + `artifact_identity` |
| Lineage edge / node ids | reuse | `explorer._lineage` + `cross-table-lineage` SKILL tiering |
| Affected stage | reuse | `readiness_projection` + `decision_gate._FLOW_TO_SPINE` |
| Next action | reuse | `readiness_classify` |
| Artifact identity | reuse | `artifact_identity` |
| Disclosure / contained write | reuse | `disclosure.scan_disclosure` + `cli.guards.resolve_local_output` |
| **decision→artifact join + `ImpactMapProjection` dict + incomplete-lineage + cycles** | **new** | `src/seshat/impact_map.py` |
