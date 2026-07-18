"""CLI seam for `seshat mapping-mirror` (issue #326)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _run(argv: list[str]) -> int:
    from seshat.cli import main

    return main(argv)


def test_mapping_mirror_writes_a_stub_for_a_mapped_table(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "mappings" / "orders_raw").mkdir(parents=True)

    exit_code = _run(
        ["mapping-mirror", "--repo", str(tmp_path), "--table", "orders_raw"]
    )

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "unresolved-questions.md" in out
    assert "open-stub" in out
    assert (tmp_path / "mappings" / "orders_raw" / "unresolved-questions.md").is_file()


def test_mapping_mirror_keeps_an_existing_ledger(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    mapping_dir = tmp_path / "mappings" / "orders_raw"
    mapping_dir.mkdir(parents=True)
    ledger = mapping_dir / "unresolved-questions.md"
    ledger.write_text("Gate status: OPEN\nhand-authored\n", encoding="utf-8")

    exit_code = _run(
        ["mapping-mirror", "--repo", str(tmp_path), "--table", "orders_raw"]
    )

    assert exit_code == 0
    assert "already-present" in capsys.readouterr().out
    assert ledger.read_text(encoding="utf-8") == "Gate status: OPEN\nhand-authored\n"


def test_mapping_mirror_refuses_an_unmapped_table(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = _run(
        ["mapping-mirror", "--repo", str(tmp_path), "--table", "orders_raw"]
    )

    assert exit_code == 1
    assert "[refused]" in capsys.readouterr().err
