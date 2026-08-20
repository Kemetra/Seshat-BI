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
    declined: bool = False

    @property
    def needs_action(self) -> bool:
        """Outstanding work: needed, not satisfied, and not declined away.

        A declined capability is NOT outstanding -- that is the point of recording
        the decline (FR-009). A declined REQUIRED capability is still a blocker,
        which `SetupPlan.blocked` reports separately; it is simply not proposed
        again as if newly discovered.
        """
        return (
            self.strength in {"required", "recommended"}
            and not self.satisfied
            and not self.declined
        )


@dataclass(frozen=True)
class SetupPlan:
    rows: tuple[SetupPlanRow, ...]

    @property
    def needs_setup(self) -> int:
        return sum(1 for row in self.rows if row.needs_action)

    @property
    def blockers(self) -> tuple[str, ...]:
        return tuple(row.blocker for row in self.rows if row.blocker)

    @property
    def blocked(self) -> bool:
        """True when the project cannot be represented as set up (FR-010)."""
        return bool(self.blockers)


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


# A decline is a human choice about project SCOPE, so it lives in committed text
# for the same reason a provisioning approval does (#671): a decline supplied at
# runtime would let the caller silently suppress a capability the project
# demonstrably needs.
CAPABILITY_DECLINES_RELPATH = "contracts/capability-declines.yaml"


def _declined_ids(root: Path) -> frozenset[str]:
    """Capability ids a human has declined, from committed text.

    Fails CLOSED in the safe direction: an absent, unreadable, or malformed file
    declines NOTHING. Failing open would suppress every capability the project
    needs while rendering a clean-looking plan.
    """
    path = root / CAPABILITY_DECLINES_RELPATH
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return frozenset()

    import yaml  # lazy: keeps module import dependency-light

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return frozenset()
    if not isinstance(data, dict):
        return frozenset()
    rows = data.get("declines")
    if not isinstance(rows, list):
        return frozenset()
    return frozenset(
        str(row["capability"])
        for row in rows
        if isinstance(row, dict) and row.get("capability")
    )


def _apply_decline(row: SetupPlanRow) -> SetupPlanRow:
    """Mark a row declined, and raise a blocker if it was REQUIRED.

    The strength is NOT downgraded. Relabelling a required capability `optional`
    to silence the blocker would make the plan self-consistent and wrong: the
    strength comes from project evidence, and a human declining it does not change
    the evidence (FR-010).
    """
    blocker = None
    if row.strength == "required":
        blocker = (
            f"{row.capability.name} is required by this project "
            f"({row.reason}) but has been declined in "
            f"{CAPABILITY_DECLINES_RELPATH}; remove the decline or change the "
            "project so the capability is no longer needed"
        )
    return SetupPlanRow(
        capability=row.capability,
        strength=row.strength,
        reason=row.reason,
        satisfied=row.satisfied,
        undetermined_evidence=row.undetermined_evidence,
        blocker=blocker,
        declined=True,
    )


def derive(root: Path) -> SetupPlan:
    """The capabilities this project needs, from its committed evidence.

    Reads only. No network, no database, no writes -- so it works on a checkout
    with no optional provider installed, and the same evidence always yields the
    same plan.
    """
    root = Path(root)
    declined = _declined_ids(root)
    rows = (
        _database_connectivity(root),
        _powerbi_integration(root),
        _transformation_engine(root),
        _orchestration(root),
    )
    resolved = []
    for row in rows:
        components = CAPABILITY_COMPONENTS.get(row.capability.id, ())
        satisfied = bool(components) and all(
            _component_present(root, cid) for cid in components
        )
        if satisfied:
            row = SetupPlanRow(
                capability=row.capability,
                strength=row.strength,
                reason=row.reason,
                satisfied=True,
                undetermined_evidence=row.undetermined_evidence,
                blocker=row.blocker,
                declined=row.declined,
            )
        if row.capability.id in declined:
            row = _apply_decline(row)
        resolved.append(row)
    return SetupPlan(rows=tuple(resolved))


# Which catalog components satisfy each capability. The IDS are the catalog's,
# verified against `PROFILES` by test -- this is a mapping, not a second registry
# (FR-011): it adds no component, no version, and no coordinate of its own. A
# catalog entry added to one of these profiles reaches the technical detail with no
# change to the user-facing journey (FR-020).
CAPABILITY_COMPONENTS: dict[str, tuple[str, ...]] = {
    DATABASE_CONNECTIVITY.id: ("connectorx",),
    POWERBI_INTEGRATION.id: ("powerbi-modeling-mcp", "fabric-skills"),
    TRANSFORMATION_ENGINE.id: ("dbt-core", "dbt-postgres"),
    ORCHESTRATION.id: ("dagster", "seshat-dagster-adapter"),
}


@dataclass(frozen=True)
class ProviderDetail:
    """One official component that satisfies a capability. Catalog-sourced."""

    component_id: str
    channel: str
    role: str
    verification_basis: str


@dataclass(frozen=True)
class CapabilityDetail:
    """The technical evidence behind one capability -- on request only (FR-013)."""

    capability_id: str
    providers: tuple[ProviderDetail, ...]
    selected: str = ""
    selection_basis: str = ""


def _component_present(root: Path, component_id: str) -> bool:
    """Whether the discovery surface reports this component installed.

    Routed through `installed_ref` rather than an install RESULT: a successful
    install is not evidence of readiness (FR-019). Seam kept small so a test can
    substitute it.
    """
    from seshat.integrations.discovery import installed_ref

    try:
        return installed_ref(root, component_id) is not None
    except Exception:
        return False


def technical_detail(plan: SetupPlan) -> tuple[CapabilityDetail, ...]:
    """Provider identity, version state and verification basis, per capability.

    Every field is read from the integration catalog; nothing is restated here.
    This is the ADVANCED path -- the normal rendering never shows it (FR-012).
    """
    from seshat.integrations.catalog import PROFILES

    known = {c.id: c for rows in PROFILES.values() for c in rows}
    details: list[CapabilityDetail] = []
    for row in plan.rows:
        component_ids = CAPABILITY_COMPONENTS.get(row.capability.id, ())
        providers = tuple(
            ProviderDetail(
                component_id=cid,
                channel=known[cid].channel,
                role=known[cid].role,
                verification_basis=(
                    "required payload paths declared in the catalog"
                    if known[cid].required_paths
                    else "package metadata or MCP registration"
                ),
            )
            for cid in component_ids
            if cid in known
        )
        selected = providers[0].component_id if providers else ""
        details.append(
            CapabilityDetail(
                capability_id=row.capability.id,
                providers=providers,
                selected=selected,
                selection_basis=(
                    "first catalog-declared provider for this capability"
                    if len(providers) > 1
                    else ""
                ),
            )
        )
    return tuple(details)


def render_json(plan: SetupPlan) -> str:
    """Machine-readable status for an agent (FR-015).

    Carries strength, satisfaction, the reason, and any blocker or undetermined
    marker -- enough to answer what is needed, what is satisfied, what is missing,
    why something is recommended, and the next safe action, WITHOUT exposing
    provider internals. Provider detail is `technical_detail`, on request.
    """
    import json

    payload = {
        "needs_setup": plan.needs_setup,
        "blocked": plan.blocked,
        "blockers": list(plan.blockers),
        "capabilities": [
            {
                "id": row.capability.id,
                "name": row.capability.name,
                "strength": row.strength,
                "reason": row.reason,
                "satisfied": row.satisfied,
                "declined": row.declined,
                "undetermined_evidence": row.undetermined_evidence,
                "blocker": row.blocker,
            }
            for row in plan.rows
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def requested_outside_need(
    plan: SetupPlan, requested: tuple[str, ...]
) -> tuple[str, ...]:
    """Requested capability ids the project does not actually need (FR-006).

    Reported, never promoted: asking for a capability does not make it required.
    """
    needed = {
        row.capability.id
        for row in plan.rows
        if row.strength in {"required", "recommended"}
    }
    return tuple(cap for cap in requested if cap not in needed)


_MARK = {
    "required": "o",
    "recommended": "o",
    "optional": "-",
    "not-required": "-",
}


def _status_line(row: SetupPlanRow, width: int) -> str:
    """One aligned status row: mark, capability name, readiness label."""
    mark = "+" if row.satisfied else _MARK[row.strength]
    label = "Ready" if row.satisfied else row.strength.replace("-", " ").title()
    return f"  {mark} {row.capability.name:<{width}}  {label}"


def _reason_lines(row: SetupPlanRow) -> list[str]:
    """The reason for one capability, plus its undetermined-evidence note."""
    lines = [f"  {row.capability.name}: {row.reason}"]
    if row.undetermined_evidence:
        lines.append(f"    undetermined -- needs {row.undetermined_evidence}")
    return lines


def render_text(plan: SetupPlan) -> str:
    """The normal presentation: capability names and reasons, no package names.

    Deliberately ASCII (the Windows console charmap codec cannot encode the
    tick/cross glyphs the spec's illustration uses).
    """
    lines = ["Project Setup", ""]
    width = max(len(row.capability.name) for row in plan.rows)
    for row in plan.rows:
        lines.append(_status_line(row, width))
    lines.append("")
    for row in plan.rows:
        lines.extend(_reason_lines(row))
    lines.append("")
    count = plan.needs_setup
    lines.append(
        f"{count} capabilit{'y' if count == 1 else 'ies'} require setup."
        if count
        else "No capabilities require setup."
    )
    return "\n".join(lines)
