"""Curated stack: the CLI surface -- profile composition and JSON purity.

Which components a profile names, that every profile is reachable from the
CLI choices and allowlisted, and that `--json` emits parseable JSON and
never prompts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.cli.commands.integrations import integrations_main
from seshat.integrations.catalog import (
    ANALYTICS_FULL,
    PROFILE_NAMES,
    Channel,
    Component,
    SourceType,
    profile_components,
)
from tests.unit._curated_stack_fixtures import (
    _args,
    _workspace,
)

pytestmark = pytest.mark.unit


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
