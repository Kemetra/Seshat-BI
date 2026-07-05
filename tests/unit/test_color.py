"""Unit tests for the shared WCAG color helper (retail.color)."""

from __future__ import annotations

import pytest

from retail.color import contrast_ratio, is_valid_hex, relative_luminance

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
