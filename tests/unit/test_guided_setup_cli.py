"""The derived plan reached through the NORMAL journey (spec 155, US1).

FR-001 is the requirement this whole feature exists for, and it is the one a
library-only implementation would silently fail: before this feature the derived
plan had no consumer anywhere outside its own unit tests -- no CLI verb, no flag,
no skill. So these tests drive the verb, not the module.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _project(root: Path, *, pbip: bool = True, source_map: bool = True) -> Path:
    (root / ".seshat").mkdir(parents=True, exist_ok=True)
    if source_map:
        table = root / "mappings" / "sales"
        table.mkdir(parents=True)
        (table / "source-map.yaml").write_text(
            "meta:\n  table_id: sales\n  source_system: kaggle_retail\n",
            encoding="utf-8",
        )
    if pbip:
        (root / "powerbi").mkdir()
        (root / "powerbi" / "Sales.pbip").write_text("{}", encoding="utf-8")
    return root


def _args(root: Path, **overrides) -> Namespace:
    base = dict(
        repo=str(root),
        profile=None,
        refresh=False,
        apply=False,
        yes=False,
        as_json=False,
        harness=[],
        derived=True,
    )
    base.update(overrides)
    return Namespace(**base)


def _mark_installed(root: Path, *component_ids: str) -> None:
    from seshat.integrations.catalog import SKILLS_DIR

    for component_id in component_ids:
        target = root / SKILLS_DIR / component_id
        target.mkdir(parents=True, exist_ok=True)
        (target / ".seshat-installed").write_text("v1\n", encoding="utf-8")


def _catalog_coordinates() -> set[str]:
    """Every package/coordinate token the catalog knows, read at test time.

    Asserting against a hardcoded list would keep passing after the catalog
    changed, which is exactly the vacuous test this assertion exists to avoid.
    """
    from seshat.integrations.catalog import DEFAULT_PROFILE, PROFILES

    tokens = set()
    for item in PROFILES[DEFAULT_PROFILE]:
        tokens.add(item.coordinate)
        tokens.add(item.id)
    return {token for token in tokens if token}


# --------------------------------------------------------------------------- #
# T027a: the journey exists.
# --------------------------------------------------------------------------- #


def test_the_derived_plan_is_reachable_through_the_verb(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T027a (FR-001): the normal journey, not a library call."""
    from seshat.cli.commands.integrations import integrations_main

    integrations_main(_args(_project(tmp_path)))
    out = capsys.readouterr().out

    assert "Database Connectivity" in out
    assert "Power BI Integration" in out


def test_the_derived_plan_reports_the_proposed_change_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T025 (FR-009, US1 AS2): capability-oriented, with a change count."""
    from seshat.cli.commands.integrations import integrations_main

    integrations_main(_args(_project(tmp_path)))
    out = capsys.readouterr().out

    assert "Proposed changes: 2 capabilities" in out


def test_the_normal_presentation_names_no_package(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T025 (FR-009, SC-001): no package, MCP, npm, runtime id, no install command."""
    from seshat.cli.commands.integrations import integrations_main

    integrations_main(_args(_project(tmp_path)))
    out = capsys.readouterr().out

    leaked = sorted(token for token in _catalog_coordinates() if token in out)
    assert leaked == [], leaked
    assert "pip " not in out
    assert "npm " not in out
    assert "--refresh --apply" not in out


def test_a_not_required_capability_is_shown_as_not_required(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T025 (US1 AS1): the four capabilities are all visible, with strengths."""
    from seshat.cli.commands.integrations import integrations_main

    integrations_main(_args(_project(tmp_path)))
    out = capsys.readouterr().out

    assert "Orchestration" in out
    assert "Not Required" in out


# --------------------------------------------------------------------------- #
# T028a: exit codes.
# --------------------------------------------------------------------------- #


def test_a_scope_needing_setup_exits_nonzero(tmp_path: Path) -> None:
    """T028a (US1 AS7): "needs setup" is distinguishable from "nothing to do"."""
    from seshat.cli.commands.integrations import integrations_main

    assert integrations_main(_args(_project(tmp_path))) == 1


def test_nothing_to_do_exits_zero(tmp_path: Path) -> None:
    """T028a (FR-024, US1 AS7): an empty scope is success, not a refusal."""
    from seshat.cli.commands.integrations import integrations_main

    root = _project(tmp_path, source_map=False)
    _mark_installed(root, "powerbi-modeling-mcp", "fabric-skills")

    assert integrations_main(_args(root)) == 0


def test_a_blocked_plan_exits_nonzero_and_names_the_blocker(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T015/T033 (FR-005): a declined `required` capability blocks the journey."""
    from seshat.cli.commands.integrations import integrations_main

    root = _project(tmp_path)
    (root / "contracts").mkdir()
    (root / "contracts" / "capability-declines.yaml").write_text(
        "declines:\n  - capability: powerbi-integration\n", encoding="utf-8"
    )

    code = integrations_main(_args(root))
    captured = capsys.readouterr()

    assert code == 1
    assert "declined" in (captured.out + captured.err).lower()


# --------------------------------------------------------------------------- #
# T044: the machine-readable status.
# --------------------------------------------------------------------------- #


def test_json_mode_emits_one_document_with_the_eight_agent_facts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T044 (FR-011, US3 AS5, SC-012): drivable without package reasoning."""
    import json

    from seshat.cli.commands.integrations import integrations_main

    integrations_main(_args(_project(tmp_path), as_json=True))
    payload = json.loads(capsys.readouterr().out)

    assert payload["proposed_changes"] == 2
    row = next(
        item
        for item in payload["capabilities"]
        if item["id"] == "database-connectivity"
    )
    for field in (
        "name",
        "strength",
        "reason",
        "satisfied",
        "needs_setup",
        "proposed_action",
        "blocker",
        "approval_required",
        "approval_met",
        "post_execution_status",
    ):
        assert field in row, field


def test_the_machine_readable_status_carries_no_secret(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T048 (FR-022, SC-014)."""
    from seshat.cli.commands.integrations import integrations_main

    integrations_main(_args(_project(tmp_path), as_json=True))
    out = capsys.readouterr().out.lower()

    for token in ("password", "secret", "token=", "postgresql://", "api_key"):
        assert token not in out, token


# --------------------------------------------------------------------------- #
# T026: the advanced path.
# --------------------------------------------------------------------------- #


def test_technical_evidence_reports_provider_and_verification_basis(
    tmp_path: Path,
) -> None:
    """T026 (FR-010): provider, component, coordinate and basis, on request."""
    from seshat.integrations.guided_setup import derive_scope, technical_evidence

    root = _project(tmp_path)
    rows = technical_evidence(root, derive_scope(root))
    by_component = {row.component_id: row for row in rows}

    assert "connectorx" in by_component
    entry = by_component["connectorx"]
    assert entry.capability_id == "database-connectivity"
    assert entry.channel
    assert entry.coordinate
    assert entry.verification_basis


def test_technical_evidence_reads_the_resolved_version_from_the_lock(
    tmp_path: Path,
) -> None:
    """T026 (FR-010): the coordinate is control-plane sourced, not recomputed."""
    import json

    from seshat.integrations.catalog import LOCK_FILE
    from seshat.integrations.guided_setup import derive_scope, technical_evidence
    from seshat.integrations.lockfile import SCHEMA

    root = _project(tmp_path)
    (root / LOCK_FILE).parent.mkdir(parents=True, exist_ok=True)
    (root / LOCK_FILE).write_text(
        json.dumps(
            {
                "schema": SCHEMA,
                "profile": "analytics-core",
                "resolved_at": "2026-08-20T00:00:00Z",
                "components": {"connectorx": {"version": "0.4.4"}},
            }
        ),
        encoding="utf-8",
    )

    rows = technical_evidence(root, derive_scope(root))
    entry = next(row for row in rows if row.component_id == "connectorx")

    assert entry.resolved_version == "0.4.4"
