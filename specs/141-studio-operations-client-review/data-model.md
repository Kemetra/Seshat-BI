# Data Model: Studio Operations and Client Review (spec 141)

Shapes below are derived from the **shipped code**, and where a shape is new this file
says so. The distinction matters: a spec that claims to reuse a vocabulary the tree does
not have sends an implementer looking for something that is not there.

## Correction to the outline's assumption

The outline implied Operations could read component health directly from the diagnostic
engine. It cannot, and this is the single most useful thing this promotion establishes.

`seshat/doctor.py` returns `list[Finding]` (`seshat/core.py:44`), and `Finding` is:

| Field | Type |
| --- | --- |
| `rule_id` | `str` |
| `severity` | `Severity` -- `error` \| `warning` \| `info` |
| `message` | `str` |
| `locator` | `str` |

Plus `collect_findings`, `group_by_rule`, `repair_hint(rule_id)`, `next_allowed_action`,
and `build_digest_payload`.

**There is no six-state component vocabulary in the tree.** US1's `missing` /
`misconfigured` / `incompatible` / `deferred` / `failed` / `healthy` is introduced by
*this* spec. So FR-141-004 means: consume `doctor.py`'s findings as the evidence, and map
them into the component vocabulary here -- do not build a second probe set. The mapping
is new; the probing is not.

## New entities

### `ComponentState` (new closed vocabulary)

```
missing | misconfigured | incompatible | deferred | failed | healthy
```

`deferred` is not a failure (FR-141-003). It means a boundary that is legitimately
unavailable -- no DSN configured, an optional extra not installed -- and rendering it red
would train technicians to ignore red.

An unrecognized state is malformed and must fail closed to `failed`, never to `healthy`
(FR-141-006). Absence of evidence is not evidence of health.

### `ComponentDiagnostic`

| Field | Type | Notes |
| --- | --- | --- |
| `component` | `str` | one of the seven named surfaces |
| `state` | `ComponentState` | closed set above |
| `evidence` | `tuple[str, ...]` | derived from `Finding.message` / `Finding.locator` |
| `blocker` | `str \| None` | why it cannot proceed |
| `recovery_action` | `str \| None` | from `doctor.repair_hint(rule_id)` |
| `source_rule_ids` | `tuple[str, ...]` | the findings this was mapped from |

`source_rule_ids` exists so a displayed diagnosis is traceable to the rule that produced
it. Without it, Operations could show a state no rule supports and nobody could tell.

**No aggregate field.** There is deliberately no `overall`, `score`, `percent`, or
`health_index` anywhere in this model (FR-141-002). The type cannot express the roll-up,
which is stronger than a convention against computing one.

### `GovernedRunSummary`

| Field | Type | Notes |
| --- | --- | --- |
| `run_id` | `str` | |
| `requested` | `str` | business-language description |
| `proposed_tools` | `tuple[str, ...]` | from normalized events, never a raw transcript |
| `decided_by` | `str \| None` | signer, when a named human ruled |
| `decision_state` | `str` | `pending_commit` \| `authoritative` -- mirrors spec 140 |
| `gates_run` | `tuple[str, ...]` | |
| `outcome` | `str` | categorical, never a score |
| `durability` | `str` | `ephemeral` \| `durable` |
| `committed_source` | `str \| None` | required when `durability == "durable"` |

**The invariant that makes this honest**: `durability == "durable"` requires a non-None
`committed_source` (FR-141-010). A claim that cannot cite committed state is `ephemeral`,
not promoted. And `decision_state` carries spec 140's `pending_commit` through to the
render layer, because a presentation surface can lie without touching the receipt
(FR-141-021).

### `ClientReviewDraft`

`workspace_revision` (binds the selection), `selected_facts`, `narrative`,
`pending_items`, `blocked_items`.

`pending_items` and `blocked_items` are **separate fields, not a filtered view of
`selected_facts`**. Keeping them distinct means a renderer cannot accidentally omit them
while rendering the happy path (FR-141-021, US3 acceptance 2).

### `ClientReviewArtifact`

`manifest`, `content`, `generated_at`, `workspace_revision`, `asset_inventory`.

`asset_inventory` must be empty of remote references (US3 acceptance 4). An export that
fetches a remote asset is neither self-contained nor reproducible, and leaks that it was
opened.

### `ClientAcknowledgment` and `ClientFeedbackItem`

`ClientAcknowledgment`: `scope`, `acknowledged_by`, `acknowledged_at`, `run_id`.
`ClientFeedbackItem`: `scope`, `question`, `raised_by`, `raised_at`.

Neither carries an `answer` or `approval` field. That absence is the point: an
acknowledgement is not a ruling (FR-141-011), and making it structurally incapable of
holding one prevents the two collapsing under UI pressure. A scoped business answer goes
through spec 140's `POST /decisions/record` and produces a `DecisionWriteReceipt` there.

### `SupportBundleManifest`

`allowlisted_fields`, `included_files`, `file_hashes`, `versions`, `redaction_scan`.

`redaction_scan` is a required field holding the scan result. A manifest that can be
constructed without it would let an unscanned bundle look finished (FR-141-014).

## Existing shapes consumed unchanged

- `Finding` (`core.py`) -- the diagnostic evidence.
- `StudioEvent`, `ThreadEvents`, `ThreadStore` (`studio/events.py`) -- run history source.
- `DecisionWriteReceipt`, `ApplyReceipt` -- durable receipts.
- `decisions_at_head` -- the committed read.
- `review_scope.review_for` -- scoped filtering, including the refusal of an absent scope.
- `redaction.scrub_payload` / `redact_credentials` / `redact_paths`.

## Test-fixture warning for implementers

Two traps this feature is unusually exposed to:

1. **Absence-assertions on the aggregate score.** Asserting `"score" not in payload` goes
   green when the same value ships as `health_index`. Search for a numeric roll-up across
   the payload instead, and pair it with a positive test proving per-component states DO
   appear -- otherwise an empty payload passes.
2. **The deferred/failed pair.** A test that only checks "deferred is not failure" passes
   if everything is reported deferred. Assert the inverse alongside it: a genuinely failed
   component reports `failed`.

Both are instances of the same rule this repo has learned repeatedly: a negative
assertion needs its positive twin, or it proves nothing.
