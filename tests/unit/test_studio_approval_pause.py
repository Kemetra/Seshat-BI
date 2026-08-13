"""A turn paused on an approval must outlive the stalled-provider timeout.

`CodexSession.frames()` bounds its wait so a wedged child cannot pin a reader thread
forever -- a real protection worth keeping. But it could not tell two very different
silences apart:

* the provider is hung or dead -- fail fast, that is what the bound is FOR;
* the provider is BLOCKED on `requestApproval` and is correctly waiting for a human.

Both looked identical, so a paused turn died with
`turn_failed / provider_error / "the provider session failed: Empty"` -- blaming the
provider for a person reading an approval panel, and violating FR-024's requirement
that states be distinct and carry their own recovery action.

The windows here are set to fractions of a second. A test that actually waited 30s
would be too slow to run and would prove the same thing.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from seshat.studio.codex_bridge import CodexBridge, CodexSession
from seshat.studio.codex_process import CodexLaunchPlan

_CHILD = Path(__file__).parent / "_codex_child_script.py"


def _plan(tmp_path: Path, fixture: str, *, stay_open: bool = True) -> CodexLaunchPlan:
    """A child that replays `fixture` then goes SILENT rather than reaching EOF.

    Silence is the whole point: EOF is a different path (`_EOF` -> return -> "no
    terminal" -> `provider_error`) that would exercise none of this.
    """
    argv: tuple[str, ...] = (sys.executable, str(_CHILD), fixture)
    if stay_open:
        argv += ("--stay-open",)
    return CodexLaunchPlan(argv=argv, cwd=tmp_path)


def _drain(bridge: CodexBridge, mode: str = "read_only") -> list[Any]:
    return list(
        bridge.run_turn(prompt="check the grain", turn_id="t1", requested_mode=mode)
    )


def _terminal(events: list[Any]) -> Any:
    terminals = [e for e in events if e.type in {"turn_completed", "turn_failed"}]
    assert len(terminals) == 1, f"expected exactly one terminal, got {len(terminals)}"
    return terminals[0]


# --------------------------------------------------------------------------- #
# The two silences must be told apart                                         #
# --------------------------------------------------------------------------- #


def test_a_silent_provider_with_no_approval_still_fails_fast(tmp_path: Path):
    """The protection this bound exists for must survive the fix.

    A child that says nothing and is not awaiting a decision is wedged. It must fail
    on the SHORT window, not linger for the patient one -- otherwise the fix trades a
    dying turn for a pinned reader thread.
    """
    # `handshake` negotiates and then stops -- no approval, no terminal, just silence.
    bridge = CodexBridge(_plan(tmp_path, "handshake"), idle_timeout=0.3)

    events = _drain(bridge)

    terminal = _terminal(events)
    assert terminal.type == "turn_failed"
    assert terminal.payload["category"] == "provider_error"


def test_a_turn_paused_on_an_approval_outlives_the_idle_window(tmp_path: Path):
    """The defect: a human reading the panel used to kill the turn.

    The child emits `requestApproval` and then goes silent. With the idle window far
    below the paused window, an unfixed build fails as `provider_error` almost
    immediately; a fixed one is still waiting when the paused window finally expires,
    and says so in its own words.
    """
    bridge = CodexBridge(
        _plan(tmp_path, "approvals"), idle_timeout=0.3, approval_timeout=2.0
    )

    events = _drain(bridge)

    assert any(e.type == "approval_required" for e in events), (
        "the fixture must actually raise an approval, or this proves nothing"
    )
    terminal = _terminal(events)
    assert terminal.payload["category"] != "provider_error", (
        "a turn waiting on a HUMAN was reported as a provider failure -- the defect"
    )
    assert terminal.payload["category"] == "approval_not_decided"


def test_the_paused_failure_names_a_recovery_the_analyst_can_act_on(tmp_path: Path):
    """FR-024: distinct states carry distinct recovery actions.

    "the provider session failed: Empty" tells an analyst nothing they can act on.
    An approval that expired undecided has an obvious next step, and the detail must
    carry it.
    """
    bridge = CodexBridge(
        _plan(tmp_path, "approvals"), idle_timeout=0.3, approval_timeout=1.0
    )

    detail = _terminal(_drain(bridge)).payload["detail"]

    assert "approval" in detail.lower()
    assert "Empty" not in detail, (
        "the raw exception type leaked into the analyst's view"
    )


def test_the_patient_window_is_bounded_not_infinite(tmp_path: Path):
    """Patience must still END. An approval nobody ever decides cannot pin a thread.

    This is the difference between the fix and simply deleting the timeout.
    """
    bridge = CodexBridge(
        _plan(tmp_path, "approvals"), idle_timeout=0.3, approval_timeout=1.0
    )

    terminal = _terminal(_drain(bridge))

    assert terminal.type == "turn_failed", "an undecided approval must still terminate"


def test_the_default_windows_keep_the_stalled_provider_bound(tmp_path: Path):
    """The shipped defaults, asserted rather than assumed.

    A patient window that defaulted to the idle one would silently un-fix this, and
    an idle window raised to the patient one would un-protect the wedged case.
    """
    bridge = CodexBridge(_plan(tmp_path, "thread_turn", stay_open=False))

    assert bridge.idle_timeout == 30.0, "the stalled-provider bound must not change"
    assert bridge.approval_timeout > bridge.idle_timeout, (
        "a paused turn must be given more patience than a silent one"
    )


# --------------------------------------------------------------------------- #
# The session-level knob the bridge is built on                               #
# --------------------------------------------------------------------------- #


def test_frames_still_honours_an_explicit_timeout(tmp_path: Path):
    """`tests/integration/test_studio_codex_real.py` passes `timeout=60.0` positionally.

    Keeping that call working is a constraint on the signature, not an optional nicety.
    """
    session = CodexSession(_plan(tmp_path, "thread_turn", stay_open=False))
    session.start()
    try:
        assert next(session.frames(timeout=5.0), None) is not None
    finally:
        session.close()


def test_frames_asks_its_patience_source_each_wait(tmp_path: Path):
    """The budget is re-read per wait, so it can CHANGE when an approval appears.

    A budget captured once at call time could never widen mid-turn, which is the whole
    mechanism.
    """
    asked: list[int] = []

    def patience() -> float:
        asked.append(1)
        return 5.0

    session = CodexSession(_plan(tmp_path, "thread_turn", stay_open=False))
    session.start()
    try:
        list(session.frames(patience=patience))
    finally:
        session.close()

    assert len(asked) > 1, "patience must be consulted per wait, not once per call"


@pytest.mark.parametrize("fixture", ["approvals", "thread_turn"])
def test_no_fixture_leaves_a_turn_without_exactly_one_terminal(
    tmp_path: Path, fixture: str
):
    """The shared-suite invariant must hold on both paths this change touches."""
    bridge = CodexBridge(
        _plan(tmp_path, fixture), idle_timeout=0.3, approval_timeout=1.0
    )
    _terminal(_drain(bridge))  # raises if not exactly one
