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

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register
from ..rule_coverage import TEST_FIXTURES, any_tracked_file
from .yaml_tree import first_value, read, strings_for, values_for

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


@dataclass(frozen=True)
class Declaration:
    """A declaring surface's vocabulary, plus whether it could be read."""

    names: set[str]
    unreadable: bool


def _finding(locator: str, message: str) -> Finding:
    return Finding(
        rule_id=RULE_ID, severity=Severity.ERROR, message=message, locator=locator
    )


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


def _declared(repo_root: Path, suffix: str, key: str) -> Declaration:
    """What a declaring surface says, and whether it was answerable at all.

    Three outcomes, deliberately not two. An untracked surface is a coverage gap the
    census reports; a TRACKED surface that declares nothing (emptied, or its key
    removed) is real drift; an unparseable one is a file that cannot be read as
    agreement. Collapsing the first two is what let an emptied file pass parity.
    """
    path = repo_root / suffix
    document = read(path)
    if document.failed:
        return Declaration(names=set(), unreadable=True)
    return Declaration(names=_names(first_value(document.data, key)), unreadable=False)


def authority_declarations(repo_root: Path) -> list[set[str]]:
    """EVERY ``zones`` declaration in the authority, one per resolution profile.

    The desktop grid declares `zones` once per profile (1280x720 and 1920x1080).
    Reading only the first left drift in a later profile invisible, so the profiles
    are collected and compared against each other before any of them is treated as
    the vocabulary.
    """
    document = read(repo_root / _AUTHORITY[0])
    if document.failed:
        return []
    return [
        _names(block)
        for block in values_for(document.data, _AUTHORITY[1])
        if isinstance(block, (dict, list))
    ]


def canonical_sections(repo_root: Path) -> set[str]:
    """The authoritative vocabulary: ``zones`` in the desktop grid.

    The union across profiles, so a caller asking "what is the vocabulary" is never
    silently handed one profile's view. Profile DISAGREEMENT is reported separately
    by the rule; this function does not adjudicate it.
    """
    blocks = authority_declarations(repo_root)
    return set().union(*blocks) if blocks else set()


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


def _parity_findings(
    repo_root: Path, canon: set[str], tracked: frozenset[str]
) -> Iterable[Finding]:
    for suffix, key in _DECLARERS:
        # UNTRACKED is the only silent case: a partial scaffold is a coverage gap the
        # census reports. A tracked surface must answer, even to say "nothing".
        if suffix not in tracked:
            continue
        declaration = _declared(repo_root, suffix, key)
        if declaration.unreadable:
            yield _finding(
                suffix, "surface could not be parsed, so its vocabulary is unchecked"
            )
            continue
        detail = _disagreement(declaration.names, canon) or (
            f"declares no section vocabulary, while {_AUTHORITY[0]} declares "
            f"{len(canon)}"
            if not declaration.names
            else ""
        )
        if detail:
            yield _finding(
                suffix, f"section vocabulary disagrees with {_AUTHORITY[0]}: {detail}"
            )


def _instance_files(ctx: RuleContext) -> Iterable[str]:
    return (
        rel
        for rel in ctx.tracked_files
        if rel.startswith(_INSTANCE_ROOTS)
        and rel.endswith((".yaml", ".yml"))
        and not is_test_path(rel)
    )


def _named_sections(doc: Any) -> set[str]:
    """Section names from a filled ``sections`` LIST of ``{name: ...}`` entries.

    A blueprint may declare its page layout that way rather than with `section:`
    keys, so scanning only `section` left those names unvalidated. Scoped to entries
    under a `sections` collection: `name` is far too common a key to harvest
    globally, which would drag unrelated names into the vocabulary check.
    """
    names: set[str] = set()
    for collection in values_for(doc, "sections"):
        if not isinstance(collection, list):
            continue
        for entry in collection:
            if isinstance(entry, dict):
                names.update(strings_for(entry, "name"))
    return names


def _instance_findings(ctx: RuleContext, canon: set[str]) -> Iterable[Finding]:
    for rel in _instance_files(ctx):
        document = read(ctx.repo_root / rel)
        if document.failed:
            # An unexamined instance is not a compliant one. Skipping it here is the
            # fail-open Codex flagged: the census still counts DL10 as evaluated.
            yield _finding(
                rel, "file could not be parsed, so its sections are unchecked"
            )
            continue
        used = set(strings_for(document.data, "section")) | _named_sections(
            document.data
        )
        for value in sorted(used - canon):
            yield _finding(
                rel,
                f"section '{value}' is not in the vocabulary declared by "
                f"{_AUTHORITY[0]}",
            )


@register(
    RULE_ID,
    "Page-section vocabulary agrees across the grids, the blueprint template "
    "and filled blueprints",
    requires=(SECTION_CORPUS,),
)
def section_vocabulary(ctx: RuleContext) -> Iterable[Finding]:
    tracked = frozenset(rel.replace("\\", "/") for rel in ctx.tracked_files)
    authority_path, authority_key = _AUTHORITY
    if authority_path not in tracked:
        # The any-of corpus is satisfied by a DIFFERENT file than the one missing, so
        # it cannot cover this: with a secondary declarer tracked, a silent return
        # reports "clean" for a repo that has no authoritative vocabulary at all.
        # Only a repo declaring NOTHING is the census's business.
        if any(suffix in tracked for suffix, _ in _DECLARERS):
            yield _finding(
                authority_path,
                "the authoritative section declaration is not tracked, so the "
                "vocabulary the other surfaces are compared against is missing",
            )
        return
    profiles = authority_declarations(ctx.repo_root)
    if len(profiles) > 1:
        # Each profile describes the SAME grid, so they must agree with each other
        # before any of them can serve as the authority.
        for index, block in enumerate(profiles[1:], start=1):
            detail = _disagreement(block, profiles[0])
            if detail:
                yield _finding(
                    authority_path,
                    f"authority profile {index} disagrees with the first: {detail}",
                )
    authority = _declared(ctx.repo_root, authority_path, authority_key)
    if authority.unreadable or not authority.names:
        # A TRACKED authority that cannot be read, or declares nothing, must not end
        # the rule in silence: the any-of corpus is still satisfied by the other
        # surfaces, so the census would report DL10 as evaluated either way.
        reason = (
            "could not be parsed"
            if authority.unreadable
            else "declares no section vocabulary"
        )
        yield _finding(
            authority_path,
            f"the authoritative section declaration {reason}, so no vocabulary "
            "could be compared",
        )
        return
    canon = authority.names
    yield from _parity_findings(ctx.repo_root, canon, tracked)
    yield from _instance_findings(ctx, canon)
