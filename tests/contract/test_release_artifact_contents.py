from __future__ import annotations

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


def test_wheel_inventory_requires_packages_entrypoints_and_license() -> None:
    valid = [
        "seshat/__init__.py",
        "retail/__init__.py",
        "seshat_bi-0.2.0.dist-info/entry_points.txt",
        "seshat_bi-0.2.0.dist-info/licenses/LICENSE",
    ]
    validate_wheel_inventory(valid)
    with pytest.raises(ArtifactInspectionError, match="development-only"):
        validate_wheel_inventory([*valid, "tests/test_release.py"])
    disguised_entry_points = [
        name.replace("entry_points.txt", "entry_points.txt.bak") for name in valid
    ]
    with pytest.raises(ArtifactInspectionError, match="entry-point"):
        validate_wheel_inventory(disguised_entry_points)


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
