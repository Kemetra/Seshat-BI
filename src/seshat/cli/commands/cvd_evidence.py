"""`seshat cvd-evidence` handler for read-only CVD simulation evidence.

Composes the evidence for ONE committed theme and writes a single companion file
next to the theme (``themes/<name>.cvd-simulation-evidence.md``) unless ``--out``
redirects it -- there is no deterministic theme -> table resolution, because one
theme can back many tables, so the default is theme-adjacent rather than
per-table. ``--format json`` prints the machine shape instead of writing.

Always exits 0: this is an evidence aid, not a gate. It ticks no checkbox, sets
no theme value, and touches no readiness-status.yaml.
"""

from __future__ import annotations

import argparse
from pathlib import Path

_SUFFIX = ".cvd-simulation-evidence.md"


def _default_out(repo_root: Path, theme_path: Path) -> Path:
    """Theme-adjacent companion path, derived from the theme's own filename."""
    resolved = theme_path if theme_path.is_absolute() else repo_root / theme_path
    stem = theme_path.name
    for ending in (".theme.json", ".json"):
        if stem.endswith(ending):
            stem = stem[: -len(ending)]
            break
    return resolved.parent / f"{stem}{_SUFFIX}"


def cvd_evidence_main(args: argparse.Namespace) -> int:
    from seshat.cvd_evidence import compose_cvd_evidence, render

    repo_root = Path(args.repo)
    theme_path = Path(args.theme)
    evidence = compose_cvd_evidence(repo_root, theme_path)

    if getattr(args, "output_format", "text") == "json":
        print(render(evidence, "json"), end="")
        return 0

    body = render(evidence, "text")
    out = (
        Path(args.out)
        if getattr(args, "out", None)
        else _default_out(repo_root, theme_path)
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(f"wrote {out.as_posix()}")
    if evidence.get("unreadable"):
        print(f"note: {evidence['unreadable']}")
    print("note: this is measured evidence for a named human; it ticks no checkbox.")
    return 0
