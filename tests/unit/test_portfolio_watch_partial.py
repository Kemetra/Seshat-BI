"""US3 tests: a partial portfolio does not fail the run (spec 131, T027,
FR-017).

Some scopes fully evidenced, some empty -> the covered scopes are summarized
truthfully and the un-evidenced scopes are listed as such; the run does not
block or fail on partial coverage.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat import portfolio_watch as pw
from tests.fixtures.portfolio_watch.builders import (
    drift_artifact,
    init_git_repo,
    write_json_artifact,
    write_readiness_status,
    write_source_profile,
)

pytestmark = pytest.mark.unit


def test_partial_portfolio_summarizes_evidenced_scopes_and_lists_empty_ones(
    tmp_path: Path,
) -> None:
    write_readiness_status(tmp_path, "scope_evidenced", current_stage="source_ready")
    write_source_profile(tmp_path, "scope_evidenced")
    write_readiness_status(tmp_path, "scope_empty", current_stage="source_ready")
    # Covered requires an artifact captured at the current HEAD.
    head = init_git_repo(tmp_path)
    write_json_artifact(
        tmp_path,
        "scope_evidenced",
        "drift-findings.json",
        drift_artifact(class_="column_added", captured_at_revision=head),
    )

    summary = pw.build_portfolio_watch_summary(tmp_path)

    assert summary["portfolio"]["scope_count"] == 2
    assert "scope_empty" in summary["portfolio"]["scopes_with_no_evidence"]
    assert "scope_evidenced" not in summary["portfolio"]["scopes_with_no_evidence"]

    evidenced = next(s for s in summary["scopes"] if s["scope_id"] == "scope_evidenced")
    source_drift = next(
        d for d in evidenced["dimensions"] if d["dimension"] == "source_drift"
    )
    assert source_drift["state"] == pw.STATE_COVERED


def test_a_single_scopes_read_error_does_not_abort_the_whole_run(
    tmp_path: Path,
) -> None:
    write_readiness_status(tmp_path, "scope_good", current_stage="source_ready")
    bad_path = tmp_path / "mappings" / "scope_bad" / "readiness-status.yaml"
    bad_path.parent.mkdir(parents=True)
    bad_path.write_text("{broken: [", encoding="utf-8")

    summary = pw.build_portfolio_watch_summary(tmp_path)

    assert summary["portfolio"]["scope_count"] == 2
    scope_ids = {s["scope_id"] for s in summary["scopes"]}
    assert scope_ids == {"scope_good", "scope_bad"}
