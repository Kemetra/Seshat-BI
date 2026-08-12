"""The only proof that the committed fixtures match a real Codex build.

Marked `integration` so `pytest -m unit` in the CI `check` job never reaches it --
that job has no Codex CLI. Skips cleanly when the CLI is absent, so it is safe to
run anywhere.

Everything else in T021 drives a scripted child replaying committed fixtures. That
is the right default -- it is deterministic and runs on CI -- but it shares one
blind spot with every fixture-based suite: if the fixtures were derived from a
misreading, the client and the fixtures agree with each other and both are wrong.
This test is the only place that asks the actual provider.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def test_a_real_codex_app_server_completes_a_handshake(tmp_path: Path) -> None:
    from seshat.studio.codex_process import (
        CodexLaunchPlan,
        find_codex_executable,
        is_tested_version,
    )

    executable = find_codex_executable()
    if executable is None:
        pytest.skip("the Codex CLI is not installed on this machine")

    version = subprocess.run(
        [executable, "--version"], capture_output=True, text=True, timeout=30
    ).stdout.strip()
    reported = version.split()[-1] if version else ""
    if not is_tested_version(reported):
        pytest.skip(f"codex {reported!r} is outside the tested range")

    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(
        CodexLaunchPlan.for_workspace(tmp_path, executable=executable)
    )
    session.start()
    try:
        session.send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"clientInfo": {"name": "seshat-studio", "version": "1"}},
            }
        )
        first = next(session.frames(timeout=60.0), None)
    finally:
        session.close()

    assert first is not None, "the real app-server produced no frame"
    # Correlation, not envelope decoration: the real app-server does NOT send a
    # `jsonrpc` field and its schema never declares one, so asserting `== "2.0"`
    # here (as this test first did) pins a fiction. `id` coming back as the `1` we
    # sent is the property that actually matters -- it proves the reply is OURS.
    assert first["id"] == 1, "the reply did not correlate to the request we sent"
    assert "result" in first, "the handshake did not return a result"
    assert "sk-" not in session.stderr_text()


def test_a_real_turn_reaches_a_terminal_event(tmp_path: Path) -> None:
    """Drives `CodexBridge.run_turn` end to end against the installed CLI.

    This is the oracle that was missing. The handshake test above proves the
    process and framing work, but it sends ONE frame and reads ONE reply -- it
    never exercises `run_turn`, so the bridge shipped unable to start a turn on a
    real server (it never sent `thread/start`/`turn/start`) while every
    fixture-driven test passed. The scripted child cannot catch that: it replays
    unprompted and never reads stdin, so it answers a bridge that asks for nothing.

    Asserted on reaching a TERMINAL rather than on any particular answer -- the
    model's words are not a contract, but "the turn ends, exactly once" is.
    """
    from seshat.studio.codex_process import find_codex_executable, is_tested_version

    executable = find_codex_executable()
    if executable is None:
        pytest.skip("the Codex CLI is not installed on this machine")

    version = subprocess.run(
        [executable, "--version"], capture_output=True, text=True, timeout=30
    ).stdout.strip()
    reported = version.split()[-1] if version else ""
    if not is_tested_version(reported):
        pytest.skip(f"codex {reported!r} is outside the tested range")

    from seshat.studio.codex_bridge import CodexBridge
    from seshat.studio.codex_process import CodexLaunchPlan

    bridge = CodexBridge(CodexLaunchPlan.for_workspace(tmp_path, executable=executable))

    events = list(
        bridge.run_turn(
            prompt="Reply with the single word: ready",
            turn_id="turn-live",
            requested_mode="read_only",
        )
    )

    assert events, "the real bridge produced no events"
    assert events[0].type == "turn_started"
    terminals = [e for e in events if e.type in {"turn_completed", "turn_failed"}]
    assert len(terminals) == 1, (
        f"expected exactly one terminal from a real turn, got {len(terminals)}: "
        f"{[e.type for e in events]}"
    )
    # Must be COMPLETED, not merely terminal. `run_turn` converts any provider
    # failure into exactly one `turn_failed`, so accepting either would let a
    # regression that never starts a real turn satisfy the oracle after its
    # timeout -- the very vacuity this test exists to prevent (#617 review).
    assert terminals[0].type == "turn_completed", (
        f"the live turn did not complete: {terminals[0].payload}"
    )
