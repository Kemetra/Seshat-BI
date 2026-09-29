from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from scripts.inspect_release_artifacts import (
    ArtifactInspectionError,
    _validate_metadata,
    scan_content,
    validate_sdist_inventory,
    validate_wheel_inventory,
)

pytestmark = pytest.mark.unit


def _metadata() -> dict:
    return {
        "name": "seshat-bi",
        "version": "0.2.0",
        "summary": "Governed BI readiness",
        "requires_python": ">=3.13",
        "license_expression": "Apache-2.0",
        "description_content_type": "text/markdown",
        "requires_dist": ["pyyaml>=6", "pytest>=8; extra == 'dev'"],
        "project_urls": [
            f"{label}, https://example.invalid/{label.casefold()}"
            for label in (
                "Changelog",
                "Documentation",
                "Homepage",
                "Issues",
                "Repository",
            )
        ],
    }


def test_public_metadata_requires_urls_license_readme_and_safe_dependencies() -> None:
    _validate_metadata(_metadata())
    bad = _metadata()
    bad["requires_dist"] = ["pyyaml>=6", "pytest>=8"]
    with pytest.raises(ArtifactInspectionError, match="became mandatory"):
        _validate_metadata(bad)
    bad = _metadata()
    bad["project_urls"] = []
    with pytest.raises(ArtifactInspectionError, match="project URL"):
        _validate_metadata(bad)


_ROOT = Path(__file__).resolve().parents[2]
_FORCE_INCLUDE = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
    "tool"
]["hatch"]["build"]["targets"]["wheel"]["force-include"]


def _as_members(source: str, destination: str) -> list[str]:
    """A force-include destination as wheel members: the file itself, or -- for
    a directory source -- one representative file under it."""
    if (_ROOT / source).is_dir():
        return [f"{destination}/placeholder.txt"]
    return [destination]


# A complete, valid wheel member list -- packages, every force-include
# destination read INDEPENDENTLY from pyproject here (not via the inspector's
# own helper), the Studio UI entry page and one bundled asset, plus the
# entry-point and license metadata. Every wheel-inventory test derives its
# fixture from this.
_VALID_WHEEL_INVENTORY = (
    "seshat/__init__.py",
    "retail/__init__.py",
    *(
        member
        for source, destination in _FORCE_INCLUDE.items()
        for member in _as_members(source, destination)
    ),
    "seshat/studio/static/index.html",
    "seshat/studio/static/assets/index-abc123.js",
    "seshat_bi-0.2.0.dist-info/entry_points.txt",
    "seshat_bi-0.2.0.dist-info/licenses/LICENSE",
)


def _wheel_inventory_without(fragment: str) -> list[str]:
    """The valid inventory minus every member whose name contains ``fragment``."""
    return [name for name in _VALID_WHEEL_INVENTORY if fragment not in name]


def test_wheel_inventory_requires_packages_entrypoints_and_license() -> None:
    valid = list(_VALID_WHEEL_INVENTORY)
    validate_wheel_inventory(valid)
    with pytest.raises(ArtifactInspectionError, match="development-only"):
        validate_wheel_inventory([*valid, "tests/test_release.py"])
    disguised_entry_points = [
        name.replace("entry_points.txt", "entry_points.txt.bak") for name in valid
    ]
    with pytest.raises(ArtifactInspectionError, match="entry-point"):
        validate_wheel_inventory(disguised_entry_points)


def test_wheel_inventory_requires_pack_runtime_schemas() -> None:
    """The `pack` family reads these schemas at runtime; they reach the wheel
    only via force-include, so a dropped entry must fail the artifact gate
    rather than silently reintroduce the clean-install FileNotFoundError."""
    validate_wheel_inventory(list(_VALID_WHEEL_INVENTORY))
    without_schema = _wheel_inventory_without("seshat-pack-registry.schema.json")
    with pytest.raises(ArtifactInspectionError, match="required package data"):
        validate_wheel_inventory(without_schema)


def test_wheel_inventory_requires_stage1_templates() -> None:
    """The three Stage-1 blank templates reach the wheel only via force-include
    (issue #339). A dropped entry must fail the artifact gate rather than
    silently reintroduce the pip-user 'nothing to copy' bug."""
    validate_wheel_inventory(list(_VALID_WHEEL_INVENTORY))
    without_profile = _wheel_inventory_without("stage1_templates/source-profile.md")
    with pytest.raises(ArtifactInspectionError, match="required package data"):
        validate_wheel_inventory(without_profile)


def test_wheel_inventory_requires_the_studio_ui() -> None:
    """The v1.0.0 incident (#623): a wheel with the `seshat-studio` launcher and no
    frontend passed every gate. The inspector itself must now refuse it."""
    for fragment in ("studio/static/index.html", "studio/static/assets/"):
        with pytest.raises(ArtifactInspectionError, match="required package data"):
            validate_wheel_inventory(_wheel_inventory_without(fragment))


@pytest.mark.parametrize(
    "destination",
    sorted(_FORCE_INCLUDE.values()),
)
def test_wheel_inventory_requires_every_force_include_destination(
    destination: str,
) -> None:
    """Tripwire: EVERY force-include destination (rule-fixes.yaml, kit-source.yaml,
    design templates, governed projects, statistical schemas, ...) is required,
    so dropping any one of them from the build fails the artifact gate."""
    stripped = [
        name
        for name in _VALID_WHEEL_INVENTORY
        if name != destination and not name.startswith(destination + "/")
    ]
    with pytest.raises(ArtifactInspectionError, match="required package data"):
        validate_wheel_inventory(stripped)


def test_sdist_inventory_is_rebuildable_without_repo_integrations() -> None:
    valid = [
        "seshat_bi-0.2.0/LICENSE",
        "seshat_bi-0.2.0/README.md",
        "seshat_bi-0.2.0/pyproject.toml",
        "seshat_bi-0.2.0/src/seshat/__init__.py",
        "seshat_bi-0.2.0/src/retail/__init__.py",
    ]
    validate_sdist_inventory(valid)
    with pytest.raises(ArtifactInspectionError, match="unrelated"):
        validate_sdist_inventory([*valid, "seshat_bi-0.2.0/specs/feature/spec.md"])


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("pkg/config.txt", b"ghp_abcdefghijklmnopqrstuvwxyz123456", "GitHub token"),
        ("pkg/config.txt", b"C:\\Users\\alice\\secret", "Windows user path"),
        ("pkg/config.txt", b"CLIENT_CONFIDENTIAL", "client-confidential"),
        ("pkg/.env", b"SAFE=fixture", "prohibited archive path"),
    ],
)
def test_secret_local_path_and_prohibited_filename_scan(
    name: str, content: bytes, message: str
) -> None:
    with pytest.raises(ArtifactInspectionError, match=message):
        scan_content(name, content)
