"""Process-boundary regression tests for Dagster gate commands."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tower_bi_orchestration import commands


def test_gate_command_redacts_full_output_before_tail(monkeypatch) -> None:
    secret = "postgresql" + "://alice:s3cretpw@db.example.internal/gold"
    monkeypatch.setattr(commands, "_TAIL_CHARS", 40)
    monkeypatch.setattr(
        commands.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 1, stdout="prefix" * 20, stderr=secret
        ),
    )

    code, output = commands.run_gate_command(["gate"], Path("."))

    assert code == 1
    assert "s3cretpw" not in output
