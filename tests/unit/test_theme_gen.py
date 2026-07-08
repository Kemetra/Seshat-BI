"""Unit tests for the theme generator (retail.theme_gen), Slice 1."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest
import yaml

from retail.theme_gen import (
    ThemeGenError,
    ThemeSeed,
    build_palette,
    derive_ramp,
    generate,
    render_spec_md,
    render_theme_json,
    render_tokens_yaml,
)

pytestmark = pytest.mark.unit

DARK = dict(
    name="executive-dark",
    mode="dark",
    accent="#2FB6C4",
    background="#12263A",
    text_primary="#F2F6FA",
    text_secondary="#C4D1DE",
    text_muted="#93A6B8",
    data_colors=None,
    good="#3DDC97",
    neutral="#E5C13B",
    bad="#F2705B",
)


def _seed(**over) -> ThemeSeed:
    d = {**DARK, **over}
    return ThemeSeed(**d)


def test_derive_ramp_is_monotonic_lightness() -> None:
    from retail.color import relative_luminance

    ramp = derive_ramp("#2FB6C4", n=6)
    assert len(ramp) == 6
    lums = [relative_luminance(c) for c in ramp]
    assert lums == sorted(lums, reverse=True)  # light -> dark


def test_build_palette_derives_ramp_when_none() -> None:
    pal = build_palette(_seed(data_colors=None))
    assert len(pal["colors"]["data_colors"]) >= 4
    assert pal["colors"]["background"] == "#12263A"


def test_build_palette_uses_given_ramp() -> None:
    pal = build_palette(_seed(data_colors=("#111111", "#222222")))
    assert pal["colors"]["data_colors"] == ["#111111", "#222222"]


def test_generate_writes_three_artifacts(tmp_path: Path) -> None:
    paths = generate(_seed(), repo_root=tmp_path)
    rels = sorted(str(p.relative_to(tmp_path)).replace("\\", "/") for p in paths)
    assert rels == [
        "design/tokens/executive-dark-design-tokens.yaml",
        "themes/executive-dark.theme-spec.md",
        "themes/executive-dark.theme.json",
    ]


def test_generated_theme_is_dl3_faithful(tmp_path: Path) -> None:
    generate(_seed(), repo_root=tmp_path)
    theme = json.loads((tmp_path / "themes/executive-dark.theme.json").read_text())
    tokens = yaml.safe_load(
        (tmp_path / "design/tokens/executive-dark-design-tokens.yaml").read_text()
    )
    assert theme["background"] == tokens["colors"]["background"]
    assert theme["dataColors"] == tokens["colors"]["data_colors"]
    assert tokens["meta"]["compiles_to"] == "themes/executive-dark.theme.json"


def test_generated_theme_is_dl1_clean(tmp_path: Path) -> None:
    generate(_seed(), repo_root=tmp_path)
    theme = json.loads((tmp_path / "themes/executive-dark.theme.json").read_text())
    forbidden = (
        "dax",
        "measure",
        "calculated",
        "expression",
        "threshold",
        "rule",
        "relationship",
        "sourcemapping",
        "validation",
        "metricdefinition",
    )
    allowed = {
        "good",
        "neutral",
        "bad",
        "datacolors",
        "foreground",
        "background",
        "tableaccent",
    }

    def norm(k: str) -> str:
        return k.lower().replace("-", "").replace("_", "").replace(" ", "")

    def walk(node) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                nk = norm(k)
                if nk not in allowed:
                    assert not any(t in nk for t in forbidden), f"forbidden key {k}"
                walk(v)
        elif isinstance(node, list):
            for it in node:
                walk(it)

    walk(theme)


def test_spec_readiness_is_warning_not_pass(tmp_path: Path) -> None:
    generate(_seed(), repo_root=tmp_path)
    spec = (tmp_path / "themes/executive-dark.theme-spec.md").read_text()
    assert "**Status:** `warning`" in spec
    # the Readiness Status line must not say pass
    readiness = spec.split("## Readiness")[1]
    status_line = readiness.split("Status:")[1].splitlines()[0]
    assert "pass" not in status_line


def test_contrast_failure_refuses_to_write(tmp_path: Path) -> None:
    # text_muted too dark on a dark bg -> below 4.5:1
    with pytest.raises(ThemeGenError, match="contrast"):
        generate(_seed(text_muted="#1A2A38"), repo_root=tmp_path)
    assert not (tmp_path / "themes/executive-dark.theme.json").exists()


def test_bad_hex_is_clean_error(tmp_path: Path) -> None:
    with pytest.raises(ThemeGenError, match="hex"):
        generate(_seed(accent="not-a-hex"), repo_root=tmp_path)


def test_refuses_overwrite_without_force(tmp_path: Path) -> None:
    generate(_seed(), repo_root=tmp_path)
    with pytest.raises(ThemeGenError, match="exists"):
        generate(_seed(), repo_root=tmp_path)
    generate(_seed(), repo_root=tmp_path, force=True)  # ok with force


@pytest.mark.parametrize(
    "bad_name",
    ["../../pwned", "../powerbi/definition/report", "a/b", "a\\b", "..", ".hidden"],
)
def test_name_path_traversal_is_refused(tmp_path: Path, bad_name: str) -> None:
    # A --name that contains a path separator or '..' must be refused and write
    # NOTHING (it could otherwise escape themes/ into powerbi/ -- a hard boundary).
    with pytest.raises(ThemeGenError, match="slug"):
        generate(_seed(name=bad_name), repo_root=tmp_path)
    # nothing escaped the tmp repo
    assert list(tmp_path.rglob("*.theme.json")) == []
    assert list(tmp_path.rglob("*.theme-spec.md")) == []


def test_empty_data_colors_is_clean_error(tmp_path: Path) -> None:
    # An empty explicit ramp must raise ThemeGenError, never an IndexError
    # traceback (the module's "never a traceback" contract).
    with pytest.raises(ThemeGenError, match="empty"):
        generate(_seed(data_colors=()), repo_root=tmp_path)


def test_targets_for_returns_expected_three_paths(tmp_path: Path) -> None:
    from retail.theme_gen import _targets_for, build_palette

    seed = _seed()
    palette = build_palette(seed)
    targets = _targets_for(seed, tmp_path, palette)
    rels = sorted(str(p.relative_to(tmp_path)).replace("\\", "/") for p in targets)
    assert rels == [
        "design/tokens/executive-dark-design-tokens.yaml",
        "themes/executive-dark.theme-spec.md",
        "themes/executive-dark.theme.json",
    ]
    assert all(isinstance(v, str) and v for v in targets.values())


def test_check_font_floor_raises_below_title_floor() -> None:
    from retail.theme_gen import ThemeGenError, check_font_floor_or_raise

    seed = _seed(title_font_pt=11.9)
    with pytest.raises(ThemeGenError, match="title_font_pt"):
        check_font_floor_or_raise(seed)


def test_check_font_floor_raises_below_label_floor() -> None:
    from retail.theme_gen import ThemeGenError, check_font_floor_or_raise

    seed = _seed(label_font_pt=8.9)
    with pytest.raises(ThemeGenError, match="label_font_pt"):
        check_font_floor_or_raise(seed)


def test_check_font_floor_passes_at_exact_floor() -> None:
    from retail.theme_gen import check_font_floor_or_raise

    seed = _seed(title_font_pt=12.0, label_font_pt=9.0)
    check_font_floor_or_raise(seed)  # no raise


def test_font_floor_constants_are_fixed_values() -> None:
    from retail.theme_gen import MIN_LABEL_FONT_PT, MIN_TITLE_FONT_PT, TAP_TARGET_MIN_PX

    assert MIN_TITLE_FONT_PT == 12.0
    assert MIN_LABEL_FONT_PT == 9.0
    assert TAP_TARGET_MIN_PX == 44


def test_render_theme_json_uses_seed_font_sizes() -> None:
    theme = json.loads(render_theme_json(build_palette(_seed()), _seed()))
    title = theme["visualStyles"]["*"]["*"]["title"][0]
    labels = theme["visualStyles"]["*"]["*"]["labels"][0]
    assert title["fontSize"] == 12
    assert labels["fontSize"] == 9


def test_render_theme_json_custom_font_sizes_round_trip() -> None:
    seed = _seed(title_font_pt=14.0, label_font_pt=10.0)
    theme = json.loads(render_theme_json(build_palette(seed), seed))
    assert theme["visualStyles"]["*"]["*"]["title"][0]["fontSize"] == 14
    assert theme["visualStyles"]["*"]["*"]["labels"][0]["fontSize"] == 10


def test_tokens_yaml_emits_typography_block() -> None:
    tokens = yaml.safe_load(render_tokens_yaml(build_palette(_seed()), _seed()))
    assert tokens["typography"]["title_font_pt"] == 12
    assert tokens["typography"]["label_font_pt"] == 9


def test_generate_refuses_sub_floor_title_font(tmp_path: Path) -> None:
    with pytest.raises(ThemeGenError, match="title_font_pt"):
        generate(_seed(title_font_pt=11.9), repo_root=tmp_path)
    assert not (tmp_path / "themes").exists()  # refused before any write


def test_spec_md_has_font_floor_line_and_tap_target_is_doc_only() -> None:
    spec = render_spec_md(build_palette(_seed()), _seed())
    assert "[x]" in spec and "Font floor" in spec
    assert "tap" in spec.lower() or "Tap" in spec
    assert '"tapTarget"' not in spec


def _cli_args(**over) -> Namespace:
    base = dict(
        name="executive-dark",
        mode="dark",
        accent="#2FB6C4",
        background="#12263A",
        text_primary="#F2F6FA",
        text_secondary=None,
        text_muted=None,
        data_colors=None,
        good=None,
        neutral=None,
        bad=None,
        title_font_pt=None,
        label_font_pt=None,
        repo=".",
        force=False,
    )
    return Namespace(**{**base, **over})


def test_seed_from_args_omitted_font_flags_use_min_floor_defaults() -> None:
    from retail.theme_gen import MIN_LABEL_FONT_PT, MIN_TITLE_FONT_PT, _seed_from_args

    seed = _seed_from_args(_cli_args())
    assert seed.title_font_pt == MIN_TITLE_FONT_PT == 12.0
    assert seed.label_font_pt == MIN_LABEL_FONT_PT == 9.0


def test_seed_from_args_provided_font_flags_pass_through() -> None:
    from retail.theme_gen import _seed_from_args

    seed = _seed_from_args(_cli_args(title_font_pt=14.0, label_font_pt=10.0))
    assert seed.title_font_pt == 14.0
    assert seed.label_font_pt == 10.0
