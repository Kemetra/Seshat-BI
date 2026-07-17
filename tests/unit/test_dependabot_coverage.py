"""US3 (spec 136): Dependabot coverage + P2-passing commit subjects.

Offline, no network. T024 guards the P2-passing subject shape against P2 drift
by importing the SAME ``SUBJECT_RE`` the governance rule uses. T025 parses the
committed ``.github/dependabot.yml`` and asserts the orchestration directory is
watched and every pip block emits a scope-free commit subject.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from seshat.rules.git_meta import SUBJECT_RE, _subject_ok

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEPENDABOT = _REPO_ROOT / ".github" / "dependabot.yml"


def test_dependabot_build_subject_passes_p2():
    """FR-014: a subject Dependabot produces from a ``build`` prefix
    (``build: bump X from A to B``) matches the P2 SUBJECT_RE -- so the bot PR
    passes P2 with no human edit. Guards against P2 drift by importing the rule's
    OWN regex, not a copy."""
    subject = "build: bump dbt-core from 1.12.0 to 1.13.0"
    assert SUBJECT_RE.match(subject)
    assert _subject_ok(subject)


def test_dependabot_scoped_subject_would_fail_p2():
    """The old default (``chore(deps): ...``) carries a parenthesized scope and
    is REJECTED by P2 -- which is exactly the friction FR-014 removes."""
    assert not SUBJECT_RE.match("chore(deps): bump dbt-core from 1.12.0 to 1.13.0")


def _load_dependabot() -> dict:
    return yaml.safe_load(_DEPENDABOT.read_text(encoding="utf-8"))


def _pip_blocks(doc: dict) -> list[dict]:
    return [u for u in doc.get("updates", []) if u.get("package-ecosystem") == "pip"]


def test_orchestration_directory_is_watched():
    """FR-013: a pip update block for the orchestration project directory
    exists (it is unwatched today)."""
    doc = _load_dependabot()
    directories = {u.get("directory") for u in _pip_blocks(doc)}
    assert "/orchestration/dagster" in directories


def test_every_pip_block_emits_scope_free_subject():
    """FR-014: every pip block sets commit-message.prefix to a P2-allowed type
    WITHOUT include: scope, so the produced subject is scope-free and passes P2."""
    doc = _load_dependabot()
    pip_blocks = _pip_blocks(doc)
    assert pip_blocks, "expected at least one pip update block"
    for block in pip_blocks:
        commit_message = block.get("commit-message")
        assert isinstance(commit_message, dict), (
            f"pip block {block.get('directory')!r} has no commit-message config"
        )
        prefix = commit_message.get("prefix")
        assert isinstance(prefix, str) and prefix, (
            f"pip block {block.get('directory')!r} has no commit-message.prefix"
        )
        # The produced subject is `<prefix>: bump X from A to B`; it must pass P2.
        produced = f"{prefix}: bump some-dep from 1.0.0 to 1.1.0"
        assert SUBJECT_RE.match(produced), (
            f"prefix {prefix!r} does not yield a P2-passing subject"
        )
        # No parenthesized scope: the prefix must NOT itself contain a scope,
        # and `include: scope` must not be set (that would re-add a scope).
        assert "(" not in prefix
        assert commit_message.get("include") != "scope"
