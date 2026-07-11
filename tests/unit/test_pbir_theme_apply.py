"""Unit tests for the PBIR theme-application writer (adapter increment A)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from seshat.pbir_theme_apply import PbirApplyError, apply_theme

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "pbir" / "theme_apply"

THEME = {
    "name": "executive-dark",
    "dataColors": ["#A5E3E9", "#1C6B73"],
    "background": "#12263A",
    "foreground": "#F2F6FA",
}


def _report_copy(tmp: Path) -> Path:
    """A writable copy of the committed fixture report tree."""
    dst = tmp / "Rpt.Report"
    shutil.copytree(FIXTURES, dst)
    return dst


def _theme_file(tmp: Path, theme: dict | str = THEME) -> Path:
    p = tmp / "theme.json"
    p.write_text(
        theme if isinstance(theme, str) else json.dumps(theme), encoding="utf-8"
    )
    return p


def test_applies_theme_writes_resource_and_reference(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    written = apply_theme(_theme_file(tmp_path), report)
    base = report / "StaticResources/SharedResources/BaseThemes/executive-dark.json"
    assert base in written
    assert base.exists()
    report_json = json.loads((report / "definition/report.json").read_text())
    assert report_json["themeCollection"]["baseTheme"]["name"] == "executive-dark"
    pkg = next(
        p for p in report_json["resourcePackages"] if p["name"] == "SharedResources"
    )
    assert pkg["items"][0]["path"] == "BaseThemes/executive-dark.json"


def test_apply_is_idempotent(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    tf = _theme_file(tmp_path)
    apply_theme(tf, report)
    first = (report / "definition/report.json").read_text()
    apply_theme(tf, report, force=True)
    assert (report / "definition/report.json").read_text() == first


def test_schema_is_preserved(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    apply_theme(_theme_file(tmp_path), report)
    report_json = json.loads((report / "definition/report.json").read_text())
    assert report_json["$schema"].endswith("report/3.3.0/schema.json")


def test_invalid_theme_json_raises(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    with pytest.raises(PbirApplyError, match="JSON"):
        apply_theme(_theme_file(tmp_path, "{not json"), report)


def test_theme_without_name_raises(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    with pytest.raises(PbirApplyError, match="name"):
        apply_theme(_theme_file(tmp_path, {"dataColors": []}), report)


def test_missing_theme_file_raises(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    with pytest.raises(PbirApplyError, match="theme file not found"):
        apply_theme(tmp_path / "nope.json", report)


def test_missing_report_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(PbirApplyError, match="report dir not found"):
        apply_theme(_theme_file(tmp_path), tmp_path / "nope.Report")


def test_theme_name_traversal_refused(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    bad = _theme_file(tmp_path, {"name": "../../evil", "dataColors": []})
    with pytest.raises(PbirApplyError, match="safe slug"):
        apply_theme(bad, report)


def test_refuses_overwrite_of_different_base_theme(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    # a base theme already exists at the target name with different content
    target = report / "StaticResources/SharedResources/BaseThemes/executive-dark.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"name": "executive-dark", "dataColors": ["#000"]}))
    with pytest.raises(PbirApplyError, match="different content"):
        apply_theme(_theme_file(tmp_path), report)
    # with force it succeeds
    apply_theme(_theme_file(tmp_path), report, force=True)
