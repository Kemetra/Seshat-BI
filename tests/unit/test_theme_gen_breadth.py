import json

import pytest

from seshat.theme_gen import ThemeSeed, build_palette, render_theme_json

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
