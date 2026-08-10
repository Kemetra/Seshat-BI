"""The projection's payload must validate against `studio-api.yaml` (F10).

This is the check that was missing. `test_studio_contract_matches_authority.py`
compares the contract's ENUMS to the readiness authority's enums -- it proves the
contract is well-formed. It says nothing about whether the CODE obeys it. Those are
orthogonal properties, and the gap let three violations ship green:

* `revision` was emitted at the top level of `WorkspaceSnapshot`, which declares
  `additionalProperties: false` and puts `revision` on `WorkspaceIdentity`;
* `evidence[]` and `blocking_reasons[]` emitted plain strings where the contract
  requires `EvidenceRef` / `BlockingReason` objects with four and three required
  fields (including `live_state`, the [PENDING LIVE PROFILE] signal);
* a non-canonical `status` (e.g. `almost_done`) was projected verbatim into a closed
  enum, because the guard checked string-ness rather than membership.

One instance-level validation catches all three.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unit._studio_workspace_fixtures import (  # noqa: E402
    write_blocked_table,
    write_empty_workspace,
    write_malformed_table,
    write_missing_stage_table,
    write_pending_live_table,
    write_ready_table,
    write_warning_table,
)

_CONTRACT = (
    Path(__file__).resolve().parents[2]
    / "specs/139-seshat-studio-foundation/contracts/studio-api.yaml"
)


def _validator(schema_name: str):
    """A validator for one component schema, resolved against the WHOLE document.

    The document root must be the contract itself: every `$ref` inside it is
    `#/components/schemas/...`, so handing a bare sub-schema to jsonschema makes
    those pointers resolve to nowhere.
    """
    jsonschema = pytest.importorskip("jsonschema")
    document = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    schema = {"$ref": f"#/components/schemas/{schema_name}", **document}
    return jsonschema.validators.validator_for(document)(schema)


def _errors(schema_name: str, payload: object) -> list[str]:
    validator = _validator(schema_name)
    return [
        f"{list(error.absolute_path)}: {error.message}"
        for error in validator.iter_errors(payload)
    ]


@pytest.mark.parametrize(
    "build",
    [
        write_ready_table,
        write_blocked_table,
        write_pending_live_table,
        write_warning_table,
        write_missing_stage_table,
        write_malformed_table,
        write_empty_workspace,
    ],
    ids=[
        "ready",
        "blocked",
        "pending_live",
        "warning",
        "missing_stage",
        "malformed",
        "empty",
    ],
)
def test_the_snapshot_validates_against_the_contract(build, tmp_path: Path) -> None:
    """Every fixture state must produce a contract-valid WorkspaceSnapshot."""
    from seshat.studio import projection

    build(tmp_path)
    payload = projection.build_workspace_snapshot(tmp_path).as_dict()

    errors = _errors("WorkspaceSnapshot", payload)

    assert not errors, "snapshot violates studio-api.yaml:\n  " + "\n  ".join(errors)


def test_a_non_canonical_status_is_refused_not_projected(tmp_path: Path) -> None:
    """A status outside the closed enum must become a defect, never pass through.

    "Gate must match reader": the contract's enum is the reader, so the projection
    has to be at least as strict. Projecting `almost_done` verbatim produced a
    payload that violated the very enum this feature corrected.
    """
    from seshat.studio import projection

    (tmp_path / ".seshat").mkdir(parents=True)
    table = tmp_path / "mappings" / "weird"
    table.mkdir(parents=True)
    (table / "readiness-status.yaml").write_text(
        'table: "weird"\n'
        'current_stage: "source_ready"\n'
        "stages:\n"
        "  source_ready:\n"
        '    status: "almost_done"\n'
        "    evidence: []\n"
        "    blocking_reasons: []\n",
        encoding="utf-8",
    )

    snapshot = projection.build_workspace_snapshot(tmp_path)
    statuses = {stage.status for stage in snapshot.tables[0].stages}

    assert "almost_done" not in statuses, (
        "a non-canonical status leaked into a closed-enum field"
    )
    assert snapshot.input_defects, "an unknown status must be reported as a defect"
    assert any("almost_done" in defect.message for defect in snapshot.input_defects), (
        "the defect must name the offending value so it can be fixed"
    )


def test_the_upstream_next_action_is_preserved(tmp_path: Path) -> None:
    """FR-008 names "next action" among the fields that MUST be preserved.

    The upstream projection carries it; dropping it silently while citing FR-008 as
    satisfied was an over-claim.
    """
    from seshat.status_surface import build_status_projection
    from seshat.studio import projection

    (tmp_path / ".seshat").mkdir(parents=True)
    table = tmp_path / "mappings" / "acts"
    table.mkdir(parents=True)
    (table / "readiness-status.yaml").write_text(
        'table: "acts"\n'
        'current_stage: "mapping_ready"\n'
        'next_action: "run source-mapping to clear the gate"\n'
        "stages:\n"
        "  mapping_ready:\n"
        '    status: "blocked"\n'
        "    evidence: []\n"
        "    blocking_reasons: []\n",
        encoding="utf-8",
    )

    upstream = build_status_projection(tmp_path)["tables"][0]
    assert upstream["next_action"], "fixture must carry an upstream next_action"

    journey = projection.build_workspace_snapshot(tmp_path).tables[0]

    assert journey.next_action is not None, "next_action was dropped (FR-008)"
    assert upstream["next_action"] in journey.next_action.label


def test_a_table_level_blocking_reason_is_preserved(tmp_path: Path) -> None:
    """Upstream also carries table-level blockers; they must not vanish."""
    from seshat.studio import projection

    (tmp_path / ".seshat").mkdir(parents=True)
    table = tmp_path / "mappings" / "blocked_top"
    table.mkdir(parents=True)
    (table / "readiness-status.yaml").write_text(
        'table: "blocked_top"\n'
        'current_stage: "source_ready"\n'
        "blocking_reasons:\n"
        '  - "no named-human approval recorded for the table"\n'
        "stages:\n"
        "  source_ready:\n"
        '    status: "blocked"\n'
        "    evidence: []\n"
        "    blocking_reasons: []\n",
        encoding="utf-8",
    )

    snapshot = projection.build_workspace_snapshot(tmp_path)

    assert "no named-human approval recorded for the table" in repr(
        snapshot.as_dict()
    ), "a table-level blocking reason was dropped (FR-008)"


def test_evidence_carries_a_live_state(tmp_path: Path) -> None:
    """`EvidenceRef.live_state` is the [PENDING LIVE PROFILE] signal.

    A plain string cannot express it, which is why the contract requires an object.
    """
    from seshat.studio import projection

    write_ready_table(tmp_path)
    payload = projection.build_workspace_snapshot(tmp_path).as_dict()

    evidence = payload["tables"][0]["stages"][0]["evidence"]
    assert evidence, "the ready fixture carries evidence"
    assert evidence[0]["live_state"] in {
        "verified",
        "pending_live_profile",
        "not_applicable",
    }


def test_a_pending_live_blocker_is_marked_pending_not_verified(tmp_path: Path) -> None:
    """A [PENDING LIVE PROFILE] marker must not read as verified."""
    from seshat.studio import projection

    write_pending_live_table(tmp_path)
    payload = projection.build_workspace_snapshot(tmp_path).as_dict()

    reasons = payload["tables"][0]["stages"][0]["blocking_reasons"]
    assert reasons, "the pending-live fixture carries a blocking reason"
    assert any("PENDING LIVE PROFILE" in reason["message"] for reason in reasons)
