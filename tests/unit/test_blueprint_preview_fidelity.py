"""Findings 3, 5 and 6 from issue #521 -- the preview must honor the documented
degrade/raise split for ``tokens_path``, take its canvas fill from the emitted
``page.background``, and apply a text fill at every text site rather than only
the page title.

Scope boundary (owner ruling D3): preview fidelity stays APPROXIMATE. These
tests pin that the preview reads the same TOKENS the theme compiles, not that it
reimplements Power BI's compositor -- wallpaper and transparency blending are
deliberately out of scope and are not asserted here.
"""

import re
from pathlib import Path

import pytest

from seshat.blueprint_preview import (
    PreviewInputError,
    render_blueprint_preview,
)

pytestmark = pytest.mark.unit


def _write_min_inputs(tmp_path: Path) -> Path:
    """The four minimal preview inputs, mirroring test_blueprint_preview_styled."""
    (tmp_path / "bp.yaml").write_text(
        "pages:\n  - name: Overview\n    order: 1\n", encoding="utf-8"
    )
    (tmp_path / "comp.yaml").write_text("pages: []\n", encoding="utf-8")
    (tmp_path / "grid.yaml").write_text(
        "width: 1280\nheight: 720\ncolumns: 12\n", encoding="utf-8"
    )
    (tmp_path / "tokens.yaml").write_text(
        "meta:\n  name: t\ncolors:\n"
        "  primary: '#118DFF'\n  secondary: '#E66C37'\n  background: '#101820'\n"
        "  text:\n    primary: '#F2F2F2'\n    secondary: '#C8C8C8'\n"
        "    muted: '#A0A0A0'\n"
        "  sentiment:\n    success: '#1AAB40'\n    warning: '#D9B300'\n"
        "    danger: '#D64550'\n"
        "  data_colors: ['#118DFF', '#E66C37']\n",
        encoding="utf-8",
    )
    return tmp_path


def _render(d: Path, tokens: Path | str | None) -> str:
    return render_blueprint_preview(
        blueprint_path=d / "bp.yaml",
        visual_spec_paths=[],
        composition_path=d / "comp.yaml",
        grid_path=d / "grid.yaml",
        tokens_path=tokens,
    )


# --------------------------------------------------------------------------
# Finding 3 -- the documented degrade/raise split
# --------------------------------------------------------------------------


def test_missing_tokens_path_degrades_to_monochrome(tmp_path: Path) -> None:
    """A NAMED-but-nonexistent tokens path must degrade, not raise.

    The committed contract (`blueprint-preview.md`) says ``tokens_path``
    "follows the same degrade/raise split" as the four required inputs, whose
    MISSING state degrades. Before this fix ``_load_yaml_mapping`` correctly
    returned ``{}`` and then ``_style_from_tokens`` raised anyway -- reporting
    that a file which does not exist "has no 'colors' mapping".
    """
    d = _write_min_inputs(tmp_path)
    svg = _render(d, d / "not-authored-yet.yaml")
    assert "<svg" in svg


def test_missing_tokens_path_matches_omitting_it(tmp_path: Path) -> None:
    """Degrading means monochrome -- the same render as passing nothing.

    A stronger oracle than "it did not raise": it pins that the degrade path
    produces the no-tokens output rather than some third styled-but-default
    state.
    """
    d = _write_min_inputs(tmp_path)
    assert _render(d, d / "nope.yaml") == _render(d, None)


def test_empty_tokens_file_degrades(tmp_path: Path) -> None:
    """An existing-but-empty file parses to ``{}`` -- the ABSENT-shaped state."""
    d = _write_min_inputs(tmp_path)
    (d / "empty.yaml").write_text("", encoding="utf-8")
    assert _render(d, d / "empty.yaml") == _render(d, None)


def test_tokens_file_without_colors_still_raises(tmp_path: Path) -> None:
    """PRESENT-but-wrong-shape must still raise -- the other half of the split.

    Without this the fix could over-correct into a blanket degrade, turning a
    real authoring error into a silently monochrome preview.
    """
    d = _write_min_inputs(tmp_path)
    (d / "no-colors.yaml").write_text("meta:\n  name: t\n", encoding="utf-8")
    with pytest.raises(PreviewInputError, match="no-colors.yaml"):
        _render(d, d / "no-colors.yaml")


def test_tokens_file_that_is_a_list_still_raises(tmp_path: Path) -> None:
    d = _write_min_inputs(tmp_path)
    (d / "listy.yaml").write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(PreviewInputError, match="listy.yaml"):
        _render(d, d / "listy.yaml")


# --------------------------------------------------------------------------
# Finding 6 -- the canvas takes the EMITTED page background
# --------------------------------------------------------------------------


def _canvas_fill(svg: str) -> str | None:
    match = re.search(r'class="canvas"[^>]*?fill="([^"]+)"', svg)
    return match.group(1) if match else None


def test_canvas_uses_page_background_over_palette_background(tmp_path: Path) -> None:
    """``page.background`` OVERRIDES the palette background as the page's real
    fill (``theme_gen._non_text_ground`` documents exactly that), so a preview
    reading ``colors.background`` shows a different page color than Desktop.

    The fixture's two values differ deliberately: an assertion against a tokens
    file whose ``page.background`` equals ``colors.background`` would pass with
    or without the fix.
    """
    d = _write_min_inputs(tmp_path)
    tokens = d / "tokens.yaml"
    tokens.write_text(
        tokens.read_text(encoding="utf-8") + "page:\n  background: '#2B0A3D'\n",
        encoding="utf-8",
    )
    assert _canvas_fill(_render(d, tokens)) == "#2B0A3D"


def test_canvas_falls_back_to_palette_background(tmp_path: Path) -> None:
    """Regression: no ``page`` group means the palette background still wins."""
    d = _write_min_inputs(tmp_path)
    assert _canvas_fill(_render(d, d / "tokens.yaml")) == "#101820"


def test_explicit_null_page_background_falls_back(tmp_path: Path) -> None:
    """``page.background: null`` is a declaration, not a color; the canvas must
    fall back rather than emit an empty fill attribute."""
    d = _write_min_inputs(tmp_path)
    tokens = d / "tokens.yaml"
    tokens.write_text(
        tokens.read_text(encoding="utf-8") + "page:\n  background: null\n",
        encoding="utf-8",
    )
    assert _canvas_fill(_render(d, tokens)) == "#101820"


# --------------------------------------------------------------------------
# Finding 5 -- a text fill at every text site
# --------------------------------------------------------------------------


def _texts_without_fill(svg: str) -> list[str]:
    return [t for t in re.findall(r"<text\b[^>]*>", svg) if "fill=" not in t]


def test_every_text_element_is_filled_when_tokens_are_given(tmp_path: Path) -> None:
    """On a dark canvas an unfilled <text> falls back to SVG-default black.

    Only 3 of 14 ``_text`` call sites passed ``fill``; four block helpers never
    received the style dict at all. Asserting over EVERY emitted <text> rather
    than a named few keeps a newly-added site from silently reintroducing this.
    """
    d = _write_min_inputs(tmp_path)
    (d / "comp.yaml").write_text(
        "pages: []\nnavigation:\n  - from_page: Overview\n    to: Detail\n"
        "    label: drill\n",
        encoding="utf-8",
    )
    (d / "bp.yaml").write_text(
        "pages:\n  - name: Overview\n    order: 1\n"
        "narrative:\n  headline: H\n  so_what: S\n"
        "slicers:\n  - field: region\n    type: dropdown\n"
        "theme_json:\n  theme_ref: t.json\n"
        "grid:\n  grid_ref: g.yaml\n"
        "mobile_notes:\n  grid_ref: m.yaml\n",
        encoding="utf-8",
    )
    unfilled = _texts_without_fill(_render(d, d / "tokens.yaml"))
    assert not unfilled, f"{len(unfilled)} <text> element(s) carry no fill: {unfilled}"


def test_omitting_tokens_still_emits_no_fill_attributes(tmp_path: Path) -> None:
    """The no-tokens path must stay attribute-free.

    This is a real constraint, not a bug to fix: any implementation that
    substitutes the monochrome defaults when ``tokens_path`` is ``None`` would
    start emitting colors nobody asked for.
    """
    d = _write_min_inputs(tmp_path)
    unstyled = _render(d, None)
    assert "fill=" not in unstyled
    assert "stroke=" not in unstyled
