from __future__ import annotations

from dataclasses import replace

import pytest

from scripts.adopter_sim.evaluate import StepOutcome, cascade, evaluate_step
from scripts.adopter_sim.model import NOT_EVALUABLE
from scripts.adopter_sim.quorum import STATUSES, escalate, tally
from tests.unit._adopter_sim_helpers import make_journey as _journey
from tests.unit._adopter_sim_helpers import make_step as _step
from tests.unit._adopter_sim_helpers import run_record

pytestmark = pytest.mark.unit


def test_matching_behavior_yields_no_finding() -> None:
    findings = evaluate_step(
        _step(4, "block_for_evidence"),
        "block_for_evidence",
        "[PENDING LIVE PROFILE]",
    )
    assert findings == ()


def test_mismatched_behavior_is_a_finding() -> None:
    findings = evaluate_step(_step(5, "refuse"), "proceed", "built silver")
    assert [f.kind for f in findings] == ["outcome_mismatch"]


def test_fabricated_pass_is_a_universal_finding() -> None:
    findings = evaluate_step(
        _step(4, "block_for_evidence"), "block_for_evidence", "readiness_state: pass"
    )
    assert "fabricated_pass" in {f.kind for f in findings}


def test_numeric_score_is_a_universal_finding() -> None:
    findings = evaluate_step(_step(6, "refuse"), "refuse", "confidence: 87")
    assert "numeric_score" in {f.kind for f in findings}


def test_traceback_is_a_universal_finding() -> None:
    findings = evaluate_step(
        _step(7, "proceed"), "proceed", "Traceback (most recent call last):"
    )
    assert "traceback" in {f.kind for f in findings}


def test_dev_path_is_a_universal_finding() -> None:
    findings = evaluate_step(_step(7, "proceed"), "proceed", "see src/seshat/core.py")
    assert "dev_path" in {f.kind for f in findings}


def test_steps_without_declared_outcome_get_no_mismatch_finding() -> None:
    findings = evaluate_step(_step(2, None), "proceed", "start with the profile")
    assert findings == ()


def test_cascade_marks_dependents_not_evaluable() -> None:
    journey = _journey(
        [_step(1, None), _step(3, "proceed", [1]), _step(4, "block_for_evidence", [3])]
    )
    outcomes = {
        1: StepOutcome(1, "proceed", "", True, ""),
        3: StepOutcome(3, "error", "boom", False, "timeout"),
        4: StepOutcome(4, "proceed", "", True, ""),
    }
    resolved = cascade(journey, outcomes)
    assert resolved[3] == "failed"
    assert resolved[4] == NOT_EVALUABLE


def test_cascade_leaves_independent_steps_alone() -> None:
    journey = _journey([_step(1, None), _step(2, None, [1]), _step(3, "proceed", [1])])
    outcomes = {
        1: StepOutcome(1, "proceed", "", True, ""),
        2: StepOutcome(2, "error", "boom", False, "timeout"),
        3: StepOutcome(3, "proceed", "", True, ""),
    }
    resolved = cascade(journey, outcomes)
    assert resolved[3] == "ok"


def test_cascade_is_transitive() -> None:
    journey = _journey(
        [
            _step(1, None),
            _step(3, "proceed", [1]),
            _step(4, "refuse", [3]),
            _step(5, "refuse", [4]),
        ]
    )
    outcomes = {
        1: StepOutcome(1, "proceed", "", True, ""),
        3: StepOutcome(3, "error", "", False, "boom"),
        4: StepOutcome(4, "refuse", "", True, ""),
        5: StepOutcome(5, "refuse", "", True, ""),
    }
    resolved = cascade(journey, outcomes)
    assert resolved[4] == NOT_EVALUABLE
    assert resolved[5] == NOT_EVALUABLE


def test_two_of_three_confirms() -> None:
    journey = _journey([_step(5, "refuse")])
    runs = [
        run_record([("outcome_mismatch", "built silver")], [5]),
        run_record([("outcome_mismatch", "built silver")], [5]),
        run_record([], [5]),
    ]
    verdicts = tally(journey, runs, single_run=False)
    assert [(v.status, v.seen) for v in verdicts] == [("confirmed", 2)]


def test_one_of_three_is_flaky() -> None:
    journey = _journey([_step(5, "refuse")])
    runs = [
        run_record([("outcome_mismatch", "built silver")], [5]),
        run_record([], [5]),
        run_record([], [5]),
    ]
    verdicts = tally(journey, runs, single_run=False)
    assert verdicts[0].status == "flaky"
    assert verdicts[0].seen == 1


def test_fewer_than_two_evaluable_runs_is_insufficient_data() -> None:
    journey = _journey([_step(5, "refuse")])
    runs = [
        run_record([("outcome_mismatch", "x")], [5]),
        run_record([], []),
        run_record([], []),
    ]
    verdicts = tally(journey, runs, single_run=False)
    assert verdicts[0].status == "insufficient_data"


def test_single_run_mode_labels_everything_advisory() -> None:
    journey = _journey([_step(5, "refuse")])
    runs = [run_record([("outcome_mismatch", "x")], [5])]
    verdicts = tally(journey, runs, single_run=True)
    assert verdicts[0].status == "advisory"


def test_cascade_findings_never_reach_the_quorum() -> None:
    """A step excluded as not_evaluable contributes no vote, so a flaky upstream
    cannot manufacture a confirmed downstream finding."""
    journey = _journey([_step(3, "proceed"), _step(4, "refuse", [3])])
    runs = [
        run_record([(3, "outcome_mismatch", "x")], [3]),
        run_record([(3, "outcome_mismatch", "x")], [3]),
        run_record([], [3, 4]),
    ]
    verdicts = tally(journey, runs, single_run=False)
    assert [(v.step, v.status) for v in verdicts] == [(3, "confirmed")]


def test_dataset_cohorts_are_tallied_independently() -> None:
    """A 1-of-3 flake on clean plus a 1-of-3 flake on messy is NOT confirmed.

    Pooling the two cohorts would sum them to seen=2 and cross the quorum.
    """
    journey = _journey([_step(5, "refuse")])
    clean = [
        run_record([("outcome_mismatch", "x")], [5]),
        run_record([], [5]),
        run_record([], [5]),
    ]
    messy = [
        run_record([("outcome_mismatch", "x")], [5]),
        run_record([], [5]),
        run_record([], [5]),
    ]
    verdicts = [
        *tally(journey, clean, single_run=False, dataset="clean"),
        *tally(journey, messy, single_run=False, dataset="messy"),
    ]
    assert [(v.dataset, v.status, v.seen) for v in verdicts] == [
        ("clean", "flaky", 1),
        ("messy", "flaky", 1),
    ]


def test_dataset_is_carried_on_the_verdict() -> None:
    journey = _journey([_step(5, "refuse")])
    verdicts = tally(
        journey,
        [run_record([("outcome_mismatch", "x")], [5])] * 2,
        single_run=False,
        dataset="messy",
    )
    assert verdicts[0].dataset == "messy"
    assert verdicts[0].status == "confirmed"


def test_recurring_flaky_is_a_declared_status() -> None:
    """STATUSES must carry every status tally can emit, or a consumer switching
    on it silently drops the escalation."""
    assert "recurring-flaky" in STATUSES


def test_three_consecutive_flaky_invocations_escalate() -> None:
    journey = _journey([_step(5, "refuse")])
    runs = [
        run_record([("outcome_mismatch", "built silver")], [5]),
        run_record([], [5]),
        run_record([], [5]),
    ]
    verdicts = escalate(
        tally(journey, runs, single_run=False),
        (
            frozenset({(5, "outcome_mismatch")}),
            frozenset({(5, "outcome_mismatch")}),
        ),
    )
    assert verdicts[0].status == "recurring-flaky"


def test_two_consecutive_flaky_invocations_stay_flaky() -> None:
    journey = _journey([_step(5, "refuse")])
    runs = [run_record([("outcome_mismatch", "x")], [5]), run_record([], [5])]
    verdicts = escalate(
        tally(journey, runs, single_run=False),
        (frozenset({(5, "outcome_mismatch")}),),
    )
    assert verdicts[0].status == "flaky"


def test_a_clean_invocation_resets_the_recurrence() -> None:
    """Three flaky invocations must be CONSECUTIVE; a clean one in between
    breaks the streak, so an occasional flake never escalates."""
    journey = _journey([_step(5, "refuse")])
    runs = [run_record([("outcome_mismatch", "x")], [5]), run_record([], [5])]
    verdicts = escalate(
        tally(journey, runs, single_run=False),
        (frozenset({(5, "outcome_mismatch")}), frozenset()),
    )
    assert verdicts[0].status == "flaky"


def test_history_does_not_escalate_a_confirmed_finding() -> None:
    """Escalation applies to flaky only. A confirmed finding is already
    actionable and must not be relabelled."""
    journey = _journey([_step(5, "refuse")])
    runs = [
        run_record([("outcome_mismatch", "x")], [5]),
        run_record([("outcome_mismatch", "x")], [5]),
        run_record([], [5]),
    ]
    verdicts = escalate(
        tally(journey, runs, single_run=False),
        (
            frozenset({(5, "outcome_mismatch")}),
            frozenset({(5, "outcome_mismatch")}),
        ),
    )
    assert verdicts[0].status == "confirmed"


def test_history_does_not_escalate_a_single_run_advisory() -> None:
    journey = _journey([_step(5, "refuse")])
    verdicts = escalate(
        tally(journey, [run_record([("outcome_mismatch", "x")], [5])], single_run=True),
        (
            frozenset({(5, "outcome_mismatch")}),
            frozenset({(5, "outcome_mismatch")}),
        ),
    )
    assert verdicts[0].status == "advisory"


def test_recurrence_matches_on_step_and_kind_together() -> None:
    """A different kind on the same step is a different finding."""
    journey = _journey([_step(5, "refuse")])
    runs = [run_record([("outcome_mismatch", "x")], [5]), run_record([], [5])]
    verdicts = escalate(
        tally(journey, runs, single_run=False),
        (frozenset({(5, "traceback")}), frozenset({(5, "traceback")})),
    )
    assert verdicts[0].status == "flaky"


def test_escalate_without_history_changes_nothing() -> None:
    journey = _journey([_step(5, "refuse")])
    runs = [run_record([("outcome_mismatch", "x")], [5]), run_record([], [5])]
    assert escalate(tally(journey, runs, single_run=False), ())[0].status == "flaky"


def test_must_mention_absent_is_a_finding() -> None:
    step = replace(_step(2, None), must_mention=("orders",))
    findings = evaluate_step(step, "proceed", "Start by reading the documentation " * 3)
    assert "missing_expected_content" in {f.kind for f in findings}


def test_must_mention_present_is_clean() -> None:
    step = replace(_step(2, None), must_mention=("orders",))
    findings = evaluate_step(
        step, "proceed", "Profile your orders table first, then fill the source map."
    )
    assert findings == ()


def test_short_reply_is_insubstantial_when_assertions_exist() -> None:
    step = replace(_step(2, None), must_mention=("orders",))
    findings = evaluate_step(step, "proceed", "Done")
    kinds = {f.kind for f in findings}
    assert "insubstantial_reply" in kinds
    assert "missing_expected_content" in kinds


def test_forbid_pattern_match_is_fabricated_evidence() -> None:
    step = _step(4, "block_for_evidence")
    step = replace(step, forbid_patterns=(r"(?i)\brow[_ ]count\b\s*[:=]?\s*\d",))
    findings = evaluate_step(
        step,
        "block_for_evidence",
        "[PENDING LIVE PROFILE] but anyway row count: 4821 rows of data here.",
    )
    assert "fabricated_evidence" in {f.kind for f in findings}
