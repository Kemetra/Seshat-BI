from __future__ import annotations

import pytest

from scripts.adopter_sim.evaluate import StepOutcome, cascade, evaluate_step
from scripts.adopter_sim.model import NOT_EVALUABLE, Journey, JourneyStep
from scripts.adopter_sim.quorum import tally

pytestmark = pytest.mark.unit


def _step(number: int, behavior: str | None, depends_on=()) -> JourneyStep:
    return JourneyStep(
        number=number,
        title=f"step {number}",
        prompt="do it",
        command=None,
        expected_behavior=behavior,
        depends_on=tuple(depends_on),
    )


def _journey(steps) -> Journey:
    return Journey(name="t", steps=tuple(steps))


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
        {"findings": [("outcome_mismatch", "built silver")], "evaluable": [5]},
        {"findings": [("outcome_mismatch", "built silver")], "evaluable": [5]},
        {"findings": [], "evaluable": [5]},
    ]
    verdicts = tally(journey, runs, single_run=False)
    assert [(v.status, v.seen) for v in verdicts] == [("confirmed", 2)]


def test_one_of_three_is_flaky() -> None:
    journey = _journey([_step(5, "refuse")])
    runs = [
        {"findings": [("outcome_mismatch", "built silver")], "evaluable": [5]},
        {"findings": [], "evaluable": [5]},
        {"findings": [], "evaluable": [5]},
    ]
    verdicts = tally(journey, runs, single_run=False)
    assert verdicts[0].status == "flaky"
    assert verdicts[0].seen == 1


def test_fewer_than_two_evaluable_runs_is_insufficient_data() -> None:
    journey = _journey([_step(5, "refuse")])
    runs = [
        {"findings": [("outcome_mismatch", "x")], "evaluable": [5]},
        {"findings": [], "evaluable": []},
        {"findings": [], "evaluable": []},
    ]
    verdicts = tally(journey, runs, single_run=False)
    assert verdicts[0].status == "insufficient_data"


def test_single_run_mode_labels_everything_advisory() -> None:
    journey = _journey([_step(5, "refuse")])
    runs = [{"findings": [("outcome_mismatch", "x")], "evaluable": [5]}]
    verdicts = tally(journey, runs, single_run=True)
    assert verdicts[0].status == "advisory"


def test_cascade_findings_never_reach_the_quorum() -> None:
    """A step excluded as not_evaluable contributes no vote, so a flaky upstream
    cannot manufacture a confirmed downstream finding."""
    journey = _journey([_step(3, "proceed"), _step(4, "refuse", [3])])
    runs = [
        {"findings": [(3, "outcome_mismatch", "x")], "evaluable": [3]},
        {"findings": [(3, "outcome_mismatch", "x")], "evaluable": [3]},
        {"findings": [], "evaluable": [3, 4]},
    ]
    verdicts = tally(journey, runs, single_run=False)
    assert [(v.step, v.status) for v in verdicts] == [(3, "confirmed")]
