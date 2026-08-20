"""Project-derived capability selection (spec 153).

The shipped setup journey selects work by curated PROFILE, and its default
profile is the union of every profile -- a fixed bundle for every user. Nothing
inspected the project to decide what it actually needed, and no field said how
strongly a capability was needed.

This module answers both questions from COMMITTED evidence, and nothing else. It
does not install, resolve a version, verify, write a lock, or decide an approval:
those belong to the integration control plane (spec 144), the discovery surface
(spec 148), and the provisioning approval gate (issue #671) respectively.

Two design points worth stating, because both are easy to get wrong:

**Absence is evidence.** "No ``dbt_project.yml`` is committed" is a finding with a
citable basis, not silence -- the check is a deterministic query over committed
state. So a capability the project is not using reports ``not-required``, not
``undetermined``. Collapsing the two would make ``not-required`` unreachable.

**``undetermined`` is not a fifth strength.** It is a separate marker for evidence
that is contradictory or unreadable. The strength vocabulary stays at exactly four
values, so a caller can never be handed a strength that means "we did not know".
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Exactly four. `undetermined` is deliberately NOT here -- see the module docstring.
STRENGTHS: tuple[str, ...] = ("required", "recommended", "optional", "not-required")


@dataclass(frozen=True)
class Capability:
    """A provider-independent ability, named for a human rather than a package."""

    id: str
    name: str


@dataclass(frozen=True)
class SetupPlanRow:
    """One capability's derived need, with the evidence that produced it."""

    capability: Capability
    strength: str
    reason: str
    satisfied: bool = False
    undetermined_evidence: str | None = None
    blocker: str | None = None


@dataclass(frozen=True)
class SetupPlan:
    rows: tuple[SetupPlanRow, ...]

    @property
    def needs_setup(self) -> int:
        return sum(
            1
            for row in self.rows
            if row.strength in {"required", "recommended"} and not row.satisfied
        )


DATABASE_CONNECTIVITY = Capability("database-connectivity", "Database Connectivity")
POWERBI_INTEGRATION = Capability("powerbi-integration", "Power BI Integration")
TRANSFORMATION_ENGINE = Capability("transformation-engine", "Transformation Engine")
ORCHESTRATION = Capability("orchestration", "Orchestration")


def _source_maps(root: Path) -> list[Path]:
    mappings = root / "mappings"
    if not mappings.is_dir():
        return []
    return sorted(mappings.glob("*/source-map.yaml"))


def _declares_a_source(path: Path) -> bool | None:
    """True/False if decidable, None when the artifact cannot be read.

    None is what becomes ``undetermined``: an artifact that exists but will not
    parse is contradictory evidence, not an absence.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    import yaml  # lazy: keeps module import dependency-light

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    # Two shapes exist in committed source-maps, found by running this against the
    # repository rather than against fixtures: retail_store_sales nests the
    # declaration under `meta.source_system`, while demo_sample_orders declares
    # `source_id`/`source_kind` at the top level. Reading only the nested form
    # reported a perfectly readable file as unparseable -- a false `undetermined`
    # on real data. A missing declaration in a file that PARSES is an absence
    # (decidable), not unreadable evidence.
    meta = data.get("meta")
    if isinstance(meta, dict) and meta.get("source_system"):
        return True
    return bool(data.get("source_id") or data.get("source_kind"))


def _database_connectivity(root: Path) -> SetupPlanRow:
    maps = _source_maps(root)
    if not maps:
        return SetupPlanRow(
            DATABASE_CONNECTIVITY,
            "not-required",
            "no source-map.yaml declares a source system under mappings/",
        )
    for path in maps:
        verdict = _declares_a_source(path)
        rel = path.relative_to(root).as_posix()
        if verdict is None:
            return SetupPlanRow(
                DATABASE_CONNECTIVITY,
                "optional",
                f"{rel} exists but could not be read as a source declaration",
                undetermined_evidence=(
                    f"a readable source-map at {rel} -- it exists but does not "
                    "parse, so the source system cannot be confirmed"
                ),
            )
        if verdict:
            return SetupPlanRow(
                DATABASE_CONNECTIVITY,
                "required",
                f"a relational source is declared in {rel}",
            )
    return SetupPlanRow(
        DATABASE_CONNECTIVITY,
        "not-required",
        "a source-map exists but declares no source system",
    )


def _powerbi_integration(root: Path) -> SetupPlanRow:
    projects = (
        sorted((root / "powerbi").glob("*.pbip")) if (root / "powerbi").is_dir() else []
    )
    if projects:
        rel = projects[0].relative_to(root).as_posix()
        return SetupPlanRow(
            POWERBI_INTEGRATION,
            "required",
            f"a Power BI project is declared at {rel}",
        )
    return SetupPlanRow(
        POWERBI_INTEGRATION,
        "not-required",
        "no Power BI project (*.pbip) is committed",
    )


# The artifacts consulted are named by ROLE in user-facing reasons, never by the
# provider they belong to. A path like `orchestration/dagster/` contains a catalog
# coordinate (`dagster`), and echoing it into the normal presentation would leak a
# package name into the capability-oriented view (FR-012). The literal paths stay
# in code, where the evidence layer can still surface them on request (FR-013).
_TRANSFORMATION_MANIFEST = "dbt_project.yml"
_ORCHESTRATION_DIR = ("orchestration", "dagster")


def _transformation_engine(root: Path) -> SetupPlanRow:
    found = sorted(root.glob(f"*/{_TRANSFORMATION_MANIFEST}")) + sorted(
        root.glob(_TRANSFORMATION_MANIFEST)
    )
    if found:
        parent = found[0].parent.relative_to(root).as_posix() or "the project root"
        return SetupPlanRow(
            TRANSFORMATION_ENGINE,
            "required",
            f"a transformation project is declared under {parent}",
        )
    return SetupPlanRow(
        TRANSFORMATION_ENGINE,
        "not-required",
        "no transformation project manifest is committed, so no transformation "
        "work is declared",
    )


def _orchestration(root: Path) -> SetupPlanRow:
    project = root.joinpath(*_ORCHESTRATION_DIR)
    if project.is_dir() and any(project.iterdir()):
        return SetupPlanRow(
            ORCHESTRATION,
            "required",
            f"an orchestration project is declared under {_ORCHESTRATION_DIR[0]}/",
        )
    return SetupPlanRow(
        ORCHESTRATION,
        "not-required",
        f"no orchestration project is committed under {_ORCHESTRATION_DIR[0]}/",
    )


def derive(root: Path) -> SetupPlan:
    """The capabilities this project needs, from its committed evidence.

    Reads only. No network, no database, no writes -- so it works on a checkout
    with no optional provider installed, and the same evidence always yields the
    same plan.
    """
    root = Path(root)
    return SetupPlan(
        rows=(
            _database_connectivity(root),
            _powerbi_integration(root),
            _transformation_engine(root),
            _orchestration(root),
        )
    )


_MARK = {
    "required": "o",
    "recommended": "o",
    "optional": "-",
    "not-required": "-",
}


def render_text(plan: SetupPlan) -> str:
    """The normal presentation: capability names and reasons, no package names.

    Deliberately ASCII (the Windows console charmap codec cannot encode the
    tick/cross glyphs the spec's illustration uses).
    """
    lines = ["Project Setup", ""]
    width = max(len(row.capability.name) for row in plan.rows)
    for row in plan.rows:
        mark = "+" if row.satisfied else _MARK[row.strength]
        label = "Ready" if row.satisfied else row.strength.replace("-", " ").title()
        lines.append(f"  {mark} {row.capability.name:<{width}}  {label}")
    lines.append("")
    for row in plan.rows:
        lines.append(f"  {row.capability.name}: {row.reason}")
        if row.undetermined_evidence:
            lines.append(f"    undetermined -- needs {row.undetermined_evidence}")
    lines.append("")
    count = plan.needs_setup
    lines.append(
        f"{count} capabilit{'y' if count == 1 else 'ies'} require setup."
        if count
        else "No capabilities require setup."
    )
    return "\n".join(lines)
