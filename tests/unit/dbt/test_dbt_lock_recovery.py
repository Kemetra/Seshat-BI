"""A dbt target lock left by a dead process is recoverable; a live one is not."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _lock(root: Path, pid: int) -> Path:
    lock = root / ".seshat" / "dbt" / "locks" / "table-shadow.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "acquired_at": "2026-09-23T00:00:00.000Z",
        "owner_token": "0" * 32,
        "pid": pid,
        "table_id": "table",
        "target": "shadow",
    }
    lock.write_text(json.dumps(payload), encoding="utf-8")
    return lock


def _dead_pid() -> int:
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


def test_liveness_probe_reads_current_and_finished_processes() -> None:
    from seshat.dbt.runner import _pid_alive

    assert _pid_alive(os.getpid()) is True
    assert _pid_alive(_dead_pid()) is False


def test_lock_of_a_dead_process_is_reclaimed(tmp_path: Path) -> None:
    from seshat.dbt.runner import target_lock

    lock = _lock(tmp_path, _dead_pid())
    with target_lock(tmp_path, "table", "shadow", timeout_s=0) as path:
        assert json.loads(path.read_text(encoding="utf-8"))["pid"] == os.getpid()
    assert not lock.exists()


def test_lock_of_a_live_process_is_kept_and_named(tmp_path: Path) -> None:
    from seshat.dbt.runner import LockUnavailable, target_lock

    lock = _lock(tmp_path, os.getpid())
    before = lock.read_bytes()
    with pytest.raises(LockUnavailable) as exc:
        with target_lock(tmp_path, "table", "shadow", timeout_s=0):
            raise AssertionError("lock must not be acquired")
    message = str(exc.value)
    assert ".seshat/dbt/locks/table-shadow.lock" in message
    assert str(tmp_path) not in message
    assert "remove" in message
    assert lock.read_bytes() == before


def test_lock_replaced_between_read_and_reclaim_is_not_deleted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Re-read before unlinking: a lock another process just took survives."""
    from seshat.dbt import runner

    lock = _lock(tmp_path, _dead_pid())
    fresh = b'{"pid": 1, "owner_token": "fresh"}'

    def dead_then_replaced(pid: int) -> bool:
        lock.write_bytes(fresh)
        return False

    monkeypatch.setattr(runner, "_pid_alive", dead_then_replaced)
    with pytest.raises(runner.LockUnavailable):
        with runner.target_lock(tmp_path, "table", "shadow", timeout_s=0):
            raise AssertionError("lock must not be acquired")
    assert lock.read_bytes() == fresh
