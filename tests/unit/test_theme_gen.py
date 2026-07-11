"""Unit tests for the theme generator (seshat.theme_gen), Slice 1."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest
import yaml

from seshat.theme_gen import (
    ThemeGenError,
    ThemeSeed,
    build_palette,
    check_composite_contrast_or_raise,
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


LIGHT = dict(
    name="executive-light",
    mode="light",
    accent="#1B6E4F",
    background="#F5F7FA",
    text_primary="#1A2430",
    text_secondary="#3D4A59",
    text_muted="#5B6B7C",
    data_colors=None,
    good="#1F7A4D",
    neutral="#8A6D1D",
    bad="#A23A3A",
)


def _light_seed(**over) -> ThemeSeed:
    d = {**LIGHT, **over}
    return ThemeSeed(**d)


def test_derive_dark_seed_inverts_background_and_text_only() -> None:
    from seshat.theme_gen import derive_dark_seed

    light = _light_seed()
    dark = derive_dark_seed(light)
    assert dark.mode == "dark"
    assert dark.name == "executive-light-dark"
    assert dark.background != light.background
    assert dark.text_primary != light.text_primary
    # everything else passes through unchanged
    assert dark.accent == light.accent
    assert dark.data_colors == light.data_colors
    assert dark.good == light.good
    assert dark.neutral == light.neutral
    assert dark.bad == light.bad


def test_derive_dark_seed_clears_contrast_floor(tmp_path: Path) -> None:
    from seshat.theme_gen import (
        build_palette,
        check_contrast_or_raise,
        derive_dark_seed,
    )

    dark = derive_dark_seed(_light_seed())
    palette = build_palette(dark)
    check_contrast_or_raise(palette)  # must not raise


def test_derive_dark_seed_rejects_non_light_input() -> None:
    from seshat.theme_gen import derive_dark_seed

    with pytest.raises(ThemeGenError, match="mode"):
        derive_dark_seed(_seed())  # DARK fixture: mode="dark"


def test_generate_pair_writes_six_files(tmp_path: Path) -> None:
    from seshat.theme_gen import generate_pair

    light_written, dark_written = generate_pair(_light_seed(), repo_root=tmp_path)
    assert len(light_written) == 3
    assert len(dark_written) == 3
    dark_rels = sorted(
        str(p.relative_to(tmp_path)).replace("\\", "/") for p in dark_written
    )
    assert dark_rels == [
        "design/tokens/executive-light-dark-design-tokens.yaml",
        "themes/executive-light-dark.theme-spec.md",
        "themes/executive-light-dark.theme.json",
    ]


def test_generate_pair_rejects_dark_mode_input(tmp_path: Path) -> None:
    from seshat.theme_gen import generate_pair

    with pytest.raises(ThemeGenError, match="mode"):
        generate_pair(_seed(), repo_root=tmp_path)  # DARK fixture: mode="dark"
    assert list(tmp_path.rglob("*.theme.json")) == []


def test_generate_pair_rejects_name_already_ending_in_dark(tmp_path: Path) -> None:
    from seshat.theme_gen import generate_pair

    with pytest.raises(ThemeGenError, match="dark"):
        generate_pair(_light_seed(name="foo-dark"), repo_root=tmp_path)
    assert list(tmp_path.rglob("*.theme.json")) == []


def test_generate_pair_writes_nothing_if_dark_side_fails_aa(tmp_path: Path) -> None:
    from seshat.theme_gen import generate_pair

    # text_muted picked so the LIGHT side clears AA but the lightness-inverted
    # DARK side (1.0 - L) collapses contrast against the inverted background.
    light = _light_seed(text_muted="#EDEFF2")
    with pytest.raises(ThemeGenError, match="contrast"):
        generate_pair(light, repo_root=tmp_path)
    assert list(tmp_path.rglob("*.theme.json")) == []
    assert list(tmp_path.rglob("*.theme-spec.md")) == []


def test_composite_contrast_raises_below_floor() -> None:
    palette = build_palette(_seed())
    bg = palette["colors"]["background"]
    palette_with_weak_fg = {
        **palette,
        "transparency": {"overlay": {"fg": bg, "transparency_pct": 0.0}},
    }
    with pytest.raises(ThemeGenError, match="composite"):
        check_composite_contrast_or_raise(palette_with_weak_fg, floor=4.5)


def test_composite_contrast_passes_at_or_above_floor() -> None:
    palette = build_palette(_seed())
    fg = palette["colors"]["text"]["primary"]
    palette_with_strong_fg = {
        **palette,
        "transparency": {"overlay": {"fg": fg, "transparency_pct": 0.0}},
    }
    check_composite_contrast_or_raise(palette_with_strong_fg, floor=4.5)  # no raise


def test_composite_contrast_no_transparency_role_is_noop() -> None:
    # A seed with no transparency block declares nothing to composite against,
    # so the check is a silent no-op -- never a fabricated pass, never an error
    # on absence.
    palette = build_palette(_seed())
    assert check_composite_contrast_or_raise(palette) is None


# --- T18 wired: transparency block flows seed -> palette -> gate -> artifacts --


def test_default_seed_emits_no_transparency_block(tmp_path: Path) -> None:
    """Backward compat: a seed with transparency=None writes exactly what it did
    before T18 -- no `transparency:` in tokens, no visual `background` style."""
    generate(_seed(), repo_root=tmp_path)
    tokens = (tmp_path / "design/tokens/executive-dark-design-tokens.yaml").read_text()
    theme = json.loads((tmp_path / "themes/executive-dark.theme.json").read_text())
    assert "transparency:" not in tokens
    assert "background" not in theme["visualStyles"]["*"]["*"]


def test_generate_with_passing_overlay_writes_and_emits_blocks(tmp_path: Path) -> None:
    seed = _seed(transparency={"overlay": {"fg": "#F2F6FA", "transparency_pct": 0.0}})
    generate(seed, repo_root=tmp_path)
    tokens = yaml.safe_load(
        (tmp_path / "design/tokens/executive-dark-design-tokens.yaml").read_text()
    )
    assert tokens["transparency"]["overlay"]["fg"] == "#F2F6FA"
    assert tokens["transparency"]["overlay"]["transparency_pct"] == 0
    theme = json.loads((tmp_path / "themes/executive-dark.theme.json").read_text())
    bg_style = theme["visualStyles"]["*"]["*"]["background"][0]
    assert bg_style["color"]["solid"]["color"] == "#F2F6FA"
    assert bg_style["transparency"] == 0
    spec = (tmp_path / "themes/executive-dark.theme-spec.md").read_text()
    assert "[x] **Composite transparency contrast**" in spec


def test_generate_with_failing_overlay_refuses_write(tmp_path: Path) -> None:
    # overlay fg == background at 0% opacity -> composites to the background,
    # 1:1 contrast -> below AA -> refuse, write nothing.
    seed = _seed(transparency={"overlay": {"fg": "#12263A", "transparency_pct": 0.0}})
    with pytest.raises(ThemeGenError, match="composite"):
        generate(seed, repo_root=tmp_path)
    assert list(tmp_path.rglob("*.theme.json")) == []
    assert list(tmp_path.rglob("*.theme-spec.md")) == []


def test_build_palette_rejects_unknown_transparency_role() -> None:
    with pytest.raises(ThemeGenError, match="not allowed"):
        build_palette(
            _seed(transparency={"tooltip": {"fg": "#FFFFFF", "transparency_pct": 0.0}})
        )


def test_build_palette_rejects_out_of_range_pct() -> None:
    with pytest.raises(ThemeGenError, match="range"):
        build_palette(
            _seed(
                transparency={"overlay": {"fg": "#FFFFFF", "transparency_pct": 150.0}}
            )
        )


def test_build_palette_rejects_partial_overlay_missing_pct() -> None:
    with pytest.raises(ThemeGenError, match="number"):
        build_palette(_seed(transparency={"overlay": {"fg": "#FFFFFF"}}))


def test_seed_from_args_builds_overlay_from_flags() -> None:
    from seshat.theme_gen import _seed_from_args

    seed = _seed_from_args(
        _cli_args(overlay_fg="#F2F6FA", overlay_transparency_pct=20.0)
    )
    assert seed.transparency == {"overlay": {"fg": "#F2F6FA", "transparency_pct": 20.0}}


def test_seed_from_args_no_overlay_flags_is_none() -> None:
    from seshat.theme_gen import _seed_from_args

    assert _seed_from_args(_cli_args()).transparency is None


def test_derive_dark_seed_passes_transparency_through() -> None:
    from seshat.theme_gen import derive_dark_seed

    light = _light_seed(
        transparency={"overlay": {"fg": "#1A2430", "transparency_pct": 10.0}}
    )
    dark = derive_dark_seed(light)
    assert dark.transparency == light.transparency


def test_derive_ramp_is_monotonic_lightness() -> None:
    from seshat.color import relative_luminance

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
    from seshat.theme_gen import _targets_for, build_palette

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
    from seshat.theme_gen import ThemeGenError, check_font_floor_or_raise

    seed = _seed(title_font_pt=11.9)
    with pytest.raises(ThemeGenError, match="title_font_pt"):
        check_font_floor_or_raise(seed)


def test_check_font_floor_raises_below_label_floor() -> None:
    from seshat.theme_gen import ThemeGenError, check_font_floor_or_raise

    seed = _seed(label_font_pt=8.9)
    with pytest.raises(ThemeGenError, match="label_font_pt"):
        check_font_floor_or_raise(seed)


def test_check_font_floor_passes_at_exact_floor() -> None:
    from seshat.theme_gen import check_font_floor_or_raise

    seed = _seed(title_font_pt=12.0, label_font_pt=9.0)
    check_font_floor_or_raise(seed)  # no raise


def test_font_floor_constants_are_fixed_values() -> None:
    from seshat.theme_gen import MIN_LABEL_FONT_PT, MIN_TITLE_FONT_PT, TAP_TARGET_MIN_PX

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
        pair=False,
        overlay_fg=None,
        overlay_transparency_pct=None,
    )
    return Namespace(**{**base, **over})


def test_seed_from_args_omitted_font_flags_use_min_floor_defaults() -> None:
    from seshat.theme_gen import MIN_LABEL_FONT_PT, MIN_TITLE_FONT_PT, _seed_from_args

    seed = _seed_from_args(_cli_args())
    assert seed.title_font_pt == MIN_TITLE_FONT_PT == 12.0
    assert seed.label_font_pt == MIN_LABEL_FONT_PT == 9.0


def test_seed_from_args_provided_font_flags_pass_through() -> None:
    from seshat.theme_gen import _seed_from_args

    seed = _seed_from_args(_cli_args(title_font_pt=14.0, label_font_pt=10.0))
    assert seed.title_font_pt == 14.0
    assert seed.label_font_pt == 10.0


def test_min_categorical_delta_e_default_ramp_passes_floor() -> None:
    from seshat.theme_gen import MIN_CATEGORICAL_DELTAE, min_categorical_delta_e

    palette = build_palette(_seed())
    got = min_categorical_delta_e(tuple(palette["colors"]["data_colors"]))
    assert got >= MIN_CATEGORICAL_DELTAE


def test_check_categorical_distinctness_or_raise_flags_near_identical_pair() -> None:
    from seshat.theme_gen import check_categorical_distinctness_or_raise

    palette = build_palette(_seed())
    palette["colors"]["data_colors"] = ["#2FB6C4", "#2FB6C5", "#12263A"]
    with pytest.raises(ThemeGenError) as exc:
        check_categorical_distinctness_or_raise(palette)
    msg = str(exc.value)
    assert "#2FB6C4" in msg
    assert "#2FB6C5" in msg


def test_check_categorical_distinctness_or_raise_flags_nonadjacent_pair() -> None:
    # The near-identical pair sits at indices 0 and 2, not adjacent -- proves
    # the check is whole-set (all i<j pairs), not just neighboring entries.
    from seshat.theme_gen import check_categorical_distinctness_or_raise

    palette = build_palette(_seed())
    palette["colors"]["data_colors"] = ["#2FB6C4", "#12263A", "#2FB6C5"]
    with pytest.raises(ThemeGenError) as exc:
        check_categorical_distinctness_or_raise(palette)
    msg = str(exc.value)
    assert "#2FB6C4" in msg
    assert "#2FB6C5" in msg


def test_check_categorical_distinctness_or_raise_honors_floor_param() -> None:
    from seshat.theme_gen import check_categorical_distinctness_or_raise

    palette = build_palette(_seed())
    palette["colors"]["data_colors"] = ["#2FB6C4", "#2FB6C5"]
    check_categorical_distinctness_or_raise(palette, floor=0.0)  # does not raise


def test_min_categorical_delta_e_single_color_is_noop() -> None:
    from seshat.theme_gen import (
        check_categorical_distinctness_or_raise,
        min_categorical_delta_e,
    )

    assert min_categorical_delta_e(("#2FB6C4",)) == float("inf")
    palette = build_palette(_seed())
    palette["colors"]["data_colors"] = ["#2FB6C4"]
    check_categorical_distinctness_or_raise(palette)  # does not raise


def test_check_ramp_deltae_raises_below_floor() -> None:
    from seshat.theme_gen import (
        ThemeGenError,
        build_palette,
        check_ramp_deltae_or_raise,
    )

    palette = build_palette(
        _seed(data_colors=("#336699", "#346699"))
    )  # near-identical adjacent pair
    with pytest.raises(ThemeGenError, match="deltaE76"):
        check_ramp_deltae_or_raise(palette, floor=10.0)


def test_check_ramp_deltae_names_both_hexes() -> None:
    from seshat.theme_gen import (
        ThemeGenError,
        build_palette,
        check_ramp_deltae_or_raise,
    )

    palette = build_palette(_seed(data_colors=("#336699", "#346699")))
    with pytest.raises(ThemeGenError) as exc_info:
        check_ramp_deltae_or_raise(palette, floor=10.0)
    assert "#336699" in str(exc_info.value)
    assert "#346699" in str(exc_info.value)


def test_check_ramp_deltae_passes_at_or_above_floor() -> None:
    from seshat.theme_gen import build_palette, check_ramp_deltae_or_raise

    palette = build_palette(_seed(data_colors=("#000000", "#FFFFFF", "#000000")))
    check_ramp_deltae_or_raise(
        palette, floor=10.0
    )  # no raise -- deltaE ~= 100 each hop


def test_check_ramp_deltae_floor_is_a_real_param() -> None:
    # Measured deltaE76 for this pair is ~0.20 (see the
    # test_check_ramp_deltae_raises_below_floor / _names_both_hexes tests,
    # which use floor=10.0 and do raise). A floor below that measured value
    # must pass -- proving `floor` is a live parameter, not a fixed constant.
    from seshat.theme_gen import build_palette, check_ramp_deltae_or_raise

    palette = build_palette(_seed(data_colors=("#336699", "#346699")))
    check_ramp_deltae_or_raise(palette, floor=0.05)  # very low floor -- pair now passes


def test_check_ramp_deltae_ignores_nonadjacent_near_duplicate() -> None:
    # The near-identical pair sits at indices 0 and 2 (NOT adjacent); the
    # actual adjacent pairs (0,1) and (1,2) are both well-separated. This
    # proves check_ramp_deltae_or_raise is adjacent-only (zip(dc, dc[1:])),
    # unlike check_categorical_distinctness_or_raise's whole-set i<j scan,
    # which WOULD flag this same ramp (see the "_nonadjacent_pair" test
    # above for that whole-set counterpart).
    from seshat.theme_gen import build_palette, check_ramp_deltae_or_raise

    palette = build_palette(_seed())
    palette["colors"]["data_colors"] = ["#2FB6C4", "#12263A", "#2FB6C5"]
    check_ramp_deltae_or_raise(
        palette, floor=10.0
    )  # no raise -- adjacent pairs are fine


def test_generate_refuses_near_collapsed_data_colors(tmp_path: Path) -> None:
    # OWNER-ratified MIN_ADJACENT_DELTAE = 3.0 (Task 14). This pair
    # (#336699/#2B6092) measures ~2.52 dE76 apart: ABOVE the whole-set
    # categorical floor (2.0, so check_categorical_distinctness_or_raise does
    # NOT fire) but BELOW the adjacent-ramp floor (3.0). Only the ramp check
    # this task wires in can refuse this pair -- a genuinely discriminating
    # regression for Task 15's marginal behavior (a pair caught by the
    # near-identical #336699/#346699 case, ~0.20 apart, would already be
    # refused by the pre-existing categorical check and prove nothing new).
    seed = _seed(data_colors=("#336699", "#2B6092", "#1F4E79"))
    with pytest.raises(ThemeGenError, match="deltaE76"):
        generate(seed, repo_root=tmp_path)
    assert not (tmp_path / "themes").exists()  # refused before any write


def test_generate_shipping_default_ramp_still_passes(tmp_path: Path) -> None:
    # data_colors=None -> build_palette derives via derive_ramp(accent); this
    # must clear the ratified MIN_ADJACENT_DELTAE floor. _seed() defaults to
    # accent="#2FB6C4" (the literal DARK shipping fixture), whose derived
    # ramp has the tightest measured margin among committed accents: min
    # adjacent dE76 ~= 6.86, comfortably above the 3.0 floor. This is the
    # regression Task 14's ratification exists to protect.
    written = generate(_seed(), repo_root=tmp_path)
    assert len(written) == 3


def test_generate_shipping_default_sentiment_accent_ramp_also_passes(
    tmp_path: Path,
) -> None:
    # Secondary regression: the other committed accent cited in the Task 14
    # ratification evidence (#2E7D5B, min adjacent dE76 ~= 9.13) also clears
    # the floor end-to-end.
    seed = _seed(accent="#2E7D5B", data_colors=None)
    written = generate(seed, repo_root=tmp_path)
    assert len(written) == 3
