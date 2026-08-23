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
from .yaml_tree import first_value, load, strings_for

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

# The authority, then the two other declaring surfaces, each as (path, key).
_AUTHORITY = ("design/grids/16x9-grid.yaml", "zones")
_DECLARERS = (
    ("design/grids/mobile-grid.yaml", "safe_zones"),
    ("templates/dashboard-page-blueprint.yaml", "sections"),
)
# Filled instances live here. A positive root, not a placeholder filter.
_INSTANCE_ROOTS = ("reports/blueprints/", "reports/backgrounds/")
# The keys a list-shaped declaration may use to name its section.
_NAME_KEYS = ("band", "section", "name")


def _names(declaration: Any) -> set[str]:
    """Section names out of any of the three committed shapes.

    A mapping contributes its keys; a list contributes each item's ``band`` (or a
    bare string). Anything else contributes nothing rather than guessing.
    """
    if isinstance(declaration, dict):
        return {str(key) for key in declaration}
    if not isinstance(declaration, list):
        return set()
    bare = {item.strip() for item in declaration if isinstance(item, str)}
    return bare | set(strings_for(declaration, *_NAME_KEYS))


def _declared(repo_root: Path, suffix: str, key: str) -> set[str]:
    path = repo_root / suffix
    if not path.is_file():
        return set()
    return _names(first_value(load(path), key))


def canonical_sections(repo_root: Path) -> set[str]:
    """The authoritative vocabulary: ``zones`` in the desktop grid."""
    return _declared(repo_root, *_AUTHORITY)


def _disagreement(declared: set[str], canon: set[str]) -> str:
    """How ``declared`` differs from the authority, or "" if it does not."""
    parts = []
    extra = sorted(declared - canon)
    missing = sorted(canon - declared)
    if extra:
        parts.append(f"declares {', '.join(extra)} which {_AUTHORITY[0]} does not")
    if missing:
        parts.append(f"omits {', '.join(missing)}")
    return "; ".join(parts)


def _parity_findings(repo_root: Path, canon: set[str]) -> Iterable[Finding]:
    for suffix, key in _DECLARERS:
        declared = _declared(repo_root, suffix, key)
        # An absent or empty surface is a coverage gap the census reports, not drift.
        detail = _disagreement(declared, canon) if declared else ""
        if detail:
            yield Finding(
                rule_id=RULE_ID,
                severity=Severity.ERROR,
                message=f"section vocabulary disagrees with {_AUTHORITY[0]}: {detail}",
                locator=suffix,
            )


def _instance_files(ctx: RuleContext) -> Iterable[str]:
    return (
        rel
        for rel in ctx.tracked_files
        if rel.startswith(_INSTANCE_ROOTS)
        and rel.endswith((".yaml", ".yml"))
        and not is_test_path(rel)
    )


def _instance_findings(ctx: RuleContext, canon: set[str]) -> Iterable[Finding]:
    for rel in _instance_files(ctx):
        used = set(strings_for(load(ctx.repo_root / rel), "section"))
        for value in sorted(used - canon):
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
