"""Unit tests for the Blueprint Preview's three-way input state split (task 5).

`_load_yaml_mapping` (`src/seshat/blueprint_preview.py`) must never conflate
ABSENT (a not-yet-authored artifact -- non-fatal, returns ``{}``) with
UNREADABLE / MALFORMED YAML / WRONG-SHAPE (a corrupt or misshapen artifact --
must raise ``PreviewInputError`` naming the file, never silently render as an
empty-but-valid-looking preview).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.blueprint_preview import (
    PREVIEW_DISCLAIMER,
    PreviewInputError,
    _load_yaml_mapping,
    render_blueprint_preview,
)

pytestmark = pytest.mark.unit


def test_absent_input_is_not_an_error(tmp_path: Path) -> None:
    """A not-yet-authored page is a real use case -- stays non-fatal."""
    assert _load_yaml_mapping(tmp_path / "missing.yaml") == {}


def test_empty_input_is_not_an_error(tmp_path: Path) -> None:
    """A file that exists but parses to ``None`` (fully empty/whitespace-only)
    is the same non-fatal case as absent, not a malformed-input error."""
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    assert _load_yaml_mapping(empty) == {}


def test_unparseable_input_is_reported(tmp_path: Path) -> None:
    """A corrupt file must NOT silently become an empty preview."""
    bad = tmp_path / "bad.yaml"
    bad.write_text("pages: [unclosed\n", encoding="utf-8")
    with pytest.raises(PreviewInputError, match="bad.yaml"):
        _load_yaml_mapping(bad)


def test_non_mapping_input_is_reported(tmp_path: Path) -> None:
    """A YAML list parses fine but is the wrong shape -- name it."""
    listy = tmp_path / "listy.yaml"
    listy.write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(PreviewInputError, match="mapping"):
        _load_yaml_mapping(listy)


def test_undecodable_bytes_are_reported(tmp_path: Path) -> None:
    """An unreadable (undecodable-as-utf-8-sig) file is the UNREADABLE state,
    distinct from malformed-YAML-but-decodable -- both must raise, but this
    exercises the ``UnicodeDecodeError`` branch specifically, triggered
    portably (no chmod/permissions needed) via a byte sequence that is
    invalid UTF-8."""
    undecodable = tmp_path / "undecodable.yaml"
    raw = b"pages:\n  - \xff\xfe not valid utf-8\n"
    with pytest.raises(UnicodeDecodeError):
        raw.decode("utf-8-sig")  # confirm the fixture actually triggers this branch
    undecodable.write_bytes(raw)
    with pytest.raises(PreviewInputError, match="undecodable.yaml"):
        _load_yaml_mapping(undecodable)


def _write_min_inputs(tmp_path: Path) -> Path:
    """The four minimal preview inputs, as YAML the renderer accepts."""
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


def _write_tokens_with_chrome(tmp_path: Path, chrome_yaml: str) -> Path:
    """Same tokens shape as `_write_min_inputs`, plus a `chrome:` block."""
    tmp_path = _write_min_inputs(tmp_path)
    tokens = tmp_path / "tokens.yaml"
    tokens.write_text(
        tokens.read_text(encoding="utf-8") + chrome_yaml, encoding="utf-8"
    )
    return tmp_path


def _write_one_visual_spec(tmp_path: Path) -> Path:
    """A minimal visual-spec YAML file: enough to make `_visual_group` emit a
    `<rect class="visual-box">` so a border/stroke assertion has something
    real to check, rather than passing vacuously on an empty visuals list."""
    p = tmp_path / "visual.yaml"
    p.write_text(
        "visual_id: v1\n"
        "visual_type: card\n"
        "position:\n  section: kpi_strip\n  x: 0\n  y: 0\n  width: 1\n  height: 1\n",
        encoding="utf-8",
    )
    return p


def test_disclaimer_is_stamped_on_every_render(tmp_path: Path) -> None:
    """Mirrors tmdl-doc-comment-lint: the limit is stated even on success."""
    d = _write_min_inputs(tmp_path)
    svg = render_blueprint_preview(
        blueprint_path=d / "bp.yaml",
        visual_spec_paths=[],
        composition_path=d / "comp.yaml",
        grid_path=d / "grid.yaml",
    )
    assert PREVIEW_DISCLAIMER in svg


def test_tokens_color_the_render(tmp_path: Path) -> None:
    d = _write_min_inputs(tmp_path)
    styled = render_blueprint_preview(
        blueprint_path=d / "bp.yaml",
        visual_spec_paths=[],
        composition_path=d / "comp.yaml",
        grid_path=d / "grid.yaml",
        tokens_path=d / "tokens.yaml",
    )
    assert "#101820" in styled


def test_omitting_tokens_leaves_output_unchanged(tmp_path: Path) -> None:
    """Regression: the no-tokens path must not shift for existing callers."""
    d = _write_min_inputs(tmp_path)
    kwargs = dict(
        blueprint_path=d / "bp.yaml",
        visual_spec_paths=[],
        composition_path=d / "comp.yaml",
        grid_path=d / "grid.yaml",
    )
    assert render_blueprint_preview(**kwargs) == render_blueprint_preview(**kwargs)
    unstyled = render_blueprint_preview(**kwargs)
    assert "#101820" not in unstyled
    # Sits ON the risk: a monochrome-fallback dict passed through unconditionally
    # would satisfy the check above while silently baking in default colors no
    # caller asked for. Assert none of the internal fallback hexes leak either.
    for default_hex in ("#FFFFFF", "#252423", "#605E5C", "#C8C6C4"):
        assert default_hex not in unstyled
    # Sits ON the risk more directly still: the failure mode caught in
    # self-review was not "a default hex leaked" but "a new SVG ATTRIBUTE
    # appeared" (e.g. stroke="#C8C6C4") even though its value happened to
    # match a fallback that could change independently. No fill/stroke
    # attribute at all may appear on the no-tokens path.
    assert "fill=" not in unstyled
    assert "stroke=" not in unstyled


def test_tokens_color_the_canvas_ground_specifically(tmp_path: Path) -> None:
    """The background token must reach the page canvas rect's fill, not just
    appear somewhere incidental in the SVG text."""
    d = _write_min_inputs(tmp_path)
    styled = render_blueprint_preview(
        blueprint_path=d / "bp.yaml",
        visual_spec_paths=[],
        composition_path=d / "comp.yaml",
        grid_path=d / "grid.yaml",
        tokens_path=d / "tokens.yaml",
    )
    assert 'class="canvas" fill="#101820"' in styled


def test_preview_never_fabricates_a_number(tmp_path: Path) -> None:
    """PLACEHOLDER only -- the structural no-data guarantee holds."""
    d = _write_min_inputs(tmp_path)
    svg = render_blueprint_preview(
        blueprint_path=d / "bp.yaml",
        visual_spec_paths=[],
        composition_path=d / "comp.yaml",
        grid_path=d / "grid.yaml",
        tokens_path=d / "tokens.yaml",
    )
    assert "PLACEHOLDER" in svg


# --- Finding 4 (P2): visual borders/gridlines source from chrome, not secondary --


def test_chrome_border_colors_the_visual_box_stroke_not_secondary(
    tmp_path: Path,
) -> None:
    """chrome.border must reach the visual-box stroke; colors.secondary must
    NOT appear, so the SVG cannot disagree with the compiled theme's border."""
    d = _write_tokens_with_chrome(tmp_path, "chrome:\n  border: '#AA0000'\n")
    visual = _write_one_visual_spec(d)
    styled = render_blueprint_preview(
        blueprint_path=d / "bp.yaml",
        visual_spec_paths=[visual],
        composition_path=d / "comp.yaml",
        grid_path=d / "grid.yaml",
        tokens_path=d / "tokens.yaml",
    )
    assert 'class="visual-box" stroke="#AA0000"' in styled
    assert "#E66C37" not in styled  # colors.secondary must not leak through


def test_chrome_border_null_draws_no_stroke_at_all(tmp_path: Path) -> None:
    """chrome.border: null means borders OFF -- an explicit null must not
    silently fall through to colors.secondary; assert the ABSENCE of a stroke,
    not a substitute color."""
    d = _write_tokens_with_chrome(tmp_path, "chrome:\n  border: null\n")
    visual = _write_one_visual_spec(d)
    styled = render_blueprint_preview(
        blueprint_path=d / "bp.yaml",
        visual_spec_paths=[visual],
        composition_path=d / "comp.yaml",
        grid_path=d / "grid.yaml",
        tokens_path=d / "tokens.yaml",
    )
    assert "stroke=" not in styled
    assert "#E66C37" not in styled  # colors.secondary must not leak through either


def test_no_chrome_falls_back_to_secondary_color_unchanged(tmp_path: Path) -> None:
    """Regression: with no chrome: group at all, the border falls back to
    colors.secondary exactly as it did before this fix."""
    d = _write_min_inputs(tmp_path)
    visual = _write_one_visual_spec(d)
    styled = render_blueprint_preview(
        blueprint_path=d / "bp.yaml",
        visual_spec_paths=[visual],
        composition_path=d / "comp.yaml",
        grid_path=d / "grid.yaml",
        tokens_path=d / "tokens.yaml",
    )
    assert 'class="visual-box" stroke="#E66C37"' in styled


def test_chrome_gridline_colors_the_stroke_when_border_absent(tmp_path: Path) -> None:
    """The middle fallback tier: chrome.border ABSENT but chrome.gridline
    present must still reach the stroke -- gridline is the second-choice
    source, checked before falling back to colors.secondary."""
    d = _write_tokens_with_chrome(tmp_path, "chrome:\n  gridline: '#00AA00'\n")
    visual = _write_one_visual_spec(d)
    styled = render_blueprint_preview(
        blueprint_path=d / "bp.yaml",
        visual_spec_paths=[visual],
        composition_path=d / "comp.yaml",
        grid_path=d / "grid.yaml",
        tokens_path=d / "tokens.yaml",
    )
    assert 'class="visual-box" stroke="#00AA00"' in styled
    assert "#E66C37" not in styled  # colors.secondary must not leak through
