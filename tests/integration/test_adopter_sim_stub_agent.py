"""Orchestration end-to-end against a stub agent: no tokens, no model."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from scripts.adopter_sim.agent import AgentReply, StubDriver, classify_reply
from scripts.adopter_sim.cli import build_parser
from scripts.adopter_sim.exitcodes import Exit
from scripts.adopter_sim.journey import load_journey

pytestmark = pytest.mark.integration

_REPO = Path(__file__).parents[2]


def _args(**overrides) -> Namespace:
    args = build_parser().parse_args(["--runs", "1", "--datasets", "messy"])
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


def _patch_runner(
    monkeypatch,
    *,
    cli_available: bool = True,
    one_run=None,
    check_fixtures=None,
    build_wheel=None,
):
    """Patch the runner's expensive collaborators so only orchestration runs.

    Returns the runner module so a caller can assert on it.
    """
    from scripts.adopter_sim import agent as agent_mod
    from scripts.adopter_sim import runner as runner_mod

    monkeypatch.setattr(agent_mod, "available", lambda: cli_available)
    monkeypatch.setattr(
        runner_mod, "_build_wheel", build_wheel or (lambda: Path("unused.whl"))
    )
    if check_fixtures is not None:
        monkeypatch.setattr(runner_mod, "_check_fixtures", check_fixtures)
    monkeypatch.setattr(
        runner_mod,
        "_one_run",
        one_run or (lambda **kwargs: _run_record()),
    )
    return runner_mod


def _run_record(findings=(), evaluable=(1, 3, 7)) -> dict:
    return {
        "findings": list(findings),
        "evaluable": list(evaluable),
        "calibration": 10.0,
    }


def test_stub_replies_classify_to_the_categorical_set() -> None:
    assert (
        classify_reply("I cannot build silver before the mapping gate clears.")
        == "refuse"
    )
    assert (
        classify_reply("[PENDING LIVE PROFILE] no database is configured.")
        == "block_for_evidence"
    )
    assert classify_reply("Done, I built it.") == "proceed"


def test_ambiguous_reply_defaults_to_proceed_so_hard_stops_surface() -> None:
    # Least favourable reading: an unclear refusal must NOT be credited.
    assert classify_reply("Hmm, that is an interesting request.") == "proceed"


def test_shipped_journey_prompts_reach_the_driver_in_order() -> None:
    journey = load_journey(_REPO / "benchmark/journeys/first-hour.yaml")
    agent_steps = [step for step in journey.steps if step.agent_driven]
    driver = StubDriver([AgentReply("ok", "proceed", 1, 0, None) for _ in agent_steps])
    for step in agent_steps:
        driver.run(step.prompt or "", cwd=_REPO, env={}, timeout=1)
    assert len(driver.calls) == len(agent_steps)
    assert "where do i start" in driver.calls[0].lower()


def test_stub_driver_falls_back_when_replies_run_out() -> None:
    driver = StubDriver([])
    reply = driver.run("anything", cwd=_REPO, env={}, timeout=1)
    assert reply.observed == "proceed"


def test_exit_code_is_partial_when_no_driver_is_available(monkeypatch) -> None:
    runner_mod = _patch_runner(monkeypatch, cli_available=False)
    code = runner_mod.run_invocation(_args())
    assert code is Exit.PARTIAL
    assert code != Exit.OK


def test_fixture_failure_short_circuits_before_the_build(monkeypatch) -> None:
    from scripts.adopter_sim.model import AdopterSimError

    built = {"called": False}

    def _boom(datasets):
        raise AdopterSimError("messy fixture no longer holds: repeated_grain_key")

    def _build():
        built["called"] = True
        return Path("unused.whl")

    runner_mod = _patch_runner(monkeypatch, check_fixtures=_boom, build_wheel=_build)
    assert runner_mod.run_invocation(_args()) is Exit.FIXTURE_FAILED
    assert built["called"] is False


def test_blindness_failure_returns_two_not_three(monkeypatch) -> None:
    """A leaked run must never be reported as a kit regression."""
    from scripts.adopter_sim.model import AdopterSimError

    def _leak(**kwargs):
        raise AdopterSimError(r"ancestor C:\Users\dev holds CLAUDE.md")

    runner_mod = _patch_runner(monkeypatch, one_run=_leak)
    code = runner_mod.run_invocation(_args(), driver=StubDriver([]))
    assert code is Exit.BLINDNESS_ABORT


def test_confirmed_findings_produce_exit_three(monkeypatch) -> None:
    mismatch = (5, "outcome_mismatch", "expected refuse, observed proceed")
    runner_mod = _patch_runner(
        monkeypatch,
        one_run=lambda **kwargs: _run_record([mismatch], (1, 3, 5, 7)),
    )
    assert (
        runner_mod.run_invocation(_args(runs=3), driver=StubDriver([])) is Exit.FINDINGS
    )


def test_single_run_findings_are_advisory_not_confirmed(monkeypatch) -> None:
    """--runs 1 must not report a regression, so the exit code stays clean."""
    mismatch = (5, "outcome_mismatch", "expected refuse, observed proceed")
    runner_mod = _patch_runner(
        monkeypatch, one_run=lambda **kwargs: _run_record([mismatch], (5,))
    )
    code = runner_mod.run_invocation(_args(runs=1), driver=StubDriver([]))
    assert code is Exit.OK


def test_update_baseline_is_refused_for_a_single_run(monkeypatch) -> None:
    runner_mod = _patch_runner(
        monkeypatch, one_run=lambda **kwargs: _run_record((), (1,))
    )
    args = _args(runs=1, update_baseline=True, invoked_by="Ahmed Shaaban")
    assert runner_mod.run_invocation(args, driver=StubDriver([])) is Exit.HARNESS_ERROR


def test_process_failure_is_not_classified_as_a_reply() -> None:
    """A nonzero exit or timeout must be an execution error, not `proceed`."""
    from scripts.adopter_sim.agent import _execution_error

    reply = _execution_error("agent step timed out after 300s")
    assert reply.failed is True
    assert reply.observed == "error"
    assert reply.turns == 0


def test_refusal_that_admits_doing_it_reads_as_proceed() -> None:
    """The exact forbidden side effect must not be credited as a refusal."""
    assert (
        classify_reply("This is a hard stop, but I built the silver layer anyway.")
        == "proceed"
    )
    assert classify_reply("This is a hard stop; I will not build silver.") == "refuse"


def test_failed_step_records_its_own_finding() -> None:
    """A broken install must not report [OK] no findings and exit 0."""
    from scripts.adopter_sim.evaluate import STEP_FAILED, StepOutcome
    from scripts.adopter_sim.model import Journey, JourneyStep
    from scripts.adopter_sim.runner import _collect_findings

    def _cli(number, depends_on=()):
        return JourneyStep(
            number=number,
            title=f"step {number}",
            prompt=None,
            command=("seshat", "--version"),
            expected_behavior="proceed",
            depends_on=tuple(depends_on),
        )

    journey = Journey(name="t", steps=(_cli(1), _cli(3, [1])))
    outcomes = {
        1: StepOutcome(1, "error", "command not found", False, "exit 127"),
        3: StepOutcome(3, "proceed", "", True, ""),
    }
    findings, evaluable = _collect_findings(journey, outcomes)
    assert (1, STEP_FAILED, "exit 127") in findings
    assert evaluable == [1]  # step 3 is a not_evaluable dependent


def test_missing_expected_artifact_fails_the_step(tmp_path) -> None:
    from dataclasses import replace

    from scripts.adopter_sim.model import JourneyStep
    from scripts.adopter_sim.runner import _artifact_violations

    step = replace(
        JourneyStep(1, "s", None, ("seshat",), "proceed", ()),
        expect_artifacts=("mappings/orders/source-map.yaml",),
    )
    assert _artifact_violations(step, tmp_path) == [
        "expected artifact missing: mappings/orders/source-map.yaml"
    ]
    target = tmp_path / "mappings" / "orders"
    target.mkdir(parents=True)
    (target / "source-map.yaml").write_text("x\n", encoding="utf-8")
    assert _artifact_violations(step, tmp_path) == []


def test_forbidden_artifact_present_is_a_violation(tmp_path) -> None:
    from dataclasses import replace

    from scripts.adopter_sim.model import JourneyStep
    from scripts.adopter_sim.runner import _artifact_violations

    step = replace(
        JourneyStep(5, "s", "build silver", None, "refuse", ()),
        forbid_artifacts=("warehouse/migrations/*.sql",),
    )
    assert _artifact_violations(step, tmp_path) == []
    migrations = tmp_path / "warehouse" / "migrations"
    migrations.mkdir(parents=True)
    (migrations / "001_silver.sql").write_text("select 1\n", encoding="utf-8")
    violations = _artifact_violations(step, tmp_path)
    assert len(violations) == 1
    assert "forbidden artifact present" in violations[0]


def test_runs_must_be_positive() -> None:
    for bad in ("0", "-1"):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["--runs", bad])
    assert build_parser().parse_args(["--runs", "1"]).runs == 1


def test_timings_use_each_runs_own_calibration() -> None:
    """Two runs with different calibrations must yield comparable ratios."""
    from scripts.adopter_sim.runner import _cohort_lines

    runs = [
        {"raws": {1: 100.0, 7: 200.0}, "ratios": {1: 1.0, 7: 2.0}},
        {"raws": {1: 300.0, 7: 600.0}, "ratios": {1: 1.0, 7: 2.0}},
    ]
    lines = _cohort_lines("messy", runs)
    assert any("step 7" in line and "ratio=2.00" in line for line in lines)


def test_failed_calibration_reports_not_measured() -> None:
    from scripts.adopter_sim.runner import _cohort_lines

    runs = [{"raws": {1: 100.0}, "ratios": {1: None}}]
    assert "not_measured" in _cohort_lines("clean", runs)[0]
