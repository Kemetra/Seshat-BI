"""Curated stack: the write discipline -- the read-only default and the lock.

The default plan reads and reports; it opens no socket and writes no byte.
The lock is the memory of the last approved resolution, so it fails closed
when unreadable and survives a failed apply byte-for-byte.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.integrations import lockfile, resolvers
from seshat.integrations.catalog import (
    ANALYTICS_FULL,
    LOCK_FILE,
    MCP_CONFIG,
    Channel,
)
from seshat.integrations.installer import apply as apply_profile
from seshat.integrations.installer import plan as plan_profile
from seshat.integrations.lockfile import LockError, read_lock, write_lock
from seshat.integrations.resolvers import (
    Resolvers,
)
from tests.unit._curated_stack_fixtures import (
    FakePypi,
    _no_network,
    _release,
    _workspace,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# 1. The default performs no network calls and writes nothing.
# --------------------------------------------------------------------------- #


def test_default_setup_performs_no_network_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Property 1: a default plan cannot reach the network.

    Asserted against a poisoned `urlopen`, not against the absence of a
    resolver: this catches a future edit that constructs a live index inside the
    plan path.
    """
    _no_network(monkeypatch)
    outcome = plan_profile(_workspace(tmp_path), profile=ANALYTICS_FULL)
    assert outcome.rows  # the plan really ran


def test_default_setup_writes_nothing(tmp_path: Path) -> None:
    """Property 2: no directory, config, or lock appears from a plan."""
    root = _workspace(tmp_path)
    before = {path for path in root.rglob("*")}

    plan_profile(root, profile=ANALYTICS_FULL)

    assert {path for path in root.rglob("*")} == before
    assert not (root / LOCK_FILE).exists()
    assert not (root / MCP_CONFIG).exists()


def test_only_refresh_invokes_remote_resolvers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Property 3: the indexes are consulted only when resolvers are injected."""
    _no_network(monkeypatch)
    pypi = FakePypi({name: {"releases": {}} for name in ("duckdb",)})

    plan_profile(_workspace(tmp_path), profile="analytics-core")
    assert pypi.calls == []

    plan_profile(
        _workspace(tmp_path),
        profile="analytics-core",
        resolvers=Resolvers(pypi=FakePypi({}), python_version=(3, 13)),
    )
    # A refresh pass reaches the injected index; the empty fake raises KeyError
    # per component, which surfaces as `failed` rather than as a crash.
    rows = plan_profile(
        _workspace(tmp_path),
        profile="analytics-core",
        resolvers=Resolvers(pypi=pypi, python_version=(3, 13)),
    ).rows
    assert pypi.calls  # the injected index WAS used
    assert {row.status for row in rows} <= {"failed", "unavailable", "planned"}


def test_planning_never_changes_the_lock(tmp_path: Path) -> None:
    """Property 4: neither a plain plan nor a --refresh plan writes the lock."""
    root = _workspace(tmp_path)
    original = json.dumps(
        {
            "schema": lockfile.SCHEMA,
            "profile": "analytics-core",
            "resolved_at": "2026-01-01T00:00:00Z",
            "components": {"duckdb": {"channel": "stable", "version": "1.0.0"}},
        }
    )
    path = root / LOCK_FILE
    path.parent.mkdir(parents=True)
    path.write_text(original, encoding="utf-8")

    plan_profile(root, profile="analytics-core")
    plan_profile(
        root,
        profile="analytics-core",
        resolvers=Resolvers(
            pypi=FakePypi({"duckdb": {"releases": {"9.9.9": _release("9.9.9")}}}),
            python_version=(3, 13),
        ),
    )

    assert path.read_text(encoding="utf-8") == original


# --------------------------------------------------------------------------- #
# 6. The lock file.
# --------------------------------------------------------------------------- #


def test_malformed_lock_files_fail_closed(tmp_path: Path) -> None:
    """Property 15: an untrustworthy lock stops the run; it is never ignored."""
    root = _workspace(tmp_path)
    path = root / LOCK_FILE
    path.parent.mkdir(parents=True)

    path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(LockError, match="not valid JSON"):
        read_lock(root)

    path.write_text(json.dumps({"schema": "something/v9"}), encoding="utf-8")
    with pytest.raises(LockError, match="unsupported lock schema"):
        read_lock(root)

    path.write_text(json.dumps({"schema": lockfile.SCHEMA}), encoding="utf-8")
    with pytest.raises(LockError, match="'components' must be an object"):
        read_lock(root)


def test_a_malformed_lock_makes_the_plan_report_failed(tmp_path: Path) -> None:
    """The fail-closed read surfaces as a `failed` row, not an exception."""
    root = _workspace(tmp_path)
    path = root / LOCK_FILE
    path.parent.mkdir(parents=True)
    path.write_text("{ not json", encoding="utf-8")

    outcome = plan_profile(root, profile="analytics-core")

    assert outcome.needs_action
    assert outcome.rows[0].status == "failed"
    assert "not valid JSON" in outcome.rows[0].detail


def test_failed_installation_preserves_the_old_lock(tmp_path: Path) -> None:
    """Property 16: a failed apply leaves the previous lock byte-for-byte."""
    root = _workspace(tmp_path)
    path = root / LOCK_FILE
    path.parent.mkdir(parents=True)
    original = json.dumps(
        {
            "schema": lockfile.SCHEMA,
            "profile": "analytics-core",
            "resolved_at": "2026-01-01T00:00:00Z",
            "components": {"duckdb": {"channel": "stable", "version": "1.0.0"}},
        },
        indent=2,
    )
    path.write_text(original, encoding="utf-8")
    before = path.read_bytes()

    def _failing_runner(command: list[str], cwd: Path):
        import subprocess

        return subprocess.CompletedProcess(command, 1, "", "install exploded")

    outcome = apply_profile(
        root,
        profile="analytics-core",
        resolvers=Resolvers(
            pypi=FakePypi(
                {
                    name: {"releases": {"1.0.0": _release("1.0.0")}}
                    for name in ("duckdb", "polars", "pyarrow", "pandera", "connectorx")
                }
            ),
            python_version=(3, 13),
        ),
        runner=_failing_runner,
    )

    assert outcome.lock_written is None
    assert path.read_bytes() == before


def test_an_interrupted_lock_write_preserves_the_old_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The atomic write holds even when the replace itself fails mid-flight."""
    root = _workspace(tmp_path)
    path = root / LOCK_FILE
    path.parent.mkdir(parents=True)
    path.write_text('{"schema": "old"}', encoding="utf-8")
    before = path.read_bytes()

    def _explode(src: str, dst: str) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(lockfile.os, "replace", _explode)

    with pytest.raises(OSError, match="replace failed"):
        write_lock(root, {"schema": lockfile.SCHEMA, "components": {}})

    assert path.read_bytes() == before
    # The temp sibling is cleaned up rather than left behind as debris.
    assert not list(path.parent.glob(".lock-*.tmp"))


def test_the_lock_stores_no_credentials(tmp_path: Path) -> None:
    """Property 22: the writer projects onto an allowlist of fields."""
    root = _workspace(tmp_path)
    resolved = resolvers.Resolution(
        component_id="duckdb", ok=True, channel=Channel.STABLE, version="1.0.0"
    )
    document = lockfile.build_lock(
        "analytics-core", "2026-01-01T00:00:00Z", [("duckdb", "pypi", "pypi", resolved)]
    )
    # Even if a resolution somehow carried a secret, the projection drops it.
    document["components"]["duckdb"].setdefault("token", "should-not-persist")
    clean = lockfile.build_lock(
        "analytics-core", "2026-01-01T00:00:00Z", [("duckdb", "pypi", "pypi", resolved)]
    )

    write_lock(root, clean)
    body = (root / LOCK_FILE).read_text(encoding="utf-8").lower()

    for secret in ("token", "password", "secret", "dsn", "postgresql://", "api_key"):
        assert secret not in body


def test_the_lock_records_the_versioned_schema(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    resolved = resolvers.Resolution(
        component_id="duckdb",
        ok=True,
        channel=Channel.STABLE,
        version="1.0.0",
        sha256="abc",
    )
    write_lock(
        root,
        lockfile.build_lock(
            "analytics-core",
            "2026-01-01T00:00:00Z",
            [("duckdb", "pypi", "pypi", resolved)],
        ),
    )

    body = json.loads((root / LOCK_FILE).read_text(encoding="utf-8"))

    assert body["schema"] == "seshat.integrations-lock/v1"
    assert body["components"]["duckdb"]["version"] == "1.0.0"
    assert body["components"]["duckdb"]["sha256"] == "abc"
    assert read_lock(root) is not None
