from __future__ import annotations

import json
import subprocess
import tarfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "npm" / "stage-release-packages.js"


def _packaged_manifest(tarball: Path) -> dict:
    with tarfile.open(tarball, "r:gz") as archive:
        member = archive.getmember("package/package.json")
        stream = archive.extractfile(member)
        assert stream is not None
        return json.loads(stream.read().decode("utf-8"))


def test_release_stager_builds_version_locked_scoped_and_alias_tarballs(
    tmp_path: Path,
) -> None:
    """The published alias must depend on the exact scoped candidate version."""

    output = tmp_path / "npm-release"
    completed = subprocess.run(
        ["node", str(SCRIPT), "--output", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    scoped_tarballs = list((output / "scoped").glob("*.tgz"))
    alias_tarballs = list((output / "alias").glob("*.tgz"))
    assert len(scoped_tarballs) == 1
    assert len(alias_tarballs) == 1

    root_manifest = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    scoped = _packaged_manifest(scoped_tarballs[0])
    alias = _packaged_manifest(alias_tarballs[0])

    assert scoped["name"] == "@kemetra/seshat-bi"
    assert scoped["version"] == root_manifest["version"]
    assert alias["name"] == "seshat-bi"
    assert alias["version"] == root_manifest["version"]
    assert alias["dependencies"] == {"@kemetra/seshat-bi": root_manifest["version"]}
