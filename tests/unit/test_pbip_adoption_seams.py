"""PBIP adoption seam composition: readiness degrades WITH a report (F237)."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.pbip_adoption._seams import (
    _NextStepInputs,
    _next_step,
    _readiness,
    _readiness_response_step,
)

pytestmark = pytest.mark.unit


def _raise_key_error(_root: object) -> dict:
    raise KeyError("stages")


def test_readiness_failure_is_reported_as_an_unavailable_fact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import seshat.readiness_projection as projection

    monkeypatch.setattr(projection, "build_readiness_projection", _raise_key_error)
    readiness, blockers, facts = _readiness(tmp_path)
    assert readiness == [] and blockers == []
    assert [fact.id for fact in facts] == ["unavailable:readiness-projection"]
    assert facts[0].classification == "unavailable_with_reason"
    assert facts[0].reason == "KeyError"


def test_unevaluable_readiness_never_says_no_readiness_file() -> None:
    fact = {
        "id": "unavailable:readiness-projection",
        "classification": "unavailable_with_reason",
        "detail": "Readiness could not be evaluated.",
        "required_authority": None,
    }
    step = _next_step(_NextStepInputs("pbip_project", "clean", [fact], [], []))
    assert "No readiness file found" not in step["action"]
    assert step["kind"] == "terminal_stop"
    assert "could not be evaluated" in step["action"]


def test_healthy_empty_readiness_keeps_the_default_step(tmp_path: Path) -> None:
    readiness, blockers, facts = _readiness(tmp_path)
    assert facts == []
    step = _next_step(_NextStepInputs("pbip_project", "clean", [], readiness, []))
    assert step["action"].startswith("No readiness file found")


def test_readiness_blocking_reasons_are_redacted() -> None:
    secret = "postgresql://svc:hunter2@db.example:5432/app"
    step = _readiness_response_step(
        {"outcome": "blocked", "stage": "mapping_ready", "blocking_reasons": [secret]}
    )
    assert step["blocking_reasons"]
    assert all("hunter2" not in reason for reason in step["blocking_reasons"])
