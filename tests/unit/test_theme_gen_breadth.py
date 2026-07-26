import json

import pytest

from seshat.color import contrast_ratio
from seshat.theme_gen import (
    AA_NON_TEXT_FLOOR,
    ThemeGenError,
    ThemeSeed,
    _validate_and_collect,
    build_palette,
    check_non_text_contrast_or_raise,
    render_theme_json,
)

pytestmark = pytest.mark.unit


def _seed(**over) -> ThemeSeed:
    base = dict(
        name="breadth-test",
        mode="light",
        accent="#118DFF",
        background="#FFFFFF",
        text_primary="#252423",
        text_secondary="#605E5C",
        text_muted="#605E5C",
        data_colors=("#118DFF", "#E66C37", "#1AAB40"),
        good="#1AAB40",
        neutral="#D9B300",
        bad="#D64550",
    )
    base.update(over)
    return ThemeSeed(**base)


def test_no_chrome_emits_no_section5_cards():
    """Regression: an existing caller's output is unchanged."""
    seed = _seed()
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    star = doc["visualStyles"]["*"]["*"]
    assert set(star) == {"title", "labels"}


def test_chrome_emits_gridline_and_border_cards():
    seed = _seed(chrome={"gridline": "#E1DFDD", "border": "#C8C6C4"})
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    star = doc["visualStyles"]["*"]["*"]
    assert star["categoryAxis"][0]["gridlineColor"] == {"solid": {"color": "#E1DFDD"}}
    assert star["border"][0]["show"] is True


def test_chrome_title_align_preserves_the_font_cards():
    """Regression: title_align/data_labels must not clobber the font cards.

    build_star_cards returns "title": [{"alignment": ...}] and
    "labels": [{"show": ...}] -- a naive dict.update at the wiring site would
    replace, not merge, wiping fontFamily/fontSize that render_theme_json
    already put there.
    """
    seed = _seed(chrome={"title_align": "left", "data_labels": True})
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    star = doc["visualStyles"]["*"]["*"]
    assert star["title"][0]["fontSize"] == 12
    assert star["title"][0]["fontFamily"] == "Segoe UI Semibold"
    assert star["title"][0]["alignment"] == "left"
    assert star["labels"][0]["fontFamily"] == "Segoe UI"
    assert star["labels"][0]["show"] is True


def test_no_page_tokens_emits_no_page_visual_type():
    """Regression: absent page tokens leave visualStyles shape unchanged."""
    seed = _seed()
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    assert set(doc["visualStyles"]) == {"*"}


def test_page_tokens_emit_page_visual_type():
    seed = _seed(page={"background": "#FFFFFF", "wallpaper": "#F3F2F1"})
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    page = doc["visualStyles"]["page"]["*"]
    assert set(page) == {"background", "outspace"}


def test_page_cards_survive_a_compile_round_trip():
    """The Task-1 carve-out must not read generated page cards as hand-tuning."""
    from seshat.theme_compile import _human_owned_visual_styles

    seed = _seed(page={"background": "#FFFFFF"}, chrome={"gridline": "#E1DFDD"})
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    assert _human_owned_visual_styles(doc["visualStyles"]) == {}


def test_invisible_gridline_is_refused():
    """A gridline nearly identical to the background must not pass."""
    seed = _seed(chrome={"gridline": "#FEFEFE"})  # on #FFFFFF background
    # Oracle: compute the ratio independently rather than trusting the module.
    assert contrast_ratio("#FEFEFE", "#FFFFFF") < AA_NON_TEXT_FLOOR
    with pytest.raises(ThemeGenError, match="gridline"):
        check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_legible_gridline_passes():
    seed = _seed(chrome={"gridline": "#767676"})
    assert contrast_ratio("#767676", "#FFFFFF") >= AA_NON_TEXT_FLOOR
    check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_no_chrome_is_vacuously_fine():
    seed = _seed()
    check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_gridlines_off_is_not_a_contrast_failure():
    """None means gridlines off -- there is nothing to be invisible."""
    seed = _seed(chrome={"gridline": None})
    check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_generate_refuses_an_invisible_border_end_to_end(tmp_path):
    """The gate must run in the validate-before-write path, not just standalone."""
    seed = _seed(chrome={"border": "#FEFEFE"})
    with pytest.raises(ThemeGenError, match="border"):
        _validate_and_collect(seed, tmp_path, False)


def test_malformed_gridline_hex_raises_theme_gen_error_not_traceback():
    """A non-hex chrome color must fail cleanly, matching the module's
    "never a traceback" contract -- not leak a raw ValueError from
    contrast_ratio's hex parsing."""
    seed = _seed(chrome={"gridline": "nope"})
    with pytest.raises(ThemeGenError, match="gridline"):
        check_non_text_contrast_or_raise(build_palette(seed), seed)
