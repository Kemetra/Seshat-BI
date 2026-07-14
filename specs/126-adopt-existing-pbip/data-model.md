# Data Model: Governed Existing PBIP Adoption

## Model rules

- All persisted/output paths are POSIX-style and relative to the selected root.
- Every fact has exactly one classification: `observed`, `proposed`, `missing`,
  `blocked`, or `unavailable_with_reason`.
- An observed fact has an `artifact`; an unavailable fact has a `reason`.
- The assessment has exactly one `next_step` object and no numeric score.
- SHA-256 values identify bytes or canonical assessment content; they express
  equality/change only, never quality or confidence.

## Entities

### AdoptionTarget

| Field | Type | Meaning |
|---|---|---|
| `kind` | `pbip_project` or `pbix_unsupported` | Supported boundary |
| `label` | string | Safe basename/display label; never an absolute path |
| `version_control` | `clean`, `dirty`, `untracked`, or `absent` | Evidence eligibility boundary |
| `components` | array of Component | Deterministically ordered supported components |

### Component

| Field | Type | Meaning |
|---|---|---|
| `kind` | enum | project, semantic model, report, table, measure, relationship, parameter, page, or visual |
| `identity` | string | Format identity/name with unsafe values redacted |
| `artifact` | relative path | Cited local source |
| `sha256` | 64 lowercase hex chars or null | File fingerprint when safely readable |
| `support` | `supported`, `unsupported`, `unreadable`, `missing`, or `ambiguous` | Coverage state |

### AdoptionFact

| Field | Type | Meaning |
|---|---|---|
| `id` | stable string | Deterministic fact identity |
| `classification` | required enum | Authority-safe classification |
| `category` | string | coverage, governance, readiness, evidence, proposal, or change |
| `subject` | string | Safe description of what the fact concerns |
| `detail` | string | Redacted human-readable fact |
| `artifact` | relative path or null | Required for `observed`; optional otherwise |
| `reason` | string or null | Required for `unavailable_with_reason` |
| `rule_id` | string or null | Existing Seshat rule identity when the fact comes from governance |
| `required_authority` | string or null | Named role that must decide a proposal/blocker |

### ReadinessProjection

A verbatim/projected canonical table status plus the result returned by
`build_run_next_response`. It is optional when no `readiness-status.yaml` exists
and is never persisted as adoption-owned state.

### ScaffoldPlan

| Field | Type | Meaning |
|---|---|---|
| `writes` | array | Exactly one declared new path in v1: `.seshat/adoption/pbip-adoption.yaml` |
| `preconditions` | string array | Git worktree, accepted fresh digest, safe contained parents, destination absent |
| `approvals` | empty array | Explicit proof that scaffold grants no approval |

### AdoptionChange

| Field | Type | Meaning |
|---|---|---|
| `kind` | `added`, `removed`, `changed`, or `unchanged` | Comparison to accepted baseline |
| `artifact` | relative path | Compared authoritative input |
| `previous_sha256` | hash or null | Baseline value |
| `current_sha256` | hash or null | Current value |
| `classification` | `observed` or `blocked` | Changed governed inputs are blocked for review |

### NextStep

| Field | Type | Meaning |
|---|---|---|
| `kind` | `action` or `terminal_stop` | Whether the supported journey can continue now |
| `stage` | readiness stage or null | Existing earliest stage when applicable |
| `action` | non-empty string | The one allowed action/guidance |
| `blocking_reasons` | string array | Concrete facts, empty only for an unblocked action |
| `required_authority` | string or null | Existing authority/owner when required |

### AdoptionAssessment

Top-level stable agent contract:

```text
schema_version
target
coverage
facts[]
governance_findings[]
readiness[]
changes[]
scaffold_plan
next_step
disclosure
assessment_digest
```

`assessment_digest` is computed last from canonical JSON for every substantive
field except itself. No generated timestamp is part of the contract.

### AdoptionManifest

The accepted YAML baseline contains `schema_version`, `assessment_digest`,
`target`, `authoritative_inputs`, `facts`, `next_step`, `proposals`, and
`approvals: []`. It deliberately has no `current_stage`, `stage_status`, or
approval-validity calculation. Reassessment reads it only as a prior fingerprint
baseline.

### ScaffoldResult

The stable text/JSON result of the write command contains `schema_version`, a
categorical `outcome`, the recomputed `assessment_digest` when available,
`written` (empty or the one declared manifest path), concrete
`blocking_reasons`, exactly one `next_step`, and `approvals: []`. It contains no
partially written path, score, absolute root, secret, or implicit Git action.

## State transitions

```text
unassessed --assess/read-only--> assessed(digest, declared write)
assessed --decline/change------> unassessed (no persisted state)
assessed --accept exact digest + Git + no collision--> baseline_manifest
baseline_manifest --reassess--> same facts or explicit AdoptionChange facts
```

There is no adoption readiness state. The seven-stage readiness files and their
existing predicates remain the only readiness authority.

## Validation rules

1. Resolve the target and every discovered/scaffold path under the selected root;
   linked or redirected escapes stop the operation.
2. Sort components, facts, findings, changes, and paths by stable keys before
   hashing or rendering.
3. Never include an absolute path, raw/source value, credential-like field, DSN,
   or connection literal in the normalized model.
4. Fail closed if final disclosure scanning finds prohibited output.
5. A digest mismatch, missing Git worktree, dirty accepted input, target collision,
   or publication failure creates no governed target file.
6. A PBIX target has no components/scaffold writes and one `terminal_stop`.
7. Unsupported components remain visible with a reason; supported observations
   are retained and partial coverage is never called complete.
8. Every JSON scaffold result validates against
   `contracts/pbip-adoption-scaffold-result.schema.json`, and its text rendering
   carries the same outcome, writes, blockers, approvals, and next step.
