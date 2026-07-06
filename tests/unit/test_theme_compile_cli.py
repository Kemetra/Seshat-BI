"""CLI-level test for `retail theme-compile`."""

from __future__ import annotations

from pathlib import Path

import pytest

from retail.cli import main
from retail.theme_gen import ThemeSeed, generate

pytestmark = pytest.mark.unit

SEED = ThemeSeed(
    name="cli-dark",
    mode="dark",
    accent="#2FB6C4",
    background="#12263A",
    text_primary="#F2F6FA",
    text_secondary="#C4D1DE",
    text_muted="#93A6B8",
    data_colors=("#A5E3E9", "#7BD6DF", "#52C9D6", "#2FB7C5", "#25919C", "#1C6B73"),
    good="#2E7D5B",
    neutral="#B5832A",
    bad="#B23A3A",
)


def test_cli_compiles_and_exits_zero(tmp_path: Path):
    generate(SEED, tmp_path, force=True)
    (tmp_path / "themes/cli-dark.theme.json").unlink()
    tokens = tmp_path / "design/tokens/cli-dark-design-tokens.yaml"
    rc = main(["theme-compile", "--tokens", str(tokens)])
    assert rc == 0
    assert (tmp_path / "themes/cli-dark.theme.json").exists()


def test_cli_missing_tokens_exits_two(tmp_path: Path):
    rc = main(["theme-compile", "--tokens", str(tmp_path / "nope.yaml")])
    assert rc == 2
