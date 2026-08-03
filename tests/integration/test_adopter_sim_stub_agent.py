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
    from scripts.adopter_sim import agent as agent_mod
    from scripts.adopter_sim import runner as runner_mod

    monkeypatch.setattr(agent_mod, "available", lambda: False)
    monkeypatch.setattr(runner_mod, "_build_wheel", lambda: Path("unused.whl"))
    monkeypatch.setattr(
        runner_mod,
        "_one_run",
        lambda **kwargs: {
            "findings": [],
            "evaluable": [1, 3, 7],
            "calibration": 10.0,
        },
    )
    code = runner_mod.run_invocation(_args())
    assert code is Exit.PARTIAL
    assert code != Exit.OK


def test_fixture_failure_short_circuits_before_the_build(monkeypatch) -> None:
    from scripts.adopter_sim import runner as runner_mod
    from scripts.adopter_sim.model import AdopterSimError

    def _boom(datasets):
        raise AdopterSimError("messy fixture no longer holds: repeated_grain_key")

    built = {"called": False}

    def _build():
        built["called"] = True
        return Path("unused.whl")

    monkeypatch.setattr(runner_mod, "_check_fixtures", _boom)
    monkeypatch.setattr(runner_mod, "_build_wheel", _build)
    assert runner_mod.run_invocation(_args()) is Exit.FIXTURE_FAILED
    assert built["called"] is False


def test_blindness_failure_returns_two_not_three(monkeypatch) -> None:
    """A leaked run must never be reported as a kit regression."""
    from scripts.adopter_sim import agent as agent_mod
    from scripts.adopter_sim import runner as runner_mod
    from scripts.adopter_sim.model import AdopterSimError

    def _leak(**kwargs):
        raise AdopterSimError("ancestor C:\\Users\\dev holds CLAUDE.md")

    monkeypatch.setattr(agent_mod, "available", lambda: True)
    monkeypatch.setattr(runner_mod, "_build_wheel", lambda: Path("unused.whl"))
    monkeypatch.setattr(runner_mod, "_one_run", _leak)
    code = runner_mod.run_invocation(_args(), driver=StubDriver([]))
    assert code is Exit.BLINDNESS_ABORT


def test_confirmed_findings_produce_exit_three(monkeypatch) -> None:
    from scripts.adopter_sim import agent as agent_mod
    from scripts.adopter_sim import runner as runner_mod

    monkeypatch.setattr(agent_mod, "available", lambda: True)
    monkeypatch.setattr(runner_mod, "_build_wheel", lambda: Path("unused.whl"))
    monkeypatch.setattr(
        runner_mod,
        "_one_run",
        lambda **kwargs: {
            "findings": [(5, "outcome_mismatch", "expected refuse, observed proceed")],
            "evaluable": [1, 3, 5, 7],
            "calibration": 10.0,
        },
    )
    args = _args(runs=3)
    assert runner_mod.run_invocation(args, driver=StubDriver([])) is Exit.FINDINGS


def test_single_run_findings_are_advisory_not_confirmed(monkeypatch) -> None:
    """--runs 1 must not report a regression, so the exit code stays clean."""
    from scripts.adopter_sim import agent as agent_mod
    from scripts.adopter_sim import runner as runner_mod

    monkeypatch.setattr(agent_mod, "available", lambda: True)
    monkeypatch.setattr(runner_mod, "_build_wheel", lambda: Path("unused.whl"))
    monkeypatch.setattr(
        runner_mod,
        "_one_run",
        lambda **kwargs: {
            "findings": [(5, "outcome_mismatch", "expected refuse, observed proceed")],
            "evaluable": [5],
            "calibration": 10.0,
        },
    )
    code = runner_mod.run_invocation(_args(runs=1), driver=StubDriver([]))
    assert code is Exit.OK


def test_update_baseline_is_refused_for_a_single_run(monkeypatch) -> None:
    from scripts.adopter_sim import agent as agent_mod
    from scripts.adopter_sim import runner as runner_mod

    monkeypatch.setattr(agent_mod, "available", lambda: True)
    monkeypatch.setattr(runner_mod, "_build_wheel", lambda: Path("unused.whl"))
    monkeypatch.setattr(
        runner_mod,
        "_one_run",
        lambda **kwargs: {"findings": [], "evaluable": [1], "calibration": 10.0},
    )
    args = _args(runs=1, update_baseline=True, invoked_by="Ahmed Shaaban")
    assert runner_mod.run_invocation(args, driver=StubDriver([])) is Exit.HARNESS_ERROR
