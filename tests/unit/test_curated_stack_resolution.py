"""Curated stack: what a component resolves to, and when resolution REFUSES.

Exactness of the coordinate itself (prerelease, yanked, incompatible,
conflicting), the honesty of its label (rolling is not stable, preview stays
preview), and the `requires-python` evaluator all three rest on.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.integrations import resolvers, versions
from seshat.integrations.catalog import (
    Channel,
    Component,
    SourceType,
)
from seshat.integrations.compat import BASELINE_PINS, apply_policy
from seshat.integrations.installer import plan as plan_profile
from seshat.integrations.render import as_json, as_text
from seshat.integrations.resolvers import (
    Resolvers,
    resolve_github,
    resolve_npm,
    resolve_pypi,
)
from tests.unit._curated_stack_fixtures import (
    FakeGitHub,
    FakeNpm,
    FakePypi,
    _github_component,
    _pypi_component,
    _release,
    _workspace,
)

pytestmark = pytest.mark.unit


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


def test_a_baseline_regression_outranks_the_interpreter_refusal() -> None:
    """When both refusals hit one component, the SPECIFIC one is what it reports.

    The interpreter floor rejects every component with the same blanket message,
    so a component that ALSO regressed below its baseline must still report the
    regression -- that message names the component and both versions, and is the
    one an operator can act on. Both reasons are still reported, interpreter
    first, because each is separately true.
    """
    from seshat.integrations.catalog import component

    core = component("dbt-core")
    downgraded = resolvers.Resolution(
        component_id="dbt-core", ok=True, channel=Channel.STABLE, version="1.0.0"
    )

    verdict = apply_policy([(core, downgraded)], python_version=(3, 9))

    assert [reason.split(";")[0] for reason in verdict.reasons] == [
        "Seshat requires Python >= 3.13",
        "dbt-core resolved to 1.0.0, which is older than the known compatible "
        "baseline 1.12.0",
    ]
    assert "older than the known compatible baseline" in verdict.resolutions[0].reason


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
