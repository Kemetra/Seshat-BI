"""Windows-safety coverage for the ecosystem artifacts (spec 120, T102).

Committed artifacts must survive the Windows 260-character MAX_PATH limit
from a realistic checkout root, and every committed or generated text
artifact must be UTF-8 without a BOM with no machine-local absolute paths.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]
# A pessimistic Windows checkout prefix, e.g. C:\Users\somebody\Documents\Seshat_BI
_WINDOWS_PREFIX = len(r"C:\Users\a-long-username\Documents\Seshat_BI") + 1
_MAX_PATH = 260

_NEW_COMMITTED_ROOTS = (
    "schemas",
    "packs",
    "benchmark",
    "docs/ecosystem",
    "docs/contributing",
    "integrations/github-action",
    ".github/ISSUE_TEMPLATE",
)
_TEXT_SUFFIXES = {".yaml", ".yml", ".md", ".json", ".csv", ".txt", ".ps1"}


def _committed_files() -> list[Path]:
    files: list[Path] = []
    for root in _NEW_COMMITTED_ROOTS:
        base = _REPO / root
        if base.is_dir():
            files.extend(path for path in base.rglob("*") if path.is_file())
    assert files, "expected committed ecosystem artifacts to exist"
    return files


def test_committed_artifact_paths_fit_windows_max_path() -> None:
    for path in _committed_files():
        relative = path.relative_to(_REPO).as_posix()
        assert _WINDOWS_PREFIX + len(relative) < _MAX_PATH, relative


def test_committed_text_artifacts_are_utf8_without_bom() -> None:
    for path in _committed_files():
        if path.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{path} has a BOM"
        raw.decode("utf-8")  # raises on non-UTF-8


def _write_table(root: Path) -> None:
    table_dir = root / "mappings/orders"
    table_dir.mkdir(parents=True)
    (table_dir / "source-profile.md").write_text("profile\n", encoding="utf-8")
    (table_dir / "readiness-status.yaml").write_text(
        """\
table: orders
current_stage: mapping_ready
stages:
  source_ready:
    status: pass
    evidence: [mappings/orders/source-profile.md]
    blocking_reasons: []
  mapping_ready:
    status: blocked
    evidence: []
    blocking_reasons: [grain needs owner approval]
blocking_reasons: [grain needs owner approval]
approvals: []
next_action: Resolve grain with the data owner.
""",
        encoding="utf-8",
    )


def test_generated_artifacts_are_utf8_no_bom_with_relative_paths(
    tmp_path: Path,
) -> None:
    from seshat.cli import main

    _write_table(tmp_path)
    assert main(["passport", "export", "--repo", str(tmp_path)]) == 0
    assert main(["explorer", "build", "--repo", str(tmp_path)]) == 0
    assert (
        main(
            [
                "pack",
                "scaffold",
                "--repo",
                str(tmp_path),
                "--id",
                "acme.windows",
                "--category",
                "kpi",
                "--owner",
                "Casey Analyst",
            ]
        )
        == 0
    )
    generated = [
        path
        for path in tmp_path.rglob("*")
        if path.is_file() and path.suffix.lower() in (".json", ".html", ".yaml", ".csv")
    ]
    assert generated
    for path in generated:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{path} has a BOM"
        text = raw.decode("utf-8")
        assert str(tmp_path) not in text, f"{path} leaks an absolute path"
        relative = path.relative_to(tmp_path).as_posix()
        assert _WINDOWS_PREFIX + len(relative) < _MAX_PATH, relative
