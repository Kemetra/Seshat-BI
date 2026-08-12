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
