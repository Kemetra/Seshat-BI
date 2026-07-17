"""Audit Seshat BI version projections without authorizing a release."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from scripts.bundle_provenance import (
        ProvenanceError,
        validate_manifest_provenance,
    )
    from scripts.release_note_gate import (
        governed_release_note_path,
        governed_release_note_version,
    )
except ModuleNotFoundError:  # direct `python scripts/check_release_versions.py`
    from bundle_provenance import (
        ProvenanceError,
        validate_manifest_provenance,
    )
    from release_note_gate import (
        governed_release_note_path,
        governed_release_note_version,
    )

_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


class VersionAuditError(ValueError):
    """The version source itself is missing or invalid."""


@dataclass(frozen=True)
class _ProjectionTarget:
    surface: str
    path: str
    expected: str


def _json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise VersionAuditError(f"{path} must contain a JSON object")
    return value


def _git_revision(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _tag_map(repo_root: Path) -> dict[str, str]:
    names = subprocess.run(
        ["git", "tag", "--list"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    revisions: dict[str, str] = {}
    for name in names:
        revision = subprocess.run(
            ["git", "rev-list", "-n", "1", name],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        revisions[name] = revision
    return revisions


def _projection(
    target: _ProjectionTarget,
    observed: str | None,
    *,
    status: str | None = None,
    blocker: str | None = None,
) -> dict[str, str | None]:
    resolved_status = status or ("pass" if observed == target.expected else "blocked")
    result: dict[str, str | None] = {
        "surface": target.surface,
        "path": target.path,
        "observed": observed,
        "expected": target.expected,
        "status": resolved_status,
    }
    if blocker:
        result["blocking_reason"] = blocker
    elif resolved_status == "blocked":
        result["blocking_reason"] = (
            f"{target.surface} version is {observed!r}; expected {target.expected!r}"
        )
    return result


def _list_value(value: object, key: int) -> object:
    if not isinstance(value, list):
        raise KeyError(key)
    return value[key]


def _mapping_value(value: object, key: object) -> object:
    if not isinstance(value, Mapping):
        raise KeyError(key)
    return value[key]


def _value_at_key(value: object, key: object) -> object:
    if isinstance(key, int):
        return _list_value(value, key)
    return _mapping_value(value, key)


def _json_value(path: Path, value_path: tuple[object, ...]) -> object:
    value: object = _json(path)
    for key in value_path:
        value = _value_at_key(value, key)
    return value


def _missing_json_projection(
    target: _ProjectionTarget, schema_optional: bool
) -> dict[str, str | None]:
    if schema_optional:
        return _projection(
            target,
            None,
            status="not_schema_supported",
        )
    return _projection(
        target,
        None,
        blocker=f"governed version field is missing: {target.path}",
    )


def _json_version_projection(
    repo_root: Path,
    target: _ProjectionTarget,
    value_path: tuple[object, ...],
    *,
    schema_optional: bool = False,
) -> dict[str, str | None]:
    path = repo_root / target.path
    if not path.is_file():
        return _projection(
            target,
            None,
            blocker=f"required governed version location is missing: {target.path}",
        )
    try:
        value = _json_value(path, value_path)
    except (KeyError, IndexError, TypeError):
        return _missing_json_projection(target, schema_optional)
    return _projection(target, str(value))


def _project_version(repo_root: Path) -> str:
    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.is_file():
        raise VersionAuditError("pyproject.toml is missing")
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    try:
        version = str(pyproject["project"]["version"])
    except KeyError as exc:
        raise VersionAuditError(
            "project.version is missing from pyproject.toml"
        ) from exc
    if _SEMVER.fullmatch(version) is None:
        raise VersionAuditError(f"project.version is not SemVer: {version!r}")
    return version


def _distribution_projections(
    repo_root: Path, version: str
) -> list[dict[str, str | None]]:
    return [
        _projection(
            _ProjectionTarget("python_package", "pyproject.toml", version), version
        ),
        _json_version_projection(
            repo_root,
            _ProjectionTarget(
                "claude_plugin",
                "integrations/claude-code/seshat-bi/.claude-plugin/plugin.json",
                version,
            ),
            value_path=("version",),
        ),
        _json_version_projection(
            repo_root,
            _ProjectionTarget(
                "claude_marketplace", ".claude-plugin/marketplace.json", version
            ),
            value_path=("metadata", "version"),
        ),
        _json_version_projection(
            repo_root,
            _ProjectionTarget(
                "claude_bundle_manifest",
                "integrations/claude-code/seshat-bi/bundle-manifest.json",
                version,
            ),
            value_path=("version",),
        ),
        _json_version_projection(
            repo_root,
            _ProjectionTarget(
                "codex_plugin",
                "integrations/codex/seshat-bi/.codex-plugin/plugin.json",
                version,
            ),
            value_path=("version",),
        ),
        _json_version_projection(
            repo_root,
            _ProjectionTarget(
                "codex_catalog", ".agents/plugins/marketplace.json", version
            ),
            value_path=("plugins", 0, "version"),
            schema_optional=True,
        ),
        _json_version_projection(
            repo_root,
            _ProjectionTarget(
                "codex_bundle_manifest",
                "integrations/codex/seshat-bi/bundle-manifest.json",
                version,
            ),
            value_path=("version",),
        ),
    ]


def _bundle_provenance_projection(
    repo_root: Path, *, platform: str, path: str
) -> dict[str, str | None]:
    target = _ProjectionTarget(f"{platform}_bundle_provenance", path, "valid")
    manifest_path = repo_root / path
    if not manifest_path.is_file():
        return _projection(
            target,
            None,
            blocker=f"required bundle manifest is missing: {path}",
        )
    try:
        manifest = _json(manifest_path)
        revision = validate_manifest_provenance(
            repo_root, manifest, label=f"{platform} bundle manifest"
        )
    except (ProvenanceError, VersionAuditError, OSError, ValueError) as exc:
        return _projection(target, None, blocker=str(exc))
    return _projection(target, "valid") | {"source_revision": revision}


def _bundle_provenance_projections(
    repo_root: Path,
) -> list[dict[str, str | None]]:
    manifests = {
        "claude": "integrations/claude-code/seshat-bi/bundle-manifest.json",
        "codex": "integrations/codex/seshat-bi/bundle-manifest.json",
    }
    projections = [
        _bundle_provenance_projection(repo_root, platform=platform, path=path)
        for platform, path in manifests.items()
    ]
    revisions = {
        str(item.get("source_revision"))
        for item in projections
        if item["status"] == "pass"
    }
    if len(revisions) > 1:
        for item in projections:
            item["status"] = "blocked"
            item["blocking_reason"] = (
                "Claude and Codex bundle source_revision provenance differs"
            )
    return projections


def _document_matches(path: Path, pattern: str) -> bool:
    if not path.is_file():
        return False
    return (
        re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE) is not None
    )


def _changelog_projection(repo_root: Path, version: str) -> dict[str, str | None]:
    changelog = repo_root / "CHANGELOG.md"
    matched = _document_matches(changelog, rf"^## \[{re.escape(version)}\](?:\s|$)")
    return _projection(
        _ProjectionTarget("changelog", "CHANGELOG.md", version),
        version if matched else None,
        blocker=None
        if matched
        else f"CHANGELOG.md has no exact [{version}] release heading",
    )


def _release_note_projection(repo_root: Path, version: str) -> dict[str, str | None]:
    note_version = governed_release_note_version(version)
    note_path = governed_release_note_path(version).as_posix()
    release_note = repo_root / note_path
    matched = _document_matches(
        release_note, rf"^# .*\bv{re.escape(note_version)}(?:\b|\.)"
    )
    return _projection(
        _ProjectionTarget("release_note", note_path, note_version),
        note_version if matched else None,
        blocker=None
        if matched
        else f"release note is missing or has no v{note_version} heading: {note_path}",
    )


def _tag_projection(
    version: str, revision: str, tag_map: Mapping[str, str]
) -> dict[str, str | None]:
    tag = f"v{version}"
    tagged_revision = tag_map.get(tag)
    if tagged_revision is None:
        return _projection(
            _ProjectionTarget("git_tag", tag, revision),
            None,
            status="pending_owner_action",
        )
    return _projection(
        _ProjectionTarget("git_tag", tag, revision),
        tagged_revision,
        blocker=None
        if tagged_revision == revision
        else (
            f"existing immutable tag {tag} points to {tagged_revision}, not {revision}"
        ),
    )


def _github_release_projection(
    version: str, github_release_tag: str | None
) -> dict[str, str | None]:
    tag = f"v{version}"
    return _projection(
        _ProjectionTarget("github_release", tag, tag),
        github_release_tag,
        status="pending_owner_action" if github_release_tag is None else None,
    )


def audit_versions(
    repo_root: Path,
    *,
    source_revision: str | None = None,
    tags: Mapping[str, str] | None = None,
    github_release_tag: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic, evidence-only version synchronization audit."""

    version = _project_version(repo_root)
    revision = source_revision or _git_revision(repo_root)
    tag_map = dict(tags) if tags is not None else _tag_map(repo_root)
    projections = _distribution_projections(repo_root, version)
    projections.extend(_bundle_provenance_projections(repo_root))
    projections.extend(
        [
            _changelog_projection(repo_root, version),
            _release_note_projection(repo_root, version),
            _tag_projection(version, revision, tag_map),
            _github_release_projection(version, github_release_tag),
        ]
    )
    projections.sort(key=lambda item: (str(item["surface"]), str(item["path"])))
    blockers = sorted(
        str(item["blocking_reason"])
        for item in projections
        if item["status"] == "blocked"
    )
    return {
        "status": "blocked" if blockers else "pass",
        "candidate_version": version,
        "source_revision": revision,
        "projections": projections,
        "blocking_reasons": blockers,
        "authority_disclaimer": (
            "Version synchronization evidence does not authorize tagging or "
            "publication."
        ),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when any governed projection is blocked",
    )
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = audit_versions(args.repo.resolve())
    except (
        VersionAuditError,
        OSError,
        ValueError,
        subprocess.CalledProcessError,
    ) as exc:
        print(
            json.dumps({"status": "blocked", "blocking_reasons": [str(exc)]}, indent=2)
        )
        return 1
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 1 if args.check and report["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
