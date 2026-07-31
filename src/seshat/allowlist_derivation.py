"""Derive the public knowledge allowlist from the authored capability inventory.

Spec 138 User Story 2, `contracts/ship-classification.md` obligations 6-13.

`docs/capabilities/capabilities.yaml` is the AUTHORED source of what ships;
`distribution/public-knowledge-allowlist.yaml` is GENERATED from it and stays
committed for review. Before this module the export carried a hand-written
six-name assertion, so the inventory could say a skill ships while the artifact
silently disagreed.

Two sections of the allowlist have different authorities and this module treats
them differently:

* `entries` are DERIVED here -- one row per file of every skill the inventory
  marks `ships: true`.
* `template_entries` describe bundle-native scaffolding authored under
  `distribution/bundle-templates/` (the router skill, plugin manifests, command
  wrappers). They are carried through verbatim: their source of truth is that
  tree, not the inventory, and their `template_id` values are authored names no
  derivation should invent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import yaml

INVENTORY_PATH = "docs/capabilities/capabilities.yaml"
ALLOWLIST_PATH = "distribution/public-knowledge-allowlist.yaml"
PORTABILITY_TRANSFORM = "portability-audit-v1"

# The two roots the widened O2 scope covers. Knowledge bases live in top-level
# `skills/`; the kit's own verbs and consumer capabilities live in
# `.claude/skills/`. The destination differs by root, which is why the pair is
# ordered rather than a set.
KNOWLEDGE_ROOT = "skills"
REPO_SKILL_ROOT = ".claude/skills"

_MEDIA_TYPES = {
    ".md": "text/markdown",
    ".json": "application/json",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".txt": "text/plain",
    ".sql": "text/plain",
}

_KNOWLEDGE_REVIEW_REASON = (
    "Required canonical Seshat Knowledge Base content for public agent reasoning."
)
_SKILL_REVIEW_REASON = (
    "Required Seshat kit skill content the agent loads on demand in a consumer "
    "workspace."
)


class DerivationError(RuntimeError):
    """The inventory and the tree disagree, so no allowlist can be derived.

    Obligations 10-12 are fail-closed by contract: the export must stop and name
    the offender rather than emit a narrower allowlist. There is deliberately no
    suppression mechanism -- an unclassified skill is a decision nobody has made,
    not a warning to carry forward.
    """


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _referenced_dirs(entry: dict[str, Any]) -> list[str]:
    """Directories an inventory entry owns.

    Ownership is by `references.skill`, never by the entry's own `surface`: the
    inventory groups by capability, so `retail-validate` is a `surface: cli`
    entry that still owns a compass-verb skill directory.
    """
    reference = (entry.get("references") or {}).get("skill")
    if isinstance(reference, str):
        return [reference]
    return list(reference or [])


def _inventory_entries(repo_root: Path) -> list[dict[str, Any]]:
    return _load_yaml(repo_root / INVENTORY_PATH)["capabilities"]


def _shipping_dirs(capabilities: list[dict[str, Any]]) -> dict[str, str]:
    """Directory -> owning entry id, for every entry marked `ships: true`.

    Deterministically ordered by directory name so the derived allowlist is
    byte-stable across runs (obligation 6).
    """
    owned: dict[str, str] = {}
    for entry in capabilities:
        if entry.get("ships"):
            for directory in _referenced_dirs(entry):
                owned[directory] = entry.get("id", "<unnamed entry>")
    return {name: owned[name] for name in sorted(owned)}


def _locate(repo_root: Path, directory: str) -> tuple[str, Path]:
    """Resolve a shipping directory to its root. Obligation 10."""
    for root in (KNOWLEDGE_ROOT, REPO_SKILL_ROOT):
        candidate = repo_root / root / directory
        if candidate.is_dir():
            return root, candidate
    raise DerivationError(
        f"{directory}: marked `ships: true` but resolves to no directory under "
        f"{KNOWLEDGE_ROOT}/ or {REPO_SKILL_ROOT}/"
    )


def _shippable_files(location: Path) -> list[Path]:
    """Every committed file under a skill directory, deterministically ordered."""
    return sorted(
        (path for path in location.rglob("*") if path.is_file()),
        key=lambda path: path.as_posix(),
    )


def _destination(root: str, directory: str, relative: PurePosixPath) -> str:
    """Where a source file lands in both bundles.

    Knowledge bases land under `knowledge/` and are surfaced as skills by an
    authored wrapper in `template_entries`. Kit skills land under `skills/`
    directly, because the loadable body *is* the deliverable (FR-019: every hard
    stop must still stop in a consumer workspace).
    """
    prefix = "knowledge" if root == KNOWLEDGE_ROOT else "skills"
    return f"{prefix}/{directory}/{relative}"


@dataclass(frozen=True)
class _SkillDir:
    """One shipping skill directory: which root it lives under, and where."""

    root: str
    name: str
    location: Path

    @property
    def is_knowledge_base(self) -> bool:
        return self.root == KNOWLEDGE_ROOT


def _entry_for(skill: _SkillDir, path: Path, index: int) -> dict[str, Any]:
    root, directory = skill.root, skill.name
    relative = PurePosixPath(path.relative_to(skill.location).as_posix())
    return {
        "entry_id": f"kb-{index:03d}",
        "source": f"{root}/{directory}/{relative}",
        "classification": "public_knowledge",
        "media_type": _MEDIA_TYPES.get(path.suffix.lower(), "text/plain"),
        "targets": {
            "claude": _destination(root, directory, relative),
            "codex": _destination(root, directory, relative),
        },
        "transform": "copy-normalized-v1",
        "required": True,
        "generated_notice": "manifest",
        "review_reason": (
            _KNOWLEDGE_REVIEW_REASON if root == KNOWLEDGE_ROOT else _SKILL_REVIEW_REASON
        ),
    }


def _derive_entries(repo_root: Path, shipping: dict[str, str]) -> list[dict[str, Any]]:
    """One row per file, ids assigned over the deterministic directory order."""
    entries: list[dict[str, Any]] = []
    for directory in shipping:
        root, location = _locate(repo_root, directory)
        files = _shippable_files(location)
        if not files:
            raise DerivationError(
                f"{directory}: marked `ships: true` but the directory is empty, so "
                "it would produce no bundle file"
            )
        if not (location / "SKILL.md").is_file():
            raise DerivationError(
                f"{directory}: marked `ships: true` but carries no SKILL.md, so it "
                "would produce no loadable bundle file"
            )
        skill = _SkillDir(root=root, name=directory, location=location)
        for path in files:
            entries.append(_entry_for(skill, path, len(entries) + 1))
    return entries


def _reject_uncovered(repo_root: Path, capabilities: list[dict[str, Any]]) -> None:
    """Obligation 12 -- a skill directory with no inventory entry is an error."""
    covered = {
        directory
        for entry in capabilities
        if "ships" in entry
        for directory in _referenced_dirs(entry)
    }
    on_disk = {
        path.name
        for root in (KNOWLEDGE_ROOT, REPO_SKILL_ROOT)
        if (repo_root / root).is_dir()
        for path in (repo_root / root).iterdir()
        if path.is_dir()
    }
    uncovered = sorted(on_disk - covered)
    if uncovered:
        raise DerivationError(
            "skill directories covered by no inventory entry, so their ship "
            f"decision has not been made: {', '.join(uncovered)}"
        )


def _canonical_roots(capabilities: list[dict[str, Any]]) -> list[str]:
    roots = sorted(
        directory
        for entry in capabilities
        if entry.get("ship_classification") == "knowledge-root"
        for directory in _referenced_dirs(entry)
    )
    return [f"{KNOWLEDGE_ROOT}/{name}/SKILL.md" for name in roots]


def _is_skill_source(source: str) -> bool:
    return source.startswith(f"{KNOWLEDGE_ROOT}/") or source.startswith(
        f"{REPO_SKILL_ROOT}/"
    )


def _preserved_entries(committed: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Committed entries that are NOT skill files, carried through verbatim.

    The allowlist also ships authored public knowledge that belongs to no skill
    directory -- fillable templates, a design grid, the interview handoff contract,
    the licence. The inventory classifies *skills*, so it cannot be the authority
    for these; dropping them silently removed ten files from the bundle, which the
    reviewed-entries contract test caught.
    """
    return [
        dict(entry)
        for entry in committed.get("entries", [])
        if not _is_skill_source(str(entry.get("source", "")))
    ]


def derive_allowlist(
    repo_root: Path | str,
    *,
    capabilities: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Derive the whole allowlist document from the authored inventory.

    Raises `DerivationError`, naming the offender, on any of obligations 10-12.
    `capabilities` is injectable so the fail-closed paths can be exercised
    without doctoring the committed inventory.
    """
    root = Path(repo_root)
    entries = _inventory_entries(root) if capabilities is None else capabilities
    shipping = _shipping_dirs(entries)
    for directory in shipping:
        _locate(root, directory)
    derived = _derive_entries(root, shipping)
    _reject_uncovered(root, entries)
    committed = _load_yaml(root / ALLOWLIST_PATH)
    policy = dict(committed["policy"])
    # T048 -- the gate must be declared where the allowed transforms are declared,
    # so an allowlist that omits it cannot quietly ship unaudited skill text.
    transforms = list(policy.get("transforms", []))
    if PORTABILITY_TRANSFORM not in transforms:
        transforms.append(PORTABILITY_TRANSFORM)
    policy["transforms"] = transforms
    # Derived skill entries first, then the authored non-skill entries ordered by
    # source. `entry_id` is (re)assigned over the whole ordered list so the same
    # inventory always yields the same bytes (obligation 6); every other field of a
    # preserved entry is carried through untouched (obligation 8).
    preserved = sorted(_preserved_entries(committed), key=lambda e: str(e["source"]))
    all_entries = derived + preserved
    for index, entry in enumerate(all_entries, start=1):
        entry["entry_id"] = f"kb-{index:03d}"
    return {
        "schema_version": committed["schema_version"],
        "canonical_repository": committed["canonical_repository"],
        "canonical_roots": _canonical_roots(entries),
        "policy": policy,
        "entries": all_entries,
        "template_entries": committed["template_entries"],
    }
