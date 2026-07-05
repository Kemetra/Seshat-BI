"""PBIR theme-application writer (adapter increment A).

Applies a ``retail theme-gen`` theme to a committed PBIR report by writing the
theme JSON as a BaseTheme resource and pointing the report's
``themeCollection.baseTheme`` (+ its ``resourcePackages`` item) at it. This is the
SAFE theme-application path: it touches only the report-level theme wiring and the
BaseTheme resource file -- never a ``visual.json``, never ``page.json`` geometry,
never a semantic-model file (ADR 0015 decision 2, the allow-list).

Companion authoring adapter (ADR 0015): it MAY write committed PBIR JSON, but only
within the allow-list, deterministically (byte-identical re-run), validated
(valid JSON + ``$schema`` preserved + round-trip stable), all-or-nothing per report.
No pbi-cli, no live Power BI, no network -- stdlib json + pathlib only. It grants no
readiness ``pass`` and emits no score (hard rule #9).
"""

from __future__ import annotations

import json
from pathlib import Path

# The report-level keys this increment is permitted to write. Anything else is out
# of the allow-list (ADR 0015 decision 2); the writer never touches another key.
_ALLOWED_REPORT_KEYS = ("themeCollection", "resourcePackages")
_BASE_THEME_SUBDIR = ("StaticResources", "SharedResources", "BaseThemes")


class PbirApplyError(Exception):
    """A theme-application input/output problem surfaced cleanly (never a traceback)."""


def _within(root: Path, target: Path) -> bool:
    """True iff ``target`` resolves inside ``root`` (no path-traversal escape)."""
    try:
        target.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _load_json(path: Path) -> object:
    try:
        with path.open(encoding="utf-8-sig") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise PbirApplyError(
            f"{path} could not be read as JSON ({exc.__class__.__name__})"
        ) from exc


def _dump(doc: object) -> str:
    """Deterministic JSON text: stable key order, 2-space indent, trailing NL."""
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def apply_theme(theme_json: Path, report_dir: Path, force: bool = False) -> list[Path]:
    """Apply ``theme_json`` to the PBIR report at ``report_dir``.

    Writes the theme as a BaseTheme resource and repoints the report's
    themeCollection + resourcePackages at it. All-or-nothing: staged in memory,
    validated, then written; on any validation failure nothing is written.
    Returns the written paths. Raises PbirApplyError on bad input, a traversal
    escape, an existing different base theme without ``force``, or invalid output.
    """
    theme_json = Path(theme_json)
    report_dir = Path(report_dir)
    repo_hint = report_dir.resolve()
    # Path guards: the theme file must exist; the report dir must be a directory;
    # the resource we write must stay under the report dir.
    if not theme_json.is_file():
        raise PbirApplyError(f"theme file not found: {theme_json}")
    if not report_dir.is_dir():
        raise PbirApplyError(f"report dir not found: {report_dir}")

    theme = _load_json(theme_json)
    if not isinstance(theme, dict) or not isinstance(theme.get("name"), str):
        raise PbirApplyError(
            "theme JSON must be an object with a string 'name' (a theme-gen theme)"
        )
    theme_name = theme["name"]
    if "/" in theme_name or "\\" in theme_name or ".." in theme_name:
        raise PbirApplyError(f"theme name is not a safe slug: {theme_name!r}")

    report_json_path = report_dir / "definition" / "report.json"
    if not report_json_path.is_file():
        raise PbirApplyError(f"report.json not found under {report_dir}")
    report = _load_json(report_json_path)
    if not isinstance(report, dict):
        raise PbirApplyError("report.json is not a JSON object")
    schema = report.get("$schema")

    resource_rel = f"BaseThemes/{theme_name}.json"
    base_theme_path = report_dir.joinpath(*_BASE_THEME_SUBDIR, f"{theme_name}.json")
    if not _within(repo_hint, base_theme_path):
        raise PbirApplyError("resolved BaseTheme path escapes the report dir")

    # Refuse to overwrite an EXISTING DIFFERENT base theme file without force.
    if base_theme_path.exists() and not force:
        existing = _load_json(base_theme_path)
        if existing != theme:
            raise PbirApplyError(
                f"{base_theme_path} exists with different content -- "
                f"refusing to overwrite (use force=True)"
            )

    # --- stage the report edit in memory (allow-list keys only) ---
    staged = dict(report)
    staged["themeCollection"] = {
        "baseTheme": {"name": theme_name, "type": "SharedResources"}
    }
    packages = [
        p
        for p in staged.get("resourcePackages", [])
        if isinstance(p, dict) and p.get("name") != "SharedResources"
    ]
    packages.append(
        {
            "name": "SharedResources",
            "type": "SharedResources",
            "items": [
                {
                    "name": theme_name,
                    "path": resource_rel,
                    "type": "BaseTheme",
                }
            ],
        }
    )
    staged["resourcePackages"] = packages

    # --- validate the staged output BEFORE writing anything ---
    if schema is not None and staged.get("$schema") != schema:
        raise PbirApplyError("staged report.json would lose its $schema")
    staged_text = _dump(staged)
    # round-trip stability: re-parse + re-dump must be identical.
    if _dump(json.loads(staged_text)) != staged_text:
        raise PbirApplyError("staged report.json is not round-trip stable")
    theme_text = _dump(theme)

    # --- commit (write both files) ---
    base_theme_path.parent.mkdir(parents=True, exist_ok=True)
    base_theme_path.write_text(theme_text, encoding="utf-8", newline="\n")
    report_json_path.write_text(staged_text, encoding="utf-8", newline="\n")
    return [base_theme_path, report_json_path]


def pbir_apply_main(args) -> int:
    """CLI entry: apply a theme to a report dir; exit 2 on a clean error."""
    import sys

    try:
        written = apply_theme(Path(args.theme), Path(args.report), force=args.force)
    except PbirApplyError as exc:
        print(f"pbir-apply-theme: {exc}", file=sys.stderr)
        return 2
    for p in written:
        print(f"wrote {p}")
    print(
        "note: applying a theme restyles the report's palette/fonts; it does NOT "
        "build visuals or grant a readiness pass (a human design-review does)."
    )
    return 0
