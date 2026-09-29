"""The PII notice never implies clearance from a malformed flag or a stray path."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from seshat.pii_notice import build_pii_notice, render_markdown

pytestmark = pytest.mark.unit

_MAP = """\
columns:
  - source_name: email
    pii: "true"
    decision: keep
  - source_name: phone
    pii: 1
    decision: keep
  - source_name: amount
    pii: false
    decision: keep
"""


def _write(root: Path, table: str, body: str) -> None:
    d = root / "mappings" / table
    d.mkdir(parents=True)
    (d / "source-map.yaml").write_text(body, encoding="utf-8")


def test_a_non_boolean_pii_flag_is_a_gap_not_no_pii(tmp_path: Path) -> None:
    _write(tmp_path, "t", _MAP)

    notice = build_pii_notice(tmp_path, "t")
    text = render_markdown(notice)

    assert notice["no_pii"] is False
    assert {f["column"] for f in notice["findings"]} == {"email", "phone"}
    assert "No column in this table is flagged" not in text
    assert "GAP: email" in text and "NOT cleared" in text


def test_a_missing_pii_flag_is_a_gap(tmp_path: Path) -> None:
    _write(tmp_path, "t", "columns:\n  - source_name: email\n    decision: keep\n")

    assert build_pii_notice(tmp_path, "t")["no_pii"] is False


@pytest.mark.parametrize("table", ["../outside", "a/b", "..", "x\\y"])
def test_a_path_shaped_table_reads_nothing_outside_mappings(
    tmp_path: Path, table: str
) -> None:
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "source-map.yaml").write_text(
        "columns:\n  - source_name: a\n    pii: false\n", encoding="utf-8"
    )
    (tmp_path / "mappings").mkdir()

    notice = build_pii_notice(tmp_path, table)

    assert notice["document_gap"] is not None
    assert notice["no_pii"] is False


def test_write_refuses_a_path_shaped_table(tmp_path: Path) -> None:
    from seshat.cli.commands.pii_notice import pii_notice_main

    (tmp_path / "mappings").mkdir()
    (tmp_path / "outside").mkdir()
    args = argparse.Namespace(
        repo=str(tmp_path), table="../outside", write=True, output_format="text"
    )

    assert pii_notice_main(args) == 1
    assert not (tmp_path / "outside" / "pii-touch-notice.md").exists()


def test_drift_semantics_refuses_a_non_boolean_pii_flag(tmp_path: Path) -> None:
    from seshat.drift_semantics import load_drift_semantics

    path = tmp_path / "source-map.yaml"
    path.write_text(
        'columns:\n  - source_name: email\n    pii: "true"\n    decision: drop\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not a boolean"):
        load_drift_semantics(path)
