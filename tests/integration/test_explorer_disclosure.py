"""SC-011 disclosure and zero-source-write coverage for the explorer."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from seshat.cli import main

pytestmark = pytest.mark.integration


def _write_table(root: Path, *, blocked_reason: str | None = None) -> None:
    table_dir = root / "mappings/orders"
    table_dir.mkdir(parents=True)
    (table_dir / "source-profile.md").write_text("profile\n", encoding="utf-8")
    reason = blocked_reason or "grain needs owner approval"
    (table_dir / "readiness-status.yaml").write_text(
        f"""\
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
    blocking_reasons: ["{reason}"]
blocking_reasons: ["{reason}"]
approvals: []
next_action: Resolve grain with the data owner.
""",
        encoding="utf-8",
    )


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".seshat-output" not in path.parts
    }


def test_generated_page_is_disclosure_safe_with_zero_source_writes(
    tmp_path: Path,
) -> None:
    _write_table(tmp_path)
    before = _snapshot(tmp_path)
    assert main(["explorer", "build", "--repo", str(tmp_path)]) == 0
    assert _snapshot(tmp_path) == before
    html = (tmp_path / ".seshat-output/explorer/index.html").read_text(encoding="utf-8")
    assert not re.search(r"postgres(?:ql)?://", html, re.IGNORECASE)
    assert str(tmp_path) not in html
    assert not re.search(r"[A-Za-z]:\\\\", html)
    assert "score" not in html.lower().replace("no readiness score", "")


def test_disclosure_finding_blocks_generation_entirely(tmp_path: Path) -> None:
    _write_table(
        tmp_path,
        blocked_reason="dsn postgresql://user:pw@example/db is unreachable",
    )
    assert main(["explorer", "build", "--repo", str(tmp_path)]) == 1
    assert not (tmp_path / ".seshat-output/explorer/index.html").exists()


def test_uncontained_output_is_refused(tmp_path: Path) -> None:
    _write_table(tmp_path)
    assert (
        main(
            [
                "explorer",
                "build",
                "--repo",
                str(tmp_path),
                "--output",
                "docs/explorer.html",
            ]
        )
        == 2
    )
    assert not (tmp_path / "docs/explorer.html").exists()
