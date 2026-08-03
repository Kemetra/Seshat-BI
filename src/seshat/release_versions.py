"""Shipped authority for Seshat BI distribution-version projections."""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


class VersionAuditError(ValueError):
    """The version source itself is missing or invalid."""


@dataclass(frozen=True)
class ProjectionTarget:
    """One governed version projection and its expected value."""

    surface: str
    path: str
    expected: str


def load_json_object(path: Path) -> Mapping[str, Any]:
    """Load one JSON object or fail with a governed input defect."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise VersionAuditError(f"{path} must contain a JSON object")
    return value


def projection(
    target: ProjectionTarget,
    observed: str | None,
    *,
    status: str | None = None,
    blocker: str | None = None,
) -> dict[str, str | None]:
    """Build one categorical distribution-version projection."""

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


def _value_at_key(value: object, key: object) -> object:
    if isinstance(key, int):
        if not isinstance(value, list):
            raise KeyError(key)
        return value[key]
    if not isinstance(value, Mapping):
        raise KeyError(key)
    return value[key]


def _json_value(path: Path, value_path: tuple[object, ...]) -> object:
    value: object = load_json_object(path)
    for key in value_path:
        value = _value_at_key(value, key)
    return value


def _missing_json_projection(
    target: ProjectionTarget, schema_optional: bool
) -> dict[str, str | None]:
    if schema_optional:
        return projection(target, None, status="not_schema_supported")
    return projection(
        target,
        None,
        blocker=f"governed version field is missing: {target.path}",
    )


def _json_version_projection(
    repo_root: Path,
    target: ProjectionTarget,
    value_path: tuple[object, ...],
    *,
    schema_optional: bool = False,
) -> dict[str, str | None]:
    path = repo_root / target.path
    if not path.is_file():
        return projection(
            target,
            None,
            blocker=f"required governed version location is missing: {target.path}",
        )
    try:
        value = _json_value(path, value_path)
    except (KeyError, IndexError, TypeError):
        return _missing_json_projection(target, schema_optional)
    return projection(target, str(value))


def project_version(repo_root: Path) -> str:
    """Read and validate the canonical project version."""

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


def distribution_projections(
    repo_root: Path, version: str
) -> list[dict[str, str | None]]:
    """Project the canonical version into every shipped distribution surface."""

    return [
        projection(
            ProjectionTarget("python_package", "pyproject.toml", version), version
        ),
        _json_version_projection(
            repo_root,
            ProjectionTarget(
                "claude_plugin",
                "integrations/claude-code/seshat-bi/.claude-plugin/plugin.json",
                version,
            ),
            value_path=("version",),
        ),
        _json_version_projection(
            repo_root,
            ProjectionTarget(
                "claude_marketplace", ".claude-plugin/marketplace.json", version
            ),
            value_path=("metadata", "version"),
        ),
        _json_version_projection(
            repo_root,
            ProjectionTarget(
                "claude_bundle_manifest",
                "integrations/claude-code/seshat-bi/bundle-manifest.json",
                version,
            ),
            value_path=("version",),
        ),
        _json_version_projection(
            repo_root,
            ProjectionTarget(
                "codex_plugin",
                "integrations/codex/seshat-bi/.codex-plugin/plugin.json",
                version,
            ),
            value_path=("version",),
        ),
        _json_version_projection(
            repo_root,
            ProjectionTarget(
                "codex_catalog", ".agents/plugins/marketplace.json", version
            ),
            value_path=("plugins", 0, "version"),
            schema_optional=True,
        ),
        _json_version_projection(
            repo_root,
            ProjectionTarget(
                "codex_bundle_manifest",
                "integrations/codex/seshat-bi/bundle-manifest.json",
                version,
            ),
            value_path=("version",),
        ),
    ]


def audit_distribution_versions(repo_root: Path) -> dict[str, Any]:
    """Return the shipped, deterministic distribution-version audit."""

    version = project_version(repo_root)
    projections = distribution_projections(repo_root, version)
    blockers = sorted(
        str(item["blocking_reason"])
        for item in projections
        if item["status"] == "blocked"
    )
    return {
        "status": "blocked" if blockers else "pass",
        "candidate_version": version,
        "projections": projections,
        "blocking_reasons": blockers,
    }
