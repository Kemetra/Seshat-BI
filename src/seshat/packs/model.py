"""Immutable extension-pack and selection models (spec 120, US5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CATEGORIES = (
    "kpi",
    "source_vocabulary",
    "warehouse_compatibility",
    "regional_policy",
    "accessibility",
    "dashboard_blueprint",
)


class PackError(ValueError):
    """A pack manifest cannot be read or interpreted safely."""


@dataclass(frozen=True)
class PackSpec:
    """Author-supplied identity for a scaffolded pack."""

    pack_id: str
    category: str
    owner: str


@dataclass(frozen=True)
class PackArtifact:
    """One declared content artifact, path relative to the pack directory."""

    path: str
    purpose: str


@dataclass(frozen=True)
class PackManifest:
    """One parsed, schema-valid pack manifest. Frozen: a manifest is a fact
    about a committed file, never mutable runtime state."""

    manifest_path: str  # repo-relative POSIX path of seshat-pack.yaml
    pack_id: str
    version: str
    category: str
    owner: str
    description: str
    core_compatibility: str
    provides: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    artifacts: tuple[PackArtifact, ...] = ()
    human_decisions: tuple[str, ...] = ()
    fixtures: tuple[str, ...] = ()
    verification: tuple[str, ...] = ()
    non_goals: tuple[str, ...] = ()

    @property
    def directory(self) -> str:
        """Repo-relative directory that owns this pack's artifacts/fixtures."""
        return self.manifest_path.rsplit("/", 1)[0] if "/" in self.manifest_path else ""

    def qualified_provides(self) -> tuple[str, ...]:
        """Every provided ID, fully qualified as ``<pack_id>:<local_id>``."""
        return tuple(f"{self.pack_id}:{local}" for local in self.provides)


@dataclass(frozen=True)
class PackSelection:
    """An explicit, ordered set of packs offered to one projection.

    Packs have no activation lifecycle: constructing a selection installs
    nothing and persists nothing.
    """

    packs: tuple[PackManifest, ...] = field(default_factory=tuple)

    def by_id(self) -> dict[str, PackManifest]:
        return {pack.pack_id: pack for pack in self.packs}


def manifest_from_document(
    document: dict[str, Any], manifest_path: str
) -> PackManifest:
    """Build the frozen model from an already schema-validated document."""
    artifacts = tuple(
        PackArtifact(
            path=str(item.get("path", "")),
            purpose=str(item.get("purpose", "")),
        )
        for item in document.get("artifacts", [])
        if isinstance(item, dict)
    )
    return PackManifest(
        manifest_path=manifest_path,
        pack_id=document["pack_id"],
        version=document["version"],
        category=document["category"],
        owner=document["owner"],
        description=document["description"],
        core_compatibility=document["core_compatibility"],
        provides=tuple(document.get("provides", [])),
        requires=tuple(document.get("requires", [])),
        conflicts=tuple(document.get("conflicts", [])),
        artifacts=artifacts,
        human_decisions=tuple(document.get("human_decisions", [])),
        fixtures=tuple(document.get("fixtures", [])),
        verification=tuple(document.get("verification", [])),
        non_goals=tuple(document.get("non_goals", [])),
    )
