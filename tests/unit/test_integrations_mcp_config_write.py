"""mcp.json holds operator-authored servers, so it is written atomically.

A crash, a full disk or an antivirus lock mid-write must leave the previous
file byte-for-byte intact, never a truncated one that loses the operator's own
servers -- the same guarantee the integration lock already has.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from seshat.integrations import lockfile, mcp_config

pytestmark = pytest.mark.unit

_ORIGINAL = '{\n  "mcpServers": {\n    "mine": {"command": "x"}\n  }\n}\n'


def _config(tmp_path: Path) -> Path:
    path = tmp_path / ".seshat" / "integrations" / "mcp.json"
    path.parent.mkdir(parents=True)
    path.write_text(_ORIGINAL, encoding="utf-8")
    return path


def test_a_failed_write_leaves_the_previous_config_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _config(tmp_path)

    def _disk_full(fd: int) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(lockfile.os, "fsync", _disk_full)

    with pytest.raises(OSError):
        mcp_config.write_config(path, {"mcpServers": {"dbt-mcp": {"command": "uvx"}}})

    assert path.read_text(encoding="utf-8") == _ORIGINAL
    assert sorted(p.name for p in path.parent.iterdir()) == ["mcp.json"]


def test_a_successful_write_replaces_via_a_sibling_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _config(tmp_path)
    replaced: list[tuple[str, str]] = []
    real_replace = os.replace

    def _spy(src, dst):
        replaced.append((str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(lockfile.os, "replace", _spy)

    mcp_config.write_config(path, {"mcpServers": {"dbt-mcp": {"command": "uvx"}}})

    assert len(replaced) == 1
    source, target = replaced[0]
    assert Path(source).parent == path.parent
    assert Path(target) == path
    assert "dbt-mcp" in path.read_text(encoding="utf-8")
