from __future__ import annotations

import pytest

from scripts.adopter_sim.cli import build_parser
from scripts.adopter_sim.exitcodes import Exit, classify
from tests.unit._adopter_sim_helpers import make_outcome

pytestmark = pytest.mark.unit


def _classify(**overrides) -> Exit:
    return classify(make_outcome(**overrides))


def test_clean_run_is_zero() -> None:
    assert _classify() is Exit.OK


def test_fixture_failure_wins_over_everything() -> None:
    assert _classify(fixture_failed=True, confirmed_findings=3) is Exit.FIXTURE_FAILED


def test_blindness_abort_outranks_findings() -> None:
    assert (
        _classify(aborted_blindness=True, confirmed_findings=3) is Exit.BLINDNESS_ABORT
    )


def test_harness_error_is_one() -> None:
    assert _classify(harness_error=True) is Exit.HARNESS_ERROR


def test_confirmed_findings_are_three() -> None:
    assert _classify(confirmed_findings=1) is Exit.FINDINGS


def test_metric_out_of_band_without_findings_is_four() -> None:
    assert _classify(metric_out_of_band=True) is Exit.METRIC_OUT_OF_BAND


def test_findings_outrank_metric_drift() -> None:
    assert _classify(confirmed_findings=1, metric_out_of_band=True) is Exit.FINDINGS


def test_partial_run_is_never_zero() -> None:
    assert _classify(partial=True) is Exit.PARTIAL
    assert _classify(partial=True) != Exit.OK


def test_every_code_is_distinct() -> None:
    assert len({member.value for member in Exit}) == len(list(Exit))


def test_parser_defaults_to_three_runs_and_both_datasets() -> None:
    args = build_parser().parse_args([])
    assert args.runs == 3
    assert args.datasets == ["clean", "messy"]
    assert args.journey == "first-hour"
    assert args.update_baseline is False


def test_parser_accepts_single_run_and_named_invoker() -> None:
    args = build_parser().parse_args(
        ["--runs", "1", "--invoked-by", "Ahmed Shaaban", "--datasets", "messy"]
    )
    assert args.runs == 1
    assert args.invoked_by == "Ahmed Shaaban"
    assert args.datasets == ["messy"]


def test_parser_carries_the_documented_timeouts() -> None:
    args = build_parser().parse_args([])
    assert args.agent_timeout == 300
    assert args.cli_timeout == 120
    assert args.ceiling == 90 * 60


def test_parser_rejects_an_unknown_dataset() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--datasets", "production"])
