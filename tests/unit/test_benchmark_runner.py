from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from seshat.benchmark.model import (
    BenchmarkError,
    Participant,
    RunConditions,
    Scenario,
)
from seshat.benchmark.reference import ScriptedParticipant, reference_participant
from seshat.benchmark.render import render_report_document, render_report_text
from seshat.benchmark.runner import missing_disclosure, run_benchmark

pytestmark = pytest.mark.unit


def _scenario(scenario_id: str = "syn-1", expected: str = "refuse") -> Scenario:
    return Scenario(
        scenario_id=scenario_id,
        title="Synthetic scenario",
        principle="example_principle",
        fixture="fixtures/data.csv",
        prompt="Do the synthetic thing.",
        expected_behavior=expected,
        observable_evidence=("Names the boundary.",),
    )


def _run(participant=None, scenarios=None, **kwargs):
    conditions = RunConditions(
        instructions="reference instructions",
        started_at="2026-07-11T00:00:00+00:00",
        **kwargs,
    )
    return run_benchmark(
        [_scenario()] if scenarios is None else scenarios,
        participant or reference_participant(),
        conditions,
    )


def test_reference_participant_matches_every_declared_behavior() -> None:
    scenarios = [
        _scenario("a", "refuse"),
        _scenario("b", "proceed"),
        _scenario("c", "request_human_decision"),
    ]
    run = _run(scenarios=scenarios)
    assert [obs.comparison for obs in run.observations] == ["match"] * 3
    assert all(obs.variation_note is None for obs in run.observations)


def test_mismatch_and_over_refusal_are_visible_distinctly() -> None:
    participant = ScriptedParticipant(
        script={
            "a": ("proceed", ("went ahead",)),
            "b": ("refuse", ("declined",)),
        }
    )
    run = _run(
        participant=participant,
        scenarios=[_scenario("a", "refuse"), _scenario("b", "proceed")],
    )
    assert run.observations[0].comparison == "mismatch"
    assert run.observations[1].comparison == "over_refusal"


def test_repetitions_are_disclosed_and_variation_is_reported() -> None:
    @dataclass(frozen=True)
    class FlakyParticipant(ScriptedParticipant):
        participant: Participant = Participant(name="flaky", kind="scripted")
        calls: list = field(default_factory=list, compare=False)

        def respond(self, scenario):
            self.calls.append(scenario.scenario_id)
            if len(self.calls) % 2 == 0:
                return "proceed", ("went ahead",)
            return "refuse", ("declined",)

    run = _run(participant=FlakyParticipant(), repetitions=4)
    assert run.repetitions == 4
    observation = run.observations[0]
    assert observation.variation_note is not None
    assert "x2" in observation.variation_note


def test_run_document_disclosure_is_complete_for_reference_runs() -> None:
    document = _run().to_document()
    assert missing_disclosure(document) == []
    assert document["participant"]["kind"] == "scripted"
    assert len(document["instructions_digest"]) == 64


def test_stochastic_participant_without_model_is_incomplete() -> None:
    document = _run().to_document()
    document["participant"] = {"name": "some-agent", "kind": "stochastic"}
    assert "participant.model" in missing_disclosure(document)
    report = render_report_document(document)
    assert report["state"] == "incomplete"
    assert report["rows"] == []
    assert "INCOMPLETE" in render_report_text(document)


def test_no_aggregate_score_percentage_rank_or_winner_anywhere() -> None:
    document = _run().to_document()
    report = render_report_document(document)
    text = render_report_text(document).lower()
    for payload in (json.dumps(document).lower(), json.dumps(report).lower()):
        for token in ('"score"', '"percentage"', '"rank"', '"winner"', '"pass_rate"'):
            assert token not in payload
    assert "no aggregate score" in text


def test_zero_scenarios_or_repetitions_fail_closed() -> None:
    with pytest.raises(BenchmarkError, match="scenario"):
        _run(scenarios=[])
    with pytest.raises(BenchmarkError, match="repetitions"):
        _run(repetitions=0)


def test_scripted_behavior_outside_vocabulary_fails_closed() -> None:
    participant = ScriptedParticipant(script={"a": ("comply", ())})
    with pytest.raises(BenchmarkError, match="observable category"):
        _run(participant=participant, scenarios=[_scenario("a")])
