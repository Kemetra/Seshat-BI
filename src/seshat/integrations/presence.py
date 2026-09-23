"""Installed-state detection for the curated integration stack.

Extracted from :mod:`seshat.integrations.installer` so the presence rules live in
one place: a partial install is never `present`, and nothing here imports or
executes third-party code to answer a status question.
"""

from __future__ import annotations

import sys
from pathlib import Path

from seshat.integrations.catalog import (
    ENV_DIR,
    NODE_DIR,
    SKILLS_DIR,
    Component,
    SourceType,
)

# Bundled skill paths, validated locally rather than downloaded.
_BUNDLED_SKILLS = {
    "seshat-dagster-workflows": (
        "integrations/claude-code/seshat-bi/skills/dagster-workflows/SKILL.md"
    ),
    "seshat-dagster-adapter": "src/seshat/dagster_adapter/__init__.py",
}


def _skill_dir(item: Component) -> Path:
    return SKILLS_DIR / item.id


def _missing_required_payload(root: Path, item: Component) -> tuple[str, ...]:
    """Catalog-declared payload files absent below ``root``."""
    return tuple(
        required
        for required in item.required_paths
        if not (root / Path(*required.split("/"))).is_file()
    )


def _venv_python(env: Path) -> Path:
    if sys.platform == "win32":
        return env / "Scripts/python.exe"
    return env / "bin/python"


def _profile_env(profile: str) -> Path:
    return ENV_DIR / profile


def _is_installed(root: Path, item: Component, profile: str) -> bool:
    """Whether the component is fully installed -- never partially.

    A skill bundle counts only when its marker file is on disk, and a Python
    component only when its profile interpreter exists AND the distribution has
    metadata inside it. A half-finished clone or a venv without the package
    reports as not installed, so it is re-planned rather than claimed.
    """
    if item.source_type is SourceType.BUNDLED:
        relative = _BUNDLED_SKILLS.get(item.id)
        return bool(relative) and (root / relative).is_file()
    if item.mcp_server:
        # An MCP component is installed when its registration marker exists,
        # whatever index its version came from.
        return (root / NODE_DIR / item.id / ".seshat-installed").is_file()
    if item.source_type is SourceType.GITHUB:
        target = root / _skill_dir(item)
        marker = target / ".seshat-installed"
        return marker.is_file() and not _missing_required_payload(target, item)
    interpreter = root / _venv_python(_profile_env(profile))
    if not interpreter.is_file():
        return False
    return _distribution_present(root / _profile_env(profile), item.coordinate)


# Where a venv keeps installed distribution metadata, on Windows and on POSIX.
_SITE_PACKAGES = ("Lib/site-packages", "lib/python*/site-packages")


def _canonical_dist(name: str) -> str:
    """PEP 503-style canonical form, so `dbt-core` matches `dbt_core.dist-info`."""
    return name.replace("-", "_").lower()


def _distribution_present(env: Path, dist: str) -> bool:
    """Whether `dist` has install metadata inside `env`.

    Reads `*.dist-info` directory names rather than importing anything: an
    import would execute third-party code just to answer a status question.
    """
    canonical = _canonical_dist(dist)
    return any(
        _canonical_dist(info.name.split("-", 1)[0]) == canonical
        for pattern in _SITE_PACKAGES
        for site in env.glob(pattern)
        for info in site.glob("*.dist-info")
    )
