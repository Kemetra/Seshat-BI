"""CLI-level test for `retail theme-gen` (Slice 1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.cli import main

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


def test_theme_gen_parser_accepts_font_pt_flags() -> None:
    from seshat.cli.parser import _build_parser

    parser = _build_parser()
    args = parser.parse_args(
        [
            "theme-gen",
            "--name",
            "t1",
            "--mode",
            "light",
            "--accent",
            "#2E7D5B",
            "--background",
            "#FFFFFF",
            "--text-primary",
            "#111111",
            "--title-font-pt",
            "14",
            "--label-font-pt",
            "10",
        ]
    )
    assert args.title_font_pt == 14.0
    assert args.label_font_pt == 10.0


def test_theme_gen_parser_font_pt_flags_default_none() -> None:
    from seshat.cli.parser import _build_parser

    parser = _build_parser()
    args = parser.parse_args(
        [
            "theme-gen",
            "--name",
            "t1",
            "--mode",
            "light",
            "--accent",
            "#2E7D5B",
            "--background",
            "#FFFFFF",
            "--text-primary",
            "#111111",
        ]
    )
    assert args.title_font_pt is None
    assert args.label_font_pt is None


def test_cli_below_floor_title_font_pt_refused(tmp_path: Path) -> None:
    args = _args(tmp_path) + ["--title-font-pt", "8"]
    assert main(args) == 2
