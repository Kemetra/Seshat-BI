"""CLI tests for `retail init-project` (spec 107, roadmap M3).

`init-project <name>` scaffolds a FRESH workspace for a new user (distinct from
`retail init`, which bootstraps `.seshat/` into an EXISTING repo -- see
test_cli_init.py). This wires the subcommand: subparser presence, dispatch,
--force, and exit codes. Every scaffolding call runs with the CWD chdir'd to a
tmp_path (matching the path-traversal guard in workspace_init._validate_target,
which resolves targets relative to the CWD).
"""

from __future__ import annotations

import pytest

from seshat import cli

pytestmark = pytest.mark.unit


def test_init_project_creates_workspace_and_returns_0(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "my-retail-bi"
    code = cli.main(["init-project", str(target)])
    assert code == 0
    assert (target / "README.md").exists()
    out = capsys.readouterr().out
    assert "wrote" in out or str(target.name) in out


def test_init_project_refuses_nonempty_target_without_force(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "existing"
    target.mkdir()
    (target / "keep.txt").write_text("keep", encoding="utf-8")

    code = cli.main(["init-project", str(target)])
    assert code != 0
    err = capsys.readouterr().err
    assert "force" in err.lower() or "exists" in err.lower()
    assert (target / "keep.txt").exists()
    assert not (target / "README.md").exists()


def test_init_project_force_flag_scaffolds_nonempty_target(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "existing"
    target.mkdir()
    (target / "keep.txt").write_text("keep", encoding="utf-8")

    code = cli.main(["init-project", str(target), "--force"])
    assert code == 0
    assert (target / "README.md").exists()
    assert (target / "keep.txt").exists()


def test_init_project_subparser_is_registered() -> None:
    from seshat.cli.parser import _build_parser

    parser = _build_parser()
    args = parser.parse_args(["init-project", "some-name"])
    assert args.command == "init-project"
    assert args.name == "some-name"
    assert args.force is False


def test_init_project_does_not_read_stdin(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    def _boom(*a, **k):  # pragma: no cover - only fires on a regression
        raise AssertionError("init-project must not read stdin (no wizard)")

    monkeypatch.setattr("builtins.input", _boom)
    target = tmp_path / "no-stdin-ws"
    assert cli.main(["init-project", str(target)]) == 0


def test_init_project_returns_path_objects_type_from_handler(
    tmp_path, monkeypatch
) -> None:
    # Direct handler-level check (mirrors the sibling command test style):
    # init_project_main takes argparse.Namespace -> int.
    import argparse

    monkeypatch.chdir(tmp_path)
    from seshat.cli.commands.init_project import init_project_main

    target = tmp_path / "direct-handler-ws"
    ns = argparse.Namespace(name=str(target), force=False)
    code = init_project_main(ns)
    assert code == 0
    assert (target / "README.md").exists()
