import argparse
from pathlib import Path

import pytest

from seshat.cli.commands.dashboard import dashboard_main
from seshat.cli.parser import _build_parser

pytestmark = pytest.mark.unit


def _make_repo(tmp_path: Path) -> Path:
    d = tmp_path / "mappings" / "orders"
    d.mkdir(parents=True)
    (d / "readiness-status.yaml").write_text(
        'table: "bronze.orders"\ncurrent_stage: "source_ready"\n'
        'stages:\n  source_ready:\n    status: "pass"\n'
        "    evidence: []\n    blocking_reasons: []\n"
        'next_action: "next"\n',
        encoding="utf-8",
    )
    return tmp_path


def test_parser_registers_dashboard_with_flags():
    parser = _build_parser()
    ns = parser.parse_args(["dashboard", "--repo", "x", "--out", "y", "--no-open"])
    assert ns.command == "dashboard"
    assert ns.repo == "x" and ns.out == "y" and ns.no_open is True


def test_dashboard_main_writes_and_returns_zero(tmp_path, capsys):
    repo = _make_repo(tmp_path)
    out = tmp_path / "d.html"
    args = argparse.Namespace(repo=str(repo), out=str(out), no_open=True)
    rc = dashboard_main(args)
    assert rc == 0
    assert out.exists()
    captured = capsys.readouterr().out
    assert str(out) in captured
    assert captured.isascii()  # console output must be ASCII


def test_dashboard_main_oserror_returns_one(tmp_path, capsys):
    repo = _make_repo(tmp_path)
    blocker = tmp_path / "afile"
    blocker.write_text("x", encoding="utf-8")
    args = argparse.Namespace(
        repo=str(repo), out=str(blocker / "nested" / "index.html"), no_open=True
    )
    rc = dashboard_main(args)
    assert rc == 1


def test_no_open_does_not_open_browser(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("webbrowser.open", lambda uri: calls.append(uri))

    repo = _make_repo(tmp_path)
    out = tmp_path / "d.html"
    args = argparse.Namespace(repo=str(repo), out=str(out), no_open=True)
    rc = dashboard_main(args)

    assert rc == 0
    assert out.exists()
    assert calls == []


def test_open_branch_opens_file_uri(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("webbrowser.open", lambda uri: calls.append(uri))

    repo = _make_repo(tmp_path)
    out = tmp_path / "d.html"
    args = argparse.Namespace(repo=str(repo), out=str(out), no_open=False)
    rc = dashboard_main(args)

    assert rc == 0
    assert len(calls) == 1
    assert calls[0].startswith("file:")


def test_dispatch_has_dashboard_row():
    from seshat import cli

    assert "dashboard" in cli._DISPATCH
