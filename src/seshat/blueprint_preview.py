"""Deterministic Blueprint Preview (spec 123, US4/FR-015/FR-016/SEC-001/SEC-002).

Given a COMMITTED page blueprint, its visual specs, a report composition, and a
grid -- all already-authored design artifacts
(`templates/dashboard-page-blueprint.yaml`, `templates/visual-spec.yaml`,
`templates/report-composition.yaml`, `design/grids/16x9-grid.yaml`) -- render a
deterministic, data-free SVG that
represents structure and design INTENT only: pages + order, sections, visual
positions/sizes/types, titles + business questions, referenced metric-contract
NAMES, filters/slicers, narrative regions, navigation, freshness/DQ areas, and
theme/typography/grid/accessibility/mobile/RTL intent (FR-015).

Hard boundaries (FR-016 / SEC-001 / SEC-002):
  - NO live database read, NO network call, NO PBIR/DAX/semantic-model write --
    this module opens only the four YAML paths it is given (read-only) and
    returns a string; it performs NO file write of its own.
  - Every data VALUE (a KPI figure, a trend point, any business result) is the
    literal labeled token ``PLACEHOLDER`` -- never a fabricated number. A
    caller has no way to feed this function "realistic values": there is no
    data-source parameter, so it is structurally incapable of inventing one.
  - Determinism (FR-015/SC-006): identical inputs -> byte-identical output.
    Achieved by (a) never reading wall-clock time / random / a per-process
    salted hash -- no ``hash()``/``uuid``/``time`` anywhere in this module --
    and (b) sorting every iterable before emitting it: pages by the
    composition's declared ``order``; visuals by SECTION (the fixed seven-key
    reading-order vocabulary, not alphabetical) then ``position.y`` then
    ``position.x``.

YAML loading follows the repo-standard idiom (``yaml.safe_load`` + lazy import
+ ``utf-8-sig``, same as ``gap_detector.py`` / ``report_intent.py``) -- pyyaml
is an existing runtime dependency (`pyproject.toml`), not a new one; the
rendering itself uses stdlib only (``html.escape``, ``pathlib``).
"""

from __future__ import annotations

from html import escape as _esc
from pathlib import Path
from typing import Any

_PLACEHOLDER = "PLACEHOLDER"

# Stated on EVERY render including a clean one. An SVG approximation is not
# Power BI's renderer: a preview that looks right proves nothing about what
# Desktop will draw. Mirrors the tmdl-doc-comment-lint posture, where the scope
# limit is printed on a pass -- a pass is exactly where over-reading happens.
PREVIEW_DISCLAIMER = (
    "APPROXIMATION -- an SVG preview of committed design intent. "
    "It does NOT prove Power BI Desktop will render this way, and grants no approval."
)

# Per-key fallbacks used ONLY when tokens ARE present but a specific key is
# missing from them (e.g. `colors.text.muted` absent). Deliberately NOT used on
# the no-tokens path -- `_style_from_tokens(None)` returns `{}`, not this dict,
# so existing (pre-styling) output stays byte-identical: see its docstring.
_DEFAULT_STYLE = {
    "ground": "#FFFFFF",
    "ink": "#252423",
    "ink_muted": "#605E5C",
    "line": "#C8C6C4",
}


class PreviewInputError(Exception):
    """A preview input that exists but cannot be used, named for the caller."""


# The fixed seven-section reading-order vocabulary (dashboard-page-blueprint.yaml).
# Visuals are ordered by this rank, THEN position.y, THEN position.x -- never
# alphabetically (alphabetical would scramble the intended reading order).
_SECTION_ORDER = (
    "header",
    "kpi_strip",
    "main_insight",
    "diagnostic",
    "exception_detail",
    "filter_rail",
    "footer_status",
)


def _load_yaml_mapping(path: Path | str) -> dict[str, Any]:
    """A preview input YAML as a mapping.

    Three distinct states, never conflated: ABSENT returns ``{}`` (a
    not-yet-authored artifact is a legitimate preview subject); UNPARSEABLE and
    WRONG-SHAPE raise ``PreviewInputError`` naming the file. Silently returning
    ``{}`` for a corrupt file would render an empty SVG indistinguishable from a
    sparse one -- a degrade-without-reporting fail-open.
    """
    import yaml

    p = Path(path)
    if not p.exists():
        return {}
    try:
        text = p.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise PreviewInputError(
            f"preview input {p} is unreadable ({exc}) -- check permissions/encoding"
        ) from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PreviewInputError(
            f"preview input {p} is not valid YAML ({exc}) -- fix the syntax"
        ) from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise PreviewInputError(
            f"preview input {p} must be a YAML mapping, got {type(data).__name__}"
        )
    return data


def _line_color_from_tokens(tokens: dict[str, Any]) -> str | None:
    """The visual-box border/gridline color: ``chrome.border``, else
    ``chrome.gridline``, else ``colors.secondary`` (finding 4).

    The compiled theme draws visual borders/gridlines from ``chrome.border``/
    ``chrome.gridline`` (theme-spec section 5), not from ``colors.secondary``
    -- so this preview must source the SAME field, or a chrome override (or an
    explicit ``chrome.border: null`` turning borders OFF) would make the SVG
    disagree with the theme Power BI actually renders. Key PRESENCE decides
    fallback, not truthiness: an explicit ``null`` for ``border``/``gridline``
    is a real "borders off" declaration and must return ``None`` (no stroke
    drawn) rather than silently falling through to the next source.
    """
    chrome = tokens.get("chrome")
    chrome = chrome if isinstance(chrome, dict) else {}
    if "border" in chrome:
        return chrome["border"]
    if "gridline" in chrome:
        return chrome["gridline"]
    colors = tokens.get("colors")
    colors = colors if isinstance(colors, dict) else {}
    return colors.get("secondary", _DEFAULT_STYLE["line"])


def _ground_from_tokens(tokens: dict[str, Any], colors: dict[str, Any]) -> str | None:
    """The page canvas fill: ``page.background``, else ``colors.background``.

    A declared ``page.background`` (theme-spec sections 6/7) OVERRIDES the
    palette background as the page's real fill -- ``theme_gen._non_text_ground``
    documents exactly that, and it is what lands in
    ``visualStyles["page"]["*"]["background"]``. Reading only ``colors`` made
    the preview show a different page color than Desktop (#521 finding 6).

    Still sourced from TOKENS, never from an emitted theme JSON, so the spec's
    "render from tokens" rule holds. Transparency and wallpaper are NOT
    composited in (owner ruling D3): preview fidelity stays approximate rather
    than reimplementing Power BI's compositor in SVG.

    Falls back on ``None``, NOT on key absence -- byte-for-byte the same
    None-based test as ``theme_gen._non_text_ground``, which is the helper this
    must agree with, since it resolves the ground the compiled theme measures.

    This is deliberately the OPPOSITE of ``_line_color_from_tokens``, which
    decides on key PRESENCE (``"border" in chrome``) and returns ``None`` for an
    explicit ``chrome.border: null``. The asymmetry is real, not an oversight:
    borders-off is a renderable intent (draw no stroke), while canvas-fill-off is
    not -- a page always paints something. Note the compiled theme does not merely
    ignore ``page.background: null``, it FAILS CLOSED on it
    (``build_page_cards`` raises ``StyleCardError``: "background must be a
    #RRGGBB hex color, got None"), so a preview that renders here is showing a
    tokens file ``theme-compile`` would refuse. That is within this module's
    stated bounds -- the preview cannot produce a wrong Power BI artifact and
    ``PREVIEW_DISCLAIMER`` grants no approval -- but it is not agreement.
    """
    page = tokens.get("page")
    page = page if isinstance(page, dict) else {}
    declared = page.get("background")
    if declared is not None:
        return declared
    return colors.get("background", _DEFAULT_STYLE["ground"])


def _style_from_tokens(tokens_path: Path | str | None) -> dict[str, str | None]:
    """Preview colors from a committed tokens YAML, or nothing at all.

    Reads the SAME tokens file ``theme_compile`` consumes, so the preview and
    the emitted theme.json cannot disagree. Renders from TOKENS, never from a
    theme JSON -- the theme schema's ``"*"`` wildcard section accepts any key
    (patternProperties ``^.+$``), so a valid-but-wrong theme key is silently
    ignored by Desktop rather than rejected; reading tokens instead makes it
    structurally impossible for the preview to show styling Desktop will not
    apply.

    Returns ``{}`` when ``tokens_path`` is ``None`` -- NOT the monochrome
    defaults -- so every emission site that consults this dict via ``.get()``
    naturally emits no style attribute at all, keeping the no-tokens render
    byte-identical to before this parameter existed (only the disclaimer text
    is new). ``_DEFAULT_STYLE`` is the per-key fallback used only once tokens
    ARE present but a specific key is missing from them. ``"line"`` may be
    ``None`` (chrome.border/gridline explicitly off) -- ``_style_attr`` already
    treats a falsy value as "no attribute", so that flows through unchanged.
    """
    if tokens_path is None:
        return {}
    tokens = _load_yaml_mapping(tokens_path)
    if not tokens:
        # ABSENT (or empty) -- the documented nonfatal degrade state, same as
        # omitting tokens_path: the render is monochrome, not an error. Before
        # #521 finding 3 the loader returned {} here and the `colors` check
        # below raised anyway, reporting that a file which does not exist "has
        # no 'colors' mapping" -- contradicting the committed degrade/raise
        # split and naming a nonexistent file as malformed.
        return {}
    colors = tokens.get("colors")
    if not isinstance(colors, dict):
        raise PreviewInputError(
            f"tokens {tokens_path} has no 'colors' mapping -- cannot style the preview"
        )
    text = colors.get("text") if isinstance(colors.get("text"), dict) else {}
    return {
        "ground": _ground_from_tokens(tokens, colors),
        "ink": text.get("primary", _DEFAULT_STYLE["ink"]),
        "ink_muted": text.get("muted", _DEFAULT_STYLE["ink_muted"]),
        "line": _line_color_from_tokens(tokens),
    }


def _style_attr(name: str, value: object) -> str:
    """A single SVG attribute (` name="value"`), or empty when ``value`` is
    unset -- keeps every styled element's no-tokens form byte-identical to its
    pre-styling form instead of emitting a default-colored attribute nobody
    asked for."""
    if not value:
        return ""
    return f' {name}="{_esc(str(value))}"'


def _section_rank(section: object) -> int:
    try:
        return _SECTION_ORDER.index(str(section))
    except ValueError:
        return len(_SECTION_ORDER)  # unknown section sorts last, deterministically


def _num(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _sorted_visuals(visual_specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(v: dict[str, Any]) -> tuple[int, int, int, str]:
        position = v.get("position") if isinstance(v.get("position"), dict) else {}
        return (
            _section_rank(position.get("section")),
            _num(position.get("y")),
            _num(position.get("x")),
            str(v.get("visual_id", "")),
        )

    return sorted(visual_specs, key=key)


def _sorted_pages(composition: dict[str, Any]) -> list[dict[str, Any]]:
    pages = composition.get("pages")
    if not isinstance(pages, list):
        return []
    typed = [p for p in pages if isinstance(p, dict)]

    def key(p: dict[str, Any]) -> tuple[int, str]:
        return (_num(p.get("order"), default=1_000_000), str(p.get("page_id", "")))

    return sorted(typed, key=key)


def _grid_profile(grid: dict[str, Any]) -> dict[str, Any]:
    meta = grid.get("meta") if isinstance(grid.get("meta"), dict) else {}
    profiles = grid.get("profiles") if isinstance(grid.get("profiles"), dict) else {}
    default_name = meta.get("default_profile")
    profile = profiles.get(default_name) if isinstance(default_name, str) else None
    if not isinstance(profile, dict) and profiles:
        # deterministic fallback: the lexicographically first profile key
        first_key = sorted(profiles.keys())[0]
        profile = profiles.get(first_key)
    return profile if isinstance(profile, dict) else {}


def _canvas_size(profile: dict[str, Any]) -> tuple[int, int]:
    canvas = profile.get("canvas") if isinstance(profile.get("canvas"), dict) else {}
    return _num(canvas.get("width"), default=1280), _num(
        canvas.get("height"), default=720
    )


def _cell_size(profile: dict[str, Any]) -> tuple[int, int]:
    grid = profile.get("grid") if isinstance(profile.get("grid"), dict) else {}
    return (
        _num(grid.get("column_width"), default=40)
        + _num(grid.get("gutter"), default=0),
        _num(grid.get("row_height"), default=40) + _num(grid.get("gutter"), default=0),
    )


def _margin(profile: dict[str, Any]) -> tuple[int, int]:
    margin = profile.get("margin") if isinstance(profile.get("margin"), dict) else {}
    return _num(margin.get("left"), default=0), _num(margin.get("top"), default=0)


def _text(
    x: int,
    y: int,
    content: str,
    *,
    cls: str = "",
    fill: str | None = None,
    font_size: int | None = None,
) -> str:
    """A ``<text>`` element. ``fill``/``font_size`` are omitted entirely when
    ``None`` (the pre-styling default) so existing call sites stay
    byte-identical; only a caller that passes them changes the emitted attrs.
    """
    cls_attr = f' class="{_esc(cls)}"' if cls else ""
    style_attr = _style_attr("fill", fill)
    if font_size is not None:
        style_attr += f' font-size="{font_size}"'
    return f'<text x="{x}" y="{y}"{cls_attr}{style_attr}>{_esc(content)}</text>'


def _visual_group(
    visual: dict[str, Any],
    profile: dict[str, Any],
    origin_x: int,
    origin_y: int,
    style: dict[str, str | None],
) -> str:
    position = (
        visual.get("position") if isinstance(visual.get("position"), dict) else {}
    )
    col_w, row_h = _cell_size(profile)
    x = origin_x + _num(position.get("x")) * col_w
    y = origin_y + _num(position.get("y")) * row_h
    width = max(1, _num(position.get("width"), default=1)) * col_w
    height = max(1, _num(position.get("height"), default=1)) * row_h

    visual_id = str(visual.get("visual_id", "<unnamed>"))
    visual_type = str(visual.get("visual_type", "<unknown>"))
    question = str(visual.get("business_question", ""))
    contract = visual.get("metric_contract")
    if isinstance(contract, dict) and not contract.get("none"):
        contract_name = str(contract.get("name", "")) or _PLACEHOLDER
    else:
        contract_name = "none"
    formatting = (
        visual.get("formatting_rules")
        if isinstance(visual.get("formatting_rules"), dict)
        else {}
    )
    title = str(formatting.get("title", "")) or visual_id

    esc_type = _esc(visual_type)
    esc_contract = _esc(contract_name)
    lines = [
        f'<g class="visual" data-visual-id="{_esc(visual_id)}" '
        f'data-visual-type="{esc_type}" data-contract="{esc_contract}">',
        # `fill="none"` rides the SAME token presence as `stroke` (#526): SVG
        # defaults an unset fill to BLACK, so a styled dark-canvas preview drew
        # the box as an opaque slab over its own title/contract text. It must be
        # an outline. Gated on the style token rather than emitted
        # unconditionally so the no-tokens path stays attribute-free --
        # `test_omitting_tokens_leaves_output_unchanged` asserts `"fill=" not in
        # unstyled`.
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'class="visual-box"{_style_attr("stroke", style.get("line"))}'
        f"{_style_attr('fill', 'none' if style.get('line') else '')} />",
        _text(
            x + 4,
            y + 14,
            f"{title} [{visual_type}]",
            cls="visual-title",
            fill=style.get("ink"),
        ),
        _text(
            x + 4,
            y + 28,
            f"Q: {question}",
            cls="visual-question",
            fill=style.get("ink"),
        ),
        _text(
            x + 4,
            y + 42,
            f"contract: {contract_name}",
            cls="visual-contract",
            fill=style.get("ink_muted"),
        ),
        _text(
            x + 4,
            y + 56,
            _PLACEHOLDER,
            cls="visual-value",
            fill=style.get("ink_muted"),
        ),
        "</g>",
    ]
    return "".join(lines)


def _narrative_block(
    narrative: dict[str, Any], x: int, y: int, style: dict[str, str | None]
) -> str:
    if not narrative:
        return ""
    rows = [
        ("headline", narrative.get("headline")),
        ("so_what", narrative.get("so_what")),
        ("recommended_action", narrative.get("recommended_action")),
        ("key_exception", narrative.get("key_exception")),
    ]
    ink = style.get("ink")
    lines = [f'<g class="narrative" transform="translate({x},{y})">']
    for i, (label, value) in enumerate(rows):
        text = str(value) if value else _PLACEHOLDER
        lines.append(
            _text(0, i * 14, f"{label}: {text}", cls="narrative-line", fill=ink)
        )
    lines.append("</g>")
    return "".join(lines)


def _slicers_block(
    slicers: list[dict[str, Any]], x: int, y: int, style: dict[str, str | None]
) -> str:
    typed = [s for s in slicers if isinstance(s, dict)]
    typed.sort(key=lambda s: str(s.get("field", "")))
    ink = style.get("ink")
    lines = [f'<g class="slicers" transform="translate({x},{y})">']
    for i, slicer in enumerate(typed):
        field = str(slicer.get("field", ""))
        stype = str(slicer.get("type", ""))
        lines.append(
            _text(0, i * 14, f"slicer: {field} ({stype})", cls="slicer-line", fill=ink)
        )
    lines.append("</g>")
    return "".join(lines)


def _footer_block(
    blueprint: dict[str, Any], x: int, y: int, style: dict[str, str | None]
) -> str:
    theme = (
        blueprint.get("theme_json")
        if isinstance(blueprint.get("theme_json"), dict)
        else {}
    )
    grid_ref = blueprint.get("grid") if isinstance(blueprint.get("grid"), dict) else {}
    mobile = (
        blueprint.get("mobile_notes")
        if isinstance(blueprint.get("mobile_notes"), dict)
        else {}
    )
    # Reference/metadata lines are secondary content: ink_muted, matching the
    # visual PLACEHOLDER value and the disclaimer that already used it.
    muted = style.get("ink_muted")
    lines = [f'<g class="footer" transform="translate({x},{y})">']
    lines.append(_text(0, 0, f"freshness: {_PLACEHOLDER}", cls="freshness", fill=muted))
    lines.append(
        _text(
            0,
            14,
            f"theme: {theme.get('theme_ref', 'none')}",
            cls="theme-ref",
            fill=muted,
        )
    )
    lines.append(
        _text(
            0,
            28,
            f"grid: {grid_ref.get('grid_ref', 'none')}",
            cls="grid-ref",
            fill=muted,
        )
    )
    lines.append(
        _text(
            0,
            42,
            f"mobile_grid: {mobile.get('grid_ref', 'none')}",
            cls="mobile-grid-ref",
            fill=muted,
        )
    )
    a11y_rtl = "per a11y-rtl checklist" if mobile else _PLACEHOLDER
    lines.append(
        _text(
            0,
            56,
            f"accessibility/rtl: {a11y_rtl}",
            cls="a11y-rtl-ref",
            fill=muted,
        )
    )
    lines.append("</g>")
    return "".join(lines)


def _navigation_block(
    composition: dict[str, Any], x: int, y: int, style: dict[str, str | None]
) -> str:
    nav = composition.get("navigation")
    typed = [n for n in nav if isinstance(n, dict)] if isinstance(nav, list) else []
    typed.sort(key=lambda n: (str(n.get("from_page", "")), str(n.get("to", ""))))
    muted = style.get("ink_muted")
    lines = [f'<g class="navigation" transform="translate({x},{y})">']
    for i, link in enumerate(typed):
        label = str(link.get("label", ""))
        src = str(link.get("from_page", ""))
        dst = str(link.get("to", ""))
        lines.append(
            _text(0, i * 14, f"{src} -> {dst}: {label}", cls="nav-line", fill=muted)
        )
    lines.append("</g>")
    return "".join(lines)


def _page_order_label(page_name: str, composition: dict[str, Any]) -> str:
    """This page's 1-based reading position within the composition's
    deterministically SORTED page order (FR-015 "pages + order"); ``page ?/?``
    when the composition does not list this page (e.g. an unlinked draft)."""
    pages = _sorted_pages(composition)
    total = len(pages)
    for index, page in enumerate(pages, start=1):
        if str(page.get("page_id", "")) == page_name:
            return f"page {index}/{total}"
    return "page ?/?"


def _page_header(
    blueprint: dict[str, Any],
    page_name: str,
    order_label: str,
    origin_x: int,
    origin_y: int,
    style: dict[str, str | None],
) -> str:
    """The three page-identity lines: title, audience, business question.

    All three are primary content, so all three take ``ink`` -- before #521
    finding 5 only the title was filled, leaving the other two at SVG-default
    black on a dark canvas.
    """
    audience = str(blueprint.get("audience", ""))
    business_question = str(blueprint.get("business_question", ""))
    ink = style.get("ink")
    return "".join(
        (
            _text(
                origin_x,
                origin_y + 10,
                f"page: {page_name} ({order_label})",
                cls="page-title",
                fill=ink,
            ),
            _text(
                origin_x,
                origin_y + 24,
                f"audience: {audience}",
                cls="page-audience",
                fill=ink,
            ),
            _text(
                origin_x,
                origin_y + 38,
                f"question: {business_question}",
                cls="page-question",
                fill=ink,
            ),
        )
    )


def _page_svg(
    blueprint: dict[str, Any],
    visual_specs: list[dict[str, Any]],
    composition: dict[str, Any],
    grid: dict[str, Any],
    style: dict[str, str | None],
) -> str:
    profile = _grid_profile(grid)
    canvas_w, canvas_h = _canvas_size(profile)
    origin_x, origin_y = _margin(profile)

    page_name = str(blueprint.get("page_name", "<page>"))
    sections = (
        blueprint.get("sections") if isinstance(blueprint.get("sections"), dict) else {}
    )
    order_label = _page_order_label(page_name, composition)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" '
        f'height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}" '
        f'data-page-id="{_esc(page_name)}">',
        f'<rect x="0" y="0" width="{canvas_w}" height="{canvas_h}" class="canvas"'
        f"{_style_attr('fill', style.get('ground'))} />",
        _page_header(blueprint, page_name, order_label, origin_x, origin_y, style),
    ]

    for section_name in _SECTION_ORDER:
        block = sections.get(section_name)
        if isinstance(block, dict) and block.get("present"):
            parts.append(f'<g class="section" data-section="{_esc(section_name)}"></g>')

    for visual in _sorted_visuals(visual_specs):
        parts.append(_visual_group(visual, profile, origin_x, origin_y + 50, style))

    parts.append(
        _slicers_block(blueprint.get("slicers") or [], origin_x, origin_y + 200, style)
    )
    parts.append(
        _narrative_block(
            blueprint.get("narrative") or {}, origin_x, origin_y + 260, style
        )
    )
    parts.append(_navigation_block(composition, origin_x, origin_y + 320, style))
    parts.append(_footer_block(blueprint, origin_x, origin_y + 380, style))

    # Stated on EVERY render, unconditionally -- see PREVIEW_DISCLAIMER's
    # docstring. Not gated on `style`/tokens: a monochrome render is exactly as
    # capable of being over-read as a styled one.
    parts.append(
        _text(
            origin_x,
            origin_y + 440,
            PREVIEW_DISCLAIMER,
            cls="preview-disclaimer",
            fill=style.get("ink_muted"),
            font_size=9,
        )
    )

    parts.append("</svg>")
    return "".join(parts)


def _render(
    blueprint: dict[str, Any],
    visual_specs: list[dict[str, Any]],
    composition: dict[str, Any],
    grid: dict[str, Any],
    style: dict[str, str | None],
) -> str:
    """Pure render: already-loaded dicts in, deterministic SVG text out. No I/O."""
    return _page_svg(blueprint, visual_specs, composition, grid, style)


def render_blueprint_preview(
    *,
    blueprint_path: Path | str,
    visual_spec_paths: list[Path | str],
    composition_path: Path | str,
    grid_path: Path | str,
    tokens_path: Path | str | None = None,
) -> str:
    """Read the four committed YAML artifacts and render a deterministic,
    placeholder-only SVG (FR-015/FR-016/SC-006).

    Read-only: opens exactly the four paths given (plus each visual-spec path,
    plus ``tokens_path`` when given); writes nothing, reaches no database,
    creates no PBIR/DAX. A MISSING path degrades to an empty mapping (a
    not-yet-authored artifact is a legitimate preview subject) but an
    UNREADABLE or MALFORMED path raises ``PreviewInputError`` naming the file
    -- a corrupt input must never silently render as an empty-but-valid-looking
    preview.

    ``tokens_path`` is keyword-only and optional (default ``None``): when
    omitted, the render is byte-identical to the pre-existing monochrome
    output plus the now-unconditional ``PREVIEW_DISCLAIMER``. When given, the
    SAME tokens YAML ``theme_compile`` reads colors this SVG -- never a
    theme.json -- so the preview cannot show styling Desktop would silently
    ignore (see ``_style_from_tokens``). This function still has NO
    data-source parameter: every business value stays the literal
    ``PLACEHOLDER`` regardless of styling.
    """
    blueprint = _load_yaml_mapping(Path(blueprint_path))
    composition = _load_yaml_mapping(Path(composition_path))
    grid = _load_yaml_mapping(Path(grid_path))
    visual_specs = [_load_yaml_mapping(Path(p)) for p in visual_spec_paths]
    style = _style_from_tokens(tokens_path)
    return _render(blueprint, visual_specs, composition, grid, style)
