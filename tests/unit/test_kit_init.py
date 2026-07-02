"""TDD tests for `retail init` substrate-writing (feature 070).

The `init` MODULE is substrate-writing ONLY (BLOCKER-1): it writes the compass
projection + manifests + the fenced AGENTS.md/CLAUDE.md regions and returns a
"next agent step" string. It MUST NOT profile, open a DB, prompt, or show a menu --
delegate/route/profile is the agent's job in SKILL.md, not this module.

Covers:
* substrate written (compass.yaml, manifests, fenced regions) -- FR-004;
* module opens no DB connection / imports no profiler -- FR-003, T011;
* idempotent re-run: "already bootstrapped", one fence, outside-fence stable -- FR-008;
* no-wizard guard: no input()/stdin read, no menu, no profile emitted -- FR-001, T012;
* fenced body == the canonical prose render (single source) -- FC1.

tmp_path repos only.
"""

from __future__ import annotations

import inspect
import shutil
from pathlib import Path

import pytest

from retail import kit_init
from retail.compass_project import check_prose_drift, load_source
from retail.fence import read_fence_body

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_REL = ".seshat/kit-source.yaml"


@pytest.fixture
def repo(tmp_path) -> Path:
    """A tmp repo with the canonical source + minimal AGENTS.md / CLAUDE.md."""
    (tmp_path / ".seshat").mkdir()
    shutil.copyfile(REPO_ROOT / SOURCE_REL, tmp_path / SOURCE_REL)
    (tmp_path / "AGENTS.md").write_text("# AGENTS\n\n- rule one\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("# CLAUDE\n\nlaw line\n", encoding="utf-8")
    return tmp_path


def test_bootstrap_writes_substrate(repo) -> None:
    kit_init.bootstrap(repo)
    assert (repo / ".seshat/compass.yaml").exists()
    assert (repo / ".seshat/manifest.yaml").exists()
    assert (repo / "AGENTS.md").read_text(encoding="utf-8").count(
        "<!-- SESHAT-KIT START -->"
    ) == 1
    assert (repo / "CLAUDE.md").read_text(encoding="utf-8").count(
        "<!-- SESHAT-KIT START -->"
    ) == 1


def test_bootstrap_returns_next_agent_step_string(repo) -> None:
    result = kit_init.bootstrap(repo)
    assert isinstance(result.next_step, str) and result.next_step
    # the next step routes to the agent-performed skill, not a CLI profile
    assert "first-hour-compass" in result.next_step or "retail-init" in result.next_step


def test_fenced_body_matches_canonical_prose(repo) -> None:
    kit_init.bootstrap(repo)
    body = read_fence_body(repo / "AGENTS.md")
    assert body is not None
    assert check_prose_drift(load_source(repo), fenced_body=body) is True


def test_module_opens_no_db_and_imports_no_profiler() -> None:
    # FR-003 / T011: the init module must not pull in the DB profiler.
    src = inspect.getsource(kit_init)
    assert "import psycopg2" not in src
    assert "from .profile" not in src and "import profile" not in src
    assert "QueryRunner" not in src
    # no socket/urllib/http (FR-011 no remote fetch)
    for net in ("import socket", "import urllib", "import http", "import requests"):
        assert net not in src


def test_no_wizard_no_stdin_no_menu() -> None:
    # FR-001 / T012: substrate-only, never prompts.
    src = inspect.getsource(kit_init)
    assert "input(" not in src
    assert "sys.stdin" not in src


def test_idempotent_rerun_reports_already_bootstrapped(repo) -> None:
    kit_init.bootstrap(repo)
    agents_after_first = (repo / "AGENTS.md").read_text(encoding="utf-8")
    result2 = kit_init.bootstrap(repo)
    agents_after_second = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert result2.already_bootstrapped is True
    assert agents_after_first == agents_after_second  # no churn, one fence
    assert agents_after_second.count("<!-- SESHAT-KIT START -->") == 1


def test_rerun_leaves_outside_fence_bytes_identical(repo) -> None:
    kit_init.bootstrap(repo)
    before = (repo / "CLAUDE.md").read_text(encoding="utf-8")
    kit_init.bootstrap(repo)
    after = (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert before == after
