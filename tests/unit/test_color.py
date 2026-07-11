"""Unit tests for the shared WCAG color helper (seshat.color)."""

from __future__ import annotations

import pytest

from seshat.color import (
    composite_over,
    contrast_ratio,
    delta_e76,
    format_pt,
    hex_to_lab,
    is_valid_hex,
    relative_luminance,
)

pytestmark = pytest.mark.unit


def test_black_on_white_is_21_to_1() -> None:
    assert round(contrast_ratio("#000000", "#FFFFFF"), 1) == 21.0


def test_ratio_is_symmetric() -> None:
    assert round(contrast_ratio("#1A1D21", "#FFFFFF"), 4) == round(
        contrast_ratio("#FFFFFF", "#1A1D21"), 4
    )


def test_relative_luminance_bounds() -> None:
    assert relative_luminance("#000000") == 0.0
    assert round(relative_luminance("#FFFFFF"), 4) == 1.0


def test_is_valid_hex() -> None:
    assert is_valid_hex("#2FB6C4")
    assert not is_valid_hex("2FB6C4")
    assert not is_valid_hex("#2FB")
    assert not is_valid_hex("#GGGGGG")


def test_bad_hex_raises() -> None:
    with pytest.raises(ValueError):
        contrast_ratio("nothex", "#FFFFFF")


def test_hex_to_lab_black_is_origin() -> None:
    L, a, b = hex_to_lab("#000000")
    assert (round(L, 1), round(a, 1), round(b, 1)) == (0.0, 0.0, 0.0)


def test_hex_to_lab_white_is_l100() -> None:
    L, _a, _b = hex_to_lab("#FFFFFF")
    assert round(L, 1) == 100.0


def test_hex_to_lab_bad_hex_raises() -> None:
    with pytest.raises(ValueError):
        hex_to_lab("nothex")


def test_delta_e76_black_white_is_about_100() -> None:
    assert round(delta_e76("#000000", "#FFFFFF"), 1) == 100.0


def test_delta_e76_identical_colors_is_zero() -> None:
    assert delta_e76("#2E7D5B", "#2E7D5B") == 0.0


def test_delta_e76_bad_hex_raises() -> None:
    with pytest.raises(ValueError):
        delta_e76("nothex", "#FFFFFF")


def test_composite_over_50pct_black_over_white_is_gray() -> None:
    assert composite_over("#000000", "#FFFFFF", 50.0) == "#808080"


def test_composite_over_0pct_returns_fg() -> None:
    assert composite_over("#000000", "#FFFFFF", 0.0) == "#000000"


def test_composite_over_100pct_returns_bg() -> None:
    assert composite_over("#000000", "#FFFFFF", 100.0) == "#FFFFFF"


def test_composite_over_below_zero_raises() -> None:
    with pytest.raises(ValueError):
        composite_over("#000000", "#FFFFFF", -1.0)


def test_composite_over_above_100_raises() -> None:
    with pytest.raises(ValueError):
        composite_over("#000000", "#FFFFFF", 101.0)


def test_composite_over_bad_hex_raises() -> None:
    with pytest.raises(ValueError):
        composite_over("nothex", "#FFFFFF", 50.0)


def test_format_pt_collapses_integral_float_to_int() -> None:
    assert format_pt(12.0) == 12
    assert isinstance(format_pt(12.0), int)
    assert format_pt(9.0) == 9


def test_format_pt_preserves_fractional_value() -> None:
    assert format_pt(11.5) == 11.5
    assert isinstance(format_pt(11.5), float)
