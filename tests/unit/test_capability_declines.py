"""Declining a derived capability, and what a decline may not do (spec 153).

A decline is a human choice about project scope, so it lives in committed text
for the same reason a provisioning approval does (#671): a decline that only
exists at runtime would let the caller silently suppress a capability the project
demonstrably needs.

The load-bearing test here is T024: declining a `required` capability must
produce a blocker, and must NOT downgrade the strength to make the blocker
disappear. That is the failure mode this feature could most plausibly ship.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

DECLINES = "contracts/capability-declines.yaml"


def _project(root: Path, *, pbip: bool = False, declines: str | None = None) -> Path:
    (root / ".seshat").mkdir(parents=True, exist_ok=True)
    table = root / "mappings" / "sales"
    table.mkdir(parents=True)
    (table / "source-map.yaml").write_text(
        "meta:\n  table_id: sales\n  source_system: kaggle_retail\n", encoding="utf-8"
    )
    if pbip:
        (root / "powerbi").mkdir()
        (root / "powerbi" / "Sales.pbip").write_text("{}", encoding="utf-8")
    if declines is not None:
        (root / "contracts").mkdir(exist_ok=True)
        (root / DECLINES).write_text(declines, encoding="utf-8")
    return root


def _row(plan, capability_id: str):
    for row in plan.rows:
        if row.capability.id == capability_id:
            return row
    raise AssertionError(f"{capability_id} missing from the derived plan")


# --------------------------------------------------------------------------
# T023: declining a recommended/optional capability
# --------------------------------------------------------------------------


def test_declining_a_non_required_capability_leaves_the_rest_proceeding(
    tmp_path: Path,
) -> None:
    """T023 (FR-009): the remaining approved work is unaffected."""
    from seshat.integrations.derivation import derive

    root = _project(
        tmp_path,
        pbip=True,
        declines="declines:\n  - capability: transformation-engine\n",
    )
    plan = derive(root)
    assert _row(plan, "powerbi-integration").strength == "required"
    assert _row(plan, "database-connectivity").strength == "required"
    assert plan.needs_setup >= 2


def test_a_decline_is_recorded_so_a_later_run_does_not_re_propose_it(
    tmp_path: Path,
) -> None:
    """T023 (FR-009): declined is a distinct state from never-proposed."""
    from seshat.integrations.derivation import derive

    root = _project(
        tmp_path, declines="declines:\n  - capability: transformation-engine\n"
    )
    row = _row(derive(root), "transformation-engine")
    assert row.declined is True
    assert row.capability.id not in {
        r.capability.id for r in derive(root).rows if r.needs_action
    }


# --------------------------------------------------------------------------
# T024: declining a REQUIRED capability -- the load-bearing case
# --------------------------------------------------------------------------


def test_declining_a_required_capability_yields_a_blocker(tmp_path: Path) -> None:
    """T024 (FR-010): refused with a next action, not silently accepted."""
    from seshat.integrations.derivation import derive

    root = _project(
        tmp_path, pbip=True, declines="declines:\n  - capability: powerbi-integration\n"
    )
    row = _row(derive(root), "powerbi-integration")
    assert row.blocker is not None
    assert row.blocker.strip()


def test_declining_a_required_capability_does_not_downgrade_its_strength(
    tmp_path: Path,
) -> None:
    """T024 (FR-010): the failure mode this feature could most plausibly ship.

    Silencing the blocker by relabelling the capability `optional` would make the
    plan self-consistent and WRONG -- the project still needs it. The strength is
    derived from evidence; a human declining it does not change the evidence.
    """
    from seshat.integrations.derivation import derive

    root = _project(
        tmp_path, pbip=True, declines="declines:\n  - capability: powerbi-integration\n"
    )
    row = _row(derive(root), "powerbi-integration")
    assert row.strength == "required"
    assert row.declined is True


def test_a_declined_required_capability_means_setup_is_not_complete(
    tmp_path: Path,
) -> None:
    """T024 (FR-010): the project must not report itself set up."""
    from seshat.integrations.derivation import derive

    root = _project(
        tmp_path, pbip=True, declines="declines:\n  - capability: powerbi-integration\n"
    )
    plan = derive(root)
    assert plan.blocked is True
    assert plan.blockers


# --------------------------------------------------------------------------
# T025: a capability the project does not need
# --------------------------------------------------------------------------


def test_a_capability_outside_derived_need_is_not_promoted(tmp_path: Path) -> None:
    """T025 (FR-006): asking for it does not make it required."""
    from seshat.integrations.derivation import derive, requested_outside_need

    root = _project(tmp_path)  # no pbip -> Power BI is not needed
    plan = derive(root)
    outside = requested_outside_need(plan, ("powerbi-integration",))
    assert outside == ("powerbi-integration",)
    assert _row(plan, "powerbi-integration").strength != "required"


def test_a_capability_inside_derived_need_is_not_flagged_outside(
    tmp_path: Path,
) -> None:
    """T025: the check must discriminate, not flag everything."""
    from seshat.integrations.derivation import derive, requested_outside_need

    plan = derive(_project(tmp_path, pbip=True))
    assert requested_outside_need(plan, ("powerbi-integration",)) == ()


# --------------------------------------------------------------------------
# Reading discipline: a decline file is read like any other committed evidence
# --------------------------------------------------------------------------


def test_an_unreadable_decline_file_does_not_silently_decline_everything(
    tmp_path: Path,
) -> None:
    """A malformed declines file must not be read as "everything is declined".

    Failing OPEN here would be the dangerous direction: it would suppress every
    capability the project needs while looking like a clean plan.
    """
    from seshat.integrations.derivation import derive

    root = _project(tmp_path, pbip=True, declines="declines: [unclosed\n")
    for row in derive(root).rows:
        assert row.declined is False


def test_no_declines_file_means_nothing_is_declined(tmp_path: Path) -> None:
    """The common case: absence of the artifact declines nothing."""
    from seshat.integrations.derivation import derive

    for row in derive(_project(tmp_path, pbip=True)).rows:
        assert row.declined is False
