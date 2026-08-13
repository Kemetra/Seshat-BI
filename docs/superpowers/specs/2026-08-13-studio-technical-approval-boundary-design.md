# Seshat Studio — technical approval boundary (spec 139, Phase 6)

**Date:** 2026-08-13
**Tasks:** T024–T027
**Requirements:** FR-018, FR-019, FR-020, FR-021, FR-022, SC-005
**Branch:** `studio-2`

## Problem

Phase 4 shipped the read/observe half of Studio deliberately: `approval_required`
renders as inert activity with no actionable control, and a test pins that
absence. Phase 6 is where an **allow** control appears for the first time.

That makes this the highest-risk phase in spec 139. The kit's own hard stop is
`never_self_grant_approval`; a careless panel here would let an analyst believe
they had approved something no approval seam recorded.

The immediate defect to design around: the fake bridge
(`src/seshat/studio/bridge.py:187`) emits one event type, `approval_required`,
carrying `required_authority: "named_human"`. Meanwhile FR-019 concerns
*technical* approvals ("run this command") and FR-022 forbids Studio from
recording *business* decisions at all. Two different authorities currently share
one event type. Conflating them is the failure mode.

## Decisions

### 1. Separate the two authorities by `required_authority`

`approval_required` stays one event type. Normalization reads
`required_authority` and decides:

- `technical` → a live allow/deny panel.
- `named_human` → an **inert prepared summary**. No allow control, no route.

Rejected: two distinct event types. Clearer on the wire, but it changes the
contract and the fake bridge for no safety gain — the split has to be enforced in
normalization regardless, so the event-type change would be ceremony.

Rejected outright: gating purely on readiness `forbidden_scope` and ignoring
`required_authority`. That is the shape that eventually grants a business
decision a live allow button.

### 2. Normalization lives in a new module

`src/seshat/studio/approvals.py` — not folded into `agent_routes.py`, which is
already ~550 lines and would approach the ~800-line CodeScene single-file gate.

The module is **pure functions**: given a provider approval event plus readiness
state, return a decision envelope. No I/O, no bridge handle, no FastAPI import.
That is what makes the eight T024 cases testable without a running server.

Envelope fields:

| Field | Meaning |
|---|---|
| `authority` | `technical` \| `named_human` |
| `allow_permitted` | `False` whenever authority is `named_human` **or** readiness forbids the scope |
| `forbidden_reasons` | the sentences from `_forbidden_scope`, verbatim |
| `action`, `target`, `reason`, `scope`, `risk` | the FR-019 display set |

### 3. Readiness is consulted before the control is exposed

`allow_permitted` is computed from `seshat.agent_next._forbidden_scope()` — the
existing gate — at **normalization** time, not at click time. FR-018 requires the
scope check to pass *before* Studio may ask for a technical approval.

There is no second source of truth for forbidden scope. Reimplementing that
judgment inside Studio would be the same defect class as a second
approval-trust path.

### 4. One-time relay through a new POST route

`POST /api/v1/agent/threads/{thread_id}/turns/{turn_id}/approvals/{approval_id}`,
mirroring the existing `interrupt_turn` route shape.

- The browser sends a decision; it never executes a tool or writes an artifact
  (FR-020). The response goes to the agent bridge only.
- **Single use.** A second POST on the same `approval_id` returns a `Problem`,
  not a second allow.
- **Deny is the default.** An unknown, stale, or already-decided `approval_id`
  refuses. No input state falls through to allow.

### 5. Reuse the existing thread state

`awaiting_technical_approval` is already in `agent_routes.THREAD_STATES`. Wire
it; do not invent a state. A turn pauses in that state and resumes on the relay.

### 6. Capability flags

`app._bootstrap_capabilities()`: `technical_approvals` flips `False → True`.
`business_decision_recording` stays const `False` — FR-022, permanently for this
spec.

## Invariants the tests exist to pin

1. A `named_human` approval never gets an allow control — no route accepts it,
   no envelope permits it. (FR-021, FR-022)
2. Readiness `forbidden_scope` is evaluated before exposure, not after the
   click. (FR-018)
3. Browser code performs no side effect; a decision is a message to the bridge.
   (FR-020)
4. OpenAPI contains **no** business-approval endpoint. (T027)
5. `allow_once` is genuinely once — replay is refused. (SC-005)

## Testing

New `tests/unit/test_studio_approvals.py`, TDD — every test failing before any
implementation lands. The eight cases T024 names:

1. paused approval (turn halts in `awaiting_technical_approval`)
2. exact scope display (all five FR-019 fields present, unaltered)
3. allow-once (relay succeeds, turn resumes)
4. deny (relay refuses, turn continues without the tool)
5. readiness-prohibited allow (`allow_permitted is False`, reasons non-empty)
6. stale decision (unknown `approval_id` → Problem)
7. repeated decision (second POST on the same id → Problem)
8. prepared business judgment (`named_human` → inert, no allow route)

Plus a negative OpenAPI assertion for invariant 4.

**Assert the positive transformed form, not merely an absence** — for the inert
case, assert the envelope reports `authority == "named_human"` and
`allow_permitted is False`, not just that a button is missing. An absence
assertion passes when the feature is deleted entirely.

## Out of scope

- Frontend build and accessibility certification — Phases 7 and 8.
- Business-decision recording — belongs to the next governed-workbench spec, per
  FR-022. Never this one.
- Anything that mutates `readiness-status.yaml`. Approval remains a human file
  edit read through `approval_is_shape_valid`.
