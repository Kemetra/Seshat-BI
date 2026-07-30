"""Acceptance transcripts must name the bundle they were captured against.

CI's evidence that a dropped-in agent behaves correctly comes from PRE-RECORDED
transcripts under ``tests/fixtures/public_distribution/``, classified against the
governed expected outcome. Nothing bound a transcript to the bundle it exercised, so
a change that altered real agent behaviour could pass CI on a stale recording. These
tests pin the binding.

The guard is deliberately asymmetric, and the asymmetry is the design:

* a MISSING provenance block is a blocker -- no new fixture may be added unbound;
* a MISMATCHED digest is a blocker -- it names the re-capture command;
* an explicit ``legacy-uncaptured`` marker is NOT a blocker, but reports
  ``bundle_provenance_verified: False``.

The third case exists because re-capturing needs the real Claude/Codex CLIs and
credentials, which CI does not have. Hard-failing the five pre-existing fixtures
would red-light every unrelated PR while proving nothing. Making their unverified
state visible and enumerable is the honest improvement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.external_agent_acceptance import (
    LEGACY_PROVENANCE,
    classify_transcript,
    committed_bundle_digest,
)

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/public_distribution"

ACCEPTANCE_FIXTURES = (
    "claude/acceptance.pass.json",
    "claude/acceptance.pii-fail.json",
    "codex/acceptance.capability-fail.json",
    "codex/acceptance.cli.pass.json",
    "codex/acceptance.ide.pass.json",
)

_STALE_MARKER = "predates the current bundle"
_UNBOUND_MARKER = "declares no bundle_provenance block"


def _transcript(path: str) -> dict[str, Any]:
    return json.loads((FIXTURES / path).read_text(encoding="utf-8"))


def _provenance_blockers(record: dict[str, Any]) -> list[str]:
    return [
        blocker
        for blocker in record["blockers"]
        if "provenance" in blocker or _STALE_MARKER in blocker
    ]


def test_committed_bundles_expose_a_manifest_digest() -> None:
    """Both bundles carry the digest the guard compares against."""
    for platform in ("claude-code", "codex"):
        digest = committed_bundle_digest(ROOT, platform)
        assert digest, f"{platform} bundle-manifest.json has no manifest_digest"
        assert len(digest) == 64, f"{platform} digest is not a sha256: {digest!r}"


def test_the_two_bundles_have_distinct_digests() -> None:
    """Claude and Codex bundles differ in content, so a shared digest would be a bug."""
    claude = committed_bundle_digest(ROOT, "claude-code")
    codex = committed_bundle_digest(ROOT, "codex")
    assert claude != codex


def test_missing_manifest_reports_none_rather_than_guessing(tmp_path: Path) -> None:
    """An unreadable manifest is a reportable state, not a silent 'no drift'."""
    assert committed_bundle_digest(tmp_path, "claude-code") is None


@pytest.mark.parametrize("fixture", ACCEPTANCE_FIXTURES)
def test_every_acceptance_fixture_declares_its_provenance(fixture: str) -> None:
    """No fixture is silently unbound: each declares a digest or the legacy marker."""
    block = _transcript(fixture).get("bundle_provenance")
    assert isinstance(block, dict), f"{fixture} declares no bundle_provenance"
    if not block.get("manifest_digest"):
        assert block.get("provenance") == LEGACY_PROVENANCE


@pytest.mark.parametrize("fixture", ACCEPTANCE_FIXTURES)
def test_legacy_fixtures_classify_without_a_provenance_blocker(fixture: str) -> None:
    """Legacy fixtures still classify -- their staleness is reported, not fatal."""
    record = classify_transcript(ROOT, _transcript(fixture))
    assert _provenance_blockers(record) == []
    assert record["bundle_provenance_verified"] is False


def test_a_transcript_with_no_provenance_block_is_blocked() -> None:
    """The guard that stops a NEW fixture being added unbound."""
    transcript = _transcript("claude/acceptance.pass.json")
    del transcript["bundle_provenance"]

    record = classify_transcript(ROOT, transcript)
    assert record["status"] == "fail"
    assert any(_UNBOUND_MARKER in blocker for blocker in record["blockers"])
    assert record["bundle_provenance_verified"] is False


def test_a_null_digest_without_the_legacy_marker_is_blocked() -> None:
    """An empty provenance block cannot pass as 'legacy' without saying so."""
    transcript = _transcript("claude/acceptance.pass.json")
    transcript["bundle_provenance"] = {"manifest_digest": None}

    record = classify_transcript(ROOT, transcript)
    assert record["status"] == "fail"
    assert any("does not declare provenance" in b for b in record["blockers"])


def test_a_stale_digest_is_blocked_and_names_the_recapture_command() -> None:
    """The core drift case: a transcript recorded against a different bundle."""
    transcript = _transcript("claude/acceptance.pass.json")
    transcript["bundle_provenance"] = {
        "manifest_digest": "0" * 64,
        "provenance": "captured",
    }

    record = classify_transcript(ROOT, transcript)
    assert record["status"] == "fail"
    stale = [b for b in record["blockers"] if _STALE_MARKER in b]
    assert stale, record["blockers"]
    assert "--execute-cli" in stale[0]
    assert record["bundle_provenance_verified"] is False


def test_a_matching_digest_verifies_and_adds_no_blocker() -> None:
    """A correctly bound transcript passes and is marked verified."""
    transcript = _transcript("claude/acceptance.pass.json")
    transcript["bundle_provenance"] = {
        "manifest_digest": committed_bundle_digest(ROOT, "claude-code"),
        "provenance": "captured",
    }

    record = classify_transcript(ROOT, transcript)
    assert _provenance_blockers(record) == []
    assert record["bundle_provenance_verified"] is True
    assert record["status"] == "pass"


def test_a_codex_digest_on_a_claude_transcript_is_blocked() -> None:
    """Provenance is per-target: the wrong bundle's digest is still drift."""
    transcript = _transcript("claude/acceptance.pass.json")
    transcript["bundle_provenance"] = {
        "manifest_digest": committed_bundle_digest(ROOT, "codex"),
        "provenance": "captured",
    }

    record = classify_transcript(ROOT, transcript)
    assert any(_STALE_MARKER in b for b in record["blockers"])
    assert record["bundle_provenance_verified"] is False
