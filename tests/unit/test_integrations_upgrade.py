"""Presence is coordinate-aware, and the lock records what is ON DISK.

A component installed at one coordinate while another is now resolved is an
UPGRADE, planned and performed by apply -- never reported `present` at the new
coordinate while the old one is what is installed. When an upgrade does not
land, the lock keeps describing the installed coordinate.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from seshat.integrations import installer, mcp_config, presence
from seshat.integrations.catalog import (
    LOCK_FILE,
    MCP_CONFIG,
    SKILLS_DIR,
    component,
    profiles_for,
)
from seshat.integrations.resolvers import Resolvers
from seshat.integrations.versions import artifact_sha256
from tests.unit._curated_stack_fixtures import (
    FakeGitHub,
    FakeNpm,
    FakePypi,
    _grant_provisioning,
    _mark_installed,
    _release,
    _tools_on_path,
    _workspace,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _authorized_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    _grant_provisioning(monkeypatch)
    _tools_on_path(monkeypatch)


def _site(root: Path, component_id: str) -> Path:
    env = root / presence._profile_env(profiles_for(component_id)[0])
    return env / "Lib/site-packages"


def _set_disk_version(root: Path, component_id: str, version: str) -> None:
    env = root / presence._profile_env(profiles_for(component_id)[0])
    python = presence._venv_python(env)
    python.parent.mkdir(parents=True, exist_ok=True)
    python.touch()
    site = _site(root, component_id)
    for old in site.glob(f"{component_id}-*.dist-info"):
        old.rmdir()
    (site / f"{component_id}-{version}.dist-info").mkdir(parents=True)


def _pypi(version: str, *names: str) -> Resolvers:
    return Resolvers(
        pypi=FakePypi({n: {"releases": {version: _release(version)}} for n in names}),
        python_version=(3, 13),
    )


def _lock(root: Path) -> dict:
    return json.loads((root / LOCK_FILE).read_text(encoding="utf-8"))["components"]


def _runner(on_install=None):
    def _run(command: list[str], cwd: Path):
        if on_install and "install" in command:
            on_install(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    return _run


# --------------------------------------------------------------------------- #
# PyPI: the test-plan scenario, stated literally.
# --------------------------------------------------------------------------- #


def test_an_older_distribution_on_disk_plans_an_upgrade(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _mark_installed(root, "duckdb")  # duckdb 1.0.0 on disk

    outcome = installer.plan(
        root, components=(component("duckdb"),), resolvers=_pypi("9.9.9", "duckdb")
    )

    row = outcome.rows[0]
    assert row.status == installer.UPGRADE
    assert "1.0.0" in row.detail and "9.9.9" in row.detail


def test_an_upgrade_that_does_not_land_keeps_the_on_disk_lock(tmp_path: Path) -> None:
    """duckdb 1.0.0 on disk, 9.9.9 upstream: UPGRADE, and the lock says 1.0.0."""
    root = _workspace(tmp_path)
    _mark_installed(root, "duckdb")

    def _failing(command: list[str], cwd: Path):
        return subprocess.CompletedProcess(command, 1, "", "install exploded")

    outcome = installer.apply(
        root,
        components=(component("duckdb"),),
        resolvers=_pypi("9.9.9", "duckdb"),
        runner=_failing,
    )

    assert outcome.rows[0].status == installer.FAILED
    record = _lock(root)["duckdb"]
    assert record["version"] == "1.0.0"
    assert record["sha256"] is None


def test_an_upgrade_that_lands_records_the_new_version(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _mark_installed(root, "duckdb")

    outcome = installer.apply(
        root,
        components=(component("duckdb"),),
        resolvers=_pypi("9.9.9", "duckdb"),
        runner=_runner(lambda command: _set_disk_version(root, "duckdb", "9.9.9")),
    )

    assert outcome.rows[0].status == installer.INSTALLED
    assert _lock(root)["duckdb"]["version"] == "9.9.9"


def test_a_matching_version_is_present_and_needs_no_install(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _mark_installed(root, "duckdb")
    commands: list[list[str]] = []

    outcome = installer.apply(
        root,
        components=(component("duckdb"),),
        resolvers=_pypi("1.0.0", "duckdb"),
        runner=_runner(commands.append),
    )

    assert outcome.rows[0].status == installer.PRESENT
    assert commands == []
    assert _lock(root)["duckdb"]["version"] == "1.0.0"


def test_a_later_install_that_moves_an_earlier_one_is_not_locked_as_resolved(
    tmp_path: Path,
) -> None:
    """Separate installs share one env; the lock is checked against disk after all."""
    root = _workspace(tmp_path)

    def _install(command: list[str]) -> None:
        spec = command[-1]
        name, version = spec.split("==")
        _set_disk_version(root, name, version)
        if name == "polars":  # installing polars silently moves duckdb
            _set_disk_version(root, "duckdb", "0.5.0")

    outcome = installer.apply(
        root,
        components=(component("duckdb"), component("polars")),
        resolvers=_pypi("2.0.0", "duckdb", "polars"),
        runner=_runner(_install),
    )

    statuses = {row.component: row for row in outcome.rows}
    assert statuses["polars"].status == installer.INSTALLED
    assert statuses["duckdb"].status == installer.FAILED
    assert "0.5.0" in statuses["duckdb"].detail
    assert _lock(root)["duckdb"]["version"] == "0.5.0"


# --------------------------------------------------------------------------- #
# GitHub and MCP: the remedy discovery's STALE status points at must work.
# --------------------------------------------------------------------------- #


def _github(tag: str) -> Resolvers:
    return Resolvers(
        github=FakeGitHub(release={"tag_name": tag}, commits={tag: {"sha": "b" * 40}}),
        python_version=(3, 13),
    )


def test_a_skill_bundle_at_an_older_ref_is_staged_and_swapped(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _mark_installed(root, "fabric-skills")  # marker v1
    fabric = component("fabric-skills")

    planned = installer.plan(root, components=(fabric,), resolvers=_github("v2"))
    assert planned.rows[0].status == installer.UPGRADE

    def _clone(command: list[str], cwd: Path):
        if "clone" in command:
            for relative in fabric.required_paths:
                target = Path(command[-1]) / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("# v2\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    outcome = installer.apply(
        root, components=(fabric,), resolvers=_github("v2"), runner=_clone
    )

    assert outcome.rows[0].status == installer.INSTALLED
    marker = root / SKILLS_DIR / "fabric-skills" / ".seshat-installed"
    assert marker.read_text(encoding="utf-8").strip() == "v2"
    assert _lock(root)["fabric-skills"]["tag"] == "v2"


def _npm(version: str) -> Resolvers:
    return Resolvers(
        npm=FakeNpm(
            {"@microsoft/powerbi-modeling-mcp": {"dist-tags": {"latest": version}}}
        ),
        python_version=(3, 13),
    )


def test_our_own_older_mcp_registration_is_upgraded(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    server = component("powerbi-modeling-mcp")
    installer.apply(
        root, components=(server,), resolvers=_npm("1.0.0"), runner=_runner()
    )

    planned = installer.plan(root, components=(server,), resolvers=_npm("2.0.0"))
    assert planned.rows[0].status == installer.UPGRADE

    outcome = installer.apply(
        root, components=(server,), resolvers=_npm("2.0.0"), runner=_runner()
    )

    assert outcome.rows[0].status == installer.INSTALLED
    config = mcp_config.load_config(root / MCP_CONFIG)
    assert config["mcpServers"]["powerbi-modeling-mcp"] == mcp_config.powerbi_entry(
        "2.0.0"
    )


def test_an_operator_edited_mcp_entry_is_still_never_overwritten(tmp_path) -> None:
    root = _workspace(tmp_path)
    server = component("powerbi-modeling-mcp")
    installer.apply(
        root, components=(server,), resolvers=_npm("1.0.0"), runner=_runner()
    )
    path = root / MCP_CONFIG
    config = mcp_config.load_config(path)
    config["mcpServers"]["powerbi-modeling-mcp"]["args"].append("--my-flag")
    mcp_config.write_config(path, config)

    outcome = installer.apply(
        root, components=(server,), resolvers=_npm("2.0.0"), runner=_runner()
    )

    assert outcome.rows[0].status == installer.CONFLICT
    assert "--my-flag" in path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# The recorded digest is real or null.
# --------------------------------------------------------------------------- #


def test_a_single_published_artifact_digest_is_recorded() -> None:
    assert artifact_sha256(_release("1.0.0")) == "sha-1.0.0"


def test_an_ambiguous_platform_wheel_digest_is_not_recorded() -> None:
    files = [
        {"packagetype": "bdist_wheel", "digests": {"sha256": "mac"}},
        {"packagetype": "bdist_wheel", "digests": {"sha256": "win"}},
        {"packagetype": "sdist", "digests": {"sha256": "src"}},
    ]
    assert artifact_sha256(files) is None


def test_a_pending_upgrade_is_never_summarised_as_present(tmp_path: Path) -> None:
    from seshat.integrations.render import as_text
    from seshat.integrations_setup import IntegrationResult, render_results

    root = _workspace(tmp_path)
    _mark_installed(root, "duckdb")
    outcome = installer.plan(
        root, components=(component("duckdb"),), resolvers=_pypi("9.9.9", "duckdb")
    )

    assert "are present" not in as_text(outcome)
    assert "Dry run only" in as_text(outcome)
    legacy = render_results([IntegrationResult("duckdb", installer.UPGRADE, "x")])
    assert "are present" not in legacy


def _lock_with(root: Path, *component_ids: str) -> None:
    from seshat.integrations.lockfile import SCHEMA, write_lock

    write_lock(
        root,
        {
            "schema": SCHEMA,
            "profile": "analytics-full",
            "resolved_at": "2026-08-19T00:00:00Z",
            "components": {cid: {"version": "1.0.0"} for cid in component_ids},
        },
    )


def test_a_profile_plan_warns_which_locked_components_it_would_drop(
    tmp_path: Path,
) -> None:
    """Owner-gated semantics are unchanged; the loss is announced beforehand."""
    root = _workspace(tmp_path)
    _lock_with(root, "fabric-skills", "dbt-core")

    outcome = installer.plan(root, profile="transformation")

    dropped = [note for note in outcome.notes if "outside profile" in note]
    assert dropped and "fabric-skills" in dropped[0]
    assert "dbt-core" not in dropped[0]


def test_a_derived_plan_does_not_warn_about_dropping(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _lock_with(root, "fabric-skills")

    outcome = installer.plan(root, components=(component("duckdb"),))

    assert not [note for note in outcome.notes if "outside profile" in note]
