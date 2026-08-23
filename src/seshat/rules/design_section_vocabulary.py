"""Design-lint rule DL10: one page-section vocabulary across the design surfaces.

Four committed surfaces name page sections, in three different shapes:

* ``design/grids/16x9-grid.yaml`` -- ``zones``, a mapping. THE AUTHORITY.
* ``design/grids/mobile-grid.yaml`` -- ``safe_zones``, a LIST of ``{band: ...}``.
* ``templates/dashboard-page-blueprint.yaml`` -- ``sections``, a mapping.
* filled blueprints under ``reports/blueprints/`` -- ``section:`` on each visual.

The blueprint template states its seven keys are what a visual's ``position.section``
MUST name, so a key added to one surface and not the others splits the vocabulary the
whole design layer routes on. Nothing enforced that agreement.

DL10 checks BOTH halves, because they fail differently:

* PARITY -- the three declaring surfaces declare the same set, normalized across
  their three shapes (a mapping's keys; a list's ``band`` values).
* INSTANCES -- every ``section:`` value in a filled blueprint is in that set.
  Parity proves the contract self-consistent; only this proves the instances obey it.

Deliberately NOT covered, so the docstring does not claim more than the code does:

* ``templates/background-spec.yaml`` constrains ``static_regions[].section`` in a
  COMMENT (``header | kpi_strip | ...``), which no rule can read. Hoisting that enum
  into real YAML would edit a template the init scaffolders bundle and the sdist
  ships -- a distribution change, not a lint fix. The comment stays; filled
  background specs are validated as instances against the grid instead.
* ``templates/`` are scanned for their DECLARATION only. Their ``section:`` values
  are ``<placeholders>``, so instance validation is scoped POSITIVELY to the filled
  roots rather than by filtering angle brackets out (a negative filter would excuse
  a genuinely broken real value that happens to be bracketed).

Reads committed YAML only: no execution, no DB, no Power BI. Field names only, no
tenant or brand literal (Principle VII).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register
from ..rule_coverage import TEST_FIXTURES, any_tracked_file

SECTION_CORPUS = any_tracked_file(
    "design/grids/*",
    "templates/dashboard-page-blueprint.yaml",
    exclude=(TEST_FIXTURES,),
    note=(
        "no non-fixture section-declaring surface (design/grids/** or the page "
        "blueprint template) is tracked, so this rule compared no vocabulary and "
        "its silence is not a pass"
    ),
)

RULE_ID = "DL10"

# The authority, and the two other declaring surfaces. Each entry is
# (path suffix, key, shape) where shape says how to read section names out.
_AUTHORITY = ("design/grids/16x9-grid.yaml", "zones")
_DECLARERS = (
    ("design/grids/mobile-grid.yaml", "safe_zones"),
    ("templates/dashboard-page-blueprint.yaml", "sections"),
)
# Filled instances live here. A positive root, not a placeholder filter.
_INSTANCE_ROOTS = ("reports/blueprints/", "reports/backgrounds/")


def _load_yaml(path: Path) -> Any:
    import yaml  # lazy: keep the retail-check core stdlib-only at module scope (B1/B3)

    try:
        with path.open(encoding="utf-8-sig") as fh:
            return yaml.safe_load(fh)
    except (OSError, yaml.YAMLError):
        return None


def _find_key(node: Any, key: str) -> Any:
    """First value for ``key`` anywhere in the tree, so a nested profile is found."""
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for value in node.values():
            found = _find_key(value, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_key(item, key)
            if found is not None:
                return found
    return None


def _names(declaration: Any) -> set[str]:
    """Section names out of any of the three committed shapes.

    A mapping contributes its keys; a list contributes each item's ``band`` (or a
    bare string). Anything else contributes nothing rather than guessing.
    """
    if isinstance(declaration, dict):
        return {str(k) for k in declaration}
    if isinstance(declaration, list):
        out: set[str] = set()
        for item in declaration:
            if isinstance(item, str):
                out.add(item)
            elif isinstance(item, dict):
                name = item.get("band") or item.get("section") or item.get("name")
                if isinstance(name, str):
                    out.add(name)
        return out
    return set()


def _declared(repo_root: Path, suffix: str, key: str) -> set[str] | None:
    path = repo_root / suffix
    if not path.is_file():
        return None
    return _names(_find_key(_load_yaml(path), key))


def canonical_sections(repo_root: Path) -> set[str]:
    """The authoritative vocabulary: ``zones`` in the desktop grid."""
    return _declared(repo_root, *_AUTHORITY) or set()


def _section_values(node: Any) -> Iterable[str]:
    """Every ``section:`` string value in a document tree."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "section" and isinstance(value, str):
                yield value
            yield from _section_values(value)
    elif isinstance(node, list):
        for item in node:
            yield from _section_values(item)


def _parity_findings(repo_root: Path, canon: set[str]) -> Iterable[Finding]:
    for suffix, key in _DECLARERS:
        declared = _declared(repo_root, suffix, key)
        if declared is None or not declared:
            continue  # absent surface: the coverage census reports it, not an error
        extra, missing = sorted(declared - canon), sorted(canon - declared)
        if extra or missing:
            parts = []
            if extra:
                parts.append(
                    f"declares {', '.join(extra)} which {_AUTHORITY[0]} does not"
                )
            if missing:
                parts.append(f"omits {', '.join(missing)}")
            yield Finding(
                rule_id=RULE_ID,
                severity=Severity.ERROR,
                message=(
                    f"section vocabulary disagrees with {_AUTHORITY[0]}: "
                    f"{'; '.join(parts)}"
                ),
                locator=suffix,
            )


def _instance_findings(ctx: RuleContext, canon: set[str]) -> Iterable[Finding]:
    for rel in ctx.tracked_files:
        if is_test_path(rel) or not rel.startswith(_INSTANCE_ROOTS):
            continue
        if not rel.endswith((".yaml", ".yml")):
            continue
        for value in sorted(set(_section_values(_load_yaml(ctx.repo_root / rel)))):
            if value not in canon:
                yield Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"section '{value}' is not in the vocabulary declared by "
                        f"{_AUTHORITY[0]}"
                    ),
                    locator=rel,
                )


@register(
    RULE_ID,
    "Page-section vocabulary agrees across the grids, the blueprint template "
    "and filled blueprints",
    requires=(SECTION_CORPUS,),
)
def section_vocabulary(ctx: RuleContext) -> Iterable[Finding]:
    canon = canonical_sections(ctx.repo_root)
    if not canon:
        return  # no authority tracked; the corpus requirement reports the gap
    yield from _parity_findings(ctx.repo_root, canon)
    yield from _instance_findings(ctx, canon)
