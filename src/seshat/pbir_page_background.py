"""PBIR page-background writer (adapter increment C).

Sets a report page's canvas background to a committed surface-2 IMAGE asset -- the
full Desktop "Canvas background > Image" flow, done by writing the PBIR JSON:

1. copy the asset into the report's ``StaticResources/RegisteredResources/``;
2. register it in ``report.json`` ``resourcePackages`` (the RegisteredResources
   package: ``{name, path, type: "Image"}``);
3. reference it from ``page.json`` ``objects.background`` via a ``ResourcePackageItem``
   URL + a display name + scaling (+ optional transparency).

The wire format is taken VERBATIM from a real Power BI Desktop-authored sample (the
image URL is a ``ResourcePackageItem`` wrapper with ``PackageType: 1`` -- NOT a
Literal; this could not be guessed, which is why increment C was held until a real
sample existed). Values that ARE literals (name, scaling) use the PBIR
``expr/Literal`` wrapper with single-quoted strings.

Allow-list (ADR 0015): touches ONLY ``page.json`` ``objects.background`` and the
``report.json`` RegisteredResources package + the copied asset. Every other page
object (e.g. ``outspacePane``) and every other report key is preserved unchanged (the
files are deterministically re-serialized with sorted keys -- the same house style as
increments A and B -- so values are preserved, not the original byte layout). It NEVER
writes a ``visual.json``, page geometry, ``themeCollection``, or a model file.
Surface-2 purity: it references a static image asset; it bakes no data into it.

Companion authoring adapter: stdlib json/pathlib/shutil only, no pbi-cli, no live
Power BI, no network. Deterministic, all-or-nothing, grants no readiness pass.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

_REG = "RegisteredResources"
_VALID_SCALING = ("Fit", "Fill", "Normal")


class PbirPageBgError(Exception):
    """A page-background input/output problem surfaced cleanly (no traceback)."""


def _load_json(path: Path) -> object:
    try:
        with path.open(encoding="utf-8-sig") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise PbirPageBgError(
            f"{path} could not be read as JSON ({exc.__class__.__name__})"
        ) from exc


def _dump(doc: object) -> str:
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def _literal(value: str) -> dict:
    """A single-quoted string literal in the PBIR expr/Literal wrapper."""
    return {"expr": {"Literal": {"Value": "'" + value.replace("'", "''") + "'"}}}


# Transparency is a RAW decimal literal ("0D"), NOT a quoted string -- it must not
# go through _literal (that would wrap it as '0D'). "0D" = 0% transparency = opaque,
# verbatim from the real Desktop sample. A background image with the property absent
# can render invisible, so it is set explicitly.
_OPAQUE = {"expr": {"Literal": {"Value": "0D"}}}


def _image_block(display_name: str, item_name: str, scaling: str) -> dict:
    """The page-background image property, verbatim from the real Desktop sample.

    The URL is a ResourcePackageItem reference (PackageType 1 = RegisteredResources),
    NOT a Literal -- this is the shape that could not be guessed. ``display_name``
    keeps the file extension (matching the sample's ``'name.ico'`` form).
    """
    return {
        "image": {
            "name": _literal(display_name),
            "url": {
                "expr": {
                    "ResourcePackageItem": {
                        "PackageName": _REG,
                        "PackageType": 1,
                        "ItemName": item_name,
                    }
                }
            },
            "scaling": _literal(scaling),
        }
    }


def _safe_item_name(asset: Path) -> str:
    """The asset's bare file name, refusing any path separator or ``..`` traversal."""
    item_name = asset.name
    if any(sep in item_name for sep in ("/", "\\", "..")):
        raise PbirPageBgError(f"asset name is not a safe file name: {item_name!r}")
    return item_name


def _validate_inputs(asset: Path, report_dir: Path, scaling: str) -> None:
    """Guard the caller's asset/report_dir/scaling before any file is opened."""
    if not asset.is_file():
        raise PbirPageBgError(f"background asset not found: {asset}")
    if not report_dir.is_dir():
        raise PbirPageBgError(f"report dir not found: {report_dir}")
    if scaling not in _VALID_SCALING:
        raise PbirPageBgError(
            f"scaling must be one of {_VALID_SCALING}, got {scaling!r}"
        )


def _load_report_and_page(report_dir: Path, page_name: str) -> tuple[dict, dict]:
    """Resolve + load the report.json / page.json pair as JSON objects."""
    report_json_path = report_dir / "definition" / "report.json"
    page_json_path = report_dir / "definition" / "pages" / page_name / "page.json"
    if not report_json_path.is_file():
        raise PbirPageBgError(f"report.json not found under {report_dir}")
    if not page_json_path.is_file():
        raise PbirPageBgError(
            f"page.json not found for page {page_name!r} under {report_dir}"
        )
    report = _load_json(report_json_path)
    page = _load_json(page_json_path)
    if not isinstance(report, dict) or not isinstance(page, dict):
        raise PbirPageBgError("report.json / page.json is not a JSON object")
    return report, page


def _reg_package(report: dict, item_name: str) -> dict:
    """The RegisteredResources package with ``item_name`` present exactly once.

    Any prior entry for the same name is dropped and re-appended (idempotent), while
    every sibling item in an existing package is preserved.
    """
    existing = next(
        (
            p
            for p in report.get("resourcePackages", [])
            if isinstance(p, dict) and p.get("name") == _REG
        ),
        {"name": _REG, "type": _REG, "items": []},
    )
    items = [
        it
        for it in existing.get("items", [])
        if isinstance(it, dict) and it.get("name") != item_name
    ]
    items.append({"name": item_name, "path": item_name, "type": "Image"})
    return {"name": _REG, "type": _REG, "items": items}


def _stage_report(report: dict, item_name: str) -> dict:
    """A copy of report.json with the RegisteredResources package/item ensured."""
    staged = dict(report)
    packages = [
        p
        for p in staged.get("resourcePackages", [])
        if not (isinstance(p, dict) and p.get("name") == _REG)
    ]
    packages.append(_reg_package(report, item_name))
    staged["resourcePackages"] = packages
    return staged


def _stage_page(page: dict, display_name: str, item_name: str, scaling: str) -> dict:
    """A copy of page.json with ONLY ``objects.background`` set (rest preserved)."""
    staged = dict(page)
    objects = dict(staged.get("objects", {}))
    objects["background"] = [
        {
            "properties": {
                # display name KEEPS the extension (matches the real sample's
                # 'name.ico' form); the resolver keys off url.ItemName regardless.
                "image": _image_block(display_name, item_name, scaling),
                # explicit opaque transparency ("0D") -- see _OPAQUE.
                "transparency": _OPAQUE,
            }
        }
    ]
    staged["objects"] = objects
    return staged


def _staged_text(label: str, before: dict, after: dict) -> str:
    """Serialize a staged doc, asserting $schema is kept and the dump round-trips."""
    if before.get("$schema") != after.get("$schema"):
        raise PbirPageBgError(f"staged {label} would lose its $schema")
    text = _dump(after)
    if _dump(json.loads(text)) != text:
        raise PbirPageBgError(f"staged {label} is not round-trip stable")
    return text


def set_page_background(
    asset: Path,
    report_dir: Path,
    page_name: str,
    scaling: str = "Fit",
    force: bool = False,
) -> list[Path]:
    """Set the ``page_name`` page's canvas background to ``asset``.

    Copies the asset into RegisteredResources, registers it in report.json, and
    references it from the page's ``objects.background``. All-or-nothing: staged and
    validated before any write. Returns the written paths. Raises PbirPageBgError on
    bad input, an out-of-tree path, an existing different background without force, or
    invalid output.
    """
    asset = Path(asset)
    report_dir = Path(report_dir)
    _validate_inputs(asset, report_dir, scaling)
    item_name = _safe_item_name(asset)
    report, page = _load_report_and_page(report_dir, page_name)

    # Refuse to overwrite an existing DIFFERENT background on this page w/o force.
    if page.get("objects", {}).get("background") and not force:
        raise PbirPageBgError(
            f"page {page_name!r} already has a background -- use force=True to "
            f"replace it"
        )

    # Stage both docs (report.json package/item + page.json objects.background).
    staged_report = _stage_report(report, item_name)
    staged_page = _stage_page(page, asset.name, item_name, scaling)

    # Validate + serialize BEFORE writing anything (all-or-nothing).
    report_text = _staged_text("report.json", report, staged_report)
    page_text = _staged_text("page.json", page, staged_page)

    # Commit: copy asset, then both JSON files (order preserved for atomicity).
    report_json_path = report_dir / "definition" / "report.json"
    page_json_path = report_dir / "definition" / "pages" / page_name / "page.json"
    dest_asset = report_dir / "StaticResources" / _REG / item_name
    dest_asset.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(asset, dest_asset)
    report_json_path.write_text(report_text, encoding="utf-8", newline="\n")
    page_json_path.write_text(page_text, encoding="utf-8", newline="\n")
    return [dest_asset, report_json_path, page_json_path]


def pbir_page_bg_main(args) -> int:
    """CLI entry: set a page background; exit 2 on a clean error."""
    import sys

    try:
        written = set_page_background(
            Path(args.asset),
            Path(args.report),
            args.page,
            scaling=args.scaling,
            force=args.force,
        )
    except PbirPageBgError as exc:
        print(f"pbir-set-page-background: {exc}", file=sys.stderr)
        return 2
    for p in written:
        print(f"wrote {p}")
    print(
        "note: references a static surface-2 image asset as the page background; "
        "it bakes no data into the image and grants no readiness pass."
    )
    return 0
