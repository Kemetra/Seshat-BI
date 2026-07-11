"""PBIR visual geometry writer (adapter increment D).

Sets an existing, binding-mapped visual's ``position`` rectangle -- ``x``, ``y``,
``width``, ``height``, ``z``, ``tabOrder`` -- the layout a human drags/resizes in
the Power BI canvas. Authorized by ADR 0016 (ratified).

THE FR-003 GUARANTEE (unchanged): the writer NEVER touches the visual's data
binding. It asserts ``visual.query`` and ``visual.visualType`` are byte-identical
before and after, and refuses to write if either would change. Geometry is added
BESIDE the binding guard, never through it. It NEVER changes visualType, creates or
deletes a visual, or moves an unbound visual (ADR 0016 exclusions).

THE ON-CANVAS GUARD: the result rectangle must fit the page's REAL canvas, read from
the sibling ``page.json`` (top-level ``width``/``height``) -- never a hardcoded size.
Off-canvas / negative / non-numeric rectangles are refused (objective validity);
overlap between visuals is ALLOWED (a design judgment the lint must not make).

NO FORCE PARAMETER: moving a visual necessarily changes its always-present position
keys -- that IS the operation. A force gate modeled on increment B's "differs ->
refuse" formatting gate was tried and removed here: it blocked every real move.
Repeated moves simply succeed; the reviewable git diff + human ratification is the
overwrite safety net, not a per-call flag.

Companion authoring adapter (ADR 0015/0016): committed PBIR JSON, deterministic,
validated, all-or-nothing. No pbi-cli, no live Power BI, no network -- stdlib only.
Grants no readiness pass, emits no score.
"""

from __future__ import annotations

import json
from pathlib import Path

# The only position keys this increment may write (ADR 0016). Anything else refused.
_ALLOWED_KEYS = frozenset({"x", "y", "width", "height", "z", "tabOrder"})


class PbirGeometryError(Exception):
    """A geometry input/output problem surfaced cleanly (never a traceback)."""


def _is_number(v: object) -> bool:
    """A real number, not a bool -- ``bool`` is an ``int`` subclass we must reject."""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _require_object_member(doc: dict, name: str) -> None:
    """Guard that ``doc[name]`` is a JSON object; raise the same message otherwise."""
    if not isinstance(doc.get(name), dict):
        raise PbirGeometryError(f"visual.json has no '{name}' object")


def _dump(doc: object) -> str:
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def _load_json(p: Path, what: str) -> dict:
    try:
        with p.open(encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise PbirGeometryError(
            f"{what} is not valid JSON ({exc.__class__.__name__}): {p}"
        ) from exc
    if not isinstance(doc, dict):
        raise PbirGeometryError(f"{what} is not a JSON object: {p}")
    return doc


def _canvas_dims(visual_json: Path) -> tuple[float, float]:
    """Read the REAL canvas width/height from the sibling page.json.

    Path: .../pages/<page>/visuals/<v>/visual.json -> .../pages/<page>/page.json,
    i.e. visual_json.parents[2] / 'page.json'. NEVER hardcode a fallback size.
    """
    page_json = visual_json.parents[2] / "page.json"
    if not page_json.is_file():
        raise PbirGeometryError(
            f"page.json not found next to the visual ({page_json}); cannot validate "
            f"on-canvas without the real canvas dimensions"
        )
    page = _load_json(page_json, "page.json")
    w, h = page.get("width"), page.get("height")
    if not _is_number(w) or not _is_number(h):
        raise PbirGeometryError(
            f"page.json has no numeric width/height ({page_json}); cannot validate "
            f"on-canvas"
        )
    return float(w), float(h)


def _load_visual(visual_json: Path) -> dict:
    """Load the visual.json, guarding its path + required ``visual``/``position``."""
    if not visual_json.is_file():
        raise PbirGeometryError(f"visual.json not found: {visual_json}")
    if ".Report" not in str(visual_json.resolve()):
        raise PbirGeometryError("target is not inside a *.Report/ tree")
    doc = _load_json(visual_json, "visual.json")
    _require_object_member(doc, "visual")
    _require_object_member(doc, "position")
    return doc


def _validate_key_value(key: str, val: object) -> None:
    """Reject one request entry -- the allow-list check MUST precede the numeric one.

    Order matters: a key like ``visualType`` is both out-of-list AND non-numeric;
    checking the key first is what makes it surface as an allow-list error.
    """
    if key not in _ALLOWED_KEYS:
        raise PbirGeometryError(
            f"position key {key!r} is not in the geometry allow-list "
            f"(allowed: {sorted(_ALLOWED_KEYS)})"
        )
    if not _is_number(val):
        raise PbirGeometryError(
            f"position.{key} must be a number, got {type(val).__name__}: {val!r}"
        )


def _validate_requested(position: dict) -> None:
    """Reject an empty request, an out-of-allow-list key, or a non-numeric value."""
    if not isinstance(position, dict) or not position:
        raise PbirGeometryError("position must be a non-empty object")
    for key, val in position.items():
        _validate_key_value(key, val)


def _rect_off_canvas(
    rect: tuple[float, float, float, float], canvas: tuple[float, float]
) -> bool:
    """True when the rectangle's origin is negative or it overruns the canvas edge."""
    rx, ry, rw, rh = rect
    canvas_w, canvas_h = canvas
    return rx < 0 or ry < 0 or rx + rw > canvas_w or ry + rh > canvas_h


def _require_numeric_rect(
    result: dict,
) -> tuple[float, float, float, float]:
    """Guard that x/y/width/height are numeric; return them (defaulting to 0)."""
    rx, ry = result.get("x", 0), result.get("y", 0)
    rw, rh = result.get("width", 0), result.get("height", 0)
    for label, v in (("x", rx), ("y", ry), ("width", rw), ("height", rh)):
        if not _is_number(v):
            raise PbirGeometryError(f"result {label} is not numeric: {v!r}")
    return rx, ry, rw, rh


def _validate_on_canvas(result: dict, canvas_w: float, canvas_h: float) -> None:
    """Reject a result rectangle that is non-numeric, non-positive, or off-canvas."""
    rx, ry, rw, rh = _require_numeric_rect(result)
    # A non-positive width/height is degenerate (zero-size is invisible; negative
    # is nonsensical) AND, left unchecked, a negative dimension can shrink x+w or
    # y+h enough to defeat the overrun half of the off-canvas check below while the
    # origin itself is off-canvas. Reject both before the position/overrun check.
    if rw <= 0 or rh <= 0:
        raise PbirGeometryError(
            f"result rectangle width={rw} height={rh} must be positive "
            f"(non-positive width/height is a degenerate rectangle); refusing to write"
        )
    if _rect_off_canvas((rx, ry, rw, rh), (canvas_w, canvas_h)):
        raise PbirGeometryError(
            f"result rectangle x={rx} y={ry} w={rw} h={rh} is off-canvas "
            f"(canvas {canvas_w}x{canvas_h}); refusing to write"
        )


def _binding_snapshot(visual: dict) -> str:
    """The FR-003 oracle: the visual's data binding (query + visualType), dumped."""
    return _dump({"query": visual.get("query"), "visualType": visual.get("visualType")})


def set_geometry(visual_json: Path, position: dict) -> Path:
    """Set the allow-listed ``position`` keys on the visual, on-canvas + binding-safe.

    ``position`` maps a subset of ``{x, y, width, height, z, tabOrder}`` to numeric
    values. Existing position keys not named in ``position`` are preserved. Raises
    PbirGeometryError on a bad path, an out-of-allow-list key, a non-numeric value,
    or a result rectangle that would fall off the page's real canvas. Returns the
    written path.
    """
    visual_json = Path(visual_json)
    doc = _load_visual(visual_json)
    _validate_requested(position)

    # Snapshot the data binding BEFORE editing -- the FR-003 oracle.
    binding_before = _binding_snapshot(doc["visual"])

    # Compute the RESULT rectangle (existing merged with requested) and validate it
    # on-canvas against the REAL canvas dims (never a hardcoded default).
    result = {**doc["position"], **position}
    canvas_w, canvas_h = _canvas_dims(visual_json)
    _validate_on_canvas(result, canvas_w, canvas_h)

    # No overwrite gate: moving a visual necessarily changes always-present position
    # keys, so a "differs -> refuse" gate would block every real move. Overwrite
    # safety is the reviewable git diff + human ratification, not a per-call flag.
    doc["position"] = result

    # THE FR-003 GUARANTEE: the data binding must be byte-identical after the edit.
    if _binding_snapshot(doc["visual"]) != binding_before:
        raise PbirGeometryError(
            "refusing to write: the edit would alter the visual's data binding "
            "(query/visualType) -- this adapter lays out only, never binds (FR-003)"
        )

    text = _dump(doc)
    if _dump(json.loads(text)) != text:
        raise PbirGeometryError("staged visual.json is not round-trip stable")
    visual_json.write_text(text, encoding="utf-8", newline="\n")
    return visual_json


def pbir_geometry_main(args) -> int:
    """CLI entry: set a visual's position rectangle from a JSON string/file."""
    import sys

    raw = args.position
    try:
        if raw and Path(raw).is_file():
            position = json.loads(Path(raw).read_text(encoding="utf-8"))
        else:
            position = json.loads(raw) if raw else {}
    except (OSError, json.JSONDecodeError) as exc:
        print(f"pbir-set-geometry: bad --position ({exc})", file=sys.stderr)
        return 2
    try:
        written = set_geometry(Path(args.visual), position)
    except PbirGeometryError as exc:
        print(f"pbir-set-geometry: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {written}")
    print(
        "note: layout only -- the visual's data binding (query/visualType) is "
        "unchanged; this grants no readiness pass (a human render + review does)."
    )
    return 0
