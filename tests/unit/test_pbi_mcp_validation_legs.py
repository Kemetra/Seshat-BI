"""Spec 149 -- the binding and value legs of post-write validation (#661).

Split from ``test_pbi_mcp_validation`` along the same seam the source uses: that
module proves the SEMANTIC verdict and its baseline attribution, while these two
legs answer different questions -- did this write orphan a report binding, and
does an approved value still hold. Keeping them together measured as Low
Cohesion, which was accurate: they share no state and call nothing in common.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import validation

pytestmark = pytest.mark.unit


def _runner_printing(text: str, returncode: int):
    """A validator stub that prints ``text`` and exits ``returncode``."""
    import subprocess

    def invoke(_root, args):
        return subprocess.CompletedProcess(
            args=list(args), returncode=returncode, stdout=text, stderr=""
        )

    return invoke


# Issue #661 gaps 1 + 2 -- the binding and value legs FR-013 requires.


class _FakeBindingResult:
    def __init__(self, status: str) -> None:
        self.status = status
        self.unresolved = (("Sales", "Amount"),) if status == "blocked" else ()
        self.kind_mismatches = ()


def _model_with_report(root: Path, *, points_at: str = "../Sales.SemanticModel"):
    model = root / "Sales.SemanticModel"
    (model / "definition").mkdir(parents=True, exist_ok=True)
    report = root / "Sales.Report"
    report.mkdir(parents=True, exist_ok=True)
    (report / "definition.pbir").write_text(
        '{"datasetReference": {"byPath": {"path": "%s"}}}' % points_at,
        encoding="utf-8",
    )
    return model


def test_a_blocked_binding_on_a_paired_report_is_a_failure(tmp_path: Path) -> None:
    """A measure rename can orphan a visual's binding; that must fail the write."""
    model = _model_with_report(tmp_path)

    checks_run, failures, skipped = validation.validate_bindings_for(
        tmp_path, model, validator=lambda **_kw: _FakeBindingResult("blocked")
    )

    assert checks_run == ("pbir-validate-bindings Sales.Report",)
    assert failures, "a blocked binding was not reported as a failure"
    assert skipped == ()


def test_a_warning_binding_is_not_promoted_to_a_failure(tmp_path: Path) -> None:
    """A kind mismatch is the shipped validator's WARNING class.

    Promoting it here would block writes the report layer itself does not
    consider broken.
    """
    model = _model_with_report(tmp_path)

    _run, failures, skipped = validation.validate_bindings_for(
        tmp_path, model, validator=lambda **_kw: _FakeBindingResult("warning")
    )

    assert failures == ()
    assert skipped == ()


def test_no_report_bound_to_the_model_is_a_recorded_skip(tmp_path: Path) -> None:
    """A model with no report is normal -- but 'no binding check ran' must be
    visible, not inferred from an empty checks_run."""
    model = tmp_path / "Sales.SemanticModel"
    (model / "definition").mkdir(parents=True)

    checks_run, failures, skipped = validation.validate_bindings_for(
        tmp_path, model, validator=lambda **_kw: _FakeBindingResult("pass")
    )

    assert checks_run == ()
    assert failures == ()
    assert len(skipped) == 1
    assert skipped[0][0] == "pbir-validate-bindings"
    assert "no report" in skipped[0][1].lower()


def test_a_binding_validator_that_raises_is_a_skip_not_a_pass(tmp_path: Path) -> None:
    """Fails CLOSED into a visible skip: a crashed validator never reads clean."""
    model = _model_with_report(tmp_path)

    def boom(**_kw):
        raise RuntimeError("validator exploded")

    checks_run, failures, skipped = validation.validate_bindings_for(
        tmp_path, model, validator=boom
    )

    assert checks_run == ()
    assert failures == ()
    assert len(skipped) == 1
    assert "Sales.Report" in skipped[0][1]


def test_no_dsn_is_a_loud_skip_never_a_pass(tmp_path: Path) -> None:
    """Decision D2: 'no data leg' must never read as 'validated'."""
    checks_run, failures, skipped = validation.validate_value_for(tmp_path, env={})

    assert checks_run == ()
    assert failures == ()
    assert len(skipped) == 1
    check, reason = skipped[0]
    assert check == "value-check"
    assert "[PENDING LIVE PROFILE]" in reason


def test_a_resolvable_dsn_runs_value_check(tmp_path: Path) -> None:
    """With a data leg the check runs, and a non-zero exit is a real failure."""
    checks_run, failures, skipped = validation.validate_value_for(
        tmp_path,
        env={"DATABASE_URL": "postgresql://h/db"},
        runner=_runner_printing("", 1),
    )

    assert checks_run == ("seshat value-check",)
    assert failures, "a non-zero value-check exit was not reported"
    assert skipped == ()


def test_the_dsn_never_appears_in_a_skip_reason_or_failure(tmp_path: Path) -> None:
    """A reason string reaches evidence and stdout: it carries no credential."""
    secret = "postgresql://user:hunter2@db.example.com:5432/prod"

    _run, failures, skipped = validation.validate_value_for(
        tmp_path, env={"DATABASE_URL": secret}, runner=_runner_printing("", 1)
    )

    rendered = " ".join([*failures, *(reason for _c, reason in skipped)])
    assert "hunter2" not in rendered
    assert "db.example.com" not in rendered
