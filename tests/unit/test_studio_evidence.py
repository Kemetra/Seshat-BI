"""Phase B -- the investigation journey (spec 140, US1, Tasks 2.1-2.3).

US1's load-bearing distinction: a stage with NO evidence is a defect, and a stage
awaiting a live profile is pending. Collapsing those two would launder missing data
into an expected-pending state, so every pending/defect assertion here is paired with
its inverse.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unit import _studio_workspace_fixtures as workspace_fixtures  # noqa: E402
from unit import _workbench_fixtures as fixtures  # noqa: E402

from seshat.studio import evidence, projection  # noqa: E402

pytestmark = pytest.mark.unit

API = "/api/v1"


# --- Task 2.1: assemble the bundle ---------------------------------------------------


def test_a_malformed_table_produces_a_defect_and_no_journey(tmp_path: Path):
    """Malformed committed input must surface as a defect, never as a clean bill.

    The shipped projection drops an unreadable table from `tables` entirely and
    records an `unreadable_readiness_file` defect naming it via `source_ref`. So the
    honest result is: no journey to bundle, and a defect that must not be swallowed.
    Asking for its bundle is a KeyError, not an empty success.
    """
    workspace_fixtures.write_malformed_table(tmp_path, table="malformed_sales")
    snapshot = projection.build_workspace_snapshot(tmp_path)

    assert snapshot.tables == (), "an unreadable table must not present as a journey"
    codes = {defect.code for defect in snapshot.input_defects}
    assert "unreadable_readiness_file" in codes
    assert any(
        "malformed_sales" in (defect.source_ref or "")
        for defect in snapshot.input_defects
    ), "the defect must name the table it came from"

    with pytest.raises(KeyError):
        evidence.bundle_for(snapshot, "malformed_sales")


def test_a_ready_table_reports_no_defects(tmp_path: Path):
    """The inverse of the above. Without it, `defects` could be unconditionally
    non-empty and the malformed test would still pass."""
    workspace_fixtures.write_ready_table(tmp_path, table="ready_sales")
    snapshot = projection.build_workspace_snapshot(tmp_path)

    bundle = evidence.bundle_for(snapshot, "ready_sales")

    assert bundle.defects == ()
    assert bundle.evidence, "a ready table must expose its evidence references"


def test_the_bundle_carries_the_seven_stage_journey(tmp_path: Path):
    workspace_fixtures.write_ready_table(tmp_path, table="ready_sales")
    snapshot = projection.build_workspace_snapshot(tmp_path)

    bundle = evidence.bundle_for(snapshot, "ready_sales")

    assert len(bundle.stages) == 7, "TableJourney is always seven, never a short array"
    assert bundle.table_id == "ready_sales"


def test_an_unknown_table_is_refused_rather_than_silently_empty(tmp_path: Path):
    """An empty bundle for a missing table would read as "this table is fine"."""
    workspace_fixtures.write_ready_table(tmp_path, table="ready_sales")
    snapshot = projection.build_workspace_snapshot(tmp_path)

    with pytest.raises(KeyError):
        evidence.bundle_for(snapshot, "no_such_table")


# --- Task 2.2: pending-live is derived, never inferred from emptiness ----------------


def test_a_pending_live_stage_is_reported_pending(tmp_path: Path):
    workspace_fixtures.write_pending_live_table(tmp_path, table="pending_live_sales")
    snapshot = projection.build_workspace_snapshot(tmp_path)

    bundle = evidence.bundle_for(snapshot, "pending_live_sales")

    assert bundle.pending_live, "a pending-live stage must be reported as pending"
    assert "source_ready" in bundle.pending_live


def test_a_stage_with_no_evidence_is_not_called_pending_live(tmp_path: Path):
    """The inverse, and the reason this pair exists.

    An empty evidence list means "no evidence" -- not "awaiting a live profile". A
    `pending_live` derived from emptiness would fail this. `write_blocked_table` is
    the right fixture: it leaves silver and later stages `not_started` with no
    evidence and no pending-live marker anywhere.
    """
    workspace_fixtures.write_blocked_table(tmp_path, table="blocked_sales")
    snapshot = projection.build_workspace_snapshot(tmp_path)

    bundle = evidence.bundle_for(snapshot, "blocked_sales")

    empty_stages = [stage for stage in bundle.stages if not stage.evidence]
    assert empty_stages, "fixture must supply at least one evidence-free stage"
    for stage in empty_stages:
        assert stage.stage not in bundle.pending_live


def test_a_fully_verified_table_reports_nothing_pending_live(tmp_path: Path):
    workspace_fixtures.write_ready_table(tmp_path, table="ready_sales")
    snapshot = projection.build_workspace_snapshot(tmp_path)

    bundle = evidence.bundle_for(snapshot, "ready_sales")

    assert bundle.pending_live == ()


def test_every_displayed_claim_has_a_source_or_is_pending_live(tmp_path: Path):
    """FR-140-002: nothing unattributed reaches the view."""
    workspace_fixtures.write_pending_live_table(tmp_path, table="pending_live_sales")
    snapshot = projection.build_workspace_snapshot(tmp_path)

    bundle = evidence.bundle_for(snapshot, "pending_live_sales")

    for stage in bundle.stages:
        if stage.status in {"pass", "warning"}:
            assert stage.evidence or stage.stage in bundle.pending_live, (
                f"stage {stage.stage} displays a claim with no source reference"
            )


# --- Task 2.3: the route -------------------------------------------------------------


def test_the_evidence_route_requires_a_session(tmp_path: Path):
    client = fixtures.unauthenticated_client(tmp_path)

    response = client.get(f"{API}/tables/ready_sales/evidence")

    assert response.status_code == 401, response.text


def test_the_evidence_route_returns_the_bundle(tmp_path: Path):
    client = fixtures.studio_client(tmp_path)

    response = client.get(f"{API}/tables/ready_sales/evidence")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["table_id"] == "ready_sales"
    assert len(body["stages"]) == 7
    assert body["defects"] == []


def test_the_evidence_route_reports_an_unknown_table_as_404(tmp_path: Path):
    client = fixtures.studio_client(tmp_path)

    response = client.get(f"{API}/tables/no_such_table/evidence")

    assert response.status_code == 404, response.text


def test_the_evidence_route_response_is_redacted(tmp_path: Path):
    """FR-140-019: Foundation's redaction boundary stays mandatory on new routes."""
    client = fixtures.studio_client(tmp_path)

    response = client.get(f"{API}/tables/ready_sales/evidence")

    assert "postgresql://" not in response.text
    assert "password" not in response.text.lower()
