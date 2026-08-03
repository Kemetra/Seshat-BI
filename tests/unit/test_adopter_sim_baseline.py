from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.adopter_sim.baseline import (
    diff_findings,
    findings_baseline_path,
    load_findings_baseline,
    timings_baseline_path,
    update_findings_baseline,
)
from scripts.adopter_sim.model import AdopterSimError
from tests.unit._adopter_sim_helpers import make_verdict as _verdict
from tests.unit._adopter_sim_helpers import write_findings_baseline

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]


def _baseline(tmp_path: Path, entries: list[dict[str, object]]) -> Path:
    return write_findings_baseline(tmp_path / "first-hour.findings.json", entries)


def test_findings_baseline_is_tracked_and_timings_are_not(tmp_path: Path) -> None:
    findings = findings_baseline_path(tmp_path, "first-hour")
    timings = timings_baseline_path(tmp_path, "first-hour")
    assert findings.parts[-3:] == ("journeys", "baseline", "first-hour.findings.json")
    assert ".seshat" in timings.parts and "adopter-sim" in timings.parts


def test_shipped_starting_baseline_is_empty_and_honest() -> None:
    path = findings_baseline_path(_REPO, "first-hour")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["findings"] == []
    assert "not yet accepted" in payload["provenance"]["invoked_by"]


def test_missing_baseline_loads_as_empty(tmp_path: Path) -> None:
    assert load_findings_baseline(tmp_path / "absent.json") == ()


def test_new_finding_is_reported_new(tmp_path: Path) -> None:
    baseline = load_findings_baseline(_baseline(tmp_path, []))
    rows = diff_findings((_verdict(5, "outcome_mismatch"),), baseline)
    assert [(r.step, r.state) for r in rows] == [(5, "new")]


def test_absent_finding_is_reported_resolved(tmp_path: Path) -> None:
    baseline = load_findings_baseline(
        _baseline(tmp_path, [{"step": 5, "kind": "outcome_mismatch"}])
    )
    rows = diff_findings((), baseline)
    assert [(r.step, r.state) for r in rows] == [(5, "resolved")]


def test_present_in_both_is_unchanged(tmp_path: Path) -> None:
    baseline = load_findings_baseline(
        _baseline(tmp_path, [{"step": 5, "kind": "outcome_mismatch"}])
    )
    rows = diff_findings((_verdict(5, "outcome_mismatch"),), baseline)
    assert [(r.step, r.state) for r in rows] == [(5, "unchanged")]


@pytest.mark.parametrize("status", ["flaky", "insufficient_data", "advisory"])
def test_unconfirmed_verdicts_do_not_enter_the_diff(
    tmp_path: Path, status: str
) -> None:
    baseline = load_findings_baseline(_baseline(tmp_path, []))
    rows = diff_findings((_verdict(5, "outcome_mismatch", status=status),), baseline)
    assert rows == ()


def test_update_writes_provenance(tmp_path: Path) -> None:
    path = _baseline(tmp_path, [])
    update_findings_baseline(
        path,
        (_verdict(5, "outcome_mismatch"),),
        run_id="ab12cd34",
        kit_version="0.8.0",
        invoked_by="Ahmed Shaaban",
        partial=False,
        single_run=False,
        aborted=False,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["provenance"]["run_id"] == "ab12cd34"
    assert payload["provenance"]["kit_version"] == "0.8.0"
    assert payload["provenance"]["invoked_by"] == "Ahmed Shaaban"
    assert payload["findings"] == [
        {"dataset": "", "step": 5, "kind": "outcome_mismatch", "detail": "d"}
    ]


def test_update_records_only_confirmed_verdicts(tmp_path: Path) -> None:
    path = _baseline(tmp_path, [])
    update_findings_baseline(
        path,
        (
            _verdict(5, "outcome_mismatch"),
            _verdict(6, "numeric_score", status="flaky"),
        ),
        run_id="ab12cd34",
        kit_version="0.8.0",
        invoked_by="Ahmed Shaaban",
        partial=False,
        single_run=False,
        aborted=False,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert [entry["step"] for entry in payload["findings"]] == [5]


@pytest.mark.parametrize(
    "flags",
    [
        {"partial": True, "single_run": False, "aborted": False},
        {"partial": False, "single_run": True, "aborted": False},
        {"partial": False, "single_run": False, "aborted": True},
    ],
)
def test_update_refuses_unreliable_runs(tmp_path: Path, flags: dict) -> None:
    path = _baseline(tmp_path, [])
    with pytest.raises(AdopterSimError, match="refus"):
        update_findings_baseline(
            path,
            (_verdict(5, "outcome_mismatch"),),
            run_id="ab12cd34",
            kit_version="0.8.0",
            invoked_by="Ahmed Shaaban",
            **flags,
        )


def test_update_refuses_an_unnamed_human(tmp_path: Path) -> None:
    path = _baseline(tmp_path, [])
    with pytest.raises(AdopterSimError, match="no invoking human"):
        update_findings_baseline(
            path,
            (_verdict(5, "outcome_mismatch"),),
            run_id="ab12cd34",
            kit_version="0.8.0",
            invoked_by="   ",
            partial=False,
            single_run=False,
            aborted=False,
        )
