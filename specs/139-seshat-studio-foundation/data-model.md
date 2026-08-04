# Data Model: Seshat Studio Foundation

**Feature**: 139-seshat-studio-foundation | **Date**: 2026-08-03

The model separates durable Seshat truth from ephemeral Studio process state.
Types named `Snapshot`, `Summary`, or `Ref` are projections; they do not become a
second authority.

## Closed Enumerations

### ReadinessStatus

`not_started | blocked | ready_for_review | pass`

Studio uses the repository's canonical categorical values and adapter validation.
It does not add intermediate percentages or scores.

### ReadinessStage

`source | mapping | silver | gold | semantic_model | dashboard | publish`

The order is fixed and inherited from the readiness model.

### AgentHealthState

`healthy | missing | signed_out | incompatible | quota_limited | crashed | disabled`

Each state requires a plain-language `summary` and `recovery_action`.

### ThreadState

`starting | ready | running | awaiting_technical_approval | completed | failed | interrupted`

### ToolApprovalDecision

`allow_once | deny`

Persistent blanket approval is outside Foundation.

### StudioEventType

`thread_started | turn_started | agent_message | plan_updated | tool_started |
tool_completed | file_change_proposed | approval_required | turn_completed |
turn_failed | connection_state`

## Durable Projections

### WorkspaceIdentity

| Field | Type | Invariant |
|---|---|---|
| `display_name` | string | Human-readable repository name; never an absolute path. |
| `root_fingerprint` | string | Non-reversible digest used to detect stale process reuse. |
| `branch` | string or null | Current branch if available; sanitized. |
| `revision` | string | Digest of the committed artifacts and gate inputs used by the snapshot. |

The resolved root `Path` exists only in backend process configuration and never in
the browser contract.

### WorkspaceSnapshot

| Field | Type | Invariant |
|---|---|---|
| `identity` | WorkspaceIdentity | Identifies the one pinned workspace. |
| `generated_at` | RFC 3339 timestamp | Projection time, not artifact approval time. |
| `tables` | tuple[TableJourney] | Stable display ordering. |
| `next_action` | ActionSummary or null | One next allowed workspace action. |
| `pending_decision_count` | non-negative integer | Count only, never a score. |
| `input_defects` | tuple[InputDefect] | Malformed/unreadable committed inputs; never silently dropped. |
| `agent_health` | AgentHealth | Current adapter health, independent of readiness. |

`revision` changes whenever any source artifact or applicable gate result used by
the projection changes.

### TableJourney

| Field | Type | Invariant |
|---|---|---|
| `table_id` | string | Stable opaque identifier safe for URL use. |
| `display_name` | string | Source table label; not assumed to be C086 or retail-specific. |
| `current_stage` | ReadinessStage | Recomputed from committed artifacts and gates. |
| `stages` | exactly seven StageState values | Ordered by canonical stage order. |
| `next_action` | ActionSummary or null | Next permitted table action. |
| `forbidden_scope` | tuple[string] | Concrete operations the current state forbids. |

### StageState

| Field | Type | Invariant |
|---|---|---|
| `stage` | ReadinessStage | Unique within a TableJourney. |
| `status` | ReadinessStatus | Categorical only. |
| `evidence` | tuple[EvidenceRef] | Required and non-empty when canonical state is pass. |
| `blocking_reasons` | tuple[BlockingReason] | Required and non-empty when blocked. |
| `required_authority` | tuple[AuthorityRef] | Names who or what may clear remaining boundaries. |

### EvidenceRef

| Field | Type | Invariant |
|---|---|---|
| `label` | string | Plain-language description. |
| `source_ref` | string | Workspace-relative reference or gate identifier only. |
| `kind` | string | Closed by existing projection adapter. |
| `live_state` | `verified | pending_live_profile | not_applicable` | Never upgrades pending live evidence. |

### BlockingReason

| Field | Type | Invariant |
|---|---|---|
| `code` | string or null | Existing stable code when available. |
| `message` | string | Concrete fact, never generic "needs work". |
| `source_ref` | string or null | Sanitized workspace-relative evidence. |

### ActionSummary

| Field | Type | Invariant |
|---|---|---|
| `id` | string | Stable route/action identifier. |
| `label` | string | Plain-language primary label. |
| `explanation` | string | Why this is the next allowed action. |
| `requires_agent` | boolean | Allows useful degraded-state presentation. |
| `requires_named_human` | boolean | Never inferred from a technical approval. |

### InputDefect

| Field | Type | Invariant |
|---|---|---|
| `code` | string | Stable defect category. |
| `message` | string | Safe explanation. |
| `source_ref` | string or null | Sanitized path; never outside the root. |
| `recovery_action` | string | Concrete repair or onboarding action. |

## Ephemeral Process State

### StudioSession

| Field | Type | Invariant |
|---|---|---|
| `session_id` | opaque string | Random; not derived from workspace. |
| `workspace_root` | backend Path | Resolved and pinned before server startup. |
| `bootstrap_token_digest` | bytes | Raw URL token is not retained after exchange. |
| `cookie_digest` | bytes | Compared in constant time. |
| `created_at` | timestamp | Process-local. |
| `expires_at` | timestamp | Expiry invalidates HTTP and SSE access. |
| `threads` | mapping[id, AgentThread] | Bounded process memory. |

No StudioSession field is serialized to disk.

### AgentHealth

| Field | Type | Invariant |
|---|---|---|
| `state` | AgentHealthState | One closed categorical state. |
| `summary` | string | Redacted and analyst-readable. |
| `recovery_action` | string | Specific next action. |
| `provider` | `codex | disabled` | Foundation's supported implementation. |
| `version` | string or null | Sanitized executable version. |

### AgentThread

| Field | Type | Invariant |
|---|---|---|
| `thread_id` | opaque string | Studio identifier mapped to provider thread internally. |
| `state` | ThreadState | Validated transition graph below. |
| `created_at` | timestamp | Process-local. |
| `active_turn_id` | string or null | At most one active turn per thread. |
| `next_sequence` | positive integer | Monotonic, never reused. |
| `events` | bounded deque[StudioEvent] | Already redacted. |
| `pending_approval` | ToolApprovalRequest or null | Present only in awaiting state. |

### AgentRequest

| Field | Type | Invariant |
|---|---|---|
| `prompt` | string | Non-empty, size-limited plain-language request. |
| `selected_table_id` | string or null | Must exist in the current snapshot revision. |
| `snapshot_revision` | string | Enables stale-state rejection. |
| `requested_mode` | `read_only | propose_changes` | Default is read_only. |
| `context` | AgentContext | Stage, allowed action, forbidden scope, and safe evidence only. |

### StudioEvent

| Field | Type | Invariant |
|---|---|---|
| `thread_id` | string | Matches containing thread. |
| `sequence` | positive integer | Strictly increasing per thread. |
| `type` | StudioEventType | Stable provider-neutral value. |
| `occurred_at` | timestamp | Assigned by Studio ingestion. |
| `turn_id` | string or null | Required for turn-scoped events. |
| `payload` | typed object | Type-specific and redacted. |
| `ignored_for_state` | boolean | True for late events after interruption/completion. |

Hidden reasoning and raw provider envelopes are never legal payload fields.

### ToolApprovalRequest

| Field | Type | Invariant |
|---|---|---|
| `approval_id` | opaque string | One-time within the thread. |
| `thread_id` | string | Owning thread. |
| `turn_id` | string | Active turn. |
| `action` | string | Plain-language proposed action. |
| `target` | string | Sanitized command/file/resource target. |
| `reason` | string | Provider rationale after redaction. |
| `scope` | tuple[string] | Exact proposed side-effect scope. |
| `risk` | `low | moderate | high | prohibited` | Technical risk category, not readiness score. |
| `blocked_by_readiness` | boolean | True prevents allow. |
| `expires_at` | timestamp | Stale approvals cannot be answered. |

### PreparedDecisionSummary

| Field | Type | Invariant |
|---|---|---|
| `decision_id` | opaque string | Read-only reference. |
| `question` | string | Exact business judgment needed. |
| `required_authority` | string | Named role/person requirement from existing decision model. |
| `affected_scope` | tuple[string] | Sanitized artifacts/stages. |
| `status` | `prepared` | Foundation cannot change it. |

## State Transitions

### AgentThread

```text
starting -> ready
starting -> failed
ready -> running
running -> awaiting_technical_approval
awaiting_technical_approval -> running       (allow_once or deny response sent)
running -> completed
running -> failed
running -> interrupted
awaiting_technical_approval -> interrupted
```

Terminal provider events received after `completed`, `failed`, or `interrupted` are
retained in sequence with `ignored_for_state=true`; they do not reopen the turn.

### Tool approval

1. Provider approval is normalized and redacted.
2. Studio computes readiness forbidden scope against the current snapshot.
3. If prohibited, Studio sends denial without offering an allow control.
4. Otherwise the thread pauses and one request is shown.
5. A matching, unexpired explicit decision is relayed once.
6. The request is cleared; replaying the decision returns conflict and sends nothing.

## Validation Rules

1. No browser model contains an absolute filesystem path or credential-shaped field.
2. Every blocked stage has at least one concrete blocking reason.
3. Every passing stage cites evidence as required by the canonical projection.
4. Table stage arrays contain all seven stages exactly once and in order.
5. `pending_decision_count` equals the projected prepared/pending decision summaries;
   it is not used to calculate quality.
6. Requests with stale `snapshot_revision` return a conflict before a turn starts.
7. Only one unresolved technical approval may exist for one active turn.
8. Redaction occurs before event buffering, logging, exception serialization, or SSE.
9. Workspace-relative references are resolved and containment-checked on the backend;
   the resulting absolute path is never returned.
10. Process restart loses conversations by design but changes no durable Seshat truth.
