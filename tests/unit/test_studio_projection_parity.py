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
            # Upstream emits plain strings; the contract requires EvidenceRef and
            # BlockingReason OBJECTS, so parity is asserted on the carried text. The
            # wrapper adds `live_state`/`source_ref`, which the string form could not
            # express -- it never drops or rewrites the original value.
            assert [item.label for item in stage.evidence] == expected["evidence"]
            assert [item.message for item in stage.blocking_reasons] == expected[
                "blocking_reasons"
            ]


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


def test_the_revision_is_content_addressed_not_merely_stable(tmp_path: Path) -> None:
    """Stability alone is satisfied by a CONSTANT, which would be useless.

    A constant digest passed `test_the_projection_is_deterministic` perfectly, so this
    pins the property that actually matters: the revision must MOVE when the projected
    content moves.
    """
    from seshat.studio import projection

    write_ready_table(tmp_path, "one")
    before = projection.build_workspace_snapshot(tmp_path).revision

    write_blocked_table(tmp_path, "two")
    after = projection.build_workspace_snapshot(tmp_path).revision

    assert before != after, "the revision did not change when a table was added"


def test_the_revision_changes_when_a_single_status_changes(tmp_path: Path) -> None:
    """The finest-grained content change the browser must be able to detect."""
    from seshat.studio import projection

    target = write_ready_table(tmp_path, "flip")
    before = projection.build_workspace_snapshot(tmp_path).revision

    target.write_text(
        target.read_text(encoding="utf-8").replace(
            'status: "pass"', 'status: "blocked"', 1
        ),
        encoding="utf-8",
    )
    after = projection.build_workspace_snapshot(tmp_path).revision

    assert before != after, "flipping one stage status did not move the revision"


def test_the_revision_is_path_independent(tmp_path: Path) -> None:
    """Two identical workspaces in different directories must hash the same.

    Claimed in a commit message but previously untested. If an absolute path leaked
    into the digested body, the same committed state would produce different
    revisions per checkout -- and FR-026 keeps operator layout out of payloads anyway.
    """
    from seshat.studio import projection

    first_root = tmp_path / "alpha"
    second_root = tmp_path / "beta"
    write_ready_table(first_root, "same")
    write_ready_table(second_root, "same")

    assert (
        projection.build_workspace_snapshot(first_root).revision
        == projection.build_workspace_snapshot(second_root).revision
    )


def test_the_revision_ignores_the_generation_timestamp(tmp_path: Path) -> None:
    """`generated_at` must not enter the digest, or every read looks like a change."""
    from seshat.studio import projection

    write_ready_table(tmp_path)

    early = projection.build_workspace_snapshot(
        tmp_path, generated_at="2020-01-01T00:00:00Z"
    )
    late = projection.build_workspace_snapshot(
        tmp_path, generated_at="2099-12-31T23:59:59Z"
    )

    assert early.revision == late.revision
    assert early.generated_at != late.generated_at


def test_an_omitted_current_stage_is_not_fabricated(tmp_path: Path) -> None:
    """Upstream never fabricates `current_stage`, and neither may Studio.

    No fixture previously omitted the field, so `current_stage or "publish_ready"` --
    a literal stage fabrication -- survived mutation testing undetected.
    """
    from seshat.studio import projection

    (tmp_path / ".seshat").mkdir(parents=True)
    table = tmp_path / "mappings" / "no_current"
    table.mkdir(parents=True)
    (table / "readiness-status.yaml").write_text(
        'table: "no_current"\n'
        "stages:\n"
        "  source_ready:\n"
        '    status: "not_started"\n'
        "    evidence: []\n"
        "    blocking_reasons: []\n",
        encoding="utf-8",
    )

    journey = projection.build_workspace_snapshot(tmp_path).tables[0]

    assert journey.current_stage is None, (
        f"current_stage was fabricated as {journey.current_stage!r}, but the "
        "committed source omits it"
    )


def test_tables_are_sorted_stably(tmp_path: Path) -> None:
    from seshat.studio import projection

    write_ready_table(tmp_path, "zebra")
    write_blocked_table(tmp_path, "alpha")

    snapshot = projection.build_workspace_snapshot(tmp_path)

    assert [t.table_id for t in snapshot.tables] == ["alpha", "zebra"]


# --------------------------------------------------------------------------- #
# FR-009 -- never a numeric score                                             #
# --------------------------------------------------------------------------- #


#: The ONLY numeric fields the contract declares. Anything else numeric in the payload
#: is a candidate readiness/health/confidence signal, which FR-009 forbids.
_PERMITTED_NUMERIC_KEYS = frozenset({"pending_decision_count", "sequence"})


def _numeric_leaks(node: object, path: str = "") -> list[str]:
    """Every numeric value in the payload that is not an allow-listed counter.

    Type-based, deliberately. An earlier revision grepped `repr(payload)` for the
    WORDS "score"/"confidence"/... which was wrong in both directions: it missed a
    real `{"readiness": 0.87}` (the word never appears) and it false-positived on the
    pytest tmp-dir name leaking into `display_name`. FR-009 forbids a numeric VALUE,
    so the assertion has to look at types.
    """
    if isinstance(node, dict):
        return [
            leak
            for key, value in node.items()
            for leak in _leaks_at(key, value, f"{path}.{key}" if path else str(key))
        ]
    if isinstance(node, (list, tuple)):
        return [
            leak
            for index, value in enumerate(node)
            for leak in _numeric_leaks(value, f"{path}[{index}]")
        ]
    return []


def _leaks_at(key: object, value: object, path: str) -> list[str]:
    """Whether one key/value pair is itself a numeric leak, else recurse into it."""
    if isinstance(value, bool):
        return []  # booleans are flags, not scores
    if isinstance(value, (int, float)) and key not in _PERMITTED_NUMERIC_KEYS:
        return [f"{path}={value!r}"]
    return _numeric_leaks(value, path)


def test_no_numeric_readiness_signal_appears_in_the_snapshot(tmp_path: Path) -> None:
    """FR-009 forbids a readiness, health, confidence, or maturity NUMBER."""
    from seshat.studio import projection

    write_ready_table(tmp_path)
    write_blocked_table(tmp_path)

    payload = projection.build_workspace_snapshot(tmp_path).as_dict()

    leaks = _numeric_leaks(payload)

    assert not leaks, (
        "numeric values leaked into the snapshot; FR-009 forbids a numeric readiness "
        "signal: " + ", ".join(leaks)
    )


def test_the_numeric_guard_would_catch_an_injected_score(tmp_path: Path) -> None:
    """The guard must not be vacuous -- prove it fails on a real score.

    The previous word-grep version passed with `{"readiness": 0.87}` injected.
    """
    payload = {"tables": [{"stages": [{"readiness": 0.87}]}]}

    assert _numeric_leaks(payload) == ["tables[0].stages[0].readiness=0.87"]


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
    # The TEXT matters, not just presence: without it a filled block is
    # indistinguishable from a stage that genuinely has not started.
    assert "unknown" in filled.blocking_reasons[0].message.lower(), (
        "the reason must say the state is UNKNOWN, not merely not started: "
        f"{filled.blocking_reasons[0].message!r}"
    )
    assert snapshot.input_defects, "a missing stage block is an input defect"


def test_stage_order_matches_the_authority(tmp_path: Path) -> None:
    from seshat.status_surface import _STAGE_ORDER
    from seshat.studio import projection

    write_ready_table(tmp_path)
    snapshot = projection.build_workspace_snapshot(tmp_path)

    assert [s.stage for s in snapshot.tables[0].stages] == list(_STAGE_ORDER)
