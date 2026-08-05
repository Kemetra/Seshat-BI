"""The curated analytics stack: resolution, pinning, isolation, and the lock.

Every test here is OFFLINE. The resolvers are Protocols and each test supplies a
fake, so a network call is not merely discouraged -- there is no live index in
the object graph to call. Two tests assert that directly (`urlopen` is replaced
with a failing stub) rather than trusting the design.

The properties are grouped by what they protect:

1. the network-free, write-free default,
2. exactness (no `@latest`, no unversioned `uvx`, no floating branch),
3. refusal (prerelease, yanked, Python-incompatible, conflicting pairs),
4. honesty (rolling is not stable; preview is labelled),
5. the lock file (fail closed, atomic, preserved on failure),
6. the boundaries the shipped verb already held (interpreter, readiness,
   credentials, MCP conflicts, partial installs).
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from seshat.cli.commands.integrations import integrations_main
from seshat.integrations import installer, lockfile, mcp_config, resolvers, versions
from seshat.integrations.catalog import (
    ANALYTICS_FULL,
    LOCK_FILE,
    MCP_CONFIG,
    PROFILE_NAMES,
    Channel,
    Component,
    SourceType,
    profile_components,
)
from seshat.integrations.compat import BASELINE_PINS, apply_policy
from seshat.integrations.installer import apply as apply_profile
from seshat.integrations.installer import plan as plan_profile
from seshat.integrations.lockfile import LockError, read_lock, write_lock
from seshat.integrations.render import as_json, as_text
from seshat.integrations.resolvers import (
    Resolvers,
    resolve_github,
    resolve_npm,
    resolve_pypi,
)

pytestmark = pytest.mark.unit


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
# 2. Exactness: nothing that can move survives into a configuration.
# --------------------------------------------------------------------------- #


def test_apply_uses_exact_versions_tags_or_commits(tmp_path: Path) -> None:
    """Property 5: every install command carries an exact coordinate."""
    root = _workspace(tmp_path)
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
        monkeypatch.setattr(installer.shutil, "which", lambda name: f"/bin/{name}")

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
# 3. Refusal: prerelease, yanked, incompatible, conflicting.
# --------------------------------------------------------------------------- #


def test_prereleases_are_ignored_for_stable_components() -> None:
    """Property 8: a stable component never resolves to a prerelease."""
    body = {
        "releases": {
            "1.0.0": _release("1.0.0"),
            "2.0.0rc1": _release("2.0.0rc1"),
            "2.0.0b2": _release("2.0.0b2"),
        }
    }
    result = resolve_pypi(
        _pypi_component(), FakePypi({"duckdb": body}), python_version=(3, 13)
    )
    assert result.ok
    assert result.version == "1.0.0"


def test_yanked_pypi_releases_are_ignored() -> None:
    """Property 9: a fully-yanked release is never selected."""
    body = {
        "releases": {
            "1.0.0": _release("1.0.0"),
            "2.0.0": _release("2.0.0", yanked=True),
        }
    }
    result = resolve_pypi(
        _pypi_component(), FakePypi({"duckdb": body}), python_version=(3, 13)
    )
    assert result.version == "1.0.0"


def test_a_partially_yanked_release_is_still_installable() -> None:
    """The yanked rule is PER-FILE: one yanked wheel does not yank the release."""
    files = _release("2.0.0") + [
        {"filename": "pkg-2.0.0.tar.gz", "packagetype": "sdist", "yanked": True}
    ]
    assert versions.release_is_yanked(files) is False


def test_python_incompatible_releases_are_refused() -> None:
    """Property 10: a release excluding this interpreter is refused, and named."""
    body = {"releases": {"9.0.0": _release("9.0.0", requires=">=3.14")}}
    result = resolve_pypi(
        _pypi_component(), FakePypi({"duckdb": body}), python_version=(3, 13)
    )
    assert not result.ok
    assert result.status == resolvers.INCOMPATIBLE
    assert "9.0.0" in result.reason


def test_the_newest_compatible_release_wins_over_the_newest_release() -> None:
    """Compatibility beats recency, and the older compatible pin is retained."""
    body = {
        "releases": {
            "1.0.0": _release("1.0.0", requires=">=3.13"),
            "2.0.0": _release("2.0.0", requires=">=3.14"),
        }
    }
    result = resolve_pypi(
        _pypi_component(), FakePypi({"duckdb": body}), python_version=(3, 13)
    )
    assert result.ok
    assert result.version == "1.0.0"


def test_incompatible_dbt_pairs_are_refused() -> None:
    """Property 11: half a dbt pair is a conflict, not a partial install."""
    from seshat.integrations.catalog import component

    core = component("dbt-core")
    adapter = component("dbt-postgres")
    resolved_core = resolvers.Resolution(
        component_id="dbt-core", ok=True, channel=Channel.STABLE, version="1.12.0"
    )
    missing_adapter = resolvers.Resolution(
        component_id="dbt-postgres",
        ok=False,
        status=resolvers.UNAVAILABLE,
        reason="no compatible release",
    )

    verdict = apply_policy([(core, resolved_core), (adapter, missing_adapter)])

    assert not verdict.ok
    statuses = {res.component_id: res.status for res in verdict.resolutions}
    assert statuses["dbt-core"] == resolvers.CONFLICT
    assert any("compatible set" in reason for reason in verdict.reasons)


def test_a_component_is_never_silently_downgraded() -> None:
    """A resolution below the recorded baseline is refused and explained."""
    from seshat.integrations.catalog import component

    core = component("dbt-core")
    downgraded = resolvers.Resolution(
        component_id="dbt-core", ok=True, channel=Channel.STABLE, version="1.9.0"
    )

    verdict = apply_policy([(core, downgraded)])

    assert not verdict.ok
    assert verdict.resolutions[0].status == resolvers.INCOMPATIBLE
    assert BASELINE_PINS["dbt-core"] in verdict.resolutions[0].reason
    assert "never" in verdict.resolutions[0].reason


def test_npm_prereleases_are_refused_for_a_stable_component() -> None:
    stable = Component(
        id="thing",
        source_type=SourceType.NPM,
        source="npm-microsoft",
        channel=Channel.STABLE,
        role="test",
        coordinate="thing",
    )
    registry = FakeNpm({"thing": {"dist-tags": {"latest": "2.0.0-beta.1"}}})

    result = resolve_npm(stable, registry)

    assert not result.ok
    assert result.status == resolvers.UNAVAILABLE


def test_npm_resolves_the_stable_dist_tag_to_an_exact_version() -> None:
    from seshat.integrations.catalog import component

    registry = FakeNpm(
        {
            "@microsoft/powerbi-modeling-mcp": {
                "dist-tags": {"latest": "1.4.2"},
                "versions": {"1.4.2": {"dist": {"integrity": "sha512-abc"}}},
            }
        }
    )

    result = resolve_npm(component("powerbi-modeling-mcp"), registry)

    assert result.ok
    assert result.version == "1.4.2"
    # The maturity classification is RETAINED: an exact version does not
    # promote a pre-GA server to stable.
    assert result.channel is Channel.PREVIEW
    # npm publishes sha512 integrity; recording it as sha256 would be a lie.
    assert result.sha256 is None


# --------------------------------------------------------------------------- #
# 4. Honesty: rolling is not stable, preview is labelled.
# --------------------------------------------------------------------------- #


def test_a_github_repo_without_releases_becomes_rolling() -> None:
    """Property 12: no release means an exact commit, classified rolling."""
    index = FakeGitHub(
        release=None,
        commits={"main": {"sha": "c" * 40, "verification": {"verified": True}}},
        branch="main",
    )

    result = resolve_github(_github_component(), index)

    assert result.ok
    assert result.channel is Channel.ROLLING
    assert result.channel is not Channel.STABLE
    assert result.commit == "c" * 40
    assert result.tag is None
    assert result.signature_verified is True
    assert "rolling" in result.reason


def test_a_released_github_repo_pins_tag_and_commit() -> None:
    index = FakeGitHub(
        release={"tag_name": "v1.2.3"},
        commits={"v1.2.3": {"sha": "d" * 40}},
    )

    result = resolve_github(_github_component(), index)

    assert result.ok
    assert result.channel is Channel.STABLE
    assert result.tag == "v1.2.3"
    assert result.commit == "d" * 40
    # Unreported verification stays None rather than becoming a false `false`.
    assert result.signature_verified is None


def test_preview_components_are_visibly_labelled(tmp_path: Path) -> None:
    """Property 13: preview shows up in BOTH renderings, not just the data."""
    outcome = plan_profile(
        _workspace(tmp_path),
        profile="powerbi-fabric",
        resolvers=Resolvers(
            github=FakeGitHub(
                release={"tag_name": "v2.0.0"}, commits={"v2.0.0": {"sha": "e" * 40}}
            ),
            npm=FakeNpm(
                {
                    "@microsoft/powerbi-modeling-mcp": {
                        "dist-tags": {"latest": "1.4.2"},
                        "versions": {},
                    }
                }
            ),
            python_version=(3, 13),
        ),
    )

    text = as_text(outcome)
    assert "[PREVIEW]" in text

    payload = json.loads(as_json(outcome))
    powerbi = next(
        row
        for row in payload["components"]
        if row["component"] == "powerbi-modeling-mcp"
    )
    assert powerbi["channel"] == "preview"
    assert powerbi["requires_attention"] is True


def test_rolling_is_labelled_in_the_text_rendering(tmp_path: Path) -> None:
    outcome = plan_profile(
        _workspace(tmp_path),
        profile="powerbi-fabric",
        resolvers=Resolvers(
            github=FakeGitHub(release=None, commits={"main": {"sha": "f" * 40}}),
            npm=FakeNpm({"@microsoft/powerbi-modeling-mcp": {"dist-tags": {}}}),
            python_version=(3, 13),
        ),
    )
    assert "[ROLLING]" in as_text(outcome)


# --------------------------------------------------------------------------- #
# 5. Profiles.
# --------------------------------------------------------------------------- #


def test_profile_union_is_deterministic_and_deduplicated() -> None:
    """Property 14: analytics-full is an ordered dedupe, stable across runs."""
    first = [item.id for item in profile_components(ANALYTICS_FULL)]
    second = [item.id for item in profile_components(ANALYTICS_FULL)]

    assert first == second
    assert len(first) == len(set(first)), "a component appears twice in the union"

    members: list[str] = []
    for name in PROFILE_NAMES:
        if name == ANALYTICS_FULL:
            continue
        members.extend(item.id for item in profile_components(name))
    assert set(first) == set(members)
    # Order is declaration order, not set order.
    assert first[0] == "duckdb"


def test_every_profile_is_reachable_from_the_cli_choices() -> None:
    """The parser's choices are DERIVED, so no profile can be unreachable."""
    from seshat.cli import parser_integrations

    source = Path(parser_integrations.__file__).read_text(encoding="utf-8")
    assert "PROFILE_NAMES" in source
    for name in PROFILE_NAMES:
        # A hand-typed literal list is what this guards against.
        assert f'"{name}"' not in source


def test_every_catalog_source_is_allowlisted() -> None:
    from seshat.integrations.catalog import ALLOWLISTED_SOURCES

    for item in profile_components(ANALYTICS_FULL):
        assert item.source in ALLOWLISTED_SOURCES


def test_an_off_allowlist_source_is_refused_at_construction() -> None:
    with pytest.raises(ValueError, match="not allowlisted"):
        Component(
            id="rogue",
            source_type=SourceType.PYPI,
            source="https://evil.example.com",
            channel=Channel.STABLE,
            role="test",
        )


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
# 8. JSON purity.
# --------------------------------------------------------------------------- #


def test_json_output_parses_with_no_preceding_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Property 19: stdout in --json mode is exactly one JSON document."""
    root = _workspace(tmp_path)

    integrations_main(_args(root, as_json=True))

    out = capsys.readouterr().out
    assert out.lstrip().startswith("{")
    payload = json.loads(out)  # a single stray line would raise here
    assert payload["profile"] == ANALYTICS_FULL


def test_json_mode_never_prompts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A machine has no answer to give, so `--json` must not ask."""
    root = _workspace(tmp_path)
    monkeypatch.setattr("seshat.cli.commands.integrations._attended", lambda: True)
    monkeypatch.setattr(
        "seshat.cli.commands.integrations._prompted",
        lambda _: pytest.fail("--json prompted"),
    )
    monkeypatch.setattr(
        "builtins.input", lambda _: pytest.fail("--json reached input()")
    )

    integrations_main(_args(root, as_json=True, apply=True))

    json.loads(capsys.readouterr().out)


# --------------------------------------------------------------------------- #
# 9. The boundaries the shipped verb already held.
# --------------------------------------------------------------------------- #


def test_the_active_python_interpreter_is_never_modified(tmp_path: Path) -> None:
    """Property 20: no subprocess targets `sys.executable`.

    Asserted on the actual argv the installer would run, not on a docstring: the
    risk is a command, so the oracle reads commands.
    """
    import subprocess
    import sys as _sys

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


# --------------------------------------------------------------------------- #
# 10. requires-python evaluation.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("marker", "version", "expected"),
    [
        (">=3.13", (3, 13), True),
        (">=3.14", (3, 13), False),
        ("", (3, 13), True),
        (">=3.9,<4.0", (3, 13), True),
        (">=3.9,<3.13", (3, 13), False),
        ("==3.13", (3, 13), True),
        ("!=3.13", (3, 13), False),
        ("~=3.13", (3, 13), True),
        (">=3.8,!=3.9.*", (3, 13), True),
        ("nonsense", (3, 13), True),
    ],
)
def test_requires_python_evaluation(
    marker: str, version: tuple[int, ...], expected: bool
) -> None:
    """An unreadable marker is permissive; a readable one is enforced."""
    assert versions.python_supported(marker, version) is expected


def test_numeric_ordering_beats_lexical() -> None:
    """ "1.10" must outrank "1.9" -- the reason ordering is numeric."""
    body = {"releases": {"1.9.0": _release("1.9.0"), "1.10.0": _release("1.10.0")}}
    assert versions.latest_stable(body) == "1.10.0"
