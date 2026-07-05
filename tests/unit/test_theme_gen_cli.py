"""CLI-level test for `retail theme-gen` (Slice 1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from retail.cli import main

pytestmark = pytest.mark.unit


def _args(tmp: Path) -> list[str]:
    return [
        "theme-gen",
        "--name",
        "gen-dark",
        "--mode",
        "dark",
        "--accent",
        "#2FB6C4",
        "--background",
        "#12263A",
        "--text-primary",
        "#F2F6FA",
        "--text-secondary",
        "#C4D1DE",
        "--text-muted",
        "#93A6B8",
        "--repo",
        str(tmp),
    ]


def test_cli_generates_and_exits_zero(tmp_path: Path) -> None:
    rc = main(_args(tmp_path))
    assert rc == 0
    assert (tmp_path / "themes/gen-dark.theme.json").exists()
    assert (tmp_path / "design/tokens/gen-dark-design-tokens.yaml").exists()
    assert (tmp_path / "themes/gen-dark.theme-spec.md").exists()


def test_cli_bad_hex_exits_two(tmp_path: Path) -> None:
    bad = _args(tmp_path)
    bad[bad.index("#2FB6C4")] = "not-hex"
    assert main(bad) == 2
