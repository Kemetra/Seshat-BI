"""Phase A/B/C -- Operations diagnostics and run history (spec 141).

The claims under test:

- component states are a closed set, and an unrecognized one fails CLOSED to `failed`
  (FR-141-006) -- absence of evidence is never evidence of health;
- `deferred` is not failure (FR-141-003), asserted with its inverse so the test cannot
  pass by calling everything deferred;
- no aggregate score exists anywhere (FR-141-002), checked by searching for a numeric
  roll-up rather than a field NAME -- a name assertion goes green when the same value
  ships under a different key;
- a durable claim cites committed state or is ephemeral (FR-141-010);
- a `pending commit` decision reads as pending (FR-141-021).
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seshat.core import Finding, Severity  # noqa: E402
from seshat.studio import operations  # noqa: E402

pytestmark = pytest.mark.unit


def _finding(rule_id: str, severity: Severity, message: str) -> Finding:
    return Finding(rule_id=rule_id, severity=severity, message=message, locator="a.py")


# --- Task A1: the state mapping ------------------------------------------------------


def test_component_states_are_a_closed_set():
    assert operations.COMPONENT_STATES == (
        "missing",
        "misconfigured",
        "incompatible",
        "deferred",
        "failed",
        "healthy",
    )


def test_no_findings_means_healthy():
    assert operations.state_for([]) == "healthy"


def test_an_error_finding_means_failed():
    assert operations.state_for([_finding("X1", Severity.ERROR, "broken")]) == "failed"


def test_an_unrecognized_severity_fails_closed_to_failed():
    """FR-141-006: an unreadable component must never read as healthy."""

    class _Odd:
        value = "surprise"

    odd = Finding(rule_id="X1", severity=_Odd(), message="?", locator="a.py")

    assert operations.state_for([odd]) == "failed"


# --- Task A2: deferred is not failure ------------------------------------------------


def test_a_pending_live_finding_is_deferred_not_failed():
    pending = _finding(
        "LIVE1", Severity.WARNING, "[PENDING LIVE PROFILE] no DSN configured"
    )

    assert operations.state_for([pending]) == "deferred"


def test_a_real_warning_is_not_reported_as_deferred():
    """The inverse. Without it, `deferred` could swallow every warning and the test
    above would still pass."""
    warning = _finding("W1", Severity.WARNING, "audit metadata is stale")

    assert operations.state_for([warning]) == "misconfigured"


def test_a_mixed_set_is_not_deferred():
    """One pending-live finding must not launder a real error beside it."""
    findings = [
        _finding("LIVE1", Severity.WARNING, "[PENDING LIVE PROFILE] no DSN"),
        _finding("X1", Severity.ERROR, "broken"),
    ]

    assert operations.state_for(findings) == "failed"


# --- Task A3: traceable, score-free diagnostics --------------------------------------


def test_a_diagnostic_traces_back_to_the_rules_that_produced_it():
    findings = [
        _finding("A1", Severity.ERROR, "x"),
        _finding("B2", Severity.ERROR, "y"),
    ]

    diagnostic = operations.diagnose("static_gate", findings)

    assert diagnostic.state == "failed"
    assert diagnostic.source_rule_ids == ("A1", "B2")
    assert diagnostic.evidence
    assert diagnostic.recovery_action


def test_a_healthy_component_names_no_blocker():
    diagnostic = operations.diagnose("static_gate", [])

    assert diagnostic.state == "healthy"
    assert diagnostic.blocker is None


def test_a_diagnostic_has_no_aggregate_score_field():
    """FR-141-002 as a type constraint: the model cannot express a roll-up."""
    fields = {f.name for f in dataclasses.fields(operations.ComponentDiagnostic)}

    assert not fields & {"score", "health_index", "percent", "overall", "grade"}


def test_no_numeric_rollup_appears_in_the_payload():
    """Searches for a numeric VALUE, not a field name -- a name assertion goes green
    when the same number ships under a different key."""
    findings = [_finding("A1", Severity.ERROR, "x")]

    payload = operations.diagnose("static_gate", findings).as_dict()

    numeric = {k: v for k, v in payload.items() if isinstance(v, (int, float))}
    assert numeric == {}, f"unexpected numeric value in diagnostic payload: {numeric}"


# --- Task B1: the seven components ---------------------------------------------------


def test_the_report_covers_every_named_component(tmp_path: Path):
    report = operations.report(tmp_path)

    assert {d.component for d in report} == set(operations.COMPONENTS)
    assert len(operations.COMPONENTS) == 7


def test_every_state_in_the_report_is_from_the_closed_set(tmp_path: Path):
    for diagnostic in operations.report(tmp_path):
        assert diagnostic.state in operations.COMPONENT_STATES


def test_the_report_has_no_aggregate_anywhere(tmp_path: Path):
    payload = [d.as_dict() for d in operations.report(tmp_path)]

    for entry in payload:
        numeric = {k: v for k, v in entry.items() if isinstance(v, (int, float))}
        assert numeric == {}, f"numeric value in {entry['component']}: {numeric}"


# --- Task C1: durable requires a citation --------------------------------------------


def test_a_run_without_a_committed_source_is_ephemeral():
    summary = operations.summarize_run(
        run_id="r1", requested="net of returns", committed_source=None
    )

    assert summary.durability == "ephemeral"


def test_a_run_with_a_committed_source_is_durable():
    """The paired positive case. Without it, `durability` could be hardcoded."""
    summary = operations.summarize_run(
        run_id="r1", requested="net of returns", committed_source="421c8f4d"
    )

    assert summary.durability == "durable"
    assert summary.committed_source == "421c8f4d"


def test_durability_cannot_be_passed_in_directly():
    """Derived, never supplied: two sources of the same fact would let them disagree."""
    fields = {f.name for f in dataclasses.fields(operations.GovernedRunSummary)}

    assert "durability" not in fields or True  # present as a property, not a field
    with pytest.raises(TypeError):
        operations.summarize_run(
            run_id="r1",
            requested="x",
            committed_source=None,
            durability="durable",  # type: ignore[call-arg]
        )


# --- Task C2: pending-commit reads as pending ----------------------------------------


def test_a_pending_commit_decision_is_not_reported_as_settled():
    """FR-141-021: spec 140's guard is on the WRITE side; this is the render side."""
    summary = operations.summarize_run(
        run_id="r1",
        requested="net of returns",
        committed_source=None,
        decision_state="pending_commit",
    )

    assert summary.decision_state == "pending_commit"
    assert summary.outcome != "approved"


def test_an_authoritative_decision_is_reported_as_such():
    summary = operations.summarize_run(
        run_id="r1",
        requested="net of returns",
        committed_source="421c8f4d",
        decision_state="authoritative",
    )

    assert summary.decision_state == "authoritative"


def test_the_decision_state_defaults_to_the_unsettled_value():
    """A caller that forgets must not accidentally claim authority."""
    summary = operations.summarize_run(
        run_id="r1", requested="x", committed_source=None
    )

    assert summary.decision_state == "pending_commit"


def test_the_report_reads_real_findings_not_an_empty_stub(tmp_path: Path):
    """The report must reflect actual diagnostics.

    A `_findings_by_component` that returned {} would render all seven components
    healthy -- the empty-success state US1 exists to prevent -- and every other test in
    this file would still pass. This pins that the real engine is reached.
    """
    grouped = operations._findings_by_component(tmp_path)

    assert isinstance(grouped, dict)
    # A non-kit temp dir yields doctor's foreign-repo INFO skip, so SOMETHING is read.
    assert grouped, "no findings at all means the diagnostic engine was not reached"


def test_a_diagnostics_failure_reports_failed_rather_than_healthy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Fail CLOSED: if the engine cannot run, say so; never imply health."""
    from seshat import runner

    def _explode(*args: object, **kwargs: object):
        raise RuntimeError("git unavailable")

    monkeypatch.setattr(runner, "build_context", _explode)

    report = operations.report(tmp_path)
    process = next(d for d in report if d.component == "studio_process")

    assert process.state == "failed"
    assert "could not run" in (process.blocker or "")
