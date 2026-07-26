import pytest

from seshat.theme_style_cards import (
    VALID_NUMBER_FORMATS,
    StyleCardError,
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
