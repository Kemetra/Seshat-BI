"""CLI verb tests for seshat xray / seshat model-diff (Task 6)."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from seshat.cli.commands.xray import model_diff_main, xray_main
from tests.unit._gitfix import commit_all, make_git_repo

pytestmark = pytest.mark.unit

TABLE = "table Sales\n\tmeasure Revenue = SUM(Sales[amount])\n\tcolumn amount\n"


def _args(repo: Path, **extra: object) -> argparse.Namespace:
    return argparse.Namespace(repo=str(repo), output_format="json", **extra)


def _model_repo(tmp_path: Path) -> Path:
    repo = make_git_repo(tmp_path)
    tables = repo / "M.SemanticModel" / "definition" / "tables"
    tables.mkdir(parents=True)
    (tables / "Sales.tmdl").write_text(TABLE, encoding="utf-8")
    commit_all(repo, "model v1")
    return repo


def test_xray_completed_exit_zero_with_findings(tmp_path, capsys):
    repo = _model_repo(tmp_path)
    assert xray_main(_args(repo)) == 0
    out = capsys.readouterr().out
    assert '"outcome":"completed"' in out
    assert '"report_scanned":false' in out


def test_xray_blocked_when_no_model(tmp_path, capsys):
    repo = make_git_repo(tmp_path)
    (repo / "README.md").write_text("empty\n", encoding="utf-8")
    commit_all(repo, "no model")
    assert xray_main(_args(repo)) == 3
    out = capsys.readouterr().out
    assert '"code":"XR001"' in out


def test_xray_report_scanned_false_downgrades(tmp_path, capsys):
    repo = _model_repo(tmp_path)
    xray_main(_args(repo))
    out = capsys.readouterr().out
    assert "no report scanned" in out


def test_model_diff_against_prior_commit(tmp_path, capsys):
    repo = _model_repo(tmp_path)
    tables = repo / "M.SemanticModel" / "definition" / "tables"
    (tables / "Sales.tmdl").write_text(
        "table Sales\n\tmeasure Revenue = SUM(Sales[amount]) + 1\n\tcolumn amount\n",
        encoding="utf-8",
    )
    commit_all(repo, "model v2")
    assert model_diff_main(_args(repo, base="HEAD~1")) == 0
    out = capsys.readouterr().out
    assert '"outcome":"completed"' in out
    assert '"semantic":1' in out
    assert "logic changed" in out


def test_model_diff_bad_ref_blocked(tmp_path, capsys):
    repo = _model_repo(tmp_path)
    assert model_diff_main(_args(repo, base="no-such-ref")) == 3
    out = capsys.readouterr().out
    assert '"code":"XR002"' in out


def test_json_payload_is_ascii_and_compact(tmp_path, capsys):
    repo = _model_repo(tmp_path)
    xray_main(_args(repo))
    out = capsys.readouterr().out.strip()
    assert out == out.encode("ascii", errors="ignore").decode("ascii")
    assert '": ' not in out  # compact separators


def test_verbs_registered_in_real_parser(tmp_path):
    from seshat.cli.parser import _build_parser

    parser = _build_parser()
    args = parser.parse_args(["xray", "--format", "json"])
    assert args.output_format == "json"
    args = parser.parse_args(["model-diff", "--base", "main"])
    assert args.base == "main"


def test_diff_working_tree_change_visible_before_commit(tmp_path, capsys):
    # Head side reads the WORKING TREE (tracked files), so an uncommitted
    # edit to a tracked model file participates in the diff.
    repo = _model_repo(tmp_path)
    tables = repo / "M.SemanticModel" / "definition" / "tables"
    (tables / "Sales.tmdl").write_text(
        "table Sales\n\tmeasure Revenue = 0\n\tcolumn amount\n", encoding="utf-8"
    )
    subprocess.run(
        ["git", "add", "-A"], cwd=repo, check=True, capture_output=True
    )
    assert model_diff_main(_args(repo, base="HEAD")) == 0
    assert '"semantic":1' in capsys.readouterr().out
