import pytest

from seshat.theme_style_cards import (
    VALID_NUMBER_FORMATS,
    StyleCardError,
    build_page_cards,
    build_star_cards,
)

pytestmark = pytest.mark.unit

CHROME = {
    "gridline": "#E1DFDD",
    "border": "#C8C6C4",
    "title_align": "left",
    "data_labels": False,
    "number_format": "#,##0",
}


def test_build_star_cards_emits_both_axes_and_border():
    cards = build_star_cards(CHROME)
    assert set(cards) == {"categoryAxis", "valueAxis", "border", "title", "labels"}
    assert cards["categoryAxis"] == [
        {"gridlineColor": {"solid": {"color": "#E1DFDD"}}, "gridlineShow": True}
    ]
    assert cards["border"] == [{"color": {"solid": {"color": "#C8C6C4"}}, "show": True}]


def test_gridline_none_turns_gridlines_off_without_a_color():
    cards = build_star_cards({**CHROME, "gridline": None})
    assert cards["categoryAxis"] == [{"gridlineShow": False}]
    assert cards["valueAxis"] == [{"gridlineShow": False}]


def test_out_of_vocabulary_number_format_is_refused():
    with pytest.raises(StyleCardError, match="number_format"):
        build_star_cards({**CHROME, "number_format": "0.000"})


def test_every_valid_number_format_is_accepted():
    for fmt in VALID_NUMBER_FORMATS:
        build_star_cards({**CHROME, "number_format": fmt})


def test_invalid_hex_is_refused():
    with pytest.raises(StyleCardError, match="gridline"):
        build_star_cards({**CHROME, "gridline": "not-a-hex"})


def test_bad_title_alignment_is_refused():
    with pytest.raises(StyleCardError, match="title_align"):
        build_star_cards({**CHROME, "title_align": "justified"})


def test_empty_chrome_emits_no_cards():
    assert build_star_cards({}) == {}


PAGE = {
    "background": "#FFFFFF",
    "background_transparency": 0,
    "wallpaper": "#F3F2F1",
    "wallpaper_transparency": 0,
    "filter_pane_background": "#FFFFFF",
    "filter_pane_text": "#252423",
    "filter_card_applied": "#E1DFDD",
    "filter_card_available": "#FFFFFF",
}


def test_page_cards_use_outspace_for_wallpaper():
    """outspace IS the wallpaper card per the published schema."""
    cards = build_page_cards(PAGE)
    assert cards["background"] == [
        {"color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0.0}
    ]
    assert cards["outspace"] == [
        {"color": {"solid": {"color": "#F3F2F1"}}, "transparency": 0.0}
    ]


def test_filter_card_is_an_array_keyed_by_id():
    """filterCard carries a $id discriminator for its two states."""
    cards = build_page_cards(PAGE)
    ids = [c["$id"] for c in cards["filterCard"]]
    assert ids == ["Applied", "Available"]


def test_filter_pane_card_emitted():
    cards = build_page_cards(PAGE)
    assert cards["outspacePane"][0]["backgroundColor"] == {
        "solid": {"color": "#FFFFFF"}
    }


def test_page_transparency_out_of_range_is_refused():
    with pytest.raises(StyleCardError, match="background_transparency"):
        build_page_cards({**PAGE, "background_transparency": 150})


def test_empty_page_emits_no_cards():
    assert build_page_cards({}) == {}
