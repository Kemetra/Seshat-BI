"""CLI-level tests for `seshat readiness-diff`.

The diff math is covered in ``test_readiness_diff.py``; these tests cover the
revision-reading seam and the render -- against a REAL temporary git repo with
two commits, because the whole point of the surface is reading committed state at
a revision rather than the worktree.

The fixture disables commit signing locally (``commit.gpgsign=false`` +
``-c user.*``) so it does not depend on -- or trip over -- whatever signing the
developer's global git config has configured.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from seshat.cli import main as main_under_test

pytestmark = pytest.mark.unit

_BASE_DOC = """\
table: "bronze.orders"
current_stage: "gold_ready"
stages:
  gold_ready:
    status: "pass"
    blocking_reasons: []
approvals:
  - stage: "mapping_ready"
    owner: "A Person (data_owner)"
    at: "2026-01-01"
"""

_HEAD_DOC_REGRESSED = """\
table: "bronze.orders"
current_stage: "silver_ready"
stages:
  gold_ready:
    status: "blocked"
    blocking_reasons: ["reconciliation failed"]
approvals: []
"""


def _run_git(repo, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _make_repo(tmp_path, head_doc: str | None = None):
    """A repo with a committed readiness file, then optionally a second commit."""
    repo = tmp_path / "wk"
    (repo / "mappings" / "orders").mkdir(parents=True)
    _run_git(repo.parent, "init", "wk")
    _run_git(repo, "config", "user.email", "t@example.com")
    _run_git(repo, "config", "user.name", "T")
    _run_git(repo, "config", "commit.gpgsign", "false")

    status = repo / "mappings" / "orders" / "readiness-status.yaml"
    status.write_text(_BASE_DOC, encoding="utf-8")
    _run_git(repo, "add", "mappings/orders/readiness-status.yaml")
    _run_git(repo, "commit", "-m", "base")

    if head_doc is not None:
        status.write_text(head_doc, encoding="utf-8")
        _run_git(repo, "add", "mappings/orders/readiness-status.yaml")
        _run_git(repo, "commit", "-m", "head")
    return repo


def _diff_json(repo, capsys, *extra: str) -> dict:
    """Run readiness-diff as JSON over ``repo`` and return the parsed document.

    Shared so the JSON-shape tests differ only in what they ASSERT, not in how
    they invoke the command (CodeScene flagged the duplicated structure).
    """
    rc = main_under_test(
        ["readiness-diff", "--repo", str(repo), "--format", "json", *extra]
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    return payload


def test_readiness_diff_reports_regression_between_two_revisions(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A pass -> blocked change between HEAD~1 and HEAD is reported as a regression."""
    repo = _make_repo(tmp_path, _HEAD_DOC_REGRESSED)

    rc = main_under_test(
        [
            "readiness-diff",
            "--repo",
            str(repo),
            "--base",
            "HEAD~1",
            "--head",
            "HEAD",
            "--format",
            "json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["has_regression"] is True
    stage_changes = payload["stage_changes"]
    assert len(stage_changes) == 1
    assert stage_changes[0]["stage"] == "gold_ready"
    assert stage_changes[0]["base_status"] == "pass"
    assert stage_changes[0]["head_status"] == "blocked"
    assert stage_changes[0]["is_regression"] is True


def test_readiness_diff_reports_lost_approval(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The removed named-human approval is surfaced, not silently dropped."""
    repo = _make_repo(tmp_path, _HEAD_DOC_REGRESSED)

    payload = _diff_json(repo, capsys, "--base", "HEAD~1", "--head", "HEAD")

    assert len(payload["approvals_removed"]) == 1
    assert payload["approvals_removed"][0]["stage"] == "mapping_ready"


def test_readiness_diff_identical_revisions_is_empty(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Comparing a revision to itself reports no change and no regression."""
    repo = _make_repo(tmp_path)

    payload = _diff_json(repo, capsys, "--base", "HEAD", "--head", "HEAD")

    assert payload["has_regression"] is False
    assert payload["stage_changes"] == []


def test_readiness_diff_accepts_range_form(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`<base>..<head>` is accepted as a positional alternative to --base/--head."""
    repo = _make_repo(tmp_path, _HEAD_DOC_REGRESSED)

    payload = _diff_json(repo, capsys, "HEAD~1..HEAD")

    assert payload["has_regression"] is True


def test_readiness_diff_text_render_names_the_regression(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The default text render names the table, the stage, and the direction."""
    repo = _make_repo(tmp_path, _HEAD_DOC_REGRESSED)

    rc = main_under_test(
        ["readiness-diff", "--repo", str(repo), "--base", "HEAD~1", "--head", "HEAD"]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "orders" in out
    assert "gold_ready" in out
    assert "pass" in out and "blocked" in out
    assert "regression" in out.lower()


def test_readiness_diff_grants_no_approval_and_writes_nothing(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Read-only posture: the surface states it grants nothing and leaves git clean."""
    repo = _make_repo(tmp_path, _HEAD_DOC_REGRESSED)

    rc = main_under_test(
        ["readiness-diff", "--repo", str(repo), "--base", "HEAD~1", "--head", "HEAD"]
    )

    assert rc == 0
    assert "grants no approval" in capsys.readouterr().out.lower()
    dirty = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    assert dirty.stdout == ""


def test_readiness_diff_unknown_revision_exits_1(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A bad revision fails closed with a message, never a traceback."""
    repo = _make_repo(tmp_path)

    rc = main_under_test(
        ["readiness-diff", "--repo", str(repo), "--base", "nope123", "--head", "HEAD"]
    )

    assert rc == 1
    assert "revision" in capsys.readouterr().err.lower()


def test_readiness_diff_rejects_unsafe_range(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unsafe range expression is refused rather than handed to git."""
    repo = _make_repo(tmp_path)

    rc = main_under_test(
        ["readiness-diff", "--repo", str(repo), "HEAD~1..HEAD; rm -rf /"]
    )

    assert rc == 1
    assert capsys.readouterr().err != ""
