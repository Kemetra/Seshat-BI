"""`CodexBridge` maps a real child's frames onto Studio events.

Driven against the scripted child, so the mapping is exercised over a real pipe
rather than a hand-built frame list. A mock cannot deadlock, and deadlock is the
risk this layer actually carries.
"""

from __future__ import annotations

import sys
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


def test_write_intent_from_the_real_bridge_is_refused_under_read_only() -> None:
    """`bridge.py` is explicit that the BINDING refusal lives in `_record_turn`.

    A bridge that never passed through it would inherit no protection at all -- the
    exact defect that docstring records for an earlier revision. So this drives the
    real route helper with a stream that DOES carry write intent and asserts the
    refusal fires, rather than inspecting the bridge's output and inferring safety.
    """
    pytest.importorskip("fastapi")
    from seshat.studio.agent_routes import ReadOnlyViolation, TurnRequest, _record_turn
    from seshat.studio.events import ThreadEvents

    thread = ThreadEvents("thread-1")
    request = TurnRequest(
        prompt="Propose the silver model", turn_id="t1", requested_mode="read_only"
    )

    with pytest.raises(ReadOnlyViolation):
        _record_turn(thread, _WriteIntentBridge(), request)


def test_the_guard_is_what_refuses_not_the_bridge() -> None:
    """Prove the refusal comes from the route, by disabling only the guard.

    If the assertion above passed because the bridge declined to emit write intent,
    this would still pass -- so it monkeypatches `WRITE_INTENT_TYPES` to empty and
    asserts the SAME stream is then recorded without complaint. That is the positive
    evidence that `_record_turn` is the thing doing the refusing.
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
        recorded = routes._record_turn(thread, _WriteIntentBridge(), request)
    finally:
        routes.WRITE_INTENT_TYPES = original

    assert any(event.type == "file_change_proposed" for event in recorded), (
        "with the guard disabled the write intent should have been recorded; if it "
        "was not, the first test proved nothing about the guard"
    )
