"""`CodexBridge` maps a real child's frames onto Studio events.

Driven against the scripted child, so the mapping is exercised over a real pipe
rather than a hand-built frame list. A mock cannot deadlock, and deadlock is the
risk this layer actually carries.
"""

from __future__ import annotations

import queue
import sys
import unittest.mock
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SCRIPT = Path(__file__).parent / "_codex_child_script.py"


def _bridge(tmp_path: Path, fixture: str = "thread_turn"):
    from seshat.studio.codex_bridge import CodexBridge
    from seshat.studio.codex_process import CodexLaunchPlan

    plan = CodexLaunchPlan(argv=(sys.executable, str(_SCRIPT), fixture), cwd=tmp_path)
    return CodexBridge(plan)


def test_a_turn_starts_and_ends_with_exactly_one_terminal(tmp_path: Path) -> None:
    events = list(
        _bridge(tmp_path).run_turn(
            prompt="Summarise the readiness spine",
            turn_id="turn-1",
            requested_mode="read_only",
        )
    )

    assert events, "the bridge produced no events"
    assert events[0].type == "turn_started"
    terminals = [e for e in events if e.type in {"turn_completed", "turn_failed"}]
    assert len(terminals) == 1, f"expected one terminal, got {len(terminals)}"
    assert events[-1].type in {"turn_completed", "turn_failed"}


def test_the_bridge_describes_itself_as_codex(tmp_path: Path) -> None:
    described = _bridge(tmp_path).describe()
    assert described["provider"] == "codex"


def test_an_unknown_mode_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        list(
            _bridge(tmp_path).run_turn(
                prompt="hello", turn_id="t", requested_mode="wat"
            )
        )


def test_a_crashed_child_still_yields_exactly_one_terminal(tmp_path: Path) -> None:
    """EOF without a terminal frame is a FAILURE, never a quiet success.

    The plan's three tests above all drive the happy `thread_turn` fixture, where
    the child sends its own terminal frame -- so the `saw_terminal` fallback that
    exists precisely for the crash path is never exercised by them. This drives
    `--crash-after`, where the child dies mid-stream: the turn must still close,
    and it must close as `turn_failed` rather than `turn_completed`.
    """
    events = list(
        _bridge(tmp_path, "thread_turn").run_turn(
            prompt="Summarise the readiness spine",
            turn_id="turn-crash",
            requested_mode="read_only",
        )
    )
    assert events[-1].type in {"turn_completed", "turn_failed"}

    crashed = list(
        _crashing_bridge(tmp_path).run_turn(
            prompt="Summarise the readiness spine",
            turn_id="turn-crash-2",
            requested_mode="read_only",
        )
    )

    terminals = [e for e in crashed if e.type in {"turn_completed", "turn_failed"}]
    assert len(terminals) == 1, f"expected one terminal, got {len(terminals)}"
    assert terminals[0].type == "turn_failed", (
        "a child that died mid-stream was reported as a completed turn"
    )


def _crashing_bridge(tmp_path: Path):
    from seshat.studio.codex_bridge import CodexBridge
    from seshat.studio.codex_process import CodexLaunchPlan

    plan = CodexLaunchPlan(
        argv=(sys.executable, str(_SCRIPT), "thread_turn", "--crash-after", "2"),
        cwd=tmp_path,
    )
    return CodexBridge(plan)


class _WriteIntentBridge:
    """Stands in for a provider that proposes a change during `read_only`.

    Deliberately NOT `CodexBridge`: the point is to prove the ROUTE refuses write
    intent no matter which bridge produced it. Using the real bridge would make the
    test pass whenever the fixture happened not to propose, which proves nothing
    about the guard.
    """

    def describe(self) -> dict[str, object]:
        return {"bridge": "codex", "provider": "codex", "deterministic": False}

    def run_turn(self, *, prompt: str, turn_id: str, requested_mode: str):
        from seshat.studio.bridge import _event

        yield _event("turn_started", {"prompt_echo": prompt[:200]}, turn_id, 1)
        yield _event(
            "file_change_proposed",
            {"paths": ["silver/model.sql"], "summary": "1 file change proposed"},
            turn_id,
            2,
        )


def _pump_to_end(app, thread_id: str, thread) -> list:
    """Drive `_pump_turn` until the turn ends, returning the thread's events."""
    import asyncio

    from seshat.studio.agent_routes import _pump_turn

    for _ in range(40):
        asyncio.run(_pump_turn(app, thread_id, thread))
        if thread_id not in app.state.pending_turns:
            break
    return list(thread.retained())


class _FakeApp:
    """Just the two `app.state` slots the pump reads."""

    def __init__(self, bridge, thread_id: str, request) -> None:
        self.state = type("S", (), {})()
        self.state.bridge = bridge
        import asyncio
        import queue

        from seshat.studio.agent_routes import _PendingTurn

        self.state.pending_turns = {
            thread_id: _PendingTurn(
                events=bridge.run_turn(
                    prompt=request.prompt,
                    turn_id=request.turn_id,
                    requested_mode=request.requested_mode,
                ),
                request=request,
                pumping=asyncio.Lock(),
                last_touched=0.0,
                results=queue.Queue(),
            )
        }


def test_write_intent_from_the_real_bridge_is_refused_under_read_only() -> None:
    """`bridge.py` is explicit that the refusal binds at the ROUTE, not the bridge.

    A bridge that never passed through it would inherit no protection at all -- the
    exact defect that docstring records for an earlier revision. So this drives the
    real pump with a stream that DOES carry write intent and asserts the write intent
    never reaches the buffer, rather than inspecting the bridge's output and
    inferring safety.

    Drives `_pump_turn` because that is where the refusal now lives: turns are
    ACCEPTED and advanced on the poll loop, so `_record_turn` -- which used to raise
    a 502 -- no longer exists. A test still pinning it would pin a function nothing
    calls.
    """
    pytest.importorskip("fastapi")
    from seshat.studio.agent_routes import TurnRequest
    from seshat.studio.events import ThreadEvents

    thread = ThreadEvents("thread-1")
    request = TurnRequest(
        prompt="Propose the silver model", turn_id="t1", requested_mode="read_only"
    )
    app = _FakeApp(_WriteIntentBridge(), "thread-1", request)

    recorded = _pump_to_end(app, "thread-1", thread)

    types = [event.type for event in recorded]
    assert "file_change_proposed" not in types, types
    assert "turn_failed" in types, types
    categories = [
        event.payload.get("category")
        for event in recorded
        if event.type == "turn_failed"
    ]
    assert "read_only_violation" in categories, categories


def test_the_guard_is_what_refuses_not_the_bridge() -> None:
    """Prove the refusal comes from the route, by disabling only the guard.

    If the assertion above passed because the bridge declined to emit write intent,
    this would still pass -- so it empties `WRITE_INTENT_TYPES` and asserts the SAME
    stream is then recorded without complaint. That is the positive evidence that the
    route, not the bridge, is what refuses.
    """
    pytest.importorskip("fastapi")
    import seshat.studio.agent_routes as routes
    from seshat.studio.events import ThreadEvents

    original = routes.WRITE_INTENT_TYPES
    try:
        routes.WRITE_INTENT_TYPES = frozenset()
        thread = ThreadEvents("thread-2")
        request = routes.TurnRequest(
            prompt="Propose the silver model", turn_id="t2", requested_mode="read_only"
        )
        app = _FakeApp(_WriteIntentBridge(), "thread-2", request)
        recorded = _pump_to_end(app, "thread-2", thread)
    finally:
        routes.WRITE_INTENT_TYPES = original

    assert any(event.type == "file_change_proposed" for event in recorded), (
        "with the guard disabled the write intent should have been recorded; if it "
        "was not, the first test proved nothing about the guard"
    )


def test_a_turn_completes_without_waiting_for_the_child_to_exit(
    tmp_path: Path,
) -> None:
    """P1 (#617 review): a real app-server is LONG-LIVED and never closes stdout.

    Every other test here drives a child that exits when its fixture runs out, so
    the loop ended because of EOF rather than because the bridge stopped reading
    at the terminal. A live server would keep the pipe open, and the bridge would
    block on the next frame until `frames()` timed out -- turning a COMPLETED turn
    into a stalled request.

    `--stay-open` models that: the child sleeps instead of exiting. The turn must
    still finish, and it must finish fast, so the assertion is on WALL CLOCK as
    well as on the events. Without the `break`, this hangs for the full 30s
    `frames()` timeout and then raises `queue.Empty`.
    """
    import sys
    import time

    from seshat.studio.codex_bridge import CodexBridge
    from seshat.studio.codex_process import CodexLaunchPlan

    bridge = CodexBridge(
        CodexLaunchPlan(
            argv=(sys.executable, str(_SCRIPT), "thread_turn", "--stay-open"),
            cwd=tmp_path,
        )
    )

    started = time.monotonic()
    events = list(
        bridge.run_turn(
            prompt="Summarise the readiness spine",
            turn_id="turn-open",
            requested_mode="read_only",
        )
    )
    elapsed = time.monotonic() - started

    assert elapsed < 20.0, (
        f"the turn took {elapsed:.1f}s against a child that never closes stdout; "
        "the bridge kept reading after the terminal event"
    )
    terminals = [e for e in events if e.type in {"turn_completed", "turn_failed"}]
    assert len(terminals) == 1, f"expected one terminal, got {len(terminals)}"
    assert terminals[0].type == "turn_completed"


def test_the_bridge_asks_the_provider_for_a_turn(tmp_path: Path) -> None:
    """P1 (#617 review): the app-server emits NOTHING until it is asked.

    The scripted child replays its fixture unprompted and never reads stdin, so a
    bridge that only LISTENED passed every fixture test while producing nothing
    from a live server. This asserts the requests are actually written, by
    capturing what the session sends.

    Checked as an ordered method sequence rather than by exact payload: the shapes
    come from the committed fixture, and pinning them twice would just restate the
    fixture. What matters is that the handshake precedes the turn request.
    """
    from seshat.studio.codex_bridge import CodexBridge, CodexSession
    from seshat.studio.codex_process import CodexLaunchPlan

    sent: list[dict] = []

    class _RecordingSession(CodexSession):
        def send(self, frame: dict) -> None:  # type: ignore[override]
            sent.append(frame)

    bridge = CodexBridge(
        CodexLaunchPlan(
            argv=(sys.executable, str(_SCRIPT), "thread_turn"), cwd=tmp_path
        )
    )

    # Drive the REAL `run_turn`, with the session class swapped -- not
    # `_request_turn` directly. Calling the helper would assert only that it
    # composes the right frames, and would keep passing if `run_turn` stopped
    # CALLING it, which is precisely the defect under test.
    monkeypatch_target = "seshat.studio.codex_bridge.CodexSession"
    import unittest.mock

    with unittest.mock.patch(monkeypatch_target, _RecordingSession):
        list(
            bridge.run_turn(
                prompt="Summarise the readiness spine",
                turn_id="turn-ask",
                requested_mode="read_only",
            )
        )

    assert [frame.get("method") for frame in sent] == [
        "initialize",
        "initialized",
        "thread/start",
        "turn/start",
    ], "the provider was not asked for a turn in the order the protocol requires"

    turn_start = sent[-1]
    assert turn_start["params"]["input"] == [
        {"type": "text", "text": "Summarise the readiness spine"}
    ], "the validated prompt never reached the provider"
    assert turn_start["params"]["sandboxPolicy"]["type"] == "readOnly"
    # The id must be the one the PROVIDER minted in its `thread/start` reply, not a
    # value we chose. A live server rejects any other, and the fixture's own
    # `turn/start` carries `thr_fixture` whether or not the bridge read it back.
    assert turn_start["params"]["threadId"] == "thr_fixture", (
        "turn/start used a thread id the provider never issued"
    )


def test_a_session_read_failure_still_ends_the_turn(tmp_path: Path) -> None:
    """P1 (#617 review): a read failure must still produce ONE terminal event.

    `frames()` raises `queue.Empty` when the provider stalls and `CodexFrameError`
    on malformed output. If either escaped `run_turn`, the consumer would hold a
    `turn_started` with no terminal -- breaking the contract the shared suite pins
    as "exactly one terminal event last". Worse, the route pump would have no
    around this drain, so it would surface as a 500 AND leave `_active_turn` set,
    wedging every later turn on that thread as already-active.

    Driven by making the session raise mid-stream, which is what both real failure
    modes look like from here.
    """
    from seshat.studio.codex_bridge import CodexBridge, CodexSession
    from seshat.studio.codex_process import CodexLaunchPlan

    class _FailingSession(CodexSession):
        def frames(self, timeout: float = 30.0):  # type: ignore[override]
            raise queue.Empty  # the provider stalled
            yield  # pragma: no cover -- keeps this a generator

    bridge = CodexBridge(
        CodexLaunchPlan(
            argv=(sys.executable, str(_SCRIPT), "thread_turn"), cwd=tmp_path
        )
    )

    with unittest.mock.patch(
        "seshat.studio.codex_bridge.CodexSession", _FailingSession
    ):
        events = list(
            bridge.run_turn(
                prompt="Summarise the readiness spine",
                turn_id="turn-fail",
                requested_mode="read_only",
            )
        )

    terminals = [e for e in events if e.type in {"turn_completed", "turn_failed"}]
    assert len(terminals) == 1, (
        f"a read failure produced {len(terminals)} terminals; the turn must end "
        "exactly once even when the session raises"
    )
    assert terminals[0].type == "turn_failed"
    assert terminals[0].payload["category"] == "provider_error"
    # The exception TYPE, never its text: provider messages can carry paths or
    # tokens, and this payload is retained.
    assert "Empty" in terminals[0].payload["detail"]


def test_a_failed_process_start_still_ends_the_turn(tmp_path: Path) -> None:
    """P1 (#617 review): a missing or non-executable binary must not escape.

    `start()` used to sit OUTSIDE the guard, so a `Popen` failure raised after
    `turn_started` had already been yielded and recorded: a 500 with no terminal,
    leaving `ThreadEvents._active_turn` set so every later turn on that Studio
    thread is refused as already-active. This is the likeliest real failure of
    the lot -- it happens whenever the configured executable is wrong.

    `close()` must also tolerate a session that never started, which the `finally`
    exercises here.
    """
    from seshat.studio.codex_bridge import CodexBridge
    from seshat.studio.codex_process import CodexLaunchPlan

    missing = tmp_path / "definitely-not-a-real-codex-binary"
    bridge = CodexBridge(CodexLaunchPlan(argv=(str(missing),), cwd=tmp_path))

    events = list(
        bridge.run_turn(
            prompt="Summarise the readiness spine",
            turn_id="turn-nostart",
            requested_mode="read_only",
        )
    )

    assert events[0].type == "turn_started"
    terminals = [e for e in events if e.type in {"turn_completed", "turn_failed"}]
    assert len(terminals) == 1, (
        f"a failed process start produced {len(terminals)} terminals; the turn must "
        "still end exactly once"
    )
    assert terminals[0].type == "turn_failed"
    assert terminals[0].payload["category"] == "provider_error"


def test_thread_start_uses_the_workspace_the_child_runs_in(tmp_path: Path) -> None:
    """P2 (#617 review): the process, provider thread, and redaction must agree.

    `_plan_for()` may select the propose plan, which can carry a different `cwd`.
    `_open_thread` hardcoded `self._plan.cwd`, so the provider would read and
    propose in the PRIMARY workspace while the child ran -- and normalization
    redacted -- against the alternate one.
    """
    from seshat.studio.codex_bridge import CodexBridge, CodexSession
    from seshat.studio.codex_process import CodexLaunchPlan

    primary = tmp_path / "primary"
    alternate = tmp_path / "alternate"
    primary.mkdir()
    alternate.mkdir()

    sent: list[dict] = []

    class _RecordingSession(CodexSession):
        def send(self, frame: dict) -> None:  # type: ignore[override]
            sent.append(frame)

    bridge = CodexBridge(
        CodexLaunchPlan(
            argv=(sys.executable, str(_SCRIPT), "thread_turn"), cwd=primary
        ),
        propose_plan=CodexLaunchPlan(
            argv=(sys.executable, str(_SCRIPT), "file_change_turn"), cwd=alternate
        ),
    )

    with unittest.mock.patch(
        "seshat.studio.codex_bridge.CodexSession", _RecordingSession
    ):
        list(
            bridge.run_turn(
                prompt="fix the silver model",
                turn_id="turn-cwd",
                requested_mode="propose_changes",
            )
        )

    thread_start = next(f for f in sent if f.get("method") == "thread/start")
    assert thread_start["params"]["cwd"] == str(alternate), (
        "thread/start pinned the provider to a workspace the child does not run in"
    )


def test_no_thread_is_requested_until_initialize_is_answered(tmp_path: Path) -> None:
    """P1 (#621 review): `initialize -> response -> initialized`, in that order.

    The contract and the captured probe both require negotiation to COMPLETE before
    any thread request. The old code wrote all three frames back to back without
    reading the reply, which the scripted child cannot expose: it replays its fixture
    regardless of what it is asked, so the write ORDER looks identical either way.

    The observable difference is timing relative to the reply, so this drives a
    fixture with NO initialize response. A bridge that waits sends only `initialize`;
    one that races sends `initialized` and `thread/start` too.
    """
    import unittest.mock

    from seshat.studio.codex_bridge import CodexBridge, CodexSession
    from seshat.studio.codex_process import CodexLaunchPlan

    sent: list[str | None] = []

    class _RecordingSession(CodexSession):
        def send(self, frame: dict) -> None:  # type: ignore[override]
            sent.append(frame.get("method"))

    # `quota` never answers our `initialize` (id 1): it carries only notifications
    # and an unrelated reply, which is exactly the shape of a provider that has not
    # finished negotiating.
    bridge = CodexBridge(
        CodexLaunchPlan(argv=(sys.executable, str(_SCRIPT), "quota"), cwd=tmp_path)
    )
    with unittest.mock.patch(
        "seshat.studio.codex_bridge.CodexSession", _RecordingSession
    ):
        list(
            bridge.run_turn(
                prompt="Summarise the readiness spine",
                turn_id="turn-handshake",
                requested_mode="read_only",
            )
        )

    assert sent == ["initialize"], (
        "a thread was requested before initialization was answered; the protocol "
        f"requires initialize -> response -> initialized, but sent {sent}"
    )
