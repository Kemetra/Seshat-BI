"""T009 -- projection parity against the existing Seshat readiness authority.

FR-007: Studio MUST use existing Seshat Python services and MUST NOT reimplement
readiness derivation. FR-008: every status shown MUST preserve categorical status,
evidence, blocking reasons, required authority, next action, and forbidden scope.
FR-009: never a numeric score. FR-010: malformed inputs are NAMED input defects,
never silently skipped.

**Parity, with one deliberate divergence.** For ready, blocked, empty, and
pending-live workspaces the upstream `build_status_projection` is the authority and
Studio must agree with it exactly. For a MALFORMED file the two are required to
differ: upstream skips it and documents that as intentional ("failing loud on
malformed readiness-status.yaml is RS1's job"), while FR-010 obliges Studio to report
it. Asserting parity there would encode an FR-010 violation as expected behaviour --
and it would pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit._studio_workspace_fixtures import (
    write_blocked_table,
    write_empty_workspace,
    write_malformed_table,
    write_missing_stage_table,
    write_pending_live_table,
    write_ready_table,
    write_warning_table,
)

# --------------------------------------------------------------------------- #
# Parity -- Studio agrees with the upstream authority                          #
# --------------------------------------------------------------------------- #


def _upstream_tables(root: Path) -> list[dict]:
    from seshat.status_surface import build_status_projection

    return build_status_projection(root)["tables"]


@pytest.mark.parametrize(
    "build",
    [write_ready_table, write_blocked_table, write_pending_live_table],
    ids=["ready", "blocked", "pending_live"],
)
def test_studio_preserves_every_upstream_status_verbatim(build, tmp_path: Path) -> None:
    """FR-008 -- the categorical status is projected, never recomputed."""
    from seshat.studio import projection

    build(tmp_path)
    snapshot = projection.build_workspace_snapshot(tmp_path)
    upstream = _upstream_tables(tmp_path)

    assert len(snapshot.tables) == len(upstream)
    for journey, source in zip(snapshot.tables, upstream, strict=True):
        for stage in journey.stages:
            expected = source["stages"].get(stage.stage)
            if expected is None:
                continue
            assert stage.status == expected["status"], (
                f"{stage.stage} status diverged from the upstream projection"
            )
            # `list(...)`: the projection's fields are tuples because the dataclasses
            # are frozen, while the upstream projection emits lists. Same contents.
            assert list(stage.evidence) == expected["evidence"]
            assert list(stage.blocking_reasons) == expected["blocking_reasons"]


@pytest.mark.parametrize(
    "build",
    [write_ready_table, write_blocked_table, write_pending_live_table],
    ids=["ready", "blocked", "pending_live"],
)
def test_studio_preserves_the_upstream_current_stage(build, tmp_path: Path) -> None:
    from seshat.studio import projection

    build(tmp_path)
    snapshot = projection.build_workspace_snapshot(tmp_path)
    upstream = _upstream_tables(tmp_path)

    for journey, source in zip(snapshot.tables, upstream, strict=True):
        assert journey.current_stage == source["current_stage"]


def test_a_warning_status_survives_the_projection(tmp_path: Path) -> None:
    """The status the contract originally had no slot for.

    `warning` means advanced-with-a-recorded-issue. Renaming it to anything else --
    `ready_for_review`, `pass`, `blocked` -- would be a silent governance upgrade or
    downgrade, so it must arrive verbatim.
    """
    from seshat.studio import projection

    write_warning_table(tmp_path)
    snapshot = projection.build_workspace_snapshot(tmp_path)

    source_stage = next(
        stage for stage in snapshot.tables[0].stages if stage.stage == "source_ready"
    )
    assert source_stage.status == "warning"


def test_an_empty_workspace_is_a_useful_state_not_an_error(tmp_path: Path) -> None:
    """FR-009/US1 -- first arrival shows no tables, no traceback, no fake pass."""
    from seshat.studio import projection

    write_empty_workspace(tmp_path)
    snapshot = projection.build_workspace_snapshot(tmp_path)

    assert snapshot.tables == ()
    assert snapshot.input_defects == ()
    assert snapshot.revision, "even an empty workspace has a stable revision"


def test_the_projection_is_deterministic(tmp_path: Path) -> None:
    """Two reads of the same committed state agree, so a revision digest is stable."""
    from seshat.studio import projection

    write_ready_table(tmp_path)
    write_blocked_table(tmp_path)

    first = projection.build_workspace_snapshot(tmp_path)
    second = projection.build_workspace_snapshot(tmp_path)

    assert first.revision == second.revision
    assert [t.table_id for t in first.tables] == [t.table_id for t in second.tables]


def test_tables_are_sorted_stably(tmp_path: Path) -> None:
    from seshat.studio import projection

    write_ready_table(tmp_path, "zebra")
    write_blocked_table(tmp_path, "alpha")

    snapshot = projection.build_workspace_snapshot(tmp_path)

    assert [t.table_id for t in snapshot.tables] == ["alpha", "zebra"]


# --------------------------------------------------------------------------- #
# FR-009 -- never a numeric score                                             #
# --------------------------------------------------------------------------- #


def test_no_numeric_score_appears_anywhere_in_the_snapshot(tmp_path: Path) -> None:
    """FR-009 forbids a readiness, health, confidence, or maturity number."""
    from seshat.studio import projection

    write_ready_table(tmp_path)
    write_blocked_table(tmp_path)

    payload = projection.build_workspace_snapshot(tmp_path).as_dict()
    serialized = repr(payload).lower()

    for forbidden in ("score", "confidence", "completeness", "maturity", "percent"):
        assert forbidden not in serialized, (
            f"{forbidden!r} leaked into the snapshot; FR-009 forbids a numeric "
            "readiness signal"
        )


# --------------------------------------------------------------------------- #
# FR-010 -- DIVERGENCE: malformed input is named, not skipped                 #
# --------------------------------------------------------------------------- #


def test_the_upstream_projection_skips_a_malformed_file(tmp_path: Path) -> None:
    """Pins the upstream behaviour Studio must deliberately diverge from.

    If this ever starts reporting the malformed file, the divergence below is no
    longer needed and this test is the signal to revisit it.
    """
    write_malformed_table(tmp_path)

    assert _upstream_tables(tmp_path) == [], (
        "build_status_projection no longer skips malformed input; the FR-010 "
        "divergence in seshat.studio.projection should be re-examined"
    )


def test_studio_reports_a_malformed_file_as_a_named_input_defect(
    tmp_path: Path,
) -> None:
    """FR-010 -- "MUST NOT skip them silently"."""
    from seshat.studio import projection

    write_malformed_table(tmp_path)
    snapshot = projection.build_workspace_snapshot(tmp_path)

    assert snapshot.input_defects, (
        "a malformed readiness-status.yaml was skipped silently, which is exactly "
        "what FR-010 forbids"
    )
    defect = snapshot.input_defects[0]
    assert defect.source_ref is not None
    assert "malformed_sales" in defect.source_ref
    assert defect.recovery_action


def test_an_input_defect_never_leaks_an_absolute_path(tmp_path: Path) -> None:
    """FR-026 -- a defect names a workspace-relative reference, not a layout."""
    from seshat.studio import projection

    write_malformed_table(tmp_path)
    snapshot = projection.build_workspace_snapshot(tmp_path)

    assert str(tmp_path) not in repr(snapshot.as_dict())


def test_a_malformed_file_does_not_suppress_the_readable_tables(
    tmp_path: Path,
) -> None:
    """One bad file must not blank the workspace."""
    from seshat.studio import projection

    write_ready_table(tmp_path)
    write_malformed_table(tmp_path)
    snapshot = projection.build_workspace_snapshot(tmp_path)

    assert [t.table_id for t in snapshot.tables] == ["ready_sales"]
    assert len(snapshot.input_defects) == 1


# --------------------------------------------------------------------------- #
# Contract shape -- seven stages, always                                      #
# --------------------------------------------------------------------------- #


def test_every_journey_carries_exactly_seven_stages(tmp_path: Path) -> None:
    from seshat.studio import projection

    write_ready_table(tmp_path)
    snapshot = projection.build_workspace_snapshot(tmp_path)

    assert len(snapshot.tables[0].stages) == 7


def test_a_missing_stage_block_is_filled_and_reported(tmp_path: Path) -> None:
    """The contract fixes `stages` at 7 while upstream omits unreadable blocks.

    Studio fills the gap with `not_started` plus an explicit blocking reason AND
    raises an input defect, so the omission is visible rather than merely absent.
    """
    from seshat.studio import projection

    write_missing_stage_table(tmp_path)
    snapshot = projection.build_workspace_snapshot(tmp_path)

    journey = snapshot.tables[0]
    assert len(journey.stages) == 7

    filled = next(stage for stage in journey.stages if stage.stage == "publish_ready")
    assert filled.status == "not_started"
    assert filled.blocking_reasons, "a filled stage must say why it is unknown"
    assert snapshot.input_defects, "a missing stage block is an input defect"


def test_stage_order_matches_the_authority(tmp_path: Path) -> None:
    from seshat.status_surface import _STAGE_ORDER
    from seshat.studio import projection

    write_ready_table(tmp_path)
    snapshot = projection.build_workspace_snapshot(tmp_path)

    assert [s.stage for s in snapshot.tables[0].stages] == list(_STAGE_ORDER)
