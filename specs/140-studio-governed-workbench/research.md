# Research: Studio Governed Analyst Workbench (spec 140)

**Date**: 2026-08-21

All findings below were read from the shipped tree at `aa643add`, not inferred from
the outline. Each names its source so a reviewer can re-verify.

## R1 -- Foundation shipped observation only; every mutation route is absent

`src/seshat/studio/app.py` registers exactly these routes:

| Route | Method |
| --- | --- |
| `{API_PREFIX}/health` | GET |
| `{API_PREFIX}/bootstrap` | POST |
| `{API_PREFIX}/bootstrap/state` | GET |
| `{API_PREFIX}/workspace` | GET |
| `{API_PREFIX}/tables/{table_id}` | GET |
| `{API_PREFIX}/decisions` | GET |
| `{API_PREFIX}/agent/health` | GET |

`POST /bootstrap` exchanges a session token; it is not a domain mutation. There is no
proposal, decision-recording, or apply endpoint.

**Consequence**: spec 140 introduces the first domain-mutating routes in Studio. This
is a security-relevant first, not an incremental addition, which is why the write
boundary is specified before the UI.

## R2 -- `ApprovalEnvelope` already models named-human authority and refuses it

`src/seshat/studio/approvals.py`:

```python
allow_permitted = authority == TECHNICAL and not reasons
```

`normalize_approval` coerces any authority that is not `TECHNICAL` to `NAMED_HUMAN`,
so an unknown or malformed authority fails toward the stricter class. `allow_permitted`
is therefore always `False` for `named_human`.

**Consequence**: the gate spec 140 must satisfy already exists and already refuses
everything. 140 builds the authorized path *through* a working fail-closed refusal
rather than building refusal and path together. This materially reduces risk: the
default-deny is shipped and proven, and a defect in 140 fails toward refusal.

## R3 -- The Decision Store is read-only, and one predicate is shared with the gate

`src/seshat/decision_store.py` exposes `store_files`, `load_store_file`, `load_store`,
`load_authority_map`, `Store`, `is_critical`, `is_open_status`, `is_known_status`,
`scope_keys`, `active_scope_conflicts`, `owner_shape_ok`, `owner_class`, and
`approval_is_valid`. There is no `record`, `append`, `save`, or `write`.

`approval_is_valid` carries this docstring:

> The ONE approval-validity predicate shared by DS2 and the gate. [...] `authority is
> None` => eligibility cannot be validated => invalid (fail closed).

**Consequence, and the correction to the outline**: FR-140-011 as written required
using "the existing Decision Store validation and persistence model". The validation
model exists; the persistence model does not. The requirement was unsatisfiable. The
promoted spec splits it: reuse validation, supply persistence, and forbid a second
predicate. Ratifying the outline unchanged would have authorized building against an
impossible requirement -- exactly what the Promotion Gate exists to prevent.

## R4 -- The store is read from tracked files, so authority is committed state

`store_files()` filters against `STORE_PATHS`:

```python
STORE_PATHS: tuple[str, ...] = (
    ".seshat/semantic-decisions.yaml",
    ".seshat/kpi-contracts.yaml",
    ".seshat/cleaning-rules.yaml",
)
```

and `DECISION_STORE_CORPUS` is built with `any_tracked_file(*STORE_PATHS, ...)`.

**Consequence**: a decision becomes authoritative only when committed and read at
`HEAD`. A working-tree write is not authority. This is the direct source of the
three-state model (`draft` / `pending commit` / `authoritative`) and of FR-140-021 and
FR-140-023. It also means Studio must never commit on a user's behalf: doing so would
let the process that writes the decision also confer its authority.

## R5 -- Provenance and revision primitives already exist

`src/seshat/studio/projection.py` ships `EvidenceRef`, `BlockingReason`,
`ActionSummary`, `StageState`, `TableJourney`, `InputDefect`, `WorkspaceIdentity`,
`AgentHealth`, `WorkspaceSnapshot`, plus `_revision_digest` and `_root_fingerprint`.

**Consequence**: `workspace_revision` (FR-140-005) reuses the existing revision digest
rather than inventing a versioning scheme, and `InputDefect` already supplies the
"malformed evidence is a defect, not an empty success" behaviour US1 requires. Both are
recorded as assumptions in the spec rather than new work.

## R6 -- Precedent: how spec 139 was ratified

`specs/139-seshat-studio-foundation/spec.md` was added in commit `6eba24ce` already
carrying `Status: ratified -- Ahmed Shaaban (owner), 2026-08-03`, alongside
`plan.md`, `tasks.md`, `contracts/`, `data-model.md`, `research.md`, `quickstart.md`,
`checklists/`, and `evidence/`. Its comment block records that the owner ratified
"this exact specification, plan, contracts, and task list".

Additionally, 140 and 141 were the only two specs in the repository carrying `spec.md`
alone, and the only two containing the phrase `program outline`.

**Consequence**: a Studio ratification is a ratification of a complete package. That
precedent is why this promotion was required before 140 could be ratified at all, and
why the direction ruling of 2026-08-21 is recorded as scope agreement rather than as
implementation authority.

## R7 -- Prerequisite state

`specs/139-seshat-studio-foundation/spec.md` reads `Status: implemented -- all 38 tasks
complete; accepted by Ahmed Shaaban, 2026-08-16`, and its `tasks.md` contains 38
checked and 0 unchecked items.

**Consequence**: 140's stated dependency ("accepted Foundation") is genuinely met, so
promotion is unblocked. Spec 141 remains gated on 140's *acceptance*, not merely on
this promotion.

## Open questions

None blocking. Two items are deliberately deferred to the plan rather than the spec:

1. Whether the Decision Store write lands as a new module or extends
   `decision_store.py` -- a structural choice constrained by the repository's
   single-file health gate, resolved in `plan.md`.
2. The YAML serialization approach for append-only writes (round-trip fidelity of
   existing entries) -- resolved in `plan.md` Phase 1.
