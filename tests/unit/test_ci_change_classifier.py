from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
CLASSIFIER = ROOT / "scripts" / "classify_ci_changes.py"


def _classify(tmp_path: Path, *paths: str) -> dict[str, str]:
    changed = tmp_path / "changed-files.txt"
    changed.write_text("".join(f"{path}\n" for path in paths), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(CLASSIFIER), "--changed-files", str(changed)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return dict(line.split("=", 1) for line in result.stdout.splitlines())


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (
            "docs/integrations/dbt-adapter.md",
            {"code_changed": "false", "contracts_required": "true"},
        ),
        (
            "README.md",
            {"code_changed": "false", "contracts_required": "true"},
        ),
        (
            "docs/architecture/pipeline.png",
            {"code_changed": "false", "contracts_required": "false"},
        ),
        (
            ".github/pull_request_template.md",
            {"code_changed": "false", "contracts_required": "false"},
        ),
        (
            "src/seshat/runner.py",
            {"code_changed": "true", "contracts_required": "true"},
        ),
    ],
)
def test_changed_path_is_routed_to_the_required_ci_depth(
    tmp_path: Path,
    path: str,
    expected: dict[str, str],
) -> None:
    """A path must not bypass the contract depth its consumers require."""

    assert _classify(tmp_path, path) == expected


def test_mixed_prose_and_code_change_fails_closed_to_the_full_suite(
    tmp_path: Path,
) -> None:
    assert _classify(tmp_path, "docs/guide.md", "src/seshat/core.py") == {
        "code_changed": "true",
        "contracts_required": "true",
    }


def test_an_empty_change_list_fails_closed_to_the_full_suite(tmp_path: Path) -> None:
    assert _classify(tmp_path) == {
        "code_changed": "true",
        "contracts_required": "true",
    }
