"""The capability inventory is the single AUTHORED source of what ships.

Spec 138 User Story 2. These assertions encode `contracts/ship-classification.md`
obligations 1-13: obligations 1-5 on the authored inventory, and obligations 6
and 10-13 on the derivation that generates the allowlist from it.

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
ALLOWLIST = REPO_ROOT / "distribution/public-knowledge-allowlist.yaml"

# A shipped skill is one the bundle carries as `skills/<dir>/SKILL.md`. Both
# harnesses must carry the same set (obligation 9), so both are checked.
BUNDLE_ROOTS = {
    "claude": REPO_ROOT / "integrations/claude-code/seshat-bi",
    "codex": REPO_ROOT / "integrations/codex/seshat-bi",
}

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


# ---------------------------------------------------------------------------
# T028-T029 -- the derivation (obligations 6, 10-13)
#
# The inventory is only the authored source of what ships if the allowlist is
# DERIVED from it and the export FAILS when the two disagree. Until then `ships`
# is an intention the artifact is free to ignore -- which is the split authority
# US2 exists to remove, not a smaller version of it.
# ---------------------------------------------------------------------------


def _derivation() -> tuple[Any, type[Exception]]:
    """The derivation T036 must provide.

    Imported inside each test rather than at module scope so that its absence is
    a readable failure naming the missing feature, not a collection error that
    takes obligations 1-5 down with it.
    """
    try:
        from seshat.allowlist_derivation import (  # noqa: PLC0415
            DerivationError,
            derive_allowlist,
        )
    except ImportError as exc:  # pragma: no cover -- the RED state
        pytest.fail(
            "obligation 6 has no implementation: expected "
            "`seshat.allowlist_derivation.derive_allowlist(repo_root, *, "
            f"capabilities=None)` raising `DerivationError` -- {exc}"
        )
    return derive_allowlist, DerivationError


def _sources_under(document: dict[str, Any], directory: str) -> list[str]:
    """Derived entry sources belonging to one skill directory."""
    return [
        str(entry["source"])
        for entry in document["entries"]
        if f"/{directory}/" in f"/{entry['source']}"
    ]


def _bundled_skill_dirs() -> dict[str, set[str]]:
    return {
        harness: {
            p.name for p in (root / "skills").iterdir() if (p / "SKILL.md").is_file()
        }
        for harness, root in BUNDLE_ROOTS.items()
    }


def _absent_from_bundles(
    entry: dict[str, Any], bundled: dict[str, set[str]]
) -> dict[str, list[str]]:
    """Per harness, the directories this entry owns that the bundle lacks."""
    return {
        harness: missing
        for harness, present in bundled.items()
        if (missing := [d for d in _referenced_dirs(entry) if d not in present])
    }


def test_committed_bundle_carries_every_shipping_entry(
    capabilities: list[dict[str, Any]],
) -> None:
    """The committed bundle is current with the inventory -- a TREE-state check.

    This is adjacent to obligation 11, not identical to it: obligation 11 governs
    the derivation (asserted below), while this governs the checked-in artifact.
    Both are wanted, because nothing in obligations 1-5 connects `ships` to a
    bundle file -- a classification can be flipped and pass every existing test
    while the bundle carries nothing.

    Consequence to expect: this goes RED between T057 and T058, and again between
    T061 and T063, because each flips `ships: true` before the regeneration that
    satisfies it. That RED means "regenerate the bundles", not "the inventory is
    wrong" -- do not silence it by narrowing the assertion.
    """
    bundled = _bundled_skill_dirs()
    offenders = {
        entry["id"]: absent
        for entry in capabilities
        if entry.get("ships") and (absent := _absent_from_bundles(entry, bundled))
    }
    assert not offenders, (
        f"{len(offenders)} entries are marked `ships: true` but produce no bundle "
        f"file, so the inventory and the artifact disagree: {offenders}"
    )


def test_every_kit_source_verb_has_a_bundle_file(kit_verbs: set[str]) -> None:
    """T046 / FR-015 -- the compass and the bundle must not drift apart again.

    `test_every_compass_verb_ships` asserts the same property one level earlier,
    against the inventory. This one asserts it against the artifact, which is
    where the original defect lived: the compass named ten verbs the agent was
    told to drive and both bundles carried none of them.
    """
    bundled = _bundled_skill_dirs()
    missing = {
        harness: sorted(kit_verbs - present)
        for harness, present in bundled.items()
        if kit_verbs - present
    }
    assert not missing, (
        "`.seshat/kit-source.yaml` names verbs the agent drives that the bundle "
        f"does not carry: {missing}"
    )


def test_committed_allowlist_matches_a_fresh_derivation() -> None:
    """Obligation 13 -- a hand-edit must fail rather than take effect."""
    derive_allowlist, _ = _derivation()
    assert derive_allowlist(REPO_ROOT) == _load(ALLOWLIST), (
        "distribution/public-knowledge-allowlist.yaml does not match a fresh "
        "derivation from docs/capabilities/capabilities.yaml -- it is generated "
        "output and must not be edited by hand"
    )


def test_derivation_fails_on_a_shipping_entry_with_no_directory(
    capabilities: list[dict[str, Any]],
) -> None:
    """Obligation 10 -- and it must name the offender."""
    derive_allowlist, DerivationError = _derivation()
    doctored = [dict(entry) for entry in capabilities]
    victim = next(entry for entry in doctored if entry.get("ships"))
    victim["references"] = {"skill": "no-such-skill-directory"}
    with pytest.raises(DerivationError, match="no-such-skill-directory"):
        derive_allowlist(REPO_ROOT, capabilities=doctored)


def test_derivation_fails_on_a_shipping_entry_that_yields_no_bundle_file(
    tmp_path: Path,
) -> None:
    """Obligation 11 -- distinct from 10: the directory is present but empty.

    No such directory exists in this repository (every skill directory carries a
    `SKILL.md`), so the condition is constructed on a synthetic root rather than
    doctored from the committed inventory. The `match` is what proves the
    derivation failed for *this* reason and not incidentally.
    """
    derive_allowlist, DerivationError = _derivation()
    orphan = "orphan-no-skill-md"
    (tmp_path / ".claude/skills" / orphan).mkdir(parents=True)
    doctored = [
        {
            "id": orphan,
            "ships": True,
            "ship_classification": "consumer-capability",
            "references": {"skill": orphan},
        }
    ]
    with pytest.raises(DerivationError, match=orphan):
        derive_allowlist(tmp_path, capabilities=doctored)


def test_no_development_only_skill_reaches_either_bundle(
    capabilities: list[dict[str, Any]],
) -> None:
    """T065 -- development-only and specification-workflow skills stay home."""
    withheld = {
        directory
        for entry in capabilities
        if entry.get("ship_classification") == "development-only"
        for directory in _referenced_dirs(entry)
    }
    assert withheld, "precondition: some skills must be classified development-only"
    for harness, present in _bundled_skill_dirs().items():
        leaked = sorted(withheld & present)
        assert not leaked, f"{harness} bundle carries development-only skills: {leaked}"


def test_exclusion_is_caused_by_classification_not_by_a_name_pattern(
    capabilities: list[dict[str, Any]],
) -> None:
    """T066 -- reclassify one development-only skill and it WOULD ship.

    The prohibition is that classification is authored, never inferred from a
    filename or path prefix. Asserting only that development-only skills are absent
    cannot tell a working classification apart from a name rule that happens to
    exclude the same set. So flip one entry in memory and prove the derivation
    follows the classification.
    """
    derive_allowlist, _ = _derivation()
    victim = next(
        entry
        for entry in capabilities
        if entry.get("ship_classification") == "development-only"
        and _referenced_dirs(entry)
    )
    directory = _referenced_dirs(victim)[0]

    baseline = derive_allowlist(REPO_ROOT)
    assert not _sources_under(baseline, directory), (
        f"precondition: {directory} must not ship while classified development-only"
    )

    doctored = [dict(entry) for entry in capabilities]
    for entry in doctored:
        if entry["id"] == victim["id"]:
            entry["ships"] = True
            entry["ship_classification"] = "consumer-capability"
    reclassified = derive_allowlist(REPO_ROOT, capabilities=doctored)
    assert _sources_under(reclassified, directory), (
        f"{directory} did not ship after being reclassified as consumer-facing, so "
        "its exclusion is not caused by the recorded classification"
    )


def test_no_skill_body_became_resident(capabilities: list[dict[str, Any]]) -> None:
    """T067 / FR-021b -- bodies load on demand; only routing metadata is resident.

    The routing-cost ceiling is measured over name+description frontmatter alone.
    That premise breaks silently if a story inlines one skill's body into another
    (typically the router), so no bundled skill may contain a second skill's body.
    """
    for harness, root in BUNDLE_ROOTS.items():
        router = (root / "skills/seshat-bi/SKILL.md").read_text(encoding="utf-8")
        for path in sorted((root / "skills").glob("*/SKILL.md")):
            if path.parent.name == "seshat-bi":
                continue
            body = path.read_text(encoding="utf-8").split("---", 2)[-1].strip()
            excerpt = "\n".join(body.splitlines()[:5]).strip()
            assert excerpt and excerpt not in router, (
                f"{harness}: the router has {path.parent.name}'s body inlined, so it "
                "is resident rather than loaded on demand"
            )


def test_derivation_fails_on_an_unclassified_skill_directory(
    capabilities: list[dict[str, Any]], skill_dirs: set[str]
) -> None:
    """Obligation 12 -- an unclassified skill is an undecided question, not a warning.

    The prohibition is explicit: no mechanism may suppress this for convenience.
    """
    derive_allowlist, DerivationError = _derivation()
    orphaned = sorted(skill_dirs)[0]
    doctored = [
        entry for entry in capabilities if orphaned not in _referenced_dirs(entry)
    ]
    with pytest.raises(DerivationError, match=orphaned):
        derive_allowlist(REPO_ROOT, capabilities=doctored)
