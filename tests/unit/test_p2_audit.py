"""Focused audit regressions for commit-subject governance."""

from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path

import pytest

from seshat.rules.git_meta import rule_p2_commit_subjects
from tests.unit._gitfix import context_for, make_git_repo


@pytest.mark.unit
def test_p2_bracket_exemption_is_limited_to_known_automation_labels(
    tmp_path: Path,
) -> None:
    """Only known automation labels bypass the human subject convention."""
    repo = make_git_repo(tmp_path)

    def findings_for(subject: str) -> list:
        ctx = dataclasses.replace(context_for(repo), commit_message=subject)
        return list(rule_p2_commit_subjects(ctx))

    for subject in ("[ImgBot] Optimize images", "[dependabot] bump x"):
        assert findings_for(subject) == [], f"expected accepted: {subject!r}"
    for subject in ("[wip] random stuff", "[x] docs(018): scoped subject"):
        assert len(findings_for(subject)) == 1, f"expected rejected: {subject!r}"


@pytest.mark.unit
def test_p2_bare_fallback_on_single_commit_repo_judges_that_commit(
    tmp_path: Path,
) -> None:
    """A first commit has no HEAD~1, so P2 must inspect HEAD itself."""
    repo = make_git_repo(tmp_path)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "feat: init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    ctx = dataclasses.replace(context_for(repo), commit_range=None, commit_message=None)
    assert list(rule_p2_commit_subjects(ctx)) == []

    (tmp_path / "other").mkdir()
    other = make_git_repo(tmp_path / "other")
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "initial import"],
        cwd=other,
        check=True,
        capture_output=True,
    )
    ctx = dataclasses.replace(
        context_for(other), commit_range=None, commit_message=None
    )
    assert [f.locator for f in rule_p2_commit_subjects(ctx)] == ["initial import"]
