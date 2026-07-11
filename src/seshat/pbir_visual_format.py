"""PBIR per-visual formatting writer (adapter increment B).

Applies allow-listed FORMATTING to an existing, already-data-bound ``visual.json``:
it sets properties under the visual's ``objects`` (chart-content formatting) and
``visualContainerObjects`` (container chrome: border, title, background) subtrees --
the settings a human sets in the Power BI UI's Format pane.

THE FR-003 GUARANTEE (formatting, never binding): the writer NEVER touches the
visual's data binding. It asserts ``visual.query`` and ``visual.visualType`` are
byte-identical before and after the edit, and refuses to write if they would change.
The data binding (``query.queryState.*.projections[].field`` Column/Measure
references) belongs to the human who authored the visual; this adapter only styles it.

Companion authoring adapter (ADR 0015): writes committed PBIR JSON within the
allow-list, deterministically, validated, all-or-nothing. No pbi-cli, no live Power
BI, no network -- stdlib json + pathlib only. Grants no readiness pass, no score.

Property values use the PBIR wrapper ``{"expr": {"Literal": {"Value": <v>}}}``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

# Allow-list: the two formatting containers this increment may write, and which
# property groups inside each. Anything outside this map is refused (ADR 0015
# decision 2). `objects` = chart-content formatting; `visualContainerObjects` =
# container chrome. NEVER `query` / `visualType` (data binding, FR-003).
_ALLOWED_CONTAINERS = {
    "objects": frozenset(
        {"legend", "labels", "dataPoint", "categoryAxis", "valueAxis", "title"}
    ),
    "visualContainerObjects": frozenset(
        {"border", "title", "subTitle", "background", "dropShadow"}
    ),
}


class PbirFormatError(Exception):
    """A visual-formatting input/output problem surfaced cleanly (no traceback)."""


def _dump(doc: object) -> str:
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def _encode_literal_value(value: object) -> str:
    """Encode a scalar to its PBIR literal string (no expr/Literal wrapper).

    Matches the wire format proven by the Microsoft PBIP sample fixture:
    - bool  -> ``true`` / ``false`` (checked first: bool is a subclass of int)
    - int   -> a DAX long literal with the ``L`` suffix (e.g. ``70L``, ``0L``)
    - float -> the plain number (e.g. ``0.5``)
    - str   -> a single-quoted literal with embedded ``'`` doubled (e.g.
      ``'Today''s Sales'``) -- an unescaped quote is malformed PBIR.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return f"{value}L"  # PBIR integer literals carry the DAX long suffix
    if isinstance(value, float):
        return f"{value}"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"  # double embedded quotes
    raise PbirFormatError(
        f"formatting value must be a bool/int/float/str, got "
        f"{type(value).__name__}: {value!r}"
    )


def _literal(value: object) -> dict:
    """Wrap a scalar in the PBIR expr/Literal value shape."""
    return {"expr": {"Literal": {"Value": _encode_literal_value(value)}}}


def _guard_visual_path(visual_json: Path) -> None:
    """Enforce the file guards: it exists and lives under a *.Report/ tree."""
    if not visual_json.is_file():
        raise PbirFormatError(f"visual.json not found: {visual_json}")
    # Guard: the file must live under a *.Report/ tree (never write elsewhere).
    if ".Report" not in str(visual_json.resolve()):
        raise PbirFormatError("target is not inside a *.Report/ tree")


def _parse_visual_doc(visual_json: Path) -> dict:
    """Read ``visual_json`` as utf-8-sig JSON and confirm the ``visual`` object."""
    try:
        with visual_json.open(encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise PbirFormatError(
            f"visual.json is not valid JSON ({exc.__class__.__name__})"
        ) from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("visual"), dict):
        raise PbirFormatError("visual.json has no 'visual' object")
    return doc


def _load_visual_doc(visual_json: Path) -> tuple[dict, dict]:
    """Load and validate the visual document at ``visual_json``.

    Enforces the file guards (exists, inside a *.Report/ tree), reads it as
    utf-8-sig JSON, and confirms the ``visual`` object is present. Returns the
    ``(doc, visual)`` pair; raises PbirFormatError exactly as the checks demand.
    """
    _guard_visual_path(visual_json)
    doc = _parse_visual_doc(visual_json)
    return doc, doc["visual"]


def _binding_snapshot(visual: dict) -> str:
    """Serialize the FR-003 data-binding oracle (query + visualType) for compare."""
    return _dump({"query": visual.get("query"), "visualType": visual.get("visualType")})


def _validate_container(container: str, groups: object) -> None:
    """Check one requested container and its groups against the allow-list."""
    if container not in _ALLOWED_CONTAINERS:
        raise PbirFormatError(
            f"container {container!r} is not in the formatting allow-list "
            f"(allowed: {sorted(_ALLOWED_CONTAINERS)})"
        )
    if not isinstance(groups, dict):
        raise PbirFormatError(f"{container} must map group -> properties")
    allowed_groups = _ALLOWED_CONTAINERS[container]
    for group in groups:
        if group not in allowed_groups:
            raise PbirFormatError(
                f"group {container}.{group!r} is not in the allow-list "
                f"(allowed: {sorted(allowed_groups)})"
            )


def _validate_formatting(formatting: dict) -> None:
    """Check every requested container/group against the allow-list up front."""
    for container, groups in formatting.items():
        _validate_container(container, groups)


class _SetCtx(NamedTuple):
    """The invariant context for a group's property writes (container/group/force).

    Bundles the three values that don't change across one group's properties so a
    single property write needs just ``(props_bag, prop, value, ctx)``.
    """

    container: str
    group: str
    force: bool


def _set_property(props_bag: dict, prop: str, value: object, ctx: _SetCtx) -> None:
    """Set one property in ``props_bag`` (expr/Literal wrapped), honouring force.

    An idempotent re-set of the same value is always allowed; overwriting a
    DIFFERENT existing value is refused unless ``ctx.force`` is set.
    """
    new_val = _literal(value)
    is_conflicting_overwrite = prop in props_bag and props_bag[prop] != new_val
    if is_conflicting_overwrite and not ctx.force:
        raise PbirFormatError(
            f"{ctx.container}.{ctx.group}.{prop} already set to a different "
            f"value -- use force=True to overwrite"
        )
    props_bag[prop] = new_val


def _group_props_bag(cont: dict, group: str) -> dict:
    """Return the mutable ``properties`` bag for ``group`` under container ``cont``.

    PBIR stores each group as a one-element list of objects; the writer targets
    ``entries[0].properties``. A missing or malformed entry list is re-initialised
    to the canonical ``[{}]`` shape before the properties bag is resolved.
    """
    entries = cont.setdefault(group, [{}])
    if not (isinstance(entries, list) and entries):
        entries = [{}]
        cont[group] = entries
    return entries[0].setdefault("properties", {})


def _apply_group(cont: dict, group: str, props: object, ctx: _SetCtx) -> None:
    """Set every property of one allow-listed group under container ``cont``."""
    if not isinstance(props, dict):
        raise PbirFormatError(f"{ctx.container}.{group} must be a property map")
    props_bag = _group_props_bag(cont, group)
    for prop, value in props.items():
        _set_property(props_bag, prop, value, ctx)


def _apply_formatting(visual: dict, formatting: dict, force: bool) -> None:
    """Apply the allow-listed formatting: for each container/group set its props."""
    for container, groups in formatting.items():
        cont = visual.setdefault(container, {})
        if not isinstance(cont, dict):
            raise PbirFormatError(f"visual.{container} is not an object")
        for group, props in groups.items():
            _apply_group(cont, group, props, _SetCtx(container, group, force))


def apply_visual_format(
    visual_json: Path, formatting: dict, force: bool = False
) -> Path:
    """Apply allow-listed ``formatting`` to the visual at ``visual_json``.

    ``formatting`` maps container -> group -> {property: scalar}, e.g.
    ``{"visualContainerObjects": {"title": {"show": True, "text": "Sales"}}}``.
    Sets each property (expr/Literal wrapped) under the group, preserving the
    visual's data binding byte-for-byte. Raises PbirFormatError on a bad path, an
    out-of-allow-list target, or if the edit would alter query/visualType.
    Returns the written path.
    """
    visual_json = Path(visual_json)
    doc, visual = _load_visual_doc(visual_json)

    # Snapshot the data binding BEFORE editing -- the FR-003 oracle.
    binding_before = _binding_snapshot(visual)

    # Validate the requested formatting against the allow-list up front.
    _validate_formatting(formatting)

    # Refuse to clobber existing formatting unless force (idempotent re-set is fine
    # since we write the same expr/Literal; force gates a DIFFERENT value).
    # Apply: for each container/group, set the named properties.
    _apply_formatting(visual, formatting, force)

    # THE FR-003 GUARANTEE: the data binding must be byte-identical after the edit.
    binding_after = _binding_snapshot(visual)
    if binding_after != binding_before:
        raise PbirFormatError(
            "refusing to write: the edit would alter the visual's data binding "
            "(query/visualType) -- this adapter formats only, never binds (FR-003)"
        )

    text = _dump(doc)
    if _dump(json.loads(text)) != text:
        raise PbirFormatError("staged visual.json is not round-trip stable")
    visual_json.write_text(text, encoding="utf-8", newline="\n")
    return visual_json


def pbir_format_main(args) -> int:
    """CLI entry: apply formatting (from a JSON string/file) to a visual."""
    import sys

    raw = args.formatting
    try:
        if raw and Path(raw).is_file():
            formatting = json.loads(Path(raw).read_text(encoding="utf-8"))
        else:
            formatting = json.loads(raw) if raw else {}
    except (OSError, json.JSONDecodeError) as exc:
        print(f"pbir-format-visual: bad --formatting ({exc})", file=sys.stderr)
        return 2
    try:
        written = apply_visual_format(Path(args.visual), formatting, force=args.force)
    except PbirFormatError as exc:
        print(f"pbir-format-visual: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {written}")
    print(
        "note: formatting only -- the visual's data binding (query/measures) is "
        "unchanged; this grants no readiness pass (a human design-review does)."
    )
    return 0
