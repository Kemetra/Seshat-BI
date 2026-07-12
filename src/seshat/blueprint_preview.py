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


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load a YAML mapping; ``{}`` on any read/parse failure or non-mapping
    content -- never raises, never fabricates a substitute value (shipped
    ``_load_yaml_mapping`` idiom, e.g. ``gap_detector.py``)."""
    import yaml

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


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


def _text(x: int, y: int, content: str, *, cls: str = "") -> str:
    cls_attr = f' class="{_esc(cls)}"' if cls else ""
    return f'<text x="{x}" y="{y}"{cls_attr}>{_esc(content)}</text>'


def _visual_group(
    visual: dict[str, Any], profile: dict[str, Any], origin_x: int, origin_y: int
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
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        'class="visual-box" />',
        _text(x + 4, y + 14, f"{title} [{visual_type}]", cls="visual-title"),
        _text(x + 4, y + 28, f"Q: {question}", cls="visual-question"),
        _text(x + 4, y + 42, f"contract: {contract_name}", cls="visual-contract"),
        _text(x + 4, y + 56, _PLACEHOLDER, cls="visual-value"),
        "</g>",
    ]
    return "".join(lines)


def _narrative_block(narrative: dict[str, Any], x: int, y: int) -> str:
    if not narrative:
        return ""
    rows = [
        ("headline", narrative.get("headline")),
        ("so_what", narrative.get("so_what")),
        ("recommended_action", narrative.get("recommended_action")),
        ("key_exception", narrative.get("key_exception")),
    ]
    lines = [f'<g class="narrative" transform="translate({x},{y})">']
    for i, (label, value) in enumerate(rows):
        text = str(value) if value else _PLACEHOLDER
        lines.append(_text(0, i * 14, f"{label}: {text}", cls="narrative-line"))
    lines.append("</g>")
    return "".join(lines)


def _slicers_block(slicers: list[dict[str, Any]], x: int, y: int) -> str:
    typed = [s for s in slicers if isinstance(s, dict)]
    typed.sort(key=lambda s: str(s.get("field", "")))
    lines = [f'<g class="slicers" transform="translate({x},{y})">']
    for i, slicer in enumerate(typed):
        field = str(slicer.get("field", ""))
        stype = str(slicer.get("type", ""))
        lines.append(_text(0, i * 14, f"slicer: {field} ({stype})", cls="slicer-line"))
    lines.append("</g>")
    return "".join(lines)


def _footer_block(blueprint: dict[str, Any], x: int, y: int) -> str:
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
    lines = [f'<g class="footer" transform="translate({x},{y})">']
    lines.append(_text(0, 0, f"freshness: {_PLACEHOLDER}", cls="freshness"))
    lines.append(
        _text(0, 14, f"theme: {theme.get('theme_ref', 'none')}", cls="theme-ref")
    )
    lines.append(
        _text(0, 28, f"grid: {grid_ref.get('grid_ref', 'none')}", cls="grid-ref")
    )
    lines.append(
        _text(
            0,
            42,
            f"mobile_grid: {mobile.get('grid_ref', 'none')}",
            cls="mobile-grid-ref",
        )
    )
    a11y_rtl = "per a11y-rtl checklist" if mobile else _PLACEHOLDER
    lines.append(_text(0, 56, f"accessibility/rtl: {a11y_rtl}", cls="a11y-rtl-ref"))
    lines.append("</g>")
    return "".join(lines)


def _navigation_block(composition: dict[str, Any], x: int, y: int) -> str:
    nav = composition.get("navigation")
    typed = [n for n in nav if isinstance(n, dict)] if isinstance(nav, list) else []
    typed.sort(key=lambda n: (str(n.get("from_page", "")), str(n.get("to", ""))))
    lines = [f'<g class="navigation" transform="translate({x},{y})">']
    for i, link in enumerate(typed):
        label = str(link.get("label", ""))
        src = str(link.get("from_page", ""))
        dst = str(link.get("to", ""))
        lines.append(_text(0, i * 14, f"{src} -> {dst}: {label}", cls="nav-line"))
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


def _page_svg(
    blueprint: dict[str, Any],
    visual_specs: list[dict[str, Any]],
    composition: dict[str, Any],
    grid: dict[str, Any],
) -> str:
    profile = _grid_profile(grid)
    canvas_w, canvas_h = _canvas_size(profile)
    origin_x, origin_y = _margin(profile)

    page_name = str(blueprint.get("page_name", "<page>"))
    audience = str(blueprint.get("audience", ""))
    business_question = str(blueprint.get("business_question", ""))
    sections = (
        blueprint.get("sections") if isinstance(blueprint.get("sections"), dict) else {}
    )
    order_label = _page_order_label(page_name, composition)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" '
        f'height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}" '
        f'data-page-id="{_esc(page_name)}">',
        f'<rect x="0" y="0" width="{canvas_w}" height="{canvas_h}" class="canvas" />',
        _text(
            origin_x,
            origin_y + 10,
            f"page: {page_name} ({order_label})",
            cls="page-title",
        ),
        _text(origin_x, origin_y + 24, f"audience: {audience}", cls="page-audience"),
        _text(
            origin_x,
            origin_y + 38,
            f"question: {business_question}",
            cls="page-question",
        ),
    ]

    for section_name in _SECTION_ORDER:
        block = sections.get(section_name)
        if isinstance(block, dict) and block.get("present"):
            parts.append(f'<g class="section" data-section="{_esc(section_name)}"></g>')

    for visual in _sorted_visuals(visual_specs):
        parts.append(_visual_group(visual, profile, origin_x, origin_y + 50))

    parts.append(
        _slicers_block(blueprint.get("slicers") or [], origin_x, origin_y + 200)
    )
    parts.append(
        _narrative_block(blueprint.get("narrative") or {}, origin_x, origin_y + 260)
    )
    parts.append(_navigation_block(composition, origin_x, origin_y + 320))
    parts.append(_footer_block(blueprint, origin_x, origin_y + 380))

    parts.append("</svg>")
    return "".join(parts)


def _render(
    blueprint: dict[str, Any],
    visual_specs: list[dict[str, Any]],
    composition: dict[str, Any],
    grid: dict[str, Any],
) -> str:
    """Pure render: already-loaded dicts in, deterministic SVG text out. No I/O."""
    return _page_svg(blueprint, visual_specs, composition, grid)


def render_blueprint_preview(
    *,
    blueprint_path: Path | str,
    visual_spec_paths: list[Path | str],
    composition_path: Path | str,
    grid_path: Path | str,
) -> str:
    """Read the four committed YAML artifacts and render a deterministic,
    placeholder-only SVG (FR-015/FR-016/SC-006).

    Read-only: opens exactly the four paths given (plus each visual-spec path);
    writes nothing, reaches no database, creates no PBIR/DAX. A path that is
    missing or unreadable degrades to an empty mapping (never fabricated
    content) rather than raising, matching the shipped ``_load_yaml_mapping``
    idiom used across the repo's other read-only composers.
    """
    blueprint = _load_yaml_mapping(Path(blueprint_path))
    composition = _load_yaml_mapping(Path(composition_path))
    grid = _load_yaml_mapping(Path(grid_path))
    visual_specs = [_load_yaml_mapping(Path(p)) for p in visual_spec_paths]
    return _render(blueprint, visual_specs, composition, grid)
