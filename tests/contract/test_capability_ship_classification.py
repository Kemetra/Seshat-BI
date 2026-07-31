"""The capability inventory is the single AUTHORED source of what ships.

Spec 138 User Story 2. These assertions encode `contracts/ship-classification.md`
obligations 1-5. Obligations 6-13 (deterministic derivation, generated allowlist,
fail-closed export) land with the derivation and are asserted separately.

Ownership is by `references.skill`, NOT by the entry's own `surface`. The
inventory groups by CAPABILITY, not by representation: `retail-validate` is a
`surface: cli` entry that still owns a skill directory. Asserting on
`surface == "skill"` would silently miss eight directories, one of them a
compass verb.
"""

from __future__ import annotations

import collections
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORY = REPO_ROOT / "docs/capabilities/capabilities.yaml"
KIT_SOURCE = REPO_ROOT / ".seshat/kit-source.yaml"
REPO_SKILLS = REPO_ROOT / ".claude/skills"
KNOWLEDGE_SKILLS = REPO_ROOT / "skills"

_CLASSIFICATIONS = {
    "compass-verb",
    "knowledge-root",
    "consumer-capability",
    "development-only",
}


def _load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def capabilities() -> list[dict[str, Any]]:
    return _load(INVENTORY)["capabilities"]


@pytest.fixture(scope="module")
def kit_verbs() -> set[str]:
    return {verb["id"] for verb in _load(KIT_SOURCE)["verbs"]}


@pytest.fixture(scope="module")
def skill_dirs() -> set[str]:
    """Every kit-authored skill directory, under the widened O2 scope."""
    return {p.name for p in REPO_SKILLS.iterdir() if (p / "SKILL.md").is_file()} | {
        p.name for p in KNOWLEDGE_SKILLS.iterdir() if (p / "SKILL.md").is_file()
    }


def _referenced_dirs(entry: dict[str, Any]) -> list[str]:
    """Directories an entry owns. Scalar and list forms are both valid."""
    reference = (entry.get("references") or {}).get("skill")
    if isinstance(reference, str):
        return [reference]
    return list(reference or [])


def _ship_owners(
    capabilities: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    owners: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for entry in capabilities:
        if "ships" in entry:
            for directory in _referenced_dirs(entry):
                owners[directory].append(entry)
    return owners


def test_every_referenced_skill_resolves(
    capabilities: list[dict[str, Any]], skill_dirs: set[str]
) -> None:
    """Obligation 2 -- already satisfied by `references.skill`.

    Spec 138 originally proposed a new `skill_dir` field for the four entry ids
    that match no directory. It was withdrawn: `references.skill` already
    resolves them all. This is the regression guard for that mechanism.
    """
    dangling = {
        entry["id"]: [d for d in _referenced_dirs(entry) if d not in skill_dirs]
        for entry in capabilities
        if any(d not in skill_dirs for d in _referenced_dirs(entry))
    }
    assert not dangling, f"references.skill pointing at no directory: {dangling}"


def test_every_skill_directory_has_exactly_one_ship_owner(
    capabilities: list[dict[str, Any]], skill_dirs: set[str]
) -> None:
    """Obligations 1 and 12 -- full coverage, and no duplicate authority."""
    owners = _ship_owners(capabilities)
    uncovered = sorted(skill_dirs - set(owners))
    assert not uncovered, (
        "skill directories with no ship decision -- a new skill must not slip in "
        f"unclassified: {uncovered}"
    )
    contested = {
        directory: [entry["id"] for entry in entries]
        for directory, entries in owners.items()
        if len(entries) > 1
    }
    assert not contested, f"directories with more than one ship owner: {contested}"


def test_ship_fields_are_complete_and_valid(
    capabilities: list[dict[str, Any]],
) -> None:
    """Obligations 2-3 -- `ships` has no default; classification is closed."""
    for entry in capabilities:
        if "ships" not in entry:
            assert not _referenced_dirs(entry) or "ship_classification" not in entry
            continue
        assert isinstance(entry["ships"], bool), (
            f"{entry['id']}: ships must be an explicit boolean, not {entry['ships']!r}"
        )
        assert entry.get("ship_classification") in _CLASSIFICATIONS, (
            f"{entry['id']}: ship_classification "
            f"{entry.get('ship_classification')!r} is outside the closed set"
        )


def test_classification_invariants_hold(
    capabilities: list[dict[str, Any]], kit_verbs: set[str]
) -> None:
    """Obligations 4-5 -- classification determines shipping, never a name pattern."""
    for entry in capabilities:
        if "ships" not in entry:
            continue
        classification = entry["ship_classification"]
        if classification == "development-only":
            assert entry["ships"] is False, (
                f"{entry['id']}: development-only capabilities must not ship"
            )
        if classification == "compass-verb":
            assert entry["ships"] is True, (
                f"{entry['id']}: a compass verb the agent is told to drive must ship"
            )
            owned = set(_referenced_dirs(entry)) | {entry["id"]}
            assert owned & kit_verbs, (
                f"{entry['id']}: classified compass-verb but names no verb in "
                ".seshat/kit-source.yaml"
            )


def test_every_compass_verb_ships(
    capabilities: list[dict[str, Any]], kit_verbs: set[str]
) -> None:
    """FR-015 -- the compass must not name a verb the bundle omits.

    This is the assertion that makes the feature's headline defect impossible to
    reintroduce: before spec 138 the compass named ten verbs and the bundles
    carried none of them.
    """
    owners = _ship_owners(capabilities)
    withheld = sorted(
        verb
        for verb in kit_verbs
        if not any(entry["ships"] for entry in owners.get(verb, []))
    )
    assert not withheld, (
        "the compass names these verbs as ones the agent drives, but they are not "
        f"marked to ship: {withheld}"
    )


def test_knowledge_roots_are_in_scope_and_ship(
    capabilities: list[dict[str, Any]],
) -> None:
    """FR-001 -- the widened O2 scope covers the shipped Knowledge Bases."""
    roots = {
        entry["id"]
        for entry in capabilities
        if entry.get("ship_classification") == "knowledge-root"
    }
    on_disk = {p.name for p in KNOWLEDGE_SKILLS.iterdir() if (p / "SKILL.md").is_file()}
    assert roots == on_disk, (
        "every reviewed Knowledge Base must be inventoried as a knowledge-root; "
        f"missing={sorted(on_disk - roots)} extra={sorted(roots - on_disk)}"
    )
