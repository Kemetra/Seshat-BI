"""CLI tests for `retail init` (feature 070).

The `init` subcommand is SUBSTRATE-WRITING ONLY: it writes .seshat/ + the fenced
regions and PRINTS the next agent step. It never prompts / reads stdin / emits a
profile (no-wizard guard, FR-001 / T012).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from retail import cli

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_REL = ".seshat/kit-source.yaml"


@pytest.fixture
def repo(tmp_path) -> Path:
    (tmp_path / ".seshat").mkdir()
    shutil.copyfile(REPO_ROOT / SOURCE_REL, tmp_path / SOURCE_REL)
    (tmp_path / "AGENTS.md").write_text("# AGENTS\n\n- rule\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("# CLAUDE\n\nlaw\n", encoding="utf-8")
    return tmp_path


def test_init_returns_0_and_writes_substrate(repo, capsys) -> None:
    code = cli.main(["init", "--repo", str(repo)])
    assert code == 0
    assert (repo / ".seshat/compass.yaml").exists()
    out = capsys.readouterr().out
    assert "wrote .seshat/compass.yaml" in out
    assert "SESHAT-KIT" in out  # projected fence reported


def test_init_prints_next_agent_step_not_a_profile(repo, capsys) -> None:
    cli.main(["init", "--repo", str(repo)])
    out = capsys.readouterr().out
    # routes to the agent-performed flow, not a CLI-emitted profile
    assert "first-hour-compass" in out or "retail-init" in out
    # The next-step text may DESCRIBE what the agent will profile, but the CLI emits
    # no actual profile VALUES (no grain list, no uniqueness %, no column-type table).
    assert "uniqueness" not in out.lower()
    assert "[store_id" not in out.lower()  # a rendered grain-candidate list
    assert "column types:" not in out.lower()


def test_init_does_not_read_stdin(repo, monkeypatch, capsys) -> None:
    # No-wizard guard: if init tried to read stdin, this would raise.
    def _boom(*a, **k):  # pragma: no cover - only fires on a regression
        raise AssertionError("init must not read stdin (no wizard)")

    monkeypatch.setattr("builtins.input", _boom)
    assert cli.main(["init", "--repo", str(repo)]) == 0


def test_init_idempotent_second_run(repo, capsys) -> None:
    cli.main(["init", "--repo", str(repo)])
    capsys.readouterr()
    code = cli.main(["init", "--repo", str(repo)])
    out = capsys.readouterr().out
    assert code == 0
    assert "already bootstrapped" in out
    assert (repo / "AGENTS.md").read_text(encoding="utf-8").count(
        "<!-- SESHAT-KIT START -->"
    ) == 1
