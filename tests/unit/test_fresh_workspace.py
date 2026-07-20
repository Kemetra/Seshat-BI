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
from seshat.rules.git_meta import (
    REQUIRED_PATHS,
    _repo_root_has_commit,
    rule_p1_layout,
    rule_p2_commit_subjects,
)

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


# ---------------------------------------------------------------------------
# #384 -- P2 does not emit an error in a fully non-git workspace (matches the
# git-init'd-no-HEAD path, which already returns cleanly)
# ---------------------------------------------------------------------------


def test_p2_emits_no_error_in_fully_non_git_workspace(tmp_path: Path) -> None:
    # A never-initialized workspace (no .git/ at all): there is no commit subject
    # to judge, exactly like the git-init'd-but-no-HEAD case that already returns
    # clean. Bare-fallback mode (no --commit-range, no commit-msg). P2 must not
    # surface a "could not read commit range 'HEAD~1..HEAD'" ERROR here.
    ctx = RuleContext(
        repo_root=tmp_path,
        tracked_files=(),
        commit_range=None,
        commit_message=None,
    )
    findings = list(rule_p2_commit_subjects(ctx))
    assert findings == [], [f.message for f in findings]


def test_p2_emits_no_error_when_repo_root_is_nested_under_an_ancestor_repo(
    tmp_path: Path,
) -> None:
    # The ACTUAL #384 root cause: repo_root is a non-git subdir that merely SITS
    # inside a version-controlled ancestor (e.g. a client whose $HOME is a git
    # repo). git's upward discovery resolves the ANCESTOR, so a naive
    # --is-inside-work-tree / --verify HEAD probe answers for the ancestor and both
    # (a) suppresses nothing -- P2 fires -- and (b) would validate the ANCESTOR's
    # commit subjects as if they were the workspace's. _repo_root_has_commit
    # compares toplevel to repo_root, so the nested workspace is correctly treated
    # as "no subject to judge". This test fails if the probe ever regresses to the
    # discovery-based form (it passes on a normal machine either way otherwise).
    import subprocess

    outer = tmp_path / "outer"
    outer.mkdir()
    for args in (
        ["init", "-b", "main"],
        ["config", "user.email", "t@example.com"],
        ["config", "user.name", "Test"],
        ["config", "commit.gpgsign", "false"],
        ["commit", "-q", "--allow-empty", "-m", "feat: ancestor commit"],
    ):
        subprocess.run(["git", *args], cwd=outer, check=True, capture_output=True)
    nested = outer / "workspace"  # NOT its own repo; discovers `outer`
    nested.mkdir()
    ctx = RuleContext(
        repo_root=nested,
        tracked_files=(),
        commit_range=None,
        commit_message=None,
    )
    findings = list(rule_p2_commit_subjects(ctx))
    assert findings == [], [f.message for f in findings]


def test_p2_emits_no_error_in_git_initd_but_no_commit_workspace(tmp_path: Path) -> None:
    # The sibling first-success state the fix must keep clean: `git init` done, but
    # no commit yet (no HEAD). This was already handled before #384; guard that the
    # refactor to _repo_root_has_commit did not regress it.
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True
    )
    ctx = RuleContext(
        repo_root=repo,
        tracked_files=(),
        commit_range=None,
        commit_message=None,
    )
    findings = list(rule_p2_commit_subjects(ctx))
    assert findings == [], [f.message for f in findings]


def test_p2_still_errors_on_a_single_commit_repo_bare_fallback(tmp_path: Path) -> None:
    # The refactor to _repo_root_has_commit must NOT swallow the defended
    # single-commit behavior: a real repo with exactly one commit still cannot form
    # HEAD~1..HEAD, so bare `check` still surfaces the P2 range ERROR (git_meta
    # lines ~280-286). _repo_root_has_commit returns True here (own root + HEAD), so
    # it falls through to DEFAULT_RANGE -- unchanged from before #384.
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (
        ["init", "-b", "main"],
        ["config", "user.email", "t@example.com"],
        ["config", "user.name", "Test"],
        ["config", "commit.gpgsign", "false"],
        ["commit", "-q", "--allow-empty", "-m", "feat: only commit"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    ctx = RuleContext(
        repo_root=repo,
        tracked_files=(),
        commit_range=None,
        commit_message=None,
    )
    errors = [
        f
        for f in rule_p2_commit_subjects(ctx)
        if f.rule_id == "P2" and f.severity is Severity.ERROR
    ]
    assert errors, "single-commit bare fallback must still surface the P2 range error"


# ---------------------------------------------------------------------------
# #393 -- _repo_root_has_commit does not rely on filesystem path comparison
# (a Cygwin/MSYS git returns a POSIX --show-toplevel that samefile cannot resolve)
# ---------------------------------------------------------------------------


def test_repo_root_has_commit_survives_posix_toplevel_from_msys_git(
    tmp_path: Path, monkeypatch
) -> None:
    # A real repo at its own root, but git reports paths POSIX-style (Cygwin/MSYS
    # on Windows: --show-toplevel = "/c/Users/..."). The old code compared that to
    # repo_root with Path.samefile, which raises OSError -> False -> P2 silently
    # dropped on a REAL repo. Keying on --show-prefix (empty == at repo root)
    # asks git the question directly, immune to how the toolchain spells paths.
    real_top = "/c/msys/home/dev/project"  # a POSIX path samefile cannot resolve here

    def fake_git_output(root: Path, *args: str) -> str:
        if args == ("rev-parse", "--show-toplevel"):
            return real_top + "\n"
        if args == ("rev-parse", "--show-prefix"):
            return "\n"  # empty => cwd IS the repo root
        if args == ("rev-parse", "--verify", "HEAD"):
            return "abc123\n"  # HEAD verifies
        raise AssertionError(f"unexpected git call: {args}")

    monkeypatch.setattr("seshat.rules.git_meta.gitutil.git_output", fake_git_output)
    assert _repo_root_has_commit(tmp_path) is True


def test_p2_still_errors_on_a_malformed_explicit_commit_range(tmp_path: Path) -> None:
    # Guard the other direction: a genuinely malformed EXPLICIT --commit-range is
    # still an ERROR even in a non-git workspace -- the non-git tolerance must not
    # swallow a caller's bad range. An option-injection-shaped range is rejected.
    ctx = RuleContext(
        repo_root=tmp_path,
        tracked_files=(),
        commit_range="--output=/etc/passwd",
        commit_message=None,
    )
    findings = list(rule_p2_commit_subjects(ctx))
    errors = [f for f in findings if f.rule_id == "P2" and f.severity is Severity.ERROR]
    assert errors, "a malformed explicit --commit-range must still surface a P2 error"
