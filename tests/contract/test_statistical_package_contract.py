from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_statistics_extras_are_exact_and_base_stays_pyyaml_only() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["dependencies"] == ["pyyaml>=6"]
    extras = project["project"]["optional-dependencies"]
    assert extras["stats"] == [
        "numpy==2.5.1",
        "scipy==1.18.0",
        "statsmodels==0.14.6",
    ]
    assert extras["stats-change"] == ["ruptures==1.1.10"]


def test_importing_seshat_does_not_load_optional_statistics_packages() -> None:
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import seshat, sys; "
                "forbidden = {'numpy', 'scipy', 'statsmodels', 'ruptures'}; "
                "loaded = forbidden.intersection(sys.modules); "
                "assert not loaded, sorted(loaded)"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 0, result.stderr
