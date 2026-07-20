"""Fresh / non-git workspace resilience (issues #370, #371, #372).

A pip-only client's very first commands run in a workspace that is NOT yet a git
repo and does NOT yet carry the kit seed. These tests pin the three defects a
standalone-readiness audit found there:

* #370 -- ``seshat init`` crashed with a raw ``FileNotFoundError`` looking for
  ``.seshat/kit-source.yaml`` (a seed the package never shipped).
* #371 -- ``gitutil.git_check_ignore`` raised ``RuntimeError`` on git exit-128
  (not-a-repo) where its sibling ``runner._git_ls_files`` tolerates it.
* #372 -- P1 flagged files that exist ON DISK as "missing" because it tested the
  git-tracked set, which is empty in a non-repo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat import cli, compass_project, gitutil
from seshat.core import RuleContext, Severity
from seshat.rules.git_meta import REQUIRED_PATHS, rule_p1_layout

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# #371 -- git_check_ignore tolerates a non-git workspace (no RuntimeError)
# ---------------------------------------------------------------------------


def test_git_check_ignore_returns_false_in_non_git_dir(tmp_path: Path) -> None:
    # A bare, non-git directory: check-ignore exits 128. The sibling
    # runner._git_ls_files treats 128 as "not a repo"; git_check_ignore must too.
    result = gitutil.git_check_ignore(tmp_path, ".env")
    assert result is False


# ---------------------------------------------------------------------------
# #372 -- P1 does not report on-disk files as "missing" in a non-git workspace
# ---------------------------------------------------------------------------


def test_p1_does_not_flag_existing_files_missing_without_git(tmp_path: Path) -> None:
    # Materialize every required layout path ON DISK, but track NOTHING (non-repo
    # => empty tracked set). P1 must not call a file that exists "missing".
    for rel in REQUIRED_PATHS:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# placeholder\n", encoding="utf-8")

    ctx = RuleContext(repo_root=tmp_path, tracked_files=())
    findings = list(rule_p1_layout(ctx))

    missing = [
        f for f in findings if "missing" in f.message and f.severity is Severity.ERROR
    ]
    assert missing == [], (
        f"P1 flagged on-disk files as missing: {[f.message for f in missing]}"
    )


def test_p1_still_flags_a_genuinely_absent_layout_path(tmp_path: Path) -> None:
    # Guard the other direction: a file that is NOT on disk is still a finding, so
    # the fix does not neuter the rule.
    ctx = RuleContext(repo_root=tmp_path, tracked_files=())
    findings = list(rule_p1_layout(ctx))
    flagged = {f.locator for f in findings if f.severity is Severity.ERROR}
    assert set(REQUIRED_PATHS) <= flagged


# ---------------------------------------------------------------------------
# #370 -- init succeeds on a fresh empty workspace (seeds kit-source.yaml)
# ---------------------------------------------------------------------------


def test_init_succeeds_on_fresh_empty_workspace(tmp_path: Path, capsys) -> None:
    # No .seshat/, no kit-source.yaml, no governed files -- exactly a pip-only
    # client's first run. The audit observed a raw FileNotFoundError here.
    code = cli.main(["init", "--repo", str(tmp_path)])
    assert code == 0
    # The seed was materialized so the compass projects real router content.
    assert (tmp_path / compass_project.SOURCE_REL).exists()
    assert (tmp_path / compass_project.COMPASS_REL).exists()
    # A REAL compass, not a hollow one: the router verbs are projected.
    compass_text = (tmp_path / compass_project.COMPASS_REL).read_text(encoding="utf-8")
    assert "retail-orchestrate" in compass_text


def test_bundled_seed_matches_live_router() -> None:
    # The seed init materializes (templates/kit-source.yaml) is a COPY of the live
    # router (.seshat/kit-source.yaml). Guard the two against silent drift: if a
    # verb is added to the live router but not the seed, fresh clients would get a
    # stale router and nobody would notice (#370 follow-through).
    repo_root = Path(__file__).resolve().parents[2]
    live = (repo_root / ".seshat" / "kit-source.yaml").read_bytes()
    seed = (repo_root / "templates" / "kit-source.yaml").read_bytes()
    assert seed == live, (
        "templates/kit-source.yaml has drifted from .seshat/kit-source.yaml -- "
        "re-copy the live router into the seed."
    )


def test_load_source_missing_seed_raises_actionable_error(tmp_path: Path) -> None:
    # Defense in depth: if the seed is somehow still absent, load_source must give
    # a friendly, ACTIONABLE error (names the file + the fix) rather than the raw
    # pathlib FileNotFoundError traceback the audit saw. FileNotFoundError is the
    # semantically correct type; what the audit flagged was the unhelpful message.
    with pytest.raises(FileNotFoundError) as exc_info:
        compass_project.load_source(tmp_path)
    message = str(exc_info.value)
    assert compass_project.SOURCE_REL in message
    assert "seshat init" in message  # tells the client what to do next
