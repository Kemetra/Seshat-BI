# Studio Technical Approval Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Studio a technical allow/deny control for provider tool approvals, while making it structurally impossible for a named-human business decision to acquire one.

**Architecture:** A new pure-function module (`seshat.studio.approvals`) normalizes a provider `approval_required` event into a decision envelope, reading `required_authority` to split technical from named-human and consulting the existing readiness gate for forbidden scope. A single-use relay route in `agent_routes.py` carries the analyst's decision to the bridge; the browser never performs a side effect.

**Tech Stack:** Python 3.13, FastAPI, pytest, anyio. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-13-studio-technical-approval-boundary-design.md`

## Global Constraints

- Tasks covered: **T024–T027** of `specs/139-seshat-studio-foundation/tasks.md`. Requirements: **FR-018, FR-019, FR-020, FR-021, FR-022, SC-005**.
- `business_decision_recording` stays const `False` in `app._bootstrap_capabilities()`. Permanently, for this spec (FR-022).
- Nothing in this plan may write, mutate, or propose a change to `readiness-status.yaml`. Readiness approval remains a human file edit.
- Readiness forbidden-scope judgment has exactly ONE source: `seshat.agent_next.build_table_next_document()`'s `forbidden_scope` key. Do not reimplement it and do not import the private `_forbidden_scope`.
- Deny is the default. No unknown, stale, or repeated input may fall through to allow.
- Every test asserts the positive transformed form. An absence-only assertion passes when the feature is deleted.
- `ruff format --check src/ tests/` and `ruff check src/ tests/` are the CI gates; run both before each commit.
- Studio tests must tolerate a missing FastAPI: CI's `pytest -m unit` runs without app extras. Use `pytest.importorskip("fastapi")` in any module that imports the app.
- Commits are unsigned in this environment: use `git commit --no-gpg-sign`.

---

### Task 1: The approval envelope and authority split

**Files:**
- Create: `src/seshat/studio/approvals.py`
- Test: `tests/unit/test_studio_approvals.py`

**Interfaces:**
- Consumes: nothing from earlier tasks. Reads `seshat.agent_next.build_table_next_document`.
- Produces:
  - `ApprovalEnvelope` — frozen dataclass with fields `approval_id: str`, `authority: str`, `allow_permitted: bool`, `forbidden_reasons: tuple[str, ...]`, `action: str`, `target: str`, `reason: str`, `scope: str`, `risk: str`.
  - `TECHNICAL: str = "technical"` and `NAMED_HUMAN: str = "named_human"`.
  - `normalize_approval(event: dict[str, Any], forbidden_scope: Sequence[str]) -> ApprovalEnvelope`.

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for the Studio technical approval boundary (T024)."""

from __future__ import annotations

import pytest

from seshat.studio.approvals import (
    NAMED_HUMAN,
    TECHNICAL,
    ApprovalEnvelope,
    normalize_approval,
)

TECHNICAL_EVENT = {
    "approval_id": "turn-1-approval-1",
    "required_authority": "technical",
    "action": "run_command",
    "target": "pytest -q",
    "reason": "Verify the mapping change",
    "scope": "read_only",
    "risk": "low",
}

BUSINESS_EVENT = {
    "approval_id": "turn-1-approval-2",
    "required_authority": "named_human",
    "action": "apply_change",
    "target": "mappings/example/source-map.yaml",
    "reason": "Add the missing grain declaration",
    "scope": "propose_changes",
    "risk": "high",
}


def test_a_technical_approval_with_clear_readiness_permits_allow():
    envelope = normalize_approval(TECHNICAL_EVENT, [])
    assert envelope.authority == TECHNICAL
    assert envelope.allow_permitted is True
    assert envelope.forbidden_reasons == ()


def test_the_five_display_fields_survive_normalization_unaltered():
    envelope = normalize_approval(TECHNICAL_EVENT, [])
    assert envelope.action == "run_command"
    assert envelope.target == "pytest -q"
    assert envelope.reason == "Verify the mapping change"
    assert envelope.scope == "read_only"
    assert envelope.risk == "low"


def test_a_named_human_approval_is_never_allowable():
    envelope = normalize_approval(BUSINESS_EVENT, [])
    assert envelope.authority == NAMED_HUMAN
    assert envelope.allow_permitted is False


def test_readiness_forbidden_scope_blocks_a_technical_allow():
    envelope = normalize_approval(
        TECHNICAL_EVENT, ["no silver before mapping is cleared"]
    )
    assert envelope.authority == TECHNICAL
    assert envelope.allow_permitted is False
    assert envelope.forbidden_reasons == ("no silver before mapping is cleared",)


def test_an_unknown_authority_is_treated_as_named_human():
    envelope = normalize_approval(
        {**TECHNICAL_EVENT, "required_authority": "wharrgarbl"}, []
    )
    assert envelope.authority == NAMED_HUMAN
    assert envelope.allow_permitted is False


def test_a_missing_authority_is_treated_as_named_human():
    event = {k: v for k, v in TECHNICAL_EVENT.items() if k != "required_authority"}
    assert normalize_approval(event, []).allow_permitted is False


def test_the_envelope_is_immutable():
    envelope = normalize_approval(TECHNICAL_EVENT, [])
    with pytest.raises(Exception):
        envelope.allow_permitted = True  # type: ignore[misc]


def test_a_missing_display_field_becomes_an_explicit_unknown_not_a_crash():
    envelope = normalize_approval({"approval_id": "x", "required_authority": "technical"}, [])
    assert envelope.action == "unknown"
    assert envelope.risk == "unknown"
    assert isinstance(envelope, ApprovalEnvelope)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_approvals.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.studio.approvals'`

- [ ] **Step 3: Write the minimal implementation**

```python
"""Normalization for provider approval requests (T025).

**The authority split is the whole point of this module.** A provider asks for one
thing -- permission to act -- but Seshat recognizes two different authorities, and
only one of them is Studio's to grant. A `technical` approval is permission to run a
command; a `named_human` approval is a governance ruling, which FR-021/FR-022 place
outside Studio entirely. Both arrive as `approval_required`, so if the split is not
made HERE it is not made at all.

**Unknown authority degrades to `named_human`, never to `technical`.** An
unrecognized value means this build does not understand what is being asked, and the
safe reading of "I do not understand this request" is "I may not grant it."

**Forbidden scope is passed IN, not computed here.** The single source of that
judgment is `agent_next.build_table_next_document()`. Taking it as a parameter keeps
this module pure -- and pure is what lets the eight T024 cases run without a repo,
a database, or a server.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

__all__ = [
    "NAMED_HUMAN",
    "TECHNICAL",
    "ApprovalEnvelope",
    "normalize_approval",
]

#: Studio may expose an allow control for this authority.
TECHNICAL = "technical"

#: A governance ruling. Studio prepares a summary and offers NO allow control.
NAMED_HUMAN = "named_human"

#: Stand-in for a display field the provider omitted. An explicit word beats an
#: empty string, which renders as a blank panel the analyst cannot interpret.
_UNKNOWN = "unknown"


@dataclass(frozen=True)
class ApprovalEnvelope:
    """One normalized approval request. Frozen: a decision already taken must not be
    editable by a later caller."""

    approval_id: str
    authority: str
    allow_permitted: bool
    forbidden_reasons: tuple[str, ...]
    action: str
    target: str
    reason: str
    scope: str
    risk: str


def normalize_approval(
    event: dict[str, Any], forbidden_scope: Sequence[str]
) -> ApprovalEnvelope:
    """Turn a provider `approval_required` payload into a decision envelope.

    `allow_permitted` is True only when BOTH hold: the authority is technical, and
    readiness forbids nothing. Two independent reasons to refuse, evaluated before any
    control is exposed (FR-018).
    """
    raw_authority = event.get("required_authority")
    authority = TECHNICAL if raw_authority == TECHNICAL else NAMED_HUMAN
    reasons = tuple(forbidden_scope)
    return ApprovalEnvelope(
        approval_id=str(event.get("approval_id", _UNKNOWN)),
        authority=authority,
        allow_permitted=authority == TECHNICAL and not reasons,
        forbidden_reasons=reasons,
        action=str(event.get("action", _UNKNOWN)),
        target=str(event.get("target", _UNKNOWN)),
        reason=str(event.get("reason", _UNKNOWN)),
        scope=str(event.get("scope", _UNKNOWN)),
        risk=str(event.get("risk", _UNKNOWN)),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_approvals.py -v --no-cov`
Expected: PASS — 8 passed

- [ ] **Step 5: Lint, then commit**

```bash
ruff format src/seshat/studio/approvals.py tests/unit/test_studio_approvals.py
ruff check src/seshat/studio/approvals.py tests/unit/test_studio_approvals.py
git add src/seshat/studio/approvals.py tests/unit/test_studio_approvals.py
git commit --no-gpg-sign -m "feat: split technical from named-human approval authority (T025)"
```

---

### Task 2: Readiness lookup adapter

**Files:**
- Modify: `src/seshat/studio/approvals.py`
- Test: `tests/unit/test_studio_approvals.py`

**Interfaces:**
- Consumes: `normalize_approval` from Task 1.
- Produces: `forbidden_scope_for(repo_root: Path | str, table: str | None) -> tuple[str, ...]` — returns the readiness gate's `forbidden_scope` sentences, or a single-element refusal tuple when the lookup fails.

- [ ] **Step 1: Write the failing tests**

```python
def test_forbidden_scope_reads_the_readiness_document(tmp_path, monkeypatch):
    from seshat.studio import approvals

    def fake_document(repo_root, table):
        return {"forbidden_scope": ["no silver before mapping is cleared"]}

    monkeypatch.setattr(approvals, "build_table_next_document", fake_document)
    assert approvals.forbidden_scope_for(tmp_path, "sales") == (
        "no silver before mapping is cleared",
    )


def test_a_readiness_lookup_failure_refuses_rather_than_permitting(tmp_path, monkeypatch):
    from seshat.studio import approvals

    def exploding_document(repo_root, table):
        raise RuntimeError("no such table")

    monkeypatch.setattr(approvals, "build_table_next_document", exploding_document)
    reasons = approvals.forbidden_scope_for(tmp_path, "sales")
    assert len(reasons) == 1
    assert "could not be read" in reasons[0]
    # The point: a failed lookup must BLOCK an allow, not silently clear the gate.
    assert normalize_approval(TECHNICAL_EVENT, reasons).allow_permitted is False


def test_no_table_refuses_rather_than_permitting(tmp_path):
    from seshat.studio import approvals

    reasons = approvals.forbidden_scope_for(tmp_path, None)
    assert reasons != ()
    assert normalize_approval(TECHNICAL_EVENT, reasons).allow_permitted is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_approvals.py -k forbidden_scope -v --no-cov`
Expected: FAIL with `AttributeError: module 'seshat.studio.approvals' has no attribute 'forbidden_scope_for'`

- [ ] **Step 3: Write the minimal implementation**

Add to `src/seshat/studio/approvals.py` — extend the imports and `__all__`:

```python
from pathlib import Path

from seshat.agent_next import build_table_next_document
```

Add `"forbidden_scope_for"` to `__all__`, then append:

```python
def forbidden_scope_for(
    repo_root: Path | str, table: str | None
) -> tuple[str, ...]:
    """The readiness gate's forbidden-scope sentences for one table.

    **Fails CLOSED.** A lookup that raises, or a turn with no table in scope, returns
    a refusal sentence rather than an empty tuple -- because an empty tuple is how
    this module says "readiness forbids nothing", which would hand out an allow
    control on the strength of a crash. Reporting the error while continuing to
    refuse is the required posture.
    """
    if table is None:
        return (
            "No table is in scope for this turn, so its readiness gate could not be "
            "read; a technical allow is refused until one is named.",
        )
    try:
        document = build_table_next_document(repo_root, table)
    except Exception as failure:  # noqa: BLE001 -- any failure must refuse, not permit
        return (
            f"The readiness gate for {table!r} could not be read ({failure}); "
            "a technical allow is refused until it can be.",
        )
    return tuple(document.get("forbidden_scope", ()))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_approvals.py -v --no-cov`
Expected: PASS — 11 passed

- [ ] **Step 5: Lint, then commit**

```bash
ruff format src/seshat/studio/approvals.py tests/unit/test_studio_approvals.py
ruff check src/seshat/studio/approvals.py tests/unit/test_studio_approvals.py
git add src/seshat/studio/approvals.py tests/unit/test_studio_approvals.py
git commit --no-gpg-sign -m "feat: read readiness forbidden scope, failing closed (T025)"
```

---

### Task 3: Single-use decision ledger

**Files:**
- Modify: `src/seshat/studio/approvals.py`
- Test: `tests/unit/test_studio_approvals.py`

**Interfaces:**
- Consumes: `ApprovalEnvelope` from Task 1.
- Produces: `PendingApprovals` class with `register(envelope: ApprovalEnvelope) -> None`, `decide(approval_id: str, allow: bool) -> str` returning one of `"allowed"` / `"denied"`, and raising `StaleApproval` for unknown or already-decided ids. Exception class `StaleApproval(Exception)`.

- [ ] **Step 1: Write the failing tests**

```python
def test_an_allow_once_decision_is_recorded_once():
    from seshat.studio.approvals import PendingApprovals

    ledger = PendingApprovals()
    ledger.register(normalize_approval(TECHNICAL_EVENT, []))
    assert ledger.decide("turn-1-approval-1", allow=True) == "allowed"


def test_a_repeated_decision_is_refused():
    from seshat.studio.approvals import PendingApprovals, StaleApproval

    ledger = PendingApprovals()
    ledger.register(normalize_approval(TECHNICAL_EVENT, []))
    ledger.decide("turn-1-approval-1", allow=True)
    with pytest.raises(StaleApproval):
        ledger.decide("turn-1-approval-1", allow=True)


def test_an_unknown_approval_id_is_refused():
    from seshat.studio.approvals import PendingApprovals, StaleApproval

    ledger = PendingApprovals()
    with pytest.raises(StaleApproval):
        ledger.decide("never-registered", allow=True)


def test_a_deny_is_recorded_and_also_burns_the_id():
    from seshat.studio.approvals import PendingApprovals, StaleApproval

    ledger = PendingApprovals()
    ledger.register(normalize_approval(TECHNICAL_EVENT, []))
    assert ledger.decide("turn-1-approval-1", allow=False) == "denied"
    with pytest.raises(StaleApproval):
        ledger.decide("turn-1-approval-1", allow=False)


def test_a_never_allowable_envelope_cannot_be_allowed_through_the_ledger():
    from seshat.studio.approvals import PendingApprovals, StaleApproval

    ledger = PendingApprovals()
    ledger.register(normalize_approval(BUSINESS_EVENT, []))
    # The ledger is the second gate, not a bypass of the first.
    with pytest.raises(StaleApproval):
        ledger.decide("turn-1-approval-2", allow=True)
    # ...but denying a business item is fine: it records no governance ruling.
    assert ledger.decide("turn-1-approval-2", allow=False) == "denied"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_approvals.py -k ledger -v --no-cov`
Expected: FAIL with `ImportError: cannot import name 'PendingApprovals'`

- [ ] **Step 3: Write the minimal implementation**

Add `"PendingApprovals"` and `"StaleApproval"` to `__all__`, then append:

```python
class StaleApproval(Exception):
    """The decision does not correspond to a live, allowable approval request."""


class PendingApprovals:
    """Approvals awaiting a decision, each decidable exactly once.

    **Burning the id on ANY decision -- allow or deny -- is deliberate.** If only
    allows consumed the id, a denied request could be re-submitted as an allow, which
    turns "deny" into "ask again until it works". SC-005's allow-once is really
    decide-once.

    **`allow=True` on a non-allowable envelope raises rather than degrading to a
    deny.** Silently recording a deny would tell the caller their allow was
    processed. The refusal has to be audible.
    """

    def __init__(self) -> None:
        self._live: dict[str, ApprovalEnvelope] = {}
        self._decided: dict[str, str] = {}

    def register(self, envelope: ApprovalEnvelope) -> None:
        self._live[envelope.approval_id] = envelope

    def decide(self, approval_id: str, allow: bool) -> str:
        if approval_id in self._decided:
            raise StaleApproval(
                f"approval {approval_id!r} was already decided "
                f"({self._decided[approval_id]})"
            )
        envelope = self._live.get(approval_id)
        if envelope is None:
            raise StaleApproval(f"approval {approval_id!r} is not awaiting a decision")
        if allow and not envelope.allow_permitted:
            raise StaleApproval(
                f"approval {approval_id!r} may not be allowed here: "
                + "; ".join(envelope.forbidden_reasons or (envelope.authority,))
            )
        outcome = "allowed" if allow else "denied"
        self._decided[approval_id] = outcome
        del self._live[approval_id]
        return outcome
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_approvals.py -v --no-cov`
Expected: PASS — 16 passed

- [ ] **Step 5: Lint, then commit**

```bash
ruff format src/seshat/studio/approvals.py tests/unit/test_studio_approvals.py
ruff check src/seshat/studio/approvals.py tests/unit/test_studio_approvals.py
git add src/seshat/studio/approvals.py tests/unit/test_studio_approvals.py
git commit --no-gpg-sign -m "feat: decide each approval exactly once, refusing replays (T026)"
```

---

### Task 4: The relay route and the OpenAPI negative

**Files:**
- Modify: `src/seshat/studio/agent_routes.py` (add `_decide_approval`; register the route in `register_agent_routes`, alongside `interrupt_turn` at ~line 367)
- Modify: `src/seshat/studio/app.py:118-122` (`_bootstrap_capabilities`)
- Test: `tests/unit/test_studio_approval_routes.py`

**Interfaces:**
- Consumes: `PendingApprovals`, `StaleApproval` from Task 3.
- Produces: `POST {API_PREFIX}/agent/threads/{thread_id}/turns/{turn_id}/approvals/{approval_id}` accepting `{"allow": bool}`, returning 204 on success and a `Problem` on refusal. `app.state.pending_approvals: PendingApprovals`.

- [ ] **Step 1: Write the failing tests**

```python
"""Route-level tests for the approval relay (T026, T027)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")  # CI's unit job installs no app extras

from fastapi.testclient import TestClient

from seshat.studio.app import create_app
from seshat.studio.approvals import normalize_approval

TECHNICAL_EVENT = {
    "approval_id": "turn-1-approval-1",
    "required_authority": "technical",
    "action": "run_command",
    "target": "pytest -q",
    "reason": "Verify the mapping change",
    "scope": "read_only",
    "risk": "low",
}


def test_the_openapi_schema_exposes_no_business_approval_endpoint():
    app = create_app()
    paths = app.openapi()["paths"]
    offenders = [
        path
        for path in paths
        if "business" in path.lower() or "decision" in path.lower()
    ]
    assert offenders == []
    # Positive form: the ONE approval route that exists is the technical relay.
    approval_paths = [p for p in paths if "approval" in p.lower()]
    assert approval_paths == [
        "/api/v1/agent/threads/{thread_id}/turns/{turn_id}/approvals/{approval_id}"
    ]


def test_business_decision_recording_stays_false_while_technical_turns_true():
    from seshat.studio.app import _bootstrap_capabilities

    capabilities = _bootstrap_capabilities()
    assert capabilities["technical_approvals"] is True
    assert capabilities["business_decision_recording"] is False


def test_an_unknown_approval_id_is_refused_with_a_problem():
    app = create_app()
    app.state.pending_approvals.register(normalize_approval(TECHNICAL_EVENT, []))
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/api/v1/agent/threads/t1/turns/turn-1/approvals/never-registered",
        json={"allow": True},
    )
    assert response.status_code == 409
    assert "recovery_action" in response.json()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_approval_routes.py -v --no-cov`
Expected: FAIL — the approval path is absent from OpenAPI, and `app.state.pending_approvals` does not exist.

- [ ] **Step 3: Write the minimal implementation**

In `src/seshat/studio/app.py`, flip the one flag in `_bootstrap_capabilities` (leave `business_decision_recording` alone):

```python
        "technical_approvals": True,
```

Where the app wires `app.state` (beside `app.state.pending_turns`), add:

```python
    app.state.pending_approvals = PendingApprovals()
```

with `from seshat.studio.approvals import PendingApprovals` at the top of `app.py`.

In `src/seshat/studio/agent_routes.py`, add the handler next to `_interrupt_turn`:

```python
def _decide_approval(
    app: FastAPI, thread_id: str, approval_id: str, body: dict[str, Any]
) -> Response:
    """Relay one analyst decision to the bridge.

    The browser sends a decision and nothing else -- no tool runs here, no artifact is
    written (FR-020). Every refusal path returns a Problem rather than a silent
    no-op, because an approval that appears to succeed and does nothing is worse than
    one that visibly fails.
    """
    if not app.state.threads.has_thread(thread_id):
        return _unknown_thread()
    try:
        outcome = app.state.pending_approvals.decide(
            approval_id, allow=bool(body.get("allow", False))
        )
    except StaleApproval as refused:
        return _problem(
            409,
            "That approval is not awaiting your decision",
            str(refused),
            "Re-read the current approval request; a decision already recorded "
            "cannot be changed here.",
        )
    app.state.threads.thread(thread_id).record_approval(approval_id, outcome)
    return Response(status_code=204)
```

Import `StaleApproval` at the top of `agent_routes.py`:

```python
from seshat.studio.approvals import StaleApproval
```

Register it inside `register_agent_routes`, after `interrupt_turn`:

```python
    @app.post(
        f"{API_PREFIX}/agent/threads/{{thread_id}}/turns/{{turn_id}}"
        f"/approvals/{{approval_id}}",
        status_code=204,
    )
    async def decide_approval(
        thread_id: str, turn_id: str, approval_id: str, body: dict[str, Any]
    ) -> Response:
        return _decide_approval(app, thread_id, approval_id, body)
```

If `record_approval` does not exist on the thread object, add it to the thread store class as a method that appends `(approval_id, outcome)` to the thread's activity and leaves the readiness state untouched.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_approval_routes.py -v --no-cov`
Expected: PASS — 3 passed

- [ ] **Step 5: Lint, then commit**

```bash
ruff format src/seshat/studio/ tests/unit/test_studio_approval_routes.py
ruff check src/seshat/studio/ tests/unit/test_studio_approval_routes.py
git add src/seshat/studio/agent_routes.py src/seshat/studio/app.py tests/unit/test_studio_approval_routes.py
git commit --no-gpg-sign -m "feat: relay one technical approval decision to the bridge (T026, T027)"
```

---

### Task 5: Pause the turn, and prove the boundary end to end

**Files:**
- Modify: `src/seshat/studio/agent_routes.py` (the `_pump_turn` path at ~line 443)
- Test: `tests/unit/test_studio_approval_routes.py`

**Interfaces:**
- Consumes: everything above.
- Produces: a turn that reports `awaiting_technical_approval` while an allowable approval is live.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_live_technical_approval_pauses_the_turn():
    app = create_app()
    app.state.pending_approvals.register(normalize_approval(TECHNICAL_EVENT, []))
    # The state must be the one the contract already names -- not a new string.
    from seshat.studio.agent_routes import THREAD_STATES

    assert "awaiting_technical_approval" in THREAD_STATES


def test_a_named_human_approval_never_becomes_allowable_through_the_route():
    business = {
        "approval_id": "turn-1-approval-2",
        "required_authority": "named_human",
        "action": "apply_change",
        "target": "mappings/example/source-map.yaml",
        "reason": "Add the missing grain declaration",
        "scope": "propose_changes",
        "risk": "high",
    }
    app = create_app()
    app.state.pending_approvals.register(normalize_approval(business, []))
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/api/v1/agent/threads/t1/turns/turn-1/approvals/turn-1-approval-2",
        json={"allow": True},
    )
    # 404 (no such thread) or 409 (refused) are both acceptable refusals;
    # 204 would mean Studio granted a governance ruling.
    assert response.status_code != 204
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_approval_routes.py -v --no-cov`
Expected: FAIL on the pause assertion if the state is not reported.

- [ ] **Step 3: Write the minimal implementation**

In `_pump_turn`, when an emitted event's type is `approval_required`, normalize it with `normalize_approval(payload, forbidden_scope_for(app.state.repo_root, table))`, register the envelope on `app.state.pending_approvals`, and set the thread's state to `awaiting_technical_approval` when `envelope.allow_permitted` is true. When it is false, emit the event as inert activity exactly as Phase 4 did — no state change, no control.

- [ ] **Step 4: Run the whole Studio suite**

Run: `PYTHONPATH=src python -m pytest tests/unit/ -k studio -q --no-cov`
Expected: PASS, with no previously-passing test now failing. In particular the Phase 4 test that pins the ABSENCE of an approve control for `named_human` must still pass — if it fails, the boundary was crossed; fix the code, not that test.

- [ ] **Step 5: Full gate, then commit**

```bash
ruff format --check src/ tests/
ruff check src/ tests/
PYTHONPATH=src python -m pytest -m unit -q
PYTHONPATH=src python -m seshat.cli check
git add -A
git commit --no-gpg-sign -m "feat: pause a turn on a live technical approval (T024)"
```

---

### Task 6: Record the evidence, do not tick the boxes

**Files:**
- Modify: `specs/139-seshat-studio-foundation/tasks.md` (T024–T027 block)

- [ ] **Step 1: Append an evidence note under T027**

Record the date, the suites run, their pass counts, and the invariants proven. Leave every `- [ ]` unchecked: a human closes tasks in this repo, and a bulk checkbox sweep is a known failure here.

- [ ] **Step 2: Verify the gate still passes and counts are unchanged**

```bash
PYTHONPATH=src python -m seshat.cli check
grep -c '^- \[ \]' specs/139-seshat-studio-foundation/tasks.md
```
Expected: `check` exits 0; the open count is unchanged from before this task.

- [ ] **Step 3: Commit**

```bash
git add specs/139-seshat-studio-foundation/tasks.md
git commit --no-gpg-sign -m "docs: record Phase 6 approval-boundary evidence without closing the tasks"
```

---

## Self-Review

**Spec coverage:** FR-018 → Tasks 1, 2, 5 (scope evaluated before exposure). FR-019 → Task 1 (five display fields). FR-020 → Task 4 (relay only, no browser side effect). FR-021 → Tasks 1, 3, 5 (technical allow cannot override readiness or a named-human stop). FR-022 → Tasks 3, 4 (no business recording; capability const false; OpenAPI negative). SC-005 → Task 3 (decide-once). T024 tests → Tasks 1–5. T025 → Tasks 1–2. T026 → Tasks 3–4. T027 → Task 4.

**Placeholder scan:** none — every code step carries real code. Task 5 Step 3 describes an edit to an existing function whose exact body depends on `_pump_turn`'s current shape; the executor reads it at `agent_routes.py:443` and the acceptance criterion is pinned by the tests in Step 1 and the Phase 4 regression in Step 4.

**Type consistency:** `ApprovalEnvelope`, `normalize_approval`, `forbidden_scope_for`, `PendingApprovals.register`, `PendingApprovals.decide`, `StaleApproval` are named identically in every task that uses them. `decide` returns `"allowed"` / `"denied"` throughout.

**Known follow-up:** `record_approval` on the thread store is conditional in Task 4 Step 3 — if absent, the executor adds it. Flagged rather than hidden.
