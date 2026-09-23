"""Two overlapping Codex turns must not share per-turn state (audit batch 12).

`app.state.bridge` is ONE `CodexBridge` shared by every thread, and `run_turn` is a
lazy generator. Anything a turn stores on the bridge is therefore read by whichever
turn advances next -- so each turn's session callback and undecided-approval set
must belong to the turn itself.

The provider is a scripted stand-in for `CodexSession`: these tests are about which
turn owns which state, not about the wire protocol, which the codex_bridge suite
already pins against the committed fixtures.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from seshat.studio import codex_bridge
from seshat.studio.codex_process import CodexLaunchPlan

pytestmark = pytest.mark.unit

_APPROVAL = {
    "jsonrpc": "2.0",
    "id": 20,
    "method": "item/commandExecution/requestApproval",
    "params": {"itemId": "item_cmd_approval", "command": "ls", "reason": "look"},
}


class _ScriptedSession:
    """Replays the handshake, then one approval request, then waits forever."""

    instances: list[_ScriptedSession] = []

    def __init__(self, plan: Any) -> None:
        self.plan = plan
        self.patience_seen: list[float] = []
        self.closed = False
        _ScriptedSession.instances.append(self)

    def start(self) -> None:
        return None

    def send(self, frame: dict[str, Any]) -> None:
        return None

    def close(self) -> None:
        self.closed = True

    def frames(self, timeout: float = 0.0, *, patience=None):
        script = [
            {"id": 1, "result": {}},
            {"id": 2, "result": {"thread": {"id": "thr_x"}}},
            _APPROVAL,
            {"method": "item/agentMessage/delta", "params": {"delta": "x"}},
        ]
        for frame in script:
            self.patience_seen.append(patience())
            yield frame


@pytest.fixture
def bridge(monkeypatch: pytest.MonkeyPatch) -> codex_bridge.CodexBridge:
    _ScriptedSession.instances = []
    monkeypatch.setattr(codex_bridge, "CodexSession", _ScriptedSession)
    plan = CodexLaunchPlan(argv=(sys.executable, "-c", "pass"), cwd=Path.cwd())
    return codex_bridge.CodexBridge(plan, idle_timeout=1.0, approval_timeout=300.0)


def _advance_to_approval(turn) -> None:
    for event in turn:
        if event.type == "approval_required":
            return
    raise AssertionError("the turn never raised its approval")


def test_each_turn_registers_its_own_session(bridge):
    seen_a: list[Any] = []
    seen_b: list[Any] = []
    turn_a = bridge.run_turn(
        prompt="a", turn_id="A", requested_mode="read_only", on_session=seen_a.append
    )
    turn_b = bridge.run_turn(
        prompt="b", turn_id="B", requested_mode="read_only", on_session=seen_b.append
    )
    next(turn_a)
    next(turn_b)  # B is created AFTER A: the order the cross-wire needed

    _advance_to_approval(turn_a)
    _advance_to_approval(turn_b)

    session_a, session_b = _ScriptedSession.instances
    assert seen_a == [session_a]
    assert seen_b == [session_b]
    turn_a.close()
    assert seen_a == [session_a, None]
    assert seen_b == [session_b], "ending turn A retracted turn B's session"


def test_starting_a_second_turn_keeps_the_first_turns_approval_budget(bridge):
    turn_a = bridge.run_turn(prompt="a", turn_id="A", requested_mode="read_only")
    _advance_to_approval(turn_a)

    turn_b = bridge.run_turn(prompt="b", turn_id="B", requested_mode="read_only")
    next(turn_b)  # B opens while A is blocked on its approval
    next(turn_a)  # A's next read

    session_a = _ScriptedSession.instances[0]
    assert session_a.patience_seen[-1] == bridge.approval_timeout, (
        "turn B reset turn A's undecided approvals, shrinking A's patience to the "
        "idle budget while its analyst was still reading the approval"
    )


def test_a_retracted_publisher_never_pops_a_newer_registration():
    """Keyed by thread, checked by identity: a late retract cannot evict a successor."""
    from types import SimpleNamespace

    pytest.importorskip("fastapi")  # agent_routes needs the app extra
    from seshat.studio import agent_routes

    app = SimpleNamespace(state=SimpleNamespace(provider_sessions={}))
    older = agent_routes._session_publisher(app, "thread-1")
    newer = agent_routes._session_publisher(app, "thread-1")
    first, second = object(), object()

    older(first)
    newer(second)
    older(None)

    assert app.state.provider_sessions == {"thread-1": second}
    newer(None)
    assert app.state.provider_sessions == {}
