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
