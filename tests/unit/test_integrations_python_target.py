"""Resolution and the profile environment agree on ONE interpreter version.

Compatibility (`requires-python`) is resolved against a Python version; the
profile environment must be created for that same version rather than whatever
uv picks from `.python-version`, `UV_PYTHON` or PATH. The version is compared
at full precision, so a micro-level bound is judged correctly.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from seshat.integrations import installer, resolvers
from seshat.integrations.catalog import component
from seshat.integrations.resolvers import Resolvers, resolve_pypi
from tests.unit._curated_stack_fixtures import (
    FakePypi,
    _grant_provisioning,
    _release,
    _tools_on_path,
    _workspace,
)

pytestmark = pytest.mark.unit


def _venv_commands(root: Path, python_version, monkeypatch) -> list[list[str]]:
    _grant_provisioning(monkeypatch)
    _tools_on_path(monkeypatch)
    commands: list[list[str]] = []

    def _runner(command: list[str], cwd: Path):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    installer.apply(
        root,
        components=(component("duckdb"),),
        resolvers=Resolvers(
            pypi=FakePypi({"duckdb": {"releases": {"1.0.0": _release("1.0.0")}}}),
            python_version=python_version,
        ),
        runner=_runner,
    )
    return [command for command in commands if command[:2] == ["uv", "venv"]]


def test_the_profile_env_is_created_for_the_resolved_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (command,) = _venv_commands(_workspace(tmp_path), (3, 13, 5), monkeypatch)

    assert command[command.index("--python") + 1] == "3.13.5"
    assert sys.executable not in " ".join(command)


def test_without_an_explicit_version_the_running_python_is_targeted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (command,) = _venv_commands(_workspace(tmp_path), None, monkeypatch)

    expected = ".".join(str(part) for part in sys.version_info[:3])
    assert command[command.index("--python") + 1] == expected


def test_live_resolvers_carry_the_running_python() -> None:
    assert resolvers.live_resolvers().python_version == tuple(sys.version_info[:3])


def test_running_python_keeps_the_micro_version() -> None:
    assert resolvers.running_python() == tuple(sys.version_info[:3])


def test_a_micro_level_requires_python_bound_is_judged_correctly() -> None:
    major, minor, micro = sys.version_info[:3]
    if micro == 0:
        pytest.skip("a .0 interpreter cannot distinguish the micro bound")
    bound = f">={major}.{minor}.{micro}"
    index = FakePypi(
        {"duckdb": {"releases": {"2.0.0": _release("2.0.0", requires=bound)}}}
    )

    result = resolve_pypi(component("duckdb"), index)

    assert result.ok, result.reason
    assert result.version == "2.0.0"
