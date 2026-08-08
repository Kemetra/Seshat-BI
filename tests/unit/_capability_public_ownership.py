"""Spec 142/143 ownership + public-distribution detectors for the oracle.

The middle tier of the oracle's layering: it builds on the shared feeder
readers and is imported (and re-exported) by ``_capability_oracle``, which
keeps every existing ``oracle.<name>`` caller working unchanged.

Split out of ``_capability_oracle`` because these detectors are one cohesive
sub-domain -- public skill -> exactly one capability owner -> a real, authored,
Git-tracked canonical source -- and the parent module had grown past the
single-file size the repo holds test modules to.

ANTI-CIRCULARITY (load-bearing, repo lesson ``verifier-must-sit-on-the-risk``):
like every oracle module, this one reads the FEEDER sources DIRECTLY and
re-implements every reader. It MUST NOT import ``seshat.capability_feeders`` or
``seshat.capability_inventory`` -- an oracle that learns what a feeder says by
calling the code under test would pass vacuously on a builder bug that hides
drift on both sides. ``test_oracle_does_not_import_code_under_test`` asserts
this across every module in the oracle stack, this one included.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from tests.unit._capability_feeder_readers import (
    _git_tracked_files,
    _reference_values,
    load_manifest,
    load_shipped_public_skills,
)

# Spec 142 FR-002 / FR-003 -- the ownership axis token sets. Independent
# restatement of the SPEC's vocabulary, like DECLARED_RECORD_FIELDS below: not
# imported from any shipped module, so the oracle checks the spec's list rather
# than whatever the code happens to allow today.
#
# Every name below is deliberately free of a NUMERIC_FIELD_HINTS substring
# (FR-008 clause 1) -- e.g. the field is ``capability_owner``, never
# ``ownership_maturity``. That constraint is enforced behaviourally by
# ``_axis_numeric_field_names``, not by convention.
OWNERSHIP_OWNERS = {
    "official-upstream",
    "seshat-adapter",
    "seshat-governance",
    "seshat-authoring",
    "seshat-domain-knowledge",
    "seshat-orchestrator",
    "vendored-upstream",
    "seshat-product-module",
    "human-deliverable",
    "specified-not-built",
    "unclassified",
}

OWNERSHIP_SURFACES = {"plugin", "mcp", "skill", "cli", "library", "format"}


def ownership_violations(entry: dict) -> list[str]:
    """O9 (spec 142): the ownership axis on ONE entry.

    Checks, in order: ``capability_owner`` present (FR-002a), drawn from the
    closed token set (FR-002); ``upstream_surface`` drawn from its own closed set
    (FR-003); and a declared ``seshat-adapter`` carrying a non-empty
    ``seshat_delta`` (FR-006).

    Takes a single entry rather than a repo root so the rule can be exercised on
    constructed input -- a detector only ever run against today's manifest is a
    detector nobody has actually tested.
    """
    entry_id = entry.get("id", "<no id>")
    ownership = entry.get("ownership")

    if not isinstance(ownership, dict) or not ownership:
        return [_missing_owner_problem(entry_id)]

    owner = ownership.get("capability_owner")
    return [
        problem
        for problem in (
            _owner_token_problem(entry_id, owner),
            _surface_token_problem(entry_id, ownership.get("upstream_surface")),
            _adapter_delta_problem(entry_id, owner, ownership.get("seshat_delta")),
        )
        if problem is not None
    ]


def _missing_owner_problem(entry_id: object) -> str:
    return (
        f"{entry_id}: no ownership.capability_owner "
        f"(FR-002a: declare 'unclassified' rather than omitting the field)"
    )


def _owner_token_problem(entry_id: object, owner: object) -> str | None:
    """FR-002a then FR-002: the field is present, and drawn from the token set."""
    if owner is None or (isinstance(owner, str) and not owner.strip()):
        return _missing_owner_problem(entry_id)
    if owner not in OWNERSHIP_OWNERS:
        return f"{entry_id}: capability_owner {owner!r} is not an ownership token"
    return None


def _surface_token_problem(entry_id: object, surface: object) -> str | None:
    """FR-003: an OPTIONAL field, but closed when declared."""
    if surface is not None and surface not in OWNERSHIP_SURFACES:
        return (
            f"{entry_id}: upstream_surface {surface!r} is not an upstream-surface token"
        )
    return None


def _adapter_delta_problem(
    entry_id: object, owner: object, delta: object
) -> str | None:
    """FR-006: declaring an adapter obliges you to say what Seshat adds."""
    if owner != "seshat-adapter":
        return None
    if not isinstance(delta, str) or not delta.strip():
        return (
            f"{entry_id}: capability_owner 'seshat-adapter' requires a "
            f"non-empty seshat_delta (FR-006)"
        )
    return None


# Spec 143 -- reconcile the public distribution surface with the capability
# ownership graph. ``references.public_skill`` is the explicit edge used when a
# portable wrapper has a different name from its canonical/internal skill. When
# no explicit edge exists, a unique same-name ``surface: skill`` entry is the
# owner. A CLI entry that merely references a skill is therefore never promoted
# to ownership.
_GENERATED_CANONICAL_PREFIXES = (
    "integrations/claude-code/seshat-bi/",
    "integrations/codex/seshat-bi/",
)


def _escapes_the_repository(source: str) -> bool:
    """Whether a declared path could resolve outside the repository root."""
    posix_path = PurePosixPath(source)
    windows_path = PureWindowsPath(source)
    return bool(
        posix_path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or ".." in posix_path.parts
    )


def _canonical_source_shape_violation(entry_id: str, source: object) -> str | None:
    """The declared path's own defects, judged without touching the disk."""
    if not isinstance(source, str) or not source.strip():
        return f"{entry_id}: ownership.canonical_source is missing or blank"
    if "\\" in source:
        return (
            f"{entry_id}: canonical_source {source!r} must be a "
            "repository-relative POSIX path"
        )
    if _escapes_the_repository(source):
        return (
            f"{entry_id}: canonical_source {source!r} must be a "
            "repository-relative path inside the repository"
        )
    if source.startswith(_GENERATED_CANONICAL_PREFIXES):
        return (
            f"{entry_id}: canonical_source {source!r} is generated output, "
            "not an authored source"
        )
    return None


def _canonical_source_file_violation(
    repo_root: Path, entry_id: str, source: str, tracked_files: set[str]
) -> str | None:
    """What the path actually points at: inside the repo, a real file, tracked.

    Only reached once the shape is valid, so a traversal string is refused
    before anything is resolved against the filesystem.
    """
    root = repo_root.resolve()
    unresolved = root / Path(*PurePosixPath(source).parts)
    if not unresolved.resolve(strict=False).is_relative_to(root):
        return (
            f"{entry_id}: canonical_source {source!r} must be a "
            "repository-relative path inside the repository"
        )
    if unresolved.is_symlink() or not unresolved.is_file():
        return (
            f"{entry_id}: canonical_source {source!r} is not a regular file "
            "(symlinks are not canonical)"
        )
    if source not in tracked_files:
        return f"{entry_id}: canonical_source {source!r} is not tracked by Git"
    return None


def _canonical_source_violations(
    repo_root: Path,
    entry: dict,
    tracked_files: set[str],
) -> list[str]:
    """Spec 143: an entry's canonical_source is an authored, tracked, real file.

    Returns at most one problem -- the FIRST failure -- because the later checks
    presuppose the earlier ones (resolving a traversal path against the
    filesystem would be meaningless).
    """
    entry_id = str(entry.get("id", "<no id>"))
    ownership = entry.get("ownership")
    source = ownership.get("canonical_source") if isinstance(ownership, dict) else None

    shape_problem = _canonical_source_shape_violation(entry_id, source)
    if shape_problem is not None:
        return [shape_problem]

    assert isinstance(source, str)  # narrowed by the shape check above
    file_problem = _canonical_source_file_violation(
        repo_root, entry_id, source, tracked_files
    )
    return [file_problem] if file_problem is not None else []


def public_capability_integrity_violations(
    repo_root: Path,
    *,
    manifest: list[dict] | None = None,
    public_skills: set[str] | None = None,
    tracked_files: set[str] | None = None,
) -> list[str]:
    """Spec 143: public skill -> one owner -> real canonical source.

    Optional inputs make every failure mode constructible in a unit test. The
    aggregate call supplies none and therefore reads all three feeder truths
    independently: public surface, capability manifest, and Git's tracked set.
    """
    entries = load_manifest(repo_root) if manifest is None else manifest
    shipped = (
        load_shipped_public_skills(repo_root)
        if public_skills is None
        else public_skills
    )
    tracked = _git_tracked_files(repo_root) if tracked_files is None else tracked_files
    problems: list[str] = []
    problems += _dangling_public_reference_violations(entries, shipped)
    for public_name in sorted(shipped):
        problems += _public_skill_owner_violations(entries, public_name)
    for entry in entries:
        ownership = entry.get("ownership")
        if isinstance(ownership, dict) and "canonical_source" in ownership:
            problems += _canonical_source_violations(repo_root, entry, tracked)
    return problems


def _dangling_public_reference_violations(
    entries: list[dict], shipped: set[str]
) -> list[str]:
    """A manifest entry pointing at a public skill that is not shipped."""
    return [
        f"{entry.get('id', '<no id>')}: references.public_skill "
        f"{public_name!r} is not a shipped public skill"
        for entry in entries
        for public_name in _reference_values(entry, "public_skill")
        if public_name not in shipped
    ]


def _owner_candidates(entries: list[dict], public_name: str) -> tuple[list[dict], str]:
    """Entries claiming one shipped public skill, and how they claimed it.

    An explicit ``references.public_skill`` wins outright; only when none exists
    does a same-name ``skill`` reference stand in, so a precise claim is never
    made ambiguous by an incidental name collision.
    """
    explicit = [
        entry
        for entry in entries
        if public_name in _reference_values(entry, "public_skill")
    ]
    if explicit:
        return explicit, "explicit"
    fallback = [
        entry
        for entry in entries
        if entry.get("surface") == "skill"
        and public_name in _reference_values(entry, "skill")
    ]
    return fallback, "same-name skill fallback"


def _public_skill_owner_violations(entries: list[dict], public_name: str) -> list[str]:
    """Exactly one manifest entry owns each shipped public skill, with a source."""
    candidates, relationship = _owner_candidates(entries, public_name)
    if not candidates:
        return [f"{public_name}: shipped public skill has no capability owner"]
    if len(candidates) != 1:
        candidate_ids = sorted(str(entry.get("id", "<no id>")) for entry in candidates)
        return [
            f"{public_name}: ambiguous {relationship} capability owners: "
            + ", ".join(candidate_ids)
        ]

    owner = candidates[0]
    problems = list(ownership_violations(owner))
    ownership = owner.get("ownership")
    if not isinstance(ownership, dict) or "canonical_source" not in ownership:
        problems.append(
            f"{owner.get('id', '<no id>')}: public skill {public_name!r} "
            "requires ownership.canonical_source"
        )
    return problems
