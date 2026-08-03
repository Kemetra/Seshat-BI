from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.adopter_sim.env import assert_no_credentials, build_client_env
from scripts.adopter_sim.model import AdopterSimError

pytestmark = pytest.mark.unit

_SEPARATOR = ";" if os.name == "nt" else ":"


def _env(tmp_path: Path, parent: dict[str, str]) -> dict[str, str]:
    return build_client_env(
        workspace=tmp_path / "ws",
        venv_bin=tmp_path / "ws" / ".venv" / "Scripts",
        config_dir=tmp_path / "ws" / ".agent",
        parent=parent,
    )


def test_dsn_from_parent_is_not_inherited(tmp_path: Path) -> None:
    env = _env(tmp_path, {"DSN": "postgres://real/db", "PATH": "/usr/bin"})
    assert "DSN" not in env


def test_arbitrary_parent_keys_are_not_inherited(tmp_path: Path) -> None:
    env = _env(
        tmp_path, {"SESHAT_SECRET": "x", "DATABASE_URL": "y", "PGPASSWORD": "z"}
    )
    assert set(env) & {"SESHAT_SECRET", "DATABASE_URL", "PGPASSWORD"} == set()


def test_venv_bin_leads_path(tmp_path: Path) -> None:
    env = _env(tmp_path, {"PATH": "/usr/bin"})
    assert env["PATH"].split(_SEPARATOR)[0].endswith("Scripts")


def test_home_points_at_the_workspace(tmp_path: Path) -> None:
    env = _env(tmp_path, {})
    workspace = str(tmp_path / "ws")
    assert env["HOME"] == workspace
    assert env["USERPROFILE"] == workspace


def test_pythonpath_is_absent(tmp_path: Path) -> None:
    env = _env(tmp_path, {"PYTHONPATH": "/dev/src"})
    assert "PYTHONPATH" not in env


def test_assert_no_credentials_accepts_a_built_env(tmp_path: Path) -> None:
    env = _env(tmp_path, {"DSN": "postgres://real/db"})
    assert assert_no_credentials(env, repo_root=tmp_path / "repo") is None


def test_assert_no_credentials_rejects_a_smuggled_key(tmp_path: Path) -> None:
    env = _env(tmp_path, {})
    env["DATABASE_URL"] = "postgres://real/db"
    with pytest.raises(AdopterSimError, match="DATABASE_URL"):
        assert_no_credentials(env, repo_root=tmp_path / "repo")


def test_assert_no_credentials_rejects_repo_root_in_a_value(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    env = _env(tmp_path, {})
    env["PATH"] = f"{env['PATH']}{_SEPARATOR}{repo_root}"
    with pytest.raises(AdopterSimError, match="REPO_ROOT"):
        assert_no_credentials(env, repo_root=repo_root)


def test_real_os_environ_is_not_leaked_by_default(tmp_path: Path) -> None:
    """The default parent is os.environ; nothing outside the allow-list survives."""
    env = build_client_env(
        workspace=tmp_path / "ws",
        venv_bin=tmp_path / "ws" / ".venv" / "Scripts",
        config_dir=tmp_path / "ws" / ".agent",
    )
    assert assert_no_credentials(env, repo_root=tmp_path / "repo") is None
