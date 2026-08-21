# Data Model: Studio Governed Analyst Workbench (spec 140)

Every shape below is derived from the **shipped validators**, not from a sample file.
This repository currently tracks no `.seshat/semantic-decisions.yaml`, so there is no
existing decision entry to copy. Building the model from validators avoids inventing a
shape that the gate would then reject.

## Existing contract this feature must satisfy

### Decision entry (consumed by `approval_is_valid`)

A decision is a mapping. The fields the shipped code reads:

| Field | Read by | Required |
| --- | --- | --- |
| `id` | error messages | practically yes (else `<no-id>`) |
| `decision_type` | `is_critical`, `_eligibility_valid` | yes |
| `status` | `is_open_status`, `is_known_status` | yes |
| `scope` | `scope_keys`, `active_scope_conflicts` | yes |
| `approval` | `approval_is_valid` | yes |

### `approval` block

`APPROVAL_REQUIRED_FIELDS` is exact and all six must be truthy:

```
approved_by, approved_at, source, evidence, evidence_identity, reviewed_scope
```

### `approved_by` -- the signer string

`owner_shape_ok` requires the literal form **`Person Name (class_token)`**:

- must be a `str`;
- must match the owner-shape regex (name plus a parenthesised role);
- the name must be non-empty and must **not** itself be a role token -- so
  `"owner (owner)"` is rejected;
- the role group must be non-empty.

`owner_class()` returns the normalized role token. For a **critical**
`decision_type`, `_eligibility_valid` additionally requires the authority contract to
declare that class eligible; **`authority is None` fails closed**.

## New entities introduced by this feature

### `EvidenceBundle` (US1)

A read-only grouping over what the projection already exposes; it introduces no new
persisted state.

| Field | Type | Notes |
| --- | --- | --- |
| `table_id` | `str` | matches `TableJourney.table_id` |
| `stages` | `tuple[StageState, ...]` | reused from `projection`, not redefined |
| `evidence` | `tuple[EvidenceRef, ...]` | flattened from `StageState.evidence` |
| `defects` | `tuple[InputDefect, ...]` | malformed evidence surfaces here, never as a pass |
| `pending_live` | `tuple[str, ...]` | stage names whose evidence carries a pending `live_state` |

**Verified against `src/seshat/studio/projection.py`** -- these are the actual shipped
field names, which differ from a naive guess in three ways that matter:

- `WorkspaceSnapshot.input_defects` (not `defects`) is the snapshot-level attribute.
- `InputDefect` has **no** `table_id`. Its fields are `code`, `message`, `source_ref`,
  `recovery_action`. Defects therefore cannot be filtered per table by identity; they
  are correlated via `source_ref`, or carried at workspace level.
- `StageState` has **no** `pending_live` field. Its fields are `stage`, `status`,
  `evidence`, `blocking_reasons`, `required_authority`. Pending-live state lives on
  `EvidenceRef.live_state` (`EvidenceRef` = `label`, `source_ref`, `kind`,
  `live_state`), so `pending_live` must be **derived** from evidence, not read off the
  stage.

Because every member is an existing projection type, US1 adds a view rather than a new
source of truth. A claim that cannot be traced to an `EvidenceRef` or a `pending_live`
entry must not be displayed.

### Decision-entry vocabulary (verified, not assumed)

The `decision_type` and `status` values a write must use are closed sets in
`decision_store.py`. Inventing a member is a silent failure: `is_known_status` treats an
unrecognized status as malformed and every consumer fails closed.

- `STATUS_VALUES` = `proposed`, `approved`, `rejected`, `pending`, `needs_user_input`,
  `needs_sample`, `blocked`, `deferred`, `superseded`. **There is no `decided`.** A
  recorded human answer uses `approved`.
- `CRITICAL_DECISION_TYPES` = `kpi_definition`, `pii_handling`, `table_grain`,
  `primary_key`, `relationship_cardinality`, `missing_value_rule`, `data_exclusion`,
  `policy_ruling`, `dashboard_blueprint_approval`, `report_intent_approval`,
  `publish_export`. A critical type additionally requires the authority contract to
  declare the signer's class eligible, and `authority is None` fails closed.
- A **non-critical** `decision_type` is any recognized type outside that set; only such
  a decision can be written with `authority=None`.

### `BusinessDecisionRequest` (US3)

The question put to a named human. Server-generated, immutable, and bound to one
proposal.

| Field | Type | Notes |
| --- | --- | --- |
| `request_id` | `str` | |
| `question` | `str` | exact business question, in business language |
| `allowed_answers` | `tuple[str, ...]` | closed set; a free-text answer is refused |
| `required_authority` | `str` | class token the signer must hold |
| `proposal_id` | `str` | the proposal this question decides |
| `proposal_hash` | `str` | binds the question to exact reviewed content |

`allowed_answers` being a closed set is what makes FR-140-009 checkable: an answer
outside the set is refused, so the agent cannot smuggle in a judgement by phrasing.

### `ChangeProposal` (immutable)

| Field | Type | Notes |
| --- | --- | --- |
| `proposal_id` | `str` | opaque |
| `proposal_hash` | `str` | canonical hash of the proposed scope + diff (FR-140-005) |
| `workspace_revision` | `str` | from the projection's existing revision digest |
| `target_artifact` | `str` | repo-relative path |
| `diff` | `str` | exact artifact diff shown before approval (FR-140-007) |
| `fields` | `tuple[FieldProvenance, ...]` | per-field provenance (FR-140-006) |
| `impact` | `ImpactSummary` | affected artifacts, stages, metrics, decisions |
| `required_authority` | `str` | `technical` or `named_human` |
| `validation` | `tuple[str, ...]` | results from the existing engines, not re-derived |

Frozen. Any change produces a **new** proposal with a new hash; the prior approval is
invalidated (FR-140-008).

### `FieldProvenance`

`kind` is a closed set (FR-140-006): `discovered_fact`, `existing_decision`,
`default`, `inference`, `new_human_judgment`. Plus `source_ref`, `author`, `recorded_at`.

`inference` and `default` are the two kinds that must never silently become
`existing_decision` in the UI -- that would present a guess as a ruling.

### `NamedHumanDecision` (the request Studio accepts)

| Field | Supplied by | Notes |
| --- | --- | --- |
| `signer` | **human** | must satisfy `owner_shape_ok` |
| `declared_authority` | **human** | class token inside `signer` |
| `answer` | **human** | one of the request's allowed answers |
| `proposal_hash` | server | must equal the current proposal (FR-140-012) |
| `workspace_revision` | server | must equal the current revision |
| `recorded_at` | server | timestamp |
| `reviewed_scope` | server | exact scope the human saw |

**FR-140-009 in the model**: `signer`, `declared_authority`, and `answer` have no
server-side or agent-side default. Absent means refuse, never infer. There is no code
path that populates them from a proposal, a prior decision, or a config value.

### `DecisionWriteReceipt`

| Field | Notes |
| --- | --- |
| `written_path` | which `.seshat/` file was appended |
| `decision_id` | the appended entry's id |
| `state` | always `pending commit` at write time (FR-140-021) |
| `gate_authority` | pointer stating the gate reads `HEAD`, so this is not yet authority |

`state` has no `approved` member. The type cannot express the false claim.

### `ApplyReceipt`

`applied_paths`, `commands`, `proposal_hash`, `verification` (static and optional
live), `remaining_blockers`. Static success is labelled necessary-not-sufficient
(FR-140-016). Never a readiness claim on its own.

## State model

```
draft ──(named human answers)──> pending commit ──(a human commits)──> authoritative
```

- `draft -> pending commit` is the only transition Studio performs.
- `pending commit -> authoritative` is performed by a human running git, never by
  Studio (FR-140-023).
- Readiness is computed only from `authoritative` state, read at `HEAD` (FR-140-015).

## Write invariants (Phase 1 test targets)

1. **Append-only** -- an existing entry is never mutated or deleted (FR-140-022).
2. **Atomic** -- a rejected or interrupted write leaves the file byte-identical.
3. **Validated before write** -- `approval_is_valid` and `owner_shape_ok` gate the
   append; a rejected entry is not partially written (US3 acceptance 4).
4. **Round-trip fidelity** -- appending must not reformat, reorder, or drop unrelated
   entries or comments.
5. **No second predicate** -- the write path calls the shipped predicates; it does not
   reimplement validity (FR-140-011).

## Fixture warning for implementers

Because no real decision-store file exists in this repo, Phase 1 tests must build
fixtures that the **shipped** `load_store_file` + `approval_is_valid` actually accept,
and must assert acceptance by calling those functions -- not by asserting against a
hand-written expected string. A fixture that only this feature's own code can read
would make the whole suite vacuous while looking green.

Concretely: assert `approval_is_valid(entry, authority) == (True, None)` for a
well-formed entry and `(False, <reason>)` for each violation, rather than asserting the
YAML text matches a template.
