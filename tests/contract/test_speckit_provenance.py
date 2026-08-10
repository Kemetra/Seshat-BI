"""Fail-closed provenance contract for the Spec Kit skills owned by Seshat."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import NamedTuple

import pytest
import yaml

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CAPABILITIES = Path("docs/capabilities/capabilities.yaml")
_CLAUDE_MANIFEST = Path(".specify/integrations/claude.manifest.json")
_SPECKIT_MANIFEST = Path(".specify/integrations/speckit.manifest.json")
_INIT_OPTIONS = Path(".specify/init-options.json")
_HASH = re.compile(r"[0-9a-f]{64}")
_VERSION = re.compile(r"\d+\.\d+\.\d+")
# The fourteen skills spec 152 closed KF-2 over; shrinking the set in lockstep
# across capabilities.yaml and the manifest must not read as a passing contract.
_EXPECTED_SKILL_COUNT = 14


def _normalized_sha256(content: bytes) -> str:
    """Hash semantic bytes while ignoring checkout-only CRLF differences."""
    return hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _load_json(
    root: Path, relative: Path, problems: list[str]
) -> dict[str, object] | None:
    try:
        value = json.loads(
            (root / relative).read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        problems.append(f"{relative.as_posix()}: malformed or unreadable: {exc}")
        return None
    if not isinstance(value, dict):
        problems.append(f"{relative.as_posix()}: top level must be an object")
        return None
    return value


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys.

    ``yaml.safe_load`` silently keeps the last of two identical keys, so a
    second ``skill:`` under ``speckit-workflow-skills`` would quietly replace
    the pinned scope and still read clean. The JSON side already rejects this
    via ``_unique_object``; the capability authority gets the same treatment.
    """


def _no_duplicate_keys(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            # YAML allows complex keys (`? [a, b]`); Python cannot hash them.
            # An unhashable key is malformed authority, so it is REPORTED as a
            # YAMLError rather than escaping as a TypeError and aborting the
            # contract that exists to fail closed.
            raise yaml.YAMLError(f"unhashable YAML key {key!r}") from exc
        if duplicate:
            raise yaml.YAMLError(f"duplicate YAML key {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys
)


def _load_capabilities(root: Path, problems: list[str]) -> dict[str, object] | None:
    try:
        value = yaml.load(  # noqa: S506 -- _UniqueKeyLoader derives from SafeLoader
            (root / _CAPABILITIES).read_text(encoding="utf-8"), Loader=_UniqueKeyLoader
        )
    except (OSError, UnicodeError, yaml.YAMLError, TypeError, ValueError) as exc:
        # TypeError/ValueError are belt-and-braces: the loader already reports
        # unhashable keys as YAMLError, but a malformed authority must never
        # escape as a raised exception from the check that gates it.
        problems.append(f"{_CAPABILITIES.as_posix()}: malformed or unreadable: {exc}")
        return None
    if not isinstance(value, dict):
        problems.append(f"{_CAPABILITIES.as_posix()}: top level must be a mapping")
        return None
    return value


def _is_rooted_or_traversing(value: str) -> bool:
    """True when a relative-looking string can still escape its base.

    Absolute on either flavour, drive-qualified, or containing a ``..`` part --
    the three ways a manifest string stops naming a path inside the repository.
    """
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if posix.is_absolute() or windows.is_absolute():
        return True
    if windows.drive:
        return True
    return ".." in posix.parts


def _safe_skill_name(value: object) -> bool:
    if not isinstance(value, str):
        return False
    if not value.strip() or value != value.strip():
        return False
    if not value.startswith("speckit-") or "\\" in value:
        return False
    if len(PurePosixPath(value).parts) != 1:
        return False
    return not _is_rooted_or_traversing(value)


def _declared_skill_references(
    capabilities: dict[str, object], problems: list[str]
) -> list[object]:
    """Locate the one speckit-workflow-skills entry's references.skill list."""
    entries = capabilities.get("capabilities")
    if not isinstance(entries, list):
        problems.append("capabilities.yaml: 'capabilities' must be a list")
        return []
    matches = [
        entry
        for entry in entries
        if isinstance(entry, dict) and entry.get("id") == "speckit-workflow-skills"
    ]
    if len(matches) != 1:
        problems.append(
            "capabilities.yaml: expected exactly one speckit-workflow-skills entry"
        )
        return []
    references = matches[0].get("references")
    skills = references.get("skill") if isinstance(references, dict) else None
    if not isinstance(skills, list) or not skills:
        problems.append(
            "speckit-workflow-skills: references.skill must be a non-empty list"
        )
        return []
    return skills


def _skill_reference_problem(index: int, skill: object, seen: set[str]) -> str | None:
    """Reject a reference that is unsafe or already claimed."""
    if not _safe_skill_name(skill):
        return (
            "speckit-workflow-skills: "
            f"references.skill[{index}] is blank, absolute, or unsafe: {skill!r}"
        )
    if skill in seen:
        return f"speckit-workflow-skills: duplicate references.skill {skill!r}"
    return None


def _expected_skill_paths(
    capabilities: dict[str, object], problems: list[str]
) -> set[str]:
    skills = _declared_skill_references(capabilities, problems)
    expected: set[str] = set()
    seen: set[str] = set()
    for index, skill in enumerate(skills):
        problem = _skill_reference_problem(index, skill, seen)
        if problem is not None:
            problems.append(problem)
            continue
        assert isinstance(skill, str)
        seen.add(skill)
        expected.add(f".claude/skills/{skill}/SKILL.md")
    return expected


def _safe_repo_path(path: object) -> bool:
    if not isinstance(path, str):
        return False
    if not path or "\\" in path:
        return False
    return not _is_rooted_or_traversing(path)


def _git_tracked_files(root: Path, problems: list[str]) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        problems.append(f"git ls-files: unable to establish tracked provenance: {exc}")
        return set()
    return {path.decode("utf-8") for path in result.stdout.split(b"\0") if path}


def _manifest_scope_problems(expected: set[str], declared: set[str]) -> list[str]:
    """The manifest must pin exactly the capability-referenced skills."""
    problems: list[str] = []
    missing = sorted(expected - declared)
    unexpected = sorted(declared - expected)
    if missing:
        problems.append(f"Claude manifest missing skill paths: {missing}")
    if unexpected:
        problems.append(f"Claude manifest has unexpected skill paths: {unexpected}")
    return problems


def _scope_size_problems(expected: set[str], root: Path) -> list[str]:
    """The pinned scope must stay the full fourteen-skill set.

    Dropping a ``references.skill`` entry and its manifest entry together would
    shrink both sides in lockstep and read as clean, leaving a still-tracked
    vendored skill no longer hash-protected. Only checked against the real
    repository, so constructed fixtures stay free to use a smaller scope.
    """
    if root != _REPO_ROOT or len(expected) == _EXPECTED_SKILL_COUNT:
        return []
    return [
        f"speckit-workflow-skills: expected {_EXPECTED_SKILL_COUNT} pinned skills, "
        f"found {len(expected)}"
    ]


def _manifest_shape_problems(manifest_files: dict[str, object]) -> list[str]:
    """Every declared entry is a safe repo path mapped to a lowercase SHA-256."""
    problems: list[str] = []
    for path, digest in manifest_files.items():
        if not _safe_repo_path(path):
            problems.append(f"Claude manifest path is absolute or unsafe: {path!r}")
        if not isinstance(digest, str) or _HASH.fullmatch(digest) is None:
            problems.append(
                f"Claude manifest hash for {path!r} is not lowercase SHA-256"
            )
    return problems


class _Checkout(NamedTuple):
    """The one repository checkout a target is validated against."""

    root: Path
    resolved_root: Path
    tracked: frozenset[str]


def _target_problems(checkout: _Checkout, path: str, digest: object) -> list[str]:
    """Validate one pinned target: real file, inside the repo, tracked, undrifted."""
    candidate = checkout.root / Path(*PurePosixPath(path).parts)
    if candidate.is_symlink() or not candidate.is_file():
        return [f"{path}: provenance target is not a regular file"]
    if not candidate.resolve().is_relative_to(checkout.resolved_root):
        return [f"{path}: provenance target escapes the repository"]

    problems: list[str] = []
    if path not in checkout.tracked:
        problems.append(f"{path}: provenance target is not tracked by Git")
    if isinstance(digest, str) and _HASH.fullmatch(digest):
        observed = _normalized_sha256(candidate.read_bytes())
        if digest != observed:
            problems.append(
                f"{path}: content drift; expected {digest}, observed {observed}"
            )
    return problems


def _identity_problems(
    claude: dict[str, object], speckit: dict[str, object]
) -> list[str]:
    """Each manifest must name the integration it claims to pin.

    A mislabeled or swapped manifest would otherwise be trusted for its hashes
    and version, since nothing else in the contract reads ``integration``.
    """
    declared = (
        (_CLAUDE_MANIFEST, "claude", claude.get("integration")),
        (_SPECKIT_MANIFEST, "speckit", speckit.get("integration")),
    )
    return [
        f"{relative.as_posix()}: integration must be {expected!r}, got {actual!r}"
        for relative, expected, actual in declared
        if actual != expected
    ]


def _version_agreement_problems(
    claude: dict[str, object],
    speckit: dict[str, object],
    init_options: dict[str, object],
) -> list[str]:
    """All three Spec Kit version claims must be present and identical."""
    versions = {
        _INIT_OPTIONS.as_posix(): init_options.get("speckit_version"),
        _CLAUDE_MANIFEST.as_posix(): claude.get("version"),
        _SPECKIT_MANIFEST.as_posix(): speckit.get("version"),
    }
    if any(
        not isinstance(value, str) or not value.strip() for value in versions.values()
    ):
        return [f"Spec Kit version claim is missing or blank: {versions}"]
    malformed = sorted(
        source
        for source, value in versions.items()
        if not isinstance(value, str) or _VERSION.fullmatch(value) is None
    )
    if malformed:
        # Agreement on a non-version ("latest", "0.8.10x") is not reproducible
        # provenance, so shape is checked before equality (FR-012).
        return [f"Spec Kit version claim is not a dotted release: {malformed}"]
    if len(set(versions.values())) != 1:
        return [f"Spec Kit version claims disagree: {versions}"]
    return []


def _provenance_violations(
    root: Path, *, tracked_files: set[str] | None = None
) -> list[str]:
    problems: list[str] = []
    capabilities = _load_capabilities(root, problems)
    claude = _load_json(root, _CLAUDE_MANIFEST, problems)
    speckit = _load_json(root, _SPECKIT_MANIFEST, problems)
    init_options = _load_json(root, _INIT_OPTIONS, problems)
    if None in (capabilities, claude, speckit, init_options):
        return problems
    assert capabilities is not None
    assert claude is not None
    assert speckit is not None
    assert init_options is not None

    expected = _expected_skill_paths(capabilities, problems)
    manifest_files = claude.get("files")
    if not isinstance(manifest_files, dict):
        problems.append(f"{_CLAUDE_MANIFEST.as_posix()}: 'files' must be an object")
        return problems

    declared = set(manifest_files)
    problems += _identity_problems(claude, speckit)
    problems += _manifest_scope_problems(expected, declared)
    problems += _scope_size_problems(expected, root)
    problems += _manifest_shape_problems(manifest_files)

    tracked = (
        _git_tracked_files(root, problems) if tracked_files is None else tracked_files
    )
    checkout = _Checkout(
        root=root, resolved_root=root.resolve(), tracked=frozenset(tracked)
    )
    for path in sorted(expected & declared):
        if _safe_repo_path(path):
            problems += _target_problems(checkout, path, manifest_files[path])

    problems += _version_agreement_problems(claude, speckit, init_options)
    return problems


def _write_fixture(root: Path) -> set[str]:
    skills = ["speckit-alpha", "speckit-beta"]
    capabilities = {
        "capabilities": [
            {
                "id": "speckit-workflow-skills",
                "references": {"skill": skills},
            }
        ]
    }
    paths = {f".claude/skills/{skill}/SKILL.md" for skill in skills}
    for path in paths:
        target = root / Path(*PurePosixPath(path).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"content for {path}\n".encode())

    (root / _CAPABILITIES).parent.mkdir(parents=True, exist_ok=True)
    (root / _CAPABILITIES).write_text(json.dumps(capabilities), encoding="utf-8")
    (root / _CLAUDE_MANIFEST).parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "integration": "claude",
        "version": "0.8.10",
        "files": {
            path: _normalized_sha256(
                (root / Path(*PurePosixPath(path).parts)).read_bytes()
            )
            for path in sorted(paths)
        },
    }
    (root / _CLAUDE_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    (root / _SPECKIT_MANIFEST).write_text(
        json.dumps({"integration": "speckit", "version": "0.8.10", "files": {}}),
        encoding="utf-8",
    )
    (root / _INIT_OPTIONS).write_text(
        json.dumps({"speckit_version": "0.8.10"}), encoding="utf-8"
    )
    return paths


def _read_fixture_json(root: Path, relative: Path) -> dict[str, object]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _write_fixture_json(root: Path, relative: Path, value: object) -> None:
    (root / relative).write_text(json.dumps(value), encoding="utf-8")


def test_real_speckit_skill_provenance_is_closed() -> None:
    assert _provenance_violations(_REPO_ROOT) == []


@pytest.mark.parametrize("change", ["missing", "unexpected"])
def test_manifest_skill_scope_must_exactly_match_capability_references(
    tmp_path: Path, change: str
) -> None:
    tracked = _write_fixture(tmp_path)
    manifest = _read_fixture_json(tmp_path, _CLAUDE_MANIFEST)
    files = manifest["files"]
    assert isinstance(files, dict)
    if change == "missing":
        files.pop(sorted(files)[0])
    else:
        files[".claude/skills/speckit-extra/SKILL.md"] = "0" * 64
    _write_fixture_json(tmp_path, _CLAUDE_MANIFEST, manifest)

    problems = _provenance_violations(tmp_path, tracked_files=tracked)

    assert any(change in problem for problem in problems), problems


@pytest.mark.parametrize(
    "reference", ["", "   ", "../escape", "/absolute", "C:\\escape"]
)
def test_capability_skill_references_reject_blank_or_unsafe_values(
    tmp_path: Path, reference: str
) -> None:
    tracked = _write_fixture(tmp_path)
    capabilities = json.loads((tmp_path / _CAPABILITIES).read_text(encoding="utf-8"))
    capabilities["capabilities"][0]["references"]["skill"] = [reference]
    (tmp_path / _CAPABILITIES).write_text(json.dumps(capabilities), encoding="utf-8")

    problems = _provenance_violations(tmp_path, tracked_files=tracked)

    assert any("blank, absolute, or unsafe" in problem for problem in problems)


def test_capability_skill_references_reject_duplicates(tmp_path: Path) -> None:
    tracked = _write_fixture(tmp_path)
    capabilities = json.loads((tmp_path / _CAPABILITIES).read_text(encoding="utf-8"))
    capabilities["capabilities"][0]["references"]["skill"] = [
        "speckit-alpha",
        "speckit-alpha",
    ]
    (tmp_path / _CAPABILITIES).write_text(json.dumps(capabilities), encoding="utf-8")

    problems = _provenance_violations(tmp_path, tracked_files=tracked)

    assert any("duplicate references.skill" in problem for problem in problems)


def test_manifest_rejects_duplicate_json_paths(tmp_path: Path) -> None:
    tracked = _write_fixture(tmp_path)
    path = ".claude/skills/speckit-alpha/SKILL.md"
    (tmp_path / _CLAUDE_MANIFEST).write_text(
        '{"version":"0.8.10","files":{'
        + json.dumps(path)
        + ':"'
        + "0" * 64
        + '",'
        + json.dumps(path)
        + ':"'
        + "1" * 64
        + '"}}',
        encoding="utf-8",
    )

    problems = _provenance_violations(tmp_path, tracked_files=tracked)

    assert any("duplicate JSON key" in problem for problem in problems)


def test_capabilities_yaml_rejects_duplicate_mapping_keys(tmp_path: Path) -> None:
    """A second `skill:` must fail, not silently replace the pinned scope."""
    tracked = _write_fixture(tmp_path)
    (tmp_path / _CAPABILITIES).write_text(
        "capabilities:\n"
        "  - id: speckit-workflow-skills\n"
        "    references:\n"
        "      skill: [speckit-alpha, speckit-beta]\n"
        "      skill: [speckit-alpha]\n",
        encoding="utf-8",
    )

    problems = _provenance_violations(tmp_path, tracked_files=tracked)

    assert any("duplicate YAML key" in problem for problem in problems), problems


@pytest.mark.parametrize(
    "document",
    [
        "capabilities:\n  ? [a, b]\n  : value\n",
        "capabilities:\n  ? {a: b}\n  : value\n",
        "? [a, b]\n: value\n",
    ],
)
def test_capabilities_yaml_reports_unhashable_keys(
    tmp_path: Path, document: str
) -> None:
    """A complex YAML key is reported, never raised past the contract."""
    tracked = _write_fixture(tmp_path)
    (tmp_path / _CAPABILITIES).write_text(document, encoding="utf-8")

    problems = _provenance_violations(tmp_path, tracked_files=tracked)

    assert any("malformed or unreadable" in problem for problem in problems), problems


def test_capabilities_yaml_accepts_the_real_authority() -> None:
    """The duplicate-key loader must not reject the shipped capabilities.yaml."""
    problems: list[str] = []

    assert _load_capabilities(_REPO_ROOT, problems) is not None
    assert problems == []


@pytest.mark.parametrize("version", ["latest", "0.8.10x", "v0.8.10", "0.8", "main"])
def test_agreeing_but_malformed_versions_are_rejected(
    tmp_path: Path, version: str
) -> None:
    """FR-012: agreement on a non-version is not reproducible provenance."""
    tracked = _write_fixture(tmp_path)
    for relative, field in (
        (_INIT_OPTIONS, "speckit_version"),
        (_CLAUDE_MANIFEST, "version"),
        (_SPECKIT_MANIFEST, "version"),
    ):
        document = _read_fixture_json(tmp_path, relative)
        document[field] = version
        _write_fixture_json(tmp_path, relative, document)

    problems = _provenance_violations(tmp_path, tracked_files=tracked)

    assert any("not a dotted release" in problem for problem in problems), problems


@pytest.mark.parametrize(
    ("relative", "value"),
    [
        (_CLAUDE_MANIFEST, "speckit"),
        (_CLAUDE_MANIFEST, None),
        (_SPECKIT_MANIFEST, "claude"),
        (_SPECKIT_MANIFEST, None),
    ],
)
def test_manifest_identity_must_match_its_file(
    tmp_path: Path, relative: Path, value: object
) -> None:
    """A swapped or unlabeled manifest is never authoritative for its hashes."""
    tracked = _write_fixture(tmp_path)
    document = _read_fixture_json(tmp_path, relative)
    if value is None:
        document.pop("integration", None)
    else:
        document["integration"] = value
    _write_fixture_json(tmp_path, relative, document)

    problems = _provenance_violations(tmp_path, tracked_files=tracked)

    assert any("integration must be" in problem for problem in problems), problems


def test_real_repository_pins_the_full_fourteen_skill_scope() -> None:
    """Spec 152 closure: the pinned scope is fourteen skills, not merely non-empty."""
    problems: list[str] = []
    expected = _expected_skill_paths(_load_capabilities(_REPO_ROOT, problems), problems)

    assert problems == []
    assert len(expected) == _EXPECTED_SKILL_COUNT


def test_shrinking_the_scope_in_lockstep_still_fails() -> None:
    """Dropping a reference and its manifest entry together must not read clean."""
    problems = _scope_size_problems({"a", "b"}, _REPO_ROOT)

    assert any("expected 14 pinned skills" in problem for problem in problems), problems


@pytest.mark.parametrize("digest", [None, "", "abc", "A" * 64, "0" * 63])
def test_manifest_rejects_malformed_hashes(tmp_path: Path, digest: object) -> None:
    tracked = _write_fixture(tmp_path)
    manifest = _read_fixture_json(tmp_path, _CLAUDE_MANIFEST)
    files = manifest["files"]
    assert isinstance(files, dict)
    files[sorted(files)[0]] = digest
    _write_fixture_json(tmp_path, _CLAUDE_MANIFEST, manifest)

    problems = _provenance_violations(tmp_path, tracked_files=tracked)

    assert any("not lowercase SHA-256" in problem for problem in problems)


def test_manifest_rejects_content_drift(tmp_path: Path) -> None:
    tracked = _write_fixture(tmp_path)
    path = sorted(tracked)[0]
    (tmp_path / Path(*PurePosixPath(path).parts)).write_bytes(b"changed semantics\n")

    problems = _provenance_violations(tmp_path, tracked_files=tracked)

    assert any(path in problem and "content drift" in problem for problem in problems)


def test_manifest_rejects_untracked_target(tmp_path: Path) -> None:
    tracked = _write_fixture(tmp_path)
    path = sorted(tracked)[0]
    tracked.remove(path)

    problems = _provenance_violations(tmp_path, tracked_files=tracked)

    assert any(path in problem and "not tracked" in problem for problem in problems)


def test_manifest_rejects_non_file_target(tmp_path: Path) -> None:
    tracked = _write_fixture(tmp_path)
    path = sorted(tracked)[0]
    (tmp_path / Path(*PurePosixPath(path).parts)).unlink()

    problems = _provenance_violations(tmp_path, tracked_files=tracked)

    assert any(
        path in problem and "not a regular file" in problem for problem in problems
    )


def test_manifest_rejects_symlink_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tracked = _write_fixture(tmp_path)
    path = sorted(tracked)[0]
    target = tmp_path / Path(*PurePosixPath(path).parts)
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda candidate: candidate == target or original_is_symlink(candidate),
    )

    problems = _provenance_violations(tmp_path, tracked_files=tracked)

    assert any(
        path in problem and "not a regular file" in problem for problem in problems
    )


@pytest.mark.parametrize(
    ("relative", "field"),
    [
        (_INIT_OPTIONS, "speckit_version"),
        (_CLAUDE_MANIFEST, "version"),
        (_SPECKIT_MANIFEST, "version"),
    ],
)
def test_all_speckit_version_claims_must_agree(
    tmp_path: Path, relative: Path, field: str
) -> None:
    tracked = _write_fixture(tmp_path)
    document = _read_fixture_json(tmp_path, relative)
    document[field] = "9.9.9"
    _write_fixture_json(tmp_path, relative, document)

    problems = _provenance_violations(tmp_path, tracked_files=tracked)

    assert any("version claims disagree" in problem for problem in problems)


def test_lf_normalization_ignores_crlf_only_changes() -> None:
    assert _normalized_sha256(b"first\r\nsecond\r\n") == _normalized_sha256(
        b"first\nsecond\n"
    )


def test_lf_normalization_detects_semantic_byte_change() -> None:
    assert _normalized_sha256(b"first\nsecond\n") != _normalized_sha256(
        b"first\nchanged\n"
    )
