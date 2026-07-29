"""TDD tests for per-blocker remediation metadata (B1').

`blockers` already answers WHAT is blocked and WHICH surface is next. It does not
answer the question that decides who acts: **is this mine to fix, or does it need
a named human?**

The answer must come from a committed ALLOWLISTED lookup keyed by the existing
blocker categories -- never from free-form advice generated per blocker. These
tests pin the lookup, its fail-safe default, and the drift guards that keep it
honest (every category covered; every cited doc actually on disk).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.readiness_classify import CATEGORY_RANK, classify, remediation_of

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]

HUMAN_ONLY = "human_only"
MECHANICAL = "mechanical"


def test_approval_blocker_is_human_only() -> None:
    """An agent must never self-grant an approval, so this can only be human."""
    category, _, _ = classify("named-human approval missing for mapping_ready")

    assert category == "approval"
    assert remediation_of(category).remediation == HUMAN_ONLY


def test_grain_blocker_is_human_only() -> None:
    """Grain / PK certainty is a Principle-V judgment call, never agent-decided."""
    category, _, _ = classify("candidate PK not proven unique on the landed data")

    assert category == "grain"
    assert remediation_of(category).remediation == HUMAN_ONLY


def test_artifact_blocker_is_mechanical() -> None:
    """A missing committed artifact can be produced by an agent."""
    category, _, _ = classify("mappings/orders/source-profile.md does not exist")

    assert category == "artifact"
    assert remediation_of(category).remediation == MECHANICAL


def test_live_validation_blocker_is_mechanical() -> None:
    """Configuring the live-validation boundary is a mechanical setup step."""
    category, _, _ = classify("deferred: no DSN configured for retail validate")

    assert category == "live_validation"
    assert remediation_of(category).remediation == MECHANICAL


def test_unknown_category_fails_safe_to_human_only() -> None:
    """An unrecognized category must NOT be reported as agent-fixable.

    Defaulting to `mechanical` would invite an agent to act on a blocker nobody
    classified. The fail-safe direction is toward the human.
    """
    assert remediation_of("something-nobody-classified").remediation == HUMAN_ONLY


def test_default_readiness_category_is_human_only() -> None:
    """The catch-all bucket is unclassified by definition -- so human_only."""
    category, _, _ = classify("some blocker phrased in a way no keyword matches")

    assert category == "readiness"
    assert remediation_of(category).remediation == HUMAN_ONLY


def test_every_category_has_remediation_metadata() -> None:
    """Drift guard: a category added to the classifier must gain metadata too."""
    for category in CATEGORY_RANK:
        entry = remediation_of(category)
        assert entry.remediation in {HUMAN_ONLY, MECHANICAL}, category
        assert entry.doc, category
        assert entry.stop_condition, category


def test_every_cited_doc_exists_on_disk() -> None:
    """Drift guard: a doc route that does not resolve is worse than none.

    Checked against the REAL repo, the same posture the capability inventory uses
    for its `documentation` field.
    """
    for category in CATEGORY_RANK:
        doc = remediation_of(category).doc
        assert (_REPO / doc).is_file(), f"{category} cites a missing doc: {doc}"


def test_remediation_is_categorical_never_a_score() -> None:
    """Two values only; no numeric axis anywhere (hard rule #9)."""
    values = {remediation_of(c).remediation for c in CATEGORY_RANK}

    assert values <= {HUMAN_ONLY, MECHANICAL}
    for category in CATEGORY_RANK:
        entry = remediation_of(category)
        assert not isinstance(entry.remediation, (int, float))
