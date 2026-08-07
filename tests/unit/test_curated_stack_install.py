"""Curated stack: what `apply()` actually does on disk.

Every install command carries an exact coordinate, MCP registration never
overwrites an operator's entry, and the boundaries the shipped verb already
held (the active interpreter, the install root, readiness artifacts, and
partial installs) still hold.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.integrations import mcp_config
from seshat.integrations.catalog import (
    ANALYTICS_FULL,
    MCP_CONFIG,
    Channel,
)
from seshat.integrations.installer import apply as apply_profile
from seshat.integrations.installer import plan as plan_profile
from seshat.integrations.resolvers import (
    Resolvers,
)
from tests.unit._curated_stack_fixtures import (
    FakeGitHub,
    FakeNpm,
    FakePypi,
    _install_mcp,
    _release,
    _tools_on_path,
    _workspace,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# 2. Exactness: nothing that can move survives into a configuration.
# --------------------------------------------------------------------------- #


def test_apply_uses_exact_versions_tags_or_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Property 5: every install command carries an exact coordinate."""
    root = _workspace(tmp_path)
    _tools_on_path(monkeypatch)
    commands: list[list[str]] = []

    def _runner(command: list[str], cwd: Path):
        commands.append(command)
        import subprocess

        return subprocess.CompletedProcess(command, 0, "", "")

    outcome = apply_profile(
        root,
        profile="analytics-core",
        resolvers=Resolvers(
            pypi=FakePypi(
                {
                    name: {"releases": {"2.1.0": _release("2.1.0")}}
                    for name in ("duckdb", "polars", "pyarrow", "pandera", "connectorx")
                }
            ),
            python_version=(3, 13),
        ),
        runner=_runner,
    )

    installs = [c for c in commands if "install" in c]
    assert installs, "no install command was issued"
    for command in installs:
        spec = command[-1]
        assert "==" in spec, f"install spec is not pinned: {spec}"
        assert "latest" not in spec
    assert outcome.rows


def test_active_mcp_configuration_contains_no_latest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Property 6: the WRITTEN mcp.json never carries a moving reference.

    Asserted on the file's bytes rather than on a dataclass literal: what
    matters is what an MCP client will actually read.
    """
    root = _workspace(tmp_path)
    _install_mcp(root, monkeypatch)

    body = (root / MCP_CONFIG).read_text(encoding="utf-8")

    assert "@latest" not in body
    assert "latest" not in body
    # Every registered server -- whatever the profile contained -- is pinned.
    servers = json.loads(body)["mcpServers"]
    assert servers, "no server was registered, so the assertion would be vacuous"
    for name, entry in servers.items():
        rendered = json.dumps(entry)
        assert "latest" not in rendered, f"{name} carries a moving reference"
        assert any("==" in arg or "@" in arg for arg in entry["args"]), name


def test_dbt_mcp_is_never_unversioned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Property 7: `uvx dbt-mcp` without a version never reaches the config."""
    root = _workspace(tmp_path)
    _install_mcp(root, monkeypatch)

    entry = json.loads((root / MCP_CONFIG).read_text(encoding="utf-8"))["mcpServers"]
    args = entry["dbt-mcp"]["args"]

    assert args == ["dbt-mcp==1.9.0"]
    assert "dbt-mcp" not in args, "a bare, unversioned package spec survived"


def test_powerbi_mcp_stays_readonly_and_preview(tmp_path: Path) -> None:
    """The Power BI MCP is registered read-only and never promoted to stable."""
    entry = mcp_config.powerbi_entry("1.4.0")
    assert "--readonly" in entry["args"]
    assert "@microsoft/powerbi-modeling-mcp@1.4.0" in entry["args"]

    from seshat.integrations.catalog import component

    powerbi = component("powerbi-modeling-mcp")
    assert powerbi.channel is Channel.PREVIEW
    assert powerbi.mode == "readonly"


@pytest.mark.parametrize("builder", [mcp_config.powerbi_entry, mcp_config.dbt_entry])
def test_an_mcp_entry_refuses_to_build_without_a_version(builder) -> None:
    """The builders cannot produce an unpinned entry even if asked."""
    with pytest.raises(ValueError, match="exact resolved version"):
        builder("")


# --------------------------------------------------------------------------- #
# 7. MCP safety.
# --------------------------------------------------------------------------- #


def test_same_name_mcp_conflicts_do_not_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Property 17: a differing same-name registration refuses."""
    root = _workspace(tmp_path)
    path = root / MCP_CONFIG
    path.parent.mkdir(parents=True)
    hand_edited = {
        "mcpServers": {
            "dbt-mcp": {
                "command": "uvx",
                "args": ["dbt-mcp==0.0.1"],
                "env": {"MINE": "1"},
            }
        }
    }
    path.write_text(json.dumps(hand_edited, indent=2), encoding="utf-8")
    before = path.read_bytes()

    outcome = _install_mcp(root, monkeypatch)

    dbt_row = next(row for row in outcome.rows if row.component == "dbt-mcp")
    assert dbt_row.status == "conflict"
    assert "refusing to overwrite" in dbt_row.detail
    assert path.read_bytes() == before


def test_an_identical_mcp_registration_is_present_not_rewritten() -> None:
    entry = mcp_config.dbt_entry("1.9.0")
    config = {"mcpServers": {"dbt-mcp": entry}}
    assert mcp_config.classify(config, "dbt-mcp", entry) == mcp_config.PRESENT
    assert mcp_config.classify(config, "other", entry) is None


def test_unrelated_mcp_servers_survive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Property 18: merging preserves every registration it did not make."""
    root = _workspace(tmp_path)
    path = root / MCP_CONFIG
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"mcpServers": {"keep-me": {"command": "unrelated"}}}),
        encoding="utf-8",
    )

    _install_mcp(root, monkeypatch)

    servers = json.loads(path.read_text(encoding="utf-8"))["mcpServers"]
    assert servers["keep-me"] == {"command": "unrelated"}
    assert "dbt-mcp" in servers


def test_an_unparseable_mcp_config_is_never_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _workspace(tmp_path)
    path = root / MCP_CONFIG
    path.parent.mkdir(parents=True)
    path.write_text("{ not json", encoding="utf-8")

    outcome = _install_mcp(root, monkeypatch)

    dbt_row = next(row for row in outcome.rows if row.component == "dbt-mcp")
    assert dbt_row.status == "failed"
    assert path.read_text(encoding="utf-8") == "{ not json"


# --------------------------------------------------------------------------- #
# 9. The boundaries the shipped verb already held.
# --------------------------------------------------------------------------- #


def test_the_active_python_interpreter_is_never_modified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Property 20: no subprocess targets `sys.executable`.

    Asserted on the actual argv the installer would run, not on a docstring: the
    risk is a command, so the oracle reads commands.
    """
    import subprocess
    import sys as _sys

    _tools_on_path(monkeypatch)
    commands: list[list[str]] = []

    def _runner(command: list[str], cwd: Path):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    apply_profile(
        _workspace(tmp_path),
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
        runner=_runner,
    )

    assert commands, "nothing ran, so the assertion would be vacuous"
    for command in commands:
        joined = " ".join(command)
        assert _sys.executable not in joined
        assert "pip install" not in joined or "-p" in command
        # Every install names an explicit target environment.
        if "install" in command:
            assert "-p" in command


def test_installs_land_only_under_the_integrations_directory(tmp_path: Path) -> None:
    """Isolation: every env path is inside `.seshat/integrations/`."""
    import subprocess

    commands: list[list[str]] = []

    def _runner(command: list[str], cwd: Path):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    root = _workspace(tmp_path)
    apply_profile(
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
        runner=_runner,
    )

    for command in commands:
        for token in command:
            if str(root) in token:
                assert ".seshat" in token and "integrations" in token


def test_readiness_artifacts_remain_unchanged(tmp_path: Path) -> None:
    """Property 21: no readiness state is read or written by this verb."""
    root = _workspace(tmp_path)
    readiness = root / "readiness-status.yaml"
    readiness.write_text("stage: source_ready\n", encoding="utf-8")
    mappings = root / "mappings"
    mappings.mkdir()
    (mappings / "source-map.yaml").write_text("version: 1\n", encoding="utf-8")
    before = {
        path: path.read_bytes() for path in (readiness, mappings / "source-map.yaml")
    }

    import subprocess

    def _runner(command: list[str], cwd: Path):
        return subprocess.CompletedProcess(command, 0, "", "")

    plan_profile(root, profile=ANALYTICS_FULL)
    apply_profile(
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
                release={"tag_name": "v1.0.0"}, commits={"v1.0.0": {"sha": "b" * 40}}
            ),
            python_version=(3, 13),
        ),
        runner=_runner,
    )

    for path, body in before.items():
        assert path.read_bytes() == body


def test_a_partially_installed_component_is_never_reported_installed(
    tmp_path: Path,
) -> None:
    """Property 23: a clone without its activation marker is not `present`.

    The marker is written only after the staged tree moved into place, so an
    interrupted install re-plans instead of claiming success.
    """
    root = _workspace(tmp_path)
    from seshat.integrations.catalog import SKILLS_DIR

    partial = root / SKILLS_DIR / "fabric-skills"
    partial.mkdir(parents=True)
    (partial / "README.md").write_text("half a clone\n", encoding="utf-8")

    outcome = plan_profile(
        root,
        profile="powerbi-fabric",
        resolvers=Resolvers(
            github=FakeGitHub(
                release={"tag_name": "v3.0.0"}, commits={"v3.0.0": {"sha": "9" * 40}}
            ),
            npm=FakeNpm(
                {"@microsoft/powerbi-modeling-mcp": {"dist-tags": {"latest": "1.0.0"}}}
            ),
            python_version=(3, 13),
        ),
    )

    fabric = next(row for row in outcome.rows if row.component == "fabric-skills")
    assert fabric.status != "present"
    assert fabric.status == "planned"


def test_a_marked_skill_bundle_missing_required_payload_is_not_present(
    tmp_path: Path,
) -> None:
    root = _workspace(tmp_path)
    from seshat.integrations.catalog import SKILLS_DIR

    target = root / SKILLS_DIR / "fabric-skills"
    target.mkdir(parents=True)
    (target / ".seshat-installed").write_text("v3.0.0\n", encoding="utf-8")

    outcome = plan_profile(
        root,
        profile="powerbi-fabric",
        resolvers=Resolvers(
            github=FakeGitHub(
                release={"tag_name": "v3.0.0"}, commits={"v3.0.0": {"sha": "9" * 40}}
            ),
            npm=FakeNpm(
                {"@microsoft/powerbi-modeling-mcp": {"dist-tags": {"latest": "1.0.0"}}}
            ),
            python_version=(3, 13),
        ),
    )

    fabric = next(row for row in outcome.rows if row.component == "fabric-skills")
    assert fabric.status == "planned"


def test_a_clone_missing_required_payload_is_not_activated(tmp_path: Path) -> None:
    import subprocess

    root = _workspace(tmp_path)
    from seshat.integrations.catalog import SKILLS_DIR

    def _incomplete_clone(command: list[str], cwd: Path):
        if command[:2] == ["git", "clone"]:
            target = Path(command[-1])
            target.mkdir(parents=True)
            (target / "README.md").write_text("incomplete\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    outcome = apply_profile(
        root,
        profile="powerbi-fabric",
        resolvers=Resolvers(
            github=FakeGitHub(
                release={"tag_name": "v3.0.0"}, commits={"v3.0.0": {"sha": "9" * 40}}
            ),
            npm=FakeNpm({"@microsoft/powerbi-modeling-mcp": {"dist-tags": {}}}),
            python_version=(3, 13),
        ),
        runner=_incomplete_clone,
    )

    fabric = next(row for row in outcome.rows if row.component == "fabric-skills")
    assert fabric.status == "failed"
    assert "missing required payload" in fabric.detail
    assert not (root / SKILLS_DIR / "fabric-skills").exists()


def test_a_failed_clone_does_not_activate_the_staged_tree(tmp_path: Path) -> None:
    """A clone that fails leaves no half-installed component behind."""
    import subprocess

    root = _workspace(tmp_path)
    from seshat.integrations.catalog import SKILLS_DIR

    def _failing(command: list[str], cwd: Path):
        return subprocess.CompletedProcess(command, 128, "", "fatal: not found")

    outcome = apply_profile(
        root,
        profile="powerbi-fabric",
        resolvers=Resolvers(
            github=FakeGitHub(
                release={"tag_name": "v3.0.0"}, commits={"v3.0.0": {"sha": "9" * 40}}
            ),
            npm=FakeNpm({"@microsoft/powerbi-modeling-mcp": {"dist-tags": {}}}),
            python_version=(3, 13),
        ),
        runner=_failing,
    )

    fabric = next(row for row in outcome.rows if row.component == "fabric-skills")
    assert fabric.status == "failed"
    assert not (root / SKILLS_DIR / "fabric-skills" / ".seshat-installed").exists()
    assert outcome.lock_written is None
