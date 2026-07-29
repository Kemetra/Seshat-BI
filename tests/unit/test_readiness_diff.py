"""TDD tests for the readiness-diff core (F1).

The diff MATH is pure: it compares two already-parsed
``{table -> readiness-status document}`` maps and never touches git. That mirrors
``profile.py`` (math behind a QueryRunner Protocol) and ``file_profile.py`` (math
behind a FrameReader) -- the revision-reading layer is a separate seam, so these
tests need no repo fixture and no subprocess.

Regression semantics are the load-bearing part: a stage moving pass -> blocked is
a REGRESSION, while blocked -> pass is ordinary forward progress. Losing that
asymmetry would make the surface useless as a review signal.
"""

from __future__ import annotations

import pytest

from seshat.readiness_diff import diff_readiness

pytestmark = pytest.mark.unit


def _doc(current_stage: str = "gold_ready", **stages: str) -> dict:
    """A minimal readiness-status document with the given stage statuses."""
    return {
        "current_stage": current_stage,
        "stages": {name: {"status": status} for name, status in stages.items()},
    }


def test_stage_status_regression_is_flagged() -> None:
    """pass -> blocked on one stage is reported as a regression."""
    base = {"t1": _doc(gold_ready="pass")}
    head = {"t1": _doc(gold_ready="blocked")}

    result = diff_readiness(base, head)

    assert len(result.stage_changes) == 1
    change = result.stage_changes[0]
    assert change.table == "t1"
    assert change.stage == "gold_ready"
    assert change.base_status == "pass"
    assert change.head_status == "blocked"
    assert change.is_regression is True


def test_forward_progress_is_not_a_regression() -> None:
    """blocked -> pass is ordinary progress; the asymmetry is the whole point."""
    result = diff_readiness(
        {"t1": _doc(gold_ready="blocked")}, {"t1": _doc(gold_ready="pass")}
    )

    assert len(result.stage_changes) == 1
    assert result.stage_changes[0].is_regression is False


def test_unchanged_state_reports_nothing() -> None:
    """An identical snapshot is silent -- no-change noise would bury real signal."""
    doc = {"t1": _doc(source_ready="pass", gold_ready="warning")}

    result = diff_readiness(doc, doc)

    assert result.stage_changes == ()
    assert result.tables_added == ()
    assert result.tables_removed == ()
    assert result.has_regression is False


def test_unknown_status_reports_change_without_claiming_direction() -> None:
    """A malformed status is a CHANGE but not a regression -- never a guessed rank."""
    base = {"t1": _doc(gold_ready="pass")}
    head = {"t1": _doc(gold_ready="banana")}

    result = diff_readiness(base, head)

    assert len(result.stage_changes) == 1
    assert result.stage_changes[0].is_regression is False
    assert result.has_regression is False


def test_added_and_removed_tables_are_reported() -> None:
    """A table appearing or disappearing between revisions is named."""
    result = diff_readiness({"gone": _doc()}, {"fresh": _doc()})

    assert result.tables_removed == ("gone",)
    assert result.tables_added == ("fresh",)


def test_current_stage_move_backwards_is_a_regression() -> None:
    """current_stage moving earlier in the seven-stage spine is a regression."""
    base = {"t1": _doc(current_stage="publish_ready")}
    head = {"t1": _doc(current_stage="silver_ready")}

    result = diff_readiness(base, head)

    assert len(result.current_stage_changes) == 1
    move = result.current_stage_changes[0]
    assert move.table == "t1"
    assert move.base_stage == "publish_ready"
    assert move.head_stage == "silver_ready"
    assert move.is_regression is True
    assert result.has_regression is True


def test_current_stage_move_forwards_is_not_a_regression() -> None:
    """current_stage advancing is progress, not a regression."""
    result = diff_readiness(
        {"t1": _doc(current_stage="silver_ready")},
        {"t1": _doc(current_stage="gold_ready")},
    )

    assert len(result.current_stage_changes) == 1
    assert result.current_stage_changes[0].is_regression is False


def test_blockers_added_and_removed_are_reported() -> None:
    """New and cleared blocking reasons are both surfaced, per table and stage."""
    base = {
        "t1": {
            "current_stage": "gold_ready",
            "stages": {
                "gold_ready": {"status": "warning", "blocking_reasons": ["old"]}
            },
        }
    }
    head = {
        "t1": {
            "current_stage": "gold_ready",
            "stages": {
                "gold_ready": {"status": "warning", "blocking_reasons": ["new"]}
            },
        }
    }

    result = diff_readiness(base, head)

    assert result.blockers_added == (("t1", "gold_ready", "new"),)
    assert result.blockers_removed == (("t1", "gold_ready", "old"),)


def test_approval_removal_is_reported_and_is_a_regression() -> None:
    """Losing a recorded named-human approval is a regression, not a neutral edit.

    An approval disappearing between revisions means the evidence a stage rested
    on is gone. Reporting it as neutral would let a reviewer merge away a
    signature without noticing.
    """
    base = {
        "t1": {
            "current_stage": "gold_ready",
            "stages": {},
            "approvals": [
                {"stage": "mapping_ready", "owner": "A Person", "at": "2026-01-01"}
            ],
        }
    }
    head = {"t1": {"current_stage": "gold_ready", "stages": {}, "approvals": []}}

    result = diff_readiness(base, head)

    assert len(result.approvals_removed) == 1
    assert result.approvals_removed[0].table == "t1"
    assert result.approvals_removed[0].stage == "mapping_ready"
    assert result.has_regression is True


def test_approval_added_is_not_a_regression() -> None:
    """A newly recorded approval is progress and is reported as added."""
    base = {"t1": {"current_stage": "gold_ready", "stages": {}, "approvals": []}}
    head = {
        "t1": {
            "current_stage": "gold_ready",
            "stages": {},
            "approvals": [
                {"stage": "mapping_ready", "owner": "A Person", "at": "2026-01-01"}
            ],
        }
    }

    result = diff_readiness(base, head)

    assert len(result.approvals_added) == 1
    assert result.approvals_removed == ()
    assert result.has_regression is False


def test_malformed_document_does_not_blind_other_tables() -> None:
    """One unparseable table contributes nothing; the others still diff."""
    base = {"bad": "not-a-mapping", "good": _doc(gold_ready="pass")}
    head = {"bad": None, "good": _doc(gold_ready="blocked")}

    result = diff_readiness(base, head)

    assert [c.table for c in result.stage_changes] == ["good"]
    assert result.has_regression is True


def test_status_progress_covers_the_canonical_vocabulary() -> None:
    """The ordered progress tuple must cover EXACTLY run_next's status set.

    Drift guard: the set cannot express progress order, so this module keeps an
    ordered copy. If a fifth status is ever added to the spine, this fails instead
    of silently ranking the new value as unknown (and so never a regression).
    """
    from seshat.readiness_diff import _STATUS_PROGRESS
    from seshat.run_next import _STATUS_VALUES

    assert set(_STATUS_PROGRESS) == set(_STATUS_VALUES)
