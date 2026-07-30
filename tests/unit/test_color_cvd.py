"""Pin the three CVD simulation transforms in ``seshat.color``.

These tests deliberately do NOT assert against a transcribed table of "published
expected values". A copied reference table is unverifiable here and a single
mis-typed digit would silently bless a wrong matrix. Instead they pin properties
that follow from what the transform IS -- a projection onto a dichromat plane --
plus the physiology the projection is supposed to model:

* determinism (same input -> byte-identical output);
* idempotence: projecting an already-projected colour changes nothing, which only
  holds if the forward and inverse matrix pair are actually consistent;
* the achromatic axis is fixed: grey has no red/green or blue/yellow content to
  lose, so it must survive every simulation unchanged;
* red/green collapses hardest under deuteranope and least under tritanope, which
  is the defining behavioural difference between the three deficiencies.

Golden values are included as regression anchors and are labelled as such -- they
record what this implementation produces, not an external authority.
"""

from __future__ import annotations

import pytest

from seshat.color import (
    CVD_DEFICIENCIES,
    delta_e76,
    is_valid_hex,
    simulate_cvd,
    simulate_deuteranope,
    simulate_protanope,
    simulate_tritanope,
)

_RED = "#D62728"
_GREEN = "#2CA02C"
_GREYS = ("#000000", "#404040", "#808080", "#BFBFBF", "#FFFFFF")


@pytest.mark.unit
@pytest.mark.parametrize("deficiency", CVD_DEFICIENCIES)
@pytest.mark.parametrize("color", (_RED, _GREEN, "#1F77B4", "#FF7F0E", "#7F7F7F"))
def test_transform_is_deterministic_and_returns_valid_hex(
    deficiency: str, color: str
) -> None:
    first = simulate_cvd(color, deficiency)
    assert first == simulate_cvd(color, deficiency)
    assert is_valid_hex(first)


@pytest.mark.unit
@pytest.mark.parametrize("deficiency", CVD_DEFICIENCIES)
@pytest.mark.parametrize("color", (_RED, _GREEN, "#1F77B4", "#FF7F0E"))
def test_transform_is_idempotent(deficiency: str, color: str) -> None:
    """A projection applied twice equals applying it once.

    This is the strongest available check that the RGB->LMS and LMS->RGB matrices
    are a consistent pair: an inconsistent inverse would drift on the second pass.
    """
    once = simulate_cvd(color, deficiency)
    assert simulate_cvd(once, deficiency) == once


@pytest.mark.unit
@pytest.mark.parametrize("deficiency", CVD_DEFICIENCIES)
@pytest.mark.parametrize("grey", _GREYS)
def test_achromatic_colors_are_unchanged(deficiency: str, grey: str) -> None:
    """Grey carries no chromatic signal to lose, so it must survive intact."""
    assert simulate_cvd(grey, deficiency) == grey


@pytest.mark.unit
def test_red_green_collapses_most_under_deuteranope() -> None:
    """The defining behavioural difference between the three deficiencies.

    Deuteranopes confuse red and green most; protanopes also confuse them but less
    completely; tritanopia affects the blue/yellow axis and leaves red/green
    discriminable. A matrix mix-up between the three would break this ordering.
    """
    declared = delta_e76(_RED, _GREEN)
    protan = delta_e76(simulate_protanope(_RED), simulate_protanope(_GREEN))
    deutan = delta_e76(simulate_deuteranope(_RED), simulate_deuteranope(_GREEN))
    tritan = delta_e76(simulate_tritanope(_RED), simulate_tritanope(_GREEN))

    assert deutan < protan < declared
    assert tritan > declared


@pytest.mark.unit
def test_named_wrappers_match_the_generic_entry_point() -> None:
    for name, fn in (
        ("protanope", simulate_protanope),
        ("deuteranope", simulate_deuteranope),
        ("tritanope", simulate_tritanope),
    ):
        assert fn(_RED) == simulate_cvd(_RED, name)


@pytest.mark.unit
def test_rejects_a_malformed_color_token() -> None:
    with pytest.raises(ValueError, match="not a #RRGGBB hex color"):
        simulate_cvd("not-a-colour", "protanope")


@pytest.mark.unit
def test_rejects_an_unknown_deficiency() -> None:
    with pytest.raises(ValueError, match="unknown deficiency"):
        simulate_cvd(_RED, "quadranope")


@pytest.mark.unit
def test_golden_regression_values() -> None:
    """Regression anchors for THIS implementation -- not an external reference.

    If a future change to the matrices or the gamma convention moves these, that
    is a deliberate decision to re-record, not automatically a bug.
    """
    assert simulate_protanope(_RED) == "#56562B"
    assert simulate_deuteranope(_RED) == "#7F7F13"
    assert simulate_tritanope(_RED) == "#9E9E00"
    assert simulate_protanope(_GREEN) == "#98982B"
    assert simulate_deuteranope(_GREEN) == "#8A8A32"
    assert simulate_tritanope(_GREEN) == "#7979FF"
