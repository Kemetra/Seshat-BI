"""Design-lint rule DL5: grid arithmetic-closure self-check (A7).

For each committed layout-grid profile that declares a column/row grid, DL5
recomputes whether the grid arithmetic CLOSES:

    usable_width  = canvas.width  - margin.left - margin.right
                  == columns * column_width + (columns - 1) * gutter
    usable_height = canvas.height - margin.top  - margin.bottom
                  == rows    * row_height    + (rows    - 1) * gutter

A profile whose recomputed usable dimension does not equal the grid-derived
dimension is an ERROR (the grid does not close). If the profile also declares an
``arithmetic_check`` block with ``width_closes`` / ``height_closes`` booleans,
DL5 cross-checks those against the recomputation and ERRORs on a declared-vs-
actual contradiction (a stale hand-maintained check).

Grounded in the grid file's OWN declared geometry (Principle V): DL5 invents no
numbers -- it recomputes from committed fields and compares. A band-stack grid
with no ``column_width`` (a mobile portrait stack) has no closure to check and
is skipped. Pure stdlib arithmetic on committed YAML; no execution, no DB, no
Power BI. Generic: field names only, no tenant/brand literal (Principle VII).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "DL5"

# Grid files are discovered generically under the design grids directory or by a
# ``*grid.yaml`` basename (never an enumerated tenant list -- Principle VII).
_GRID_DIR = "design/grids/"
_GRID_SUFFIX = "grid.yaml"


def _iter_grid_files(ctx: RuleContext) -> list[str]:
    out = []
    for p in ctx.tracked_files:
        if is_test_path(p):
            continue
        base = p.rsplit("/", 1)[-1]
        if p.startswith(_GRID_DIR) or base.endswith(_GRID_SUFFIX):
            out.append(p)
    return out


def _load_yaml(path: Path) -> tuple[Any, str | None]:
    import yaml  # lazy: keep the retail-check core stdlib-only at module scope (B1/B3)

    try:
        with path.open(encoding="utf-8-sig") as fh:
            return yaml.safe_load(fh), None
    except (OSError, yaml.YAMLError) as exc:
        return None, exc.__class__.__name__


def _num(node: Any, *keys: str) -> float | None:
    """Descend ``node`` by ``keys``; return the leaf if it is a number, else None."""
    cur = node
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur if isinstance(cur, (int, float)) and not isinstance(cur, bool) else None


def _check_profile(rel: str, pname: str, prof: Any) -> Iterable[Finding]:
    """Closure check for one profile mapping (canvas/margin/grid), if present."""
    if not isinstance(prof, dict):
        return
    grid = prof.get("grid")
    # No column/row grid with a column_width -> nothing to close (band-stack).
    if not isinstance(grid, dict) or _num(grid, "column_width") is None:
        return

    cw = _num(grid, "column_width")
    rh = _num(grid, "row_height")
    cols = _num(grid, "columns")
    rows = _num(grid, "rows")
    gutter = _num(grid, "gutter")
    width = _num(prof, "canvas", "width")
    height = _num(prof, "canvas", "height")
    ml = _num(prof, "margin", "left")
    mr = _num(prof, "margin", "right")
    mt = _num(prof, "margin", "top")
    mb = _num(prof, "margin", "bottom")

    needed = [cw, rh, cols, rows, gutter, width, height, ml, mr, mt, mb]
    if any(v is None for v in needed):
        yield Finding(
            RULE_ID,
            Severity.ERROR,
            f"grid profile {pname!r} declares a column/row grid but is missing a "
            f"field needed to check closure (canvas/margin/grid columns, rows, "
            f"gutter, column_width, row_height)",
            f"{rel}#profiles/{pname}",
        )
        return

    loc = f"{rel}#profiles/{pname}"
    check = prof.get("arithmetic_check")
    declared = check if isinstance(check, dict) else {}

    usable_w = width - ml - mr
    grid_w = cols * cw + (cols - 1) * gutter
    width_closes = usable_w == grid_w
    if not width_closes:
        yield Finding(
            RULE_ID,
            Severity.ERROR,
            f"grid profile {pname!r} width does not close: usable width "
            f"{usable_w:g} (canvas - margins) != grid width {grid_w:g} "
            f"(columns*column_width + (columns-1)*gutter)",
            loc,
        )
    if declared.get("width_closes") is True and not width_closes:
        yield Finding(
            RULE_ID,
            Severity.ERROR,
            f"grid profile {pname!r} declares arithmetic_check.width_closes: true "
            f"but the geometry does not close ({usable_w:g} != {grid_w:g}); the "
            f"declared check is stale",
            f"{loc}/arithmetic_check",
        )

    usable_h = height - mt - mb
    grid_h = rows * rh + (rows - 1) * gutter
    height_closes = usable_h == grid_h
    if not height_closes:
        yield Finding(
            RULE_ID,
            Severity.ERROR,
            f"grid profile {pname!r} height does not close: usable height "
            f"{usable_h:g} (canvas - margins) != grid height {grid_h:g} "
            f"(rows*row_height + (rows-1)*gutter)",
            loc,
        )
    if declared.get("height_closes") is True and not height_closes:
        yield Finding(
            RULE_ID,
            Severity.ERROR,
            f"grid profile {pname!r} declares arithmetic_check.height_closes: "
            f"true but the geometry does not close ({usable_h:g} != {grid_h:g}); "
            f"the declared check is stale",
            f"{loc}/arithmetic_check",
        )


@register(
    RULE_ID,
    "A layout grid's column/row arithmetic closes against its canvas and margins",
)
def check_grid_closure(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in sorted(_iter_grid_files(ctx)):
        doc, err = _load_yaml(ctx.repo_root / rel)
        if err is not None:
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"grid file could not be parsed ({err}); closure cannot be "
                    f"verified",
                    f"{rel}#/",
                )
            )
            continue
        if not isinstance(doc, dict):
            continue
        profiles = doc.get("profiles")
        if isinstance(profiles, dict):
            for pname, prof in profiles.items():
                findings.extend(_check_profile(rel, str(pname), prof))
        else:
            # A single top-level grid (no profiles wrapper): treat the doc itself
            # as one profile named for its grid_id (or "default").
            name = str(doc.get("grid_id", "default"))
            findings.extend(_check_profile(rel, name, doc))
    return findings
