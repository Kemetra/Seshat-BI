"""Unit tests for the tokens->theme compiler (seshat.theme_compile)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from seshat.theme_compile import (
    ThemeCompileError,
    compile_theme,
    palette_from_tokens,
    seed_from_tokens,
)

pytestmark = pytest.mark.unit

# A committed-tokens doc in the exact shape render_tokens_yaml writes.
TOKENS = {
    "meta": {
        "name": "executive-dark-design-tokens",
        "style": "generated (dark)",
        "version": "1",
        "compiles_to": "themes/executive-dark.theme.json",
    },
    "colors": {
        "primary": "#2FB6C4",
        "secondary": "#7BD6DF",
        "background": "#12263A",
        "text": {"primary": "#F2F6FA", "secondary": "#C4D1DE", "muted": "#93A6B8"},
        "sentiment": {"success": "#2E7D5B", "warning": "#B5832A", "danger": "#B23A3A"},
        "data_colors": [
            "#A5E3E9",
            "#7BD6DF",
            "#52C9D6",
            "#2FB7C5",
            "#25919C",
            "#1C6B73",
        ],
    },
}


def test_palette_from_tokens_copies_every_color_field():
    pal = palette_from_tokens(TOKENS)
    c = pal["colors"]
    assert c["primary"] == "#2FB6C4"
    assert c["background"] == "#12263A"
    assert c["text"]["muted"] == "#93A6B8"
    assert c["sentiment"]["success"] == "#2E7D5B"
    assert c["data_colors"] == TOKENS["colors"]["data_colors"]


def test_seed_from_tokens_strips_suffix_for_name():
    seed = seed_from_tokens(TOKENS, name_override=None)
    assert seed.name == "executive-dark"  # -design-tokens stripped
    assert seed.mode == "dark"  # parsed from meta.style "generated (dark)"
    assert seed.accent == "#2FB6C4"


def test_seed_from_tokens_name_override_wins():
    seed = seed_from_tokens(TOKENS, name_override="my-theme")
    assert seed.name == "my-theme"


def test_seed_from_tokens_rejects_bad_slug():
    with pytest.raises(ThemeCompileError):
        seed_from_tokens(TOKENS, name_override="../escape")


def _write_tokens(tmp: Path, doc: dict) -> Path:
    p = tmp / "design" / "tokens" / "executive-dark-design-tokens.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return p


def test_compile_is_byte_identical_to_theme_gen(tmp_path: Path):
    # 1. theme-gen produces the reference theme.json for a seed.
    from seshat.theme_gen import ThemeSeed, generate

    seed = ThemeSeed(
        name="executive-dark",
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
    generate(seed, tmp_path, force=True)
    ref_theme = (tmp_path / "themes/executive-dark.theme.json").read_bytes()
    ref_tokens_doc = yaml.safe_load(
        (tmp_path / "design/tokens/executive-dark-design-tokens.yaml").read_text(
            encoding="utf-8-sig"
        )
    )

    # 2. delete the theme, keep the tokens theme-gen wrote.
    (tmp_path / "themes/executive-dark.theme.json").unlink()

    # 3. compile from those exact committed tokens.
    tokens_path = tmp_path / "design/tokens/executive-dark-design-tokens.yaml"
    out = compile_theme(tokens_path, out_path=None, force=False)

    # 4. byte-identical to theme-gen's output.
    assert out == tmp_path / "themes/executive-dark.theme.json"
    assert out.read_bytes() == ref_theme
    assert ref_tokens_doc  # sanity: tokens were real


def test_compile_round_trips_transparency_overlay(tmp_path: Path):
    """A committed tokens file carrying an opt-in overlay role compiles to the
    same theme.json theme-gen would emit (T18 round-trip)."""
    from seshat.theme_gen import ThemeSeed, generate

    seed = ThemeSeed(
        name="executive-dark",
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
        transparency={"overlay": {"fg": "#F2F6FA", "transparency_pct": 20.0}},
    )
    generate(seed, tmp_path, force=True)
    ref_theme = (tmp_path / "themes/executive-dark.theme.json").read_bytes()
    (tmp_path / "themes/executive-dark.theme.json").unlink()

    tokens_path = tmp_path / "design/tokens/executive-dark-design-tokens.yaml"
    out = compile_theme(tokens_path, out_path=None, force=False)
    assert out.read_bytes() == ref_theme
    theme = json.loads(out.read_text(encoding="utf-8"))
    assert theme["visualStyles"]["*"]["*"]["background"][0]["transparency"] == 20


def test_compile_refuses_failing_overlay(tmp_path: Path):
    """A committed overlay that composites below AA is refused on compile too
    (the gate runs on the compile leg, not just theme-gen)."""
    doc = {
        "meta": {
            "name": "executive-dark-design-tokens",
            "compiles_to": "themes/executive-dark.theme.json",
        },
        "colors": {
            "primary": "#2FB6C4",
            "secondary": "#7BD6DF",
            "background": "#12263A",
            "text": {"primary": "#F2F6FA", "secondary": "#C4D1DE", "muted": "#93A6B8"},
            "sentiment": {
                "success": "#2E7D5B",
                "warning": "#B5832A",
                "danger": "#B23A3A",
            },
            "data_colors": ["#A5E3E9", "#7BD6DF"],
        },
        "transparency": {"overlay": {"fg": "#12263A", "transparency_pct": 0.0}},
    }
    tokens_path = _write_tokens(tmp_path, doc)
    with pytest.raises(ThemeCompileError, match="composite"):
        compile_theme(tokens_path, out_path=None, force=False)


def _generate_executive_dark(tmp_path: Path, **seed_over):
    from seshat.theme_gen import ThemeSeed, generate

    seed = ThemeSeed(
        name="executive-dark",
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
        **seed_over,
    )
    generate(seed, tmp_path, force=True)
    return (
        tmp_path / "design/tokens/executive-dark-design-tokens.yaml",
        tmp_path / "themes/executive-dark.theme.json",
    )


def test_compile_reapplies_token_font_change_with_force(tmp_path: Path):
    """A token-driven font change recompiles cleanly over an existing theme with
    --force -- font sizes live in the generator-owned visualStyles */* keys, so
    they must not read as a hand-tuned DL3-deferred conflict (review finding)."""
    tokens_path, _ = _generate_executive_dark(tmp_path, title_font_pt=12.0)
    doc = yaml.safe_load(tokens_path.read_text(encoding="utf-8-sig"))
    doc["typography"]["title_font_pt"] = 20.0
    tokens_path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    out = compile_theme(tokens_path, out_path=None, force=True)  # must NOT raise
    theme = json.loads(out.read_text(encoding="utf-8"))
    assert theme["visualStyles"]["*"]["*"]["title"][0]["fontSize"] == 20


def test_compile_adds_token_overlay_with_force(tmp_path: Path):
    """Adding an opt-in overlay to a committed tokens file recompiles over the
    existing theme with --force (overlay background is generator-owned)."""
    tokens_path, _ = _generate_executive_dark(tmp_path)
    doc = yaml.safe_load(tokens_path.read_text(encoding="utf-8-sig"))
    doc["transparency"] = {"overlay": {"fg": "#F2F6FA", "transparency_pct": 20.0}}
    tokens_path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    out = compile_theme(tokens_path, out_path=None, force=True)  # must NOT raise
    theme = json.loads(out.read_text(encoding="utf-8"))
    assert theme["visualStyles"]["*"]["*"]["background"][0]["transparency"] == 20


def test_compile_still_refuses_hand_tuned_human_visual_style(tmp_path: Path):
    """The granular check still protects a genuinely human-added visualStyle: a
    hand-tuned non-generator key under */* is a DL3-deferred conflict and compile
    refuses to clobber it even with --force."""
    tokens_path, theme_path = _generate_executive_dark(tmp_path)
    theme = json.loads(theme_path.read_text(encoding="utf-8"))
    theme["visualStyles"]["*"]["*"]["wordWrap"] = [{"show": True}]
    theme_path.write_text(json.dumps(theme, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ThemeCompileError, match="visualStyles"):
        compile_theme(tokens_path, out_path=None, force=True)


def test_compile_refuses_overwrite_without_force(tmp_path: Path):
    tokens = _write_tokens(tmp_path, TOKENS)
    compile_theme(tokens, out_path=None, force=False)  # first write ok
    with pytest.raises(ThemeCompileError, match="refusing to overwrite"):
        compile_theme(tokens, out_path=None, force=False)


def test_compile_force_overwrites(tmp_path: Path):
    tokens = _write_tokens(tmp_path, TOKENS)
    compile_theme(tokens, out_path=None, force=False)
    out = compile_theme(tokens, out_path=None, force=True)  # no raise
    assert out.exists()


def test_missing_colors_field_is_clean_error(tmp_path: Path):
    doc = {"meta": TOKENS["meta"], "colors": {**TOKENS["colors"]}}
    del doc["colors"]["background"]
    tokens = _write_tokens(tmp_path, doc)
    with pytest.raises(ThemeCompileError, match="colors.background"):
        compile_theme(tokens, out_path=None, force=False)


def test_bad_hex_is_clean_error(tmp_path: Path):
    doc = {
        "meta": TOKENS["meta"],
        "colors": {**TOKENS["colors"], "primary": "not-a-hex"},
    }
    tokens = _write_tokens(tmp_path, doc)
    with pytest.raises(ThemeCompileError, match="#RRGGBB"):
        compile_theme(tokens, out_path=None, force=False)


def test_sub_aa_contrast_is_refused(tmp_path: Path):
    # muted text nearly equal to background -> below AA -> refuse.
    doc = {
        "meta": TOKENS["meta"],
        "colors": {
            **TOKENS["colors"],
            "text": {"primary": "#F2F6FA", "secondary": "#C4D1DE", "muted": "#13273B"},
        },
    }
    tokens = _write_tokens(tmp_path, doc)
    with pytest.raises(Exception):  # ThemeGenError from check_contrast_or_raise
        compile_theme(tokens, out_path=None, force=False)


def test_no_compiles_to_and_no_out_is_clean_error(tmp_path: Path):
    doc = {"meta": {"name": "x-design-tokens"}, "colors": TOKENS["colors"]}
    tokens = _write_tokens(tmp_path, doc)
    with pytest.raises(ThemeCompileError, match="compiles_to"):
        compile_theme(tokens, out_path=None, force=False)


def test_compile_refuses_when_deferred_field_differs_even_with_force(tmp_path: Path):
    # tower-retail-shaped case: the committed theme was hand-tuned by the owner
    # in a DL3-deferred field ("good"). compile must refuse to clobber it, even
    # with --force.
    tokens = _write_tokens(tmp_path, TOKENS)
    out = compile_theme(tokens, out_path=None, force=False)  # first write

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["good"] != "#111111"  # sanity: this is really a change
    doc["good"] = "#111111"  # simulate the owner's hand-tuned ruling
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ThemeCompileError, match="good") as exc_info:
        compile_theme(tokens, out_path=None, force=True)
    msg = str(exc_info.value).lower()
    assert "human-owned" in msg
    assert "deferred" in msg


def test_existing_theme_not_a_json_object_is_clean_error(tmp_path: Path):
    # The existing-theme file is valid JSON but not an object (e.g. a bare
    # array) -- must raise a clean ThemeCompileError, not a raw AttributeError
    # when the guard later calls .get() on it.
    tokens = _write_tokens(tmp_path, TOKENS)
    out_path = tmp_path / "themes" / "executive-dark.theme.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ThemeCompileError, match="not a JSON object"):
        compile_theme(tokens, out_path=None, force=True)


def test_compile_proceeds_when_only_dl3_governed_differs_with_force(tmp_path: Path):
    # Only dataColors (DL3-governed) drifted on disk -- this is the drift the
    # verb legitimately repairs. Deferred fields are untouched, so --force
    # still overwrites.
    tokens = _write_tokens(tmp_path, TOKENS)
    out = compile_theme(tokens, out_path=None, force=False)  # first write

    doc = json.loads(out.read_text(encoding="utf-8"))
    original_first_color = doc["dataColors"][0]
    doc["dataColors"][0] = "#000000"  # drift only a DL3-governed field
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    result = compile_theme(tokens, out_path=None, force=True)  # no raise
    rewritten = json.loads(result.read_text(encoding="utf-8"))
    assert rewritten["dataColors"][0] == original_first_color  # repaired


def test_seed_from_tokens_reads_typography_block() -> None:
    tokens = {**TOKENS, "typography": {"title_font_pt": 14, "label_font_pt": 10}}
    seed = seed_from_tokens(tokens, name_override=None)
    assert seed.title_font_pt == 14.0
    assert seed.label_font_pt == 10.0


def test_seed_from_tokens_falls_back_to_constants_when_typography_absent() -> None:
    # executive-dark shape: no typography block at all.
    seed = seed_from_tokens(TOKENS, name_override=None)
    assert seed.title_font_pt == 12.0
    assert seed.label_font_pt == 9.0


def test_seed_from_tokens_falls_back_per_key_when_typography_block_partial() -> None:
    # tower-retail shape: a typography block exists but lacks font-pt keys.
    tokens = {
        **TOKENS,
        "typography": {"font_family": "Segoe UI", "base_size_pt": 10},
    }
    seed = seed_from_tokens(tokens, name_override=None)
    assert seed.title_font_pt == 12.0
    assert seed.label_font_pt == 9.0


def test_compile_refuses_sub_floor_title_font(tmp_path: Path) -> None:
    tokens = {**TOKENS, "typography": {"title_font_pt": 11.9, "label_font_pt": 9}}
    p = _write_tokens(tmp_path, tokens)
    with pytest.raises(ThemeCompileError, match="title_font_pt"):
        compile_theme(p, out_path=None, force=False)


def test_custom_font_pt_round_trips_through_generate_then_compile(tmp_path: Path):
    """Idea 4 round-trip: gen a 14pt title, compile from its own tokens, no
    phantom DL3-deferred conflict, fontSize:14 survives byte-identical."""
    from seshat.theme_gen import ThemeSeed, generate

    seed = ThemeSeed(
        name="roundtrip",
        mode="light",
        accent="#2E7D5B",
        background="#FFFFFF",
        text_primary="#111111",
        text_secondary="#333333",
        text_muted="#555555",
        data_colors=None,
        good="#2E7D5B",
        neutral="#B5832A",
        bad="#B23A3A",
        title_font_pt=14.0,
        label_font_pt=9.0,
    )
    generate(seed, tmp_path, force=True)
    theme_path = tmp_path / "themes/roundtrip.theme.json"
    assert (
        json.loads(theme_path.read_text())["visualStyles"]["*"]["*"]["title"][0][
            "fontSize"
        ]
        == 14
    )

    # recompile from the committed tokens over the existing theme -- must NOT
    # raise a DL3-deferred conflict, and must keep fontSize:14.
    tokens_path = tmp_path / "design/tokens/roundtrip-design-tokens.yaml"
    out = compile_theme(tokens_path, out_path=None, force=True)
    recompiled = json.loads(out.read_text())
    assert recompiled["visualStyles"]["*"]["*"]["title"][0]["fontSize"] == 14
