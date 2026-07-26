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
