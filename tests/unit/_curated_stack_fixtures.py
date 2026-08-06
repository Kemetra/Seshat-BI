"""Shared fakes and workspace helpers for the curated-analytics-stack tests.

The suite is OFFLINE by construction: the resolvers are Protocols and the
fakes below are the only indexes the tests ever see, so a network call is not
merely discouraged -- there is no live index in the object graph to call.

`_no_network` and `_tools_on_path` are the two environment fakes. Both matter:
the first makes a real HTTP call a loud failure, the second stops a missing
`uv` on the host PATH from turning an argv assertion into a vacuous one.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from seshat.integrations import installer, resolvers
from seshat.integrations.catalog import (
    ANALYTICS_FULL,
    Channel,
    Component,
    SourceType,
)
from seshat.integrations.installer import apply as apply_profile
from seshat.integrations.resolvers import (
    Resolvers,
)

# --------------------------------------------------------------------------- #
# Fakes. The only indexes these tests ever see.
# --------------------------------------------------------------------------- #


def _release(version: str, *, requires: str = ">=3.13", yanked: bool = False) -> list:
    return [
        {
            "filename": f"pkg-{version}-py3-none-any.whl",
            "packagetype": "bdist_wheel",
            "requires_python": requires,
            "yanked": yanked,
            "digests": {"sha256": f"sha-{version}"},
        }
    ]


class FakePypi:
    """A PyPI index built from an explicit release map."""

    def __init__(self, projects: dict[str, dict]) -> None:
        self.projects = projects
        self.calls: list[str] = []

    def project(self, dist: str) -> dict:
        self.calls.append(dist)
        return self.projects[dist]


class FakeGitHub:
    def __init__(
        self,
        release: dict | None = None,
        commits: dict | None = None,
        branch: str = "main",
    ) -> None:
        self.release = release
        self.commits = commits or {}
        self.branch = branch
        self.calls: list[str] = []

    def latest_release(self, repo: str) -> dict | None:
        self.calls.append(f"release:{repo}")
        return self.release

    def commit_for_ref(self, repo: str, ref: str) -> dict | None:
        self.calls.append(f"commit:{repo}@{ref}")
        return self.commits.get(ref)

    def default_branch(self, repo: str) -> str:
        self.calls.append(f"branch:{repo}")
        return self.branch


class FakeNpm:
    def __init__(self, packages: dict[str, dict]) -> None:
        self.packages = packages
        self.calls: list[str] = []

    def package(self, name: str) -> dict:
        self.calls.append(name)
        return self.packages[name]


def _pypi_component(
    component_id: str = "duckdb", channel: Channel = Channel.STABLE
) -> Component:
    return Component(
        id=component_id,
        source_type=SourceType.PYPI,
        source="pypi",
        channel=channel,
        role="test",
        coordinate=component_id,
    )


def _github_component() -> Component:
    return Component(
        id="fabric-skills",
        source_type=SourceType.GITHUB,
        source="github-microsoft-fabric",
        channel=Channel.STABLE,
        role="test",
        coordinate="microsoft/skills-for-fabric",
    )


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".seshat").mkdir(exist_ok=True)
    return tmp_path


def _args(root: Path, **overrides: object) -> Namespace:
    values: dict[str, object] = {
        "repo": str(root),
        "profile": ANALYTICS_FULL,
        "refresh": False,
        "apply": False,
        "yes": False,
        "as_json": False,
    }
    values.update(overrides)
    return Namespace(**values)


def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make any real HTTP call an immediate, loud failure."""

    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError(f"the code opened a network connection: {args!r}")

    monkeypatch.setattr(resolvers, "urlopen", _boom)


def _tools_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force `uv`/`uvx`/`git`/`npx` onto a fake PATH.

    The installer probes `shutil.which` before it will build anything, and
    returns `unavailable` without running a single command when the tool is
    absent. A runner fake alone therefore does NOT make a test hermetic: on a
    machine (or CI runner) without `uv`, the argv oracles below observe an empty
    command list and pass or fail for a reason that has nothing to do with the
    property under test. Whether a launcher happens to exist on the machine
    running the suite is never what these tests are about.
    """
    monkeypatch.setattr(installer.shutil, "which", lambda name: f"/bin/{name}")


def _install_mcp(
    root: Path, monkeypatch: pytest.MonkeyPatch | None = None
) -> installer.SetupOutcome:
    """Install just the MCP-bearing components, with everything else stubbed.

    `uvx`/`npx`/`git`/`uv` are forced onto the fake PATH: whether a launcher
    happens to exist on the machine running the suite is not what these tests
    are about.
    """
    import subprocess

    if monkeypatch is not None:
        _tools_on_path(monkeypatch)

    def _runner(command: list[str], cwd: Path):
        return subprocess.CompletedProcess(command, 0, "", "")

    return apply_profile(
        root,
        profile="transformation",
        resolvers=Resolvers(
            pypi=FakePypi(
                {
                    "dbt-core": {"releases": {"1.12.0": _release("1.12.0")}},
                    "dbt-postgres": {"releases": {"1.10.2": _release("1.10.2")}},
                    "dbt-mcp": {"releases": {"1.9.0": _release("1.9.0")}},
                }
            ),
            github=FakeGitHub(
                release={"tag_name": "v0.4.0"},
                commits={"v0.4.0": {"sha": "a" * 40}},
            ),
            python_version=(3, 13),
        ),
        runner=_runner,
    )
