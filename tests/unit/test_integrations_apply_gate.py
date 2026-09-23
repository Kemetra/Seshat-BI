"""The provisioning approval is enforced at the MUTATION site, not in the CLI.

`installer.apply()` and the exported facade `setup_integrations(apply=True)` are
reachable from plain Python. A gate that lives only in the CLI's `_authorized()`
is a precondition the caller supplies (the #671 argument), so these tests call
the mutation site directly and assert that, without a committed named-human
approval, no handler runs and no lock is written.

The confirmed plan is also binding: apply installs the coordinates the human
saw, never a fresher resolution looked up after the confirmation.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.integrations import installer
from seshat.integrations.catalog import LOCK_FILE, Channel, Component, SourceType
from seshat.integrations.installer import FAILED, INSTALLED
from seshat.integrations.resolvers import Resolvers
from seshat.integrations_setup import setup_integrations
from tests.unit._curated_stack_fixtures import (
    FakePypi,
    _args,
    _no_network,
    _release,
    _tools_on_path,
)

pytestmark = pytest.mark.unit

APPROVALS = "contracts/provisioning-approvals.yaml"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    (tmp_path / ".seshat").mkdir()
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(tmp_path, "add", "seed.txt")
    _git(tmp_path, "commit", "-qm", "seed", "--no-gpg-sign")
    return tmp_path


def _approve(repo: Path, components: list[str]) -> None:
    (repo / "contracts").mkdir(exist_ok=True)
    (repo / APPROVALS).write_text(
        "approvals:\n"
        "  - stage: provisioning\n"
        '    owner: "Ahmed Shaaban (governance)"\n'
        '    at: "2026-08-20"\n'
        f"    components: {components}\n",
        encoding="utf-8",
    )
    _git(repo, "add", APPROVALS)
    _git(repo, "commit", "-qm", "approval", "--no-gpg-sign")


def _duckdb() -> Component:
    return Component(
        id="duckdb",
        source_type=SourceType.PYPI,
        source="pypi",
        channel=Channel.STABLE,
        role="test",
        coordinate="duckdb",
    )


class _Runner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], cwd: Path) -> subprocess.CompletedProcess:
        self.commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")


def _resolvers(version: str = "1.0.0") -> Resolvers:
    return Resolvers(
        pypi=FakePypi({"duckdb": {"releases": {version: _release(version)}}}),
        python_version=(3, 13),
    )


def test_apply_without_committed_approval_runs_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    _tools_on_path(monkeypatch)
    runner = _Runner()

    outcome = installer.apply(
        root, components=(_duckdb(),), resolvers=_resolvers(), runner=runner
    )

    assert runner.commands == []
    assert outcome.lock_written is None
    assert not (root / LOCK_FILE).exists()
    assert [(row.component, row.status) for row in outcome.rows] == [
        ("approval", FAILED)
    ]
    assert "approval" in outcome.rows[0].detail
    assert outcome.needs_action


def test_facade_apply_without_committed_approval_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exported facade reaches the same refusal: it has no gate of its own."""
    root = _repo(tmp_path)
    _tools_on_path(monkeypatch)
    runner = _Runner()

    results = setup_integrations(
        root,
        apply=True,
        profile="analytics-core",
        resolvers=_resolvers(),
        runner=runner,
    )

    assert runner.commands == []
    assert [(item.name, item.status) for item in results] == [("approval", "failed")]
    assert not (root / LOCK_FILE).exists()


def test_an_approval_narrower_than_the_derived_scope_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scope comes from the components apply derives itself, not from a caller."""
    root = _repo(tmp_path)
    _approve(root, ["duckdb"])
    _tools_on_path(monkeypatch)
    runner = _Runner()

    outcome = installer.apply(
        root, profile="analytics-core", resolvers=_resolvers(), runner=runner
    )

    assert runner.commands == []
    assert outcome.rows[0].component == "approval"
    assert outcome.rows[0].status == FAILED


def test_a_committed_approval_covering_the_scope_permits_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    _approve(root, ["duckdb"])
    _tools_on_path(monkeypatch)
    runner = _Runner()

    outcome = installer.apply(
        root, components=(_duckdb(),), resolvers=_resolvers(), runner=runner
    )

    assert any("duckdb==1.0.0" in command for command in runner.commands)
    assert [row.status for row in outcome.rows] == [INSTALLED]


def test_an_uncommitted_approval_authorizes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    (root / "contracts").mkdir()
    (root / APPROVALS).write_text(
        "approvals:\n  - stage: provisioning\n"
        '    owner: "Ahmed Shaaban (governance)"\n'
        '    at: "2026-08-20"\n    components: [duckdb]\n',
        encoding="utf-8",
    )
    _tools_on_path(monkeypatch)
    runner = _Runner()

    outcome = installer.apply(
        root, components=(_duckdb(),), resolvers=_resolvers(), runner=runner
    )

    assert runner.commands == []
    assert outcome.rows[0].component == "approval"


# --------------------------------------------------------------------------- #
# The confirmed plan binds apply to the coordinates the human saw.
# --------------------------------------------------------------------------- #


def test_apply_installs_the_confirmed_plan_not_a_fresher_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    _approve(root, ["duckdb"])
    _tools_on_path(monkeypatch)
    confirmed = installer.plan(
        root, components=(_duckdb(),), resolvers=_resolvers("1.0.0")
    )
    runner = _Runner()

    outcome = installer.apply(
        root,
        components=(_duckdb(),),
        resolvers=_resolvers("9.9.9"),
        runner=runner,
        pinned=confirmed.resolutions,
    )

    specs = [command[-1] for command in runner.commands if "install" in command]
    assert specs == ["duckdb==1.0.0"]
    assert outcome.rows[0].status == INSTALLED


def test_a_component_absent_from_the_confirmed_plan_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    _approve(root, ["duckdb"])
    _tools_on_path(monkeypatch)
    runner = _Runner()

    outcome = installer.apply(
        root,
        components=(_duckdb(),),
        resolvers=_resolvers("9.9.9"),
        runner=runner,
        pinned={},
    )

    assert runner.commands == []
    assert outcome.rows[0].status == FAILED
    assert "confirmed plan" in outcome.rows[0].detail


def test_cli_apply_uses_the_resolution_shown_in_the_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End to end: the index moves between the plan and the apply."""
    from seshat import integrations_setup
    from seshat.cli.commands.integrations import integrations_main

    root = _repo(tmp_path)
    _no_network(monkeypatch)
    _tools_on_path(monkeypatch)
    names = ("duckdb", "polars", "pyarrow", "pandera", "connectorx")
    _approve(root, list(names))

    class _MovingPypi(FakePypi):
        def project(self, dist: str) -> dict:
            version = "1.0.0" if self.calls.count(dist) == 0 else "9.9.9"
            self.calls.append(dist)
            return {"releases": {version: _release(version)}}

    moving = Resolvers(pypi=_MovingPypi({}), python_version=(3, 13))
    monkeypatch.setattr(integrations_setup, "live_resolvers", lambda: moving)
    runner = _Runner()
    monkeypatch.setattr(installer, "_run", runner)

    integrations_main(
        _args(root, profile="analytics-core", refresh=True, apply=True, yes=True)
    )

    specs = [command[-1] for command in runner.commands if "install" in command]
    assert specs, "nothing was installed"
    assert all(spec.endswith("==1.0.0") for spec in specs), specs
