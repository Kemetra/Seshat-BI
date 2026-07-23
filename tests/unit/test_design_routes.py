"""TDD tests for DR1 -- design-layer route path foot-gun + stale-phrase guard.

DR1 has two halves, both read-only over ctx.tracked_files:
  1. path foot-gun: no tracked file under a `.claude/worktrees/` scratch prefix.
  2. stale-phrase manifest (docs/quality/design-stale-phrases.yaml): ERROR while a
     listed stale anchor is still present in its doc (the INVERSE of SC1's presence
     requirement). A missing/malformed manifest fails loud.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.design_routes import _STALE_MANIFEST, check_design_routes

pytestmark = pytest.mark.unit


def _stage(
    tmp_path: Path,
    manifest_text: str | None = "phrases: []\n",
    docs: dict[str, str] | None = None,
    extra_tracked: tuple[str, ...] = (),
) -> RuleContext:
    """Stage a manifest + docs under tmp_path and return a context.

    ``manifest_text=None`` omits the manifest entirely (untracked -> fail loud).
    ``docs`` maps repo-relative path -> file content; all are materialized + tracked.
    ``extra_tracked`` are paths marked tracked WITHOUT being written (for foot-gun
    path tests where only the path string matters).
    """
    tracked: list[str] = []
    if manifest_text is not None:
        p = tmp_path / _STALE_MANIFEST
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(manifest_text, encoding="utf-8")
        tracked.append(_STALE_MANIFEST)
    for rel, content in (docs or {}).items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        tracked.append(rel)
    tracked.extend(extra_tracked)
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(tracked))


# --- path foot-gun half ---------------------------------------------------------


def test_clean_tree_passes(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, docs={"docs/a.md": "all good"})
    assert list(check_design_routes(ctx)) == []


def test_tracked_file_under_worktree_prefix_fails(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, extra_tracked=(".claude/worktrees/session-work/docs/a.md",))
    findings = list(check_design_routes(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "DR1"
    assert findings[0].severity is Severity.ERROR
    assert ".claude/worktrees/" in findings[0].message


# --- stale-phrase half ----------------------------------------------------------


def test_stale_phrase_still_present_fails(tmp_path: Path) -> None:
    ctx = _stage(
        tmp_path,
        manifest_text=(
            "phrases:\n"
            '  - doc: "docs/a.md"\n'
            '    anchor: "spec-only today"\n'
            '    reason: "F011 shipped; drop the spec-only wording"\n'
        ),
        docs={"docs/a.md": "the verb is spec-only today, oops"},
    )
    findings = list(check_design_routes(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "DR1"
    assert findings[0].severity is Severity.ERROR
    assert "spec-only today" in findings[0].message
    assert "F011 shipped" in findings[0].message


def test_stale_phrase_removed_passes(tmp_path: Path) -> None:
    # The phrase was corrected in the doc; the manifest entry no longer matches.
    ctx = _stage(
        tmp_path,
        manifest_text=(
            'phrases:\n  - doc: "docs/a.md"\n    anchor: "spec-only today"\n'
        ),
        docs={"docs/a.md": "the verb is shipped and live now"},
    )
    assert list(check_design_routes(ctx)) == []


def test_stale_phrase_doc_untracked_fails(tmp_path: Path) -> None:
    ctx = _stage(
        tmp_path,
        manifest_text=(
            'phrases:\n  - doc: "docs/missing.md"\n    anchor: "whatever"\n'
        ),
    )
    findings = list(check_design_routes(ctx))
    assert len(findings) == 1
    assert "not a tracked file" in findings[0].message


# --- fail-closed manifest guards ------------------------------------------------


def test_missing_manifest_fails_loud(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, manifest_text=None, docs={"docs/a.md": "x"})
    findings = list(check_design_routes(ctx))
    assert len(findings) == 1
    assert "missing or untracked" in findings[0].message


def test_tracked_but_deleted_manifest_on_disk_still_fails_loud(tmp_path: Path) -> None:
    # #430 + Codex #443 P1: the stale-phrase manifest is TRACKED but deleted-but-
    # unstaged (absent on disk). DR1 must fail loud -- NOT crash on the read.
    ctx = _stage(tmp_path, manifest_text="phrases: []\n")
    (tmp_path / _STALE_MANIFEST).unlink()
    findings = list(check_design_routes(ctx))
    assert len(findings) == 1
    assert "missing or untracked" in findings[0].message


def test_tracked_but_deleted_doc_on_disk_is_not_stale(tmp_path: Path) -> None:
    # A listed doc is tracked but deleted on disk (#430). DR1 checks a phrase is
    # still PRESENT, so a missing doc means "not present" -> skip, never crash and
    # never a false stale finding.
    ctx = _stage(
        tmp_path,
        manifest_text=(
            'phrases:\n  - doc: "docs/a.md"\n    anchor: "spec-only today"\n'
        ),
        docs={"docs/a.md": "the verb is spec-only today, oops"},
    )
    (tmp_path / "docs/a.md").unlink()  # tracked, but now missing on disk
    assert list(check_design_routes(ctx)) == []


def test_malformed_manifest_fails_loud(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, manifest_text="phrases: {not a list}\n")
    findings = list(check_design_routes(ctx))
    assert len(findings) == 1
    assert "must be a mapping with a 'phrases' list" in findings[0].message


def test_empty_manifest_is_healthy(tmp_path: Path) -> None:
    # An empty phrases list is the steady state -> no findings.
    ctx = _stage(tmp_path, manifest_text="phrases: []\n")
    assert list(check_design_routes(ctx)) == []
