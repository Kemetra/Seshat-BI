from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from scripts.inspect_release_artifacts import (
    ArtifactInspectionError,
    _compare_normalized_wheels,
    inspect_release_artifacts,
)

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]


def test_real_wheel_sdist_and_isolated_rebuild(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--sdist", "--outdir", str(dist)],
        cwd=ROOT,
        check=True,
    )
    report = inspect_release_artifacts(dist, run_twine=True, rebuild_sdist=True)
    assert report["status"] == "pass"
    assert report["twine_strict"] == "pass"
    assert report["isolated_sdist_rebuild"] == "pass"


def test_normalized_wheel_parity_rejects_governed_content_change(
    tmp_path: Path,
) -> None:
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=ROOT,
        check=True,
    )
    original = next(dist.glob("*.whl"))
    changed = tmp_path / "changed.whl"
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(changed, "w") as target:
        for info in source.infolist():
            data = source.read(info)
            if info.filename == "seshat/__init__.py":
                data += b"\n# changed\n"
            target.writestr(info, data)
    with pytest.raises(ArtifactInspectionError, match="governed contents differ"):
        _compare_normalized_wheels(original, changed)
