"""Spec 149 -- pure validator selection for the write adapter (#661, #663).

Selection is separated from execution so these rules can be pinned exhaustively
without spawning a validator: which reports pair with the mutated model, whether
a data leg exists, and which findings a run introduced.
"""

from __future__ import annotations

import pytest

from seshat.pbi_mcp_adapter import validation_plan

pytestmark = pytest.mark.unit


_PRE_EXISTING = (
    "[error] L3 measure 'Unapproved': no approved metric contract "
    "(Other.SemanticModel/definition/other.tmdl:2)"
)


def test_finding_lines_keeps_only_rendered_findings() -> None:
    """`[severity] rule message (locator)` is the shape; chatter is not a finding."""
    stdout = f"{_PRE_EXISTING}\n\nseshat semantic-check: no drift (0 findings).\n"

    assert validation_plan.finding_lines(stdout) == frozenset({_PRE_EXISTING})


def test_finding_lines_of_a_clean_run_is_empty() -> None:
    """No findings is an empty set, never a set holding the summary line."""
    clean = "seshat semantic-check: no drift (0 findings).\n"

    assert validation_plan.finding_lines(clean) == frozenset()


def test_finding_lines_tolerates_absent_output() -> None:
    """A validator that printed nothing yields no findings, not a crash.

    ``None`` is reachable: a subprocess whose reader thread died returns
    ``stdout=None`` (issue #663), and this must not raise on the way to being
    reported as an unobtainable baseline.
    """
    assert validation_plan.finding_lines("") == frozenset()
    assert validation_plan.finding_lines(None) == frozenset()


# --------------------------------------------------------------------------
# Gap 1 -- report/model pairing is READ from definition.pbir, never guessed.
# --------------------------------------------------------------------------


def _model(root, name: str = "Sales.SemanticModel"):
    model = root / name
    (model / "definition").mkdir(parents=True, exist_ok=True)
    return model


def _report(root, name: str, points_at: str | None):
    report = root / name
    report.mkdir(parents=True, exist_ok=True)
    if points_at is not None:
        (report / "definition.pbir").write_text(
            '{"datasetReference": {"byPath": {"path": "%s"}}}' % points_at,
            encoding="utf-8",
        )
    return report


def test_a_report_naming_the_model_is_paired(tmp_path) -> None:
    """The link is read from the artifact, so a differing stem still pairs."""
    model = _model(tmp_path)
    report = _report(tmp_path, "Renamed.Report", "../Sales.SemanticModel")

    paired, skipped = validation_plan.paired_reports(tmp_path, model)

    assert paired == (report,)
    assert skipped == ()


def test_a_report_naming_a_different_model_is_not_paired(tmp_path) -> None:
    """Scoping is the point: an unrelated report must not be validated."""
    model = _model(tmp_path)
    _model(tmp_path, "Other.SemanticModel")
    _report(tmp_path, "Other.Report", "../Other.SemanticModel")

    paired, skipped = validation_plan.paired_reports(tmp_path, model)

    assert paired == ()
    assert skipped == ()


def test_an_unreadable_pbir_is_a_recorded_skip_not_a_pairing(tmp_path) -> None:
    """Decision D3: unknown pairing is recorded with a reason, and does not block."""
    model = _model(tmp_path)
    broken = _report(tmp_path, "Broken.Report", None)
    (broken / "definition.pbir").write_text("{not json", encoding="utf-8")

    paired, skipped = validation_plan.paired_reports(tmp_path, model)

    assert paired == ()
    assert len(skipped) == 1
    check, reason = skipped[0]
    assert check == validation_plan.BINDING_CHECK
    assert "Broken.Report" in reason
    assert "definition.pbir" in reason


def test_a_report_with_no_pbir_at_all_is_a_recorded_skip(tmp_path) -> None:
    """Absence is reported, never silently treated as 'not paired'."""
    model = _model(tmp_path)
    _report(tmp_path, "Bare.Report", None)

    paired, skipped = validation_plan.paired_reports(tmp_path, model)

    assert paired == ()
    assert len(skipped) == 1
    assert "Bare.Report" in skipped[0][1]


def test_a_pbir_without_a_dataset_reference_is_a_recorded_skip(tmp_path) -> None:
    """Valid JSON of the wrong shape is still 'cannot tell', not 'not paired'."""
    model = _model(tmp_path)
    odd = _report(tmp_path, "Odd.Report", None)
    (odd / "definition.pbir").write_text('{"version": "1.0"}', encoding="utf-8")

    paired, skipped = validation_plan.paired_reports(tmp_path, model)

    assert paired == ()
    assert len(skipped) == 1
    assert "Odd.Report" in skipped[0][1]


# --------------------------------------------------------------------------
# Gap 2 -- is there a data leg? Presence only; never the credential.
# --------------------------------------------------------------------------


def test_a_dsn_is_available_from_either_documented_variable() -> None:
    """Both documented forms count: DATABASE_URL and the ANALYTICS_DB_* set."""
    assert validation_plan.dsn_is_available({"DATABASE_URL": "postgresql://h/db"})
    assert validation_plan.dsn_is_available({"ANALYTICS_DB_HOST": "h"})


def test_an_absent_or_empty_dsn_is_not_available() -> None:
    """An empty string is configuration, not a data leg."""
    assert not validation_plan.dsn_is_available({})
    assert not validation_plan.dsn_is_available({"DATABASE_URL": ""})
