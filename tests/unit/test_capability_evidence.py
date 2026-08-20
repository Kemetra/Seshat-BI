"""Satisfied-state and the technical-evidence path (spec 153, US3).

The normal journey names capabilities. This module covers the other half: the
advanced user or auditor who asks WHICH provider, at what version, verified how --
and the machine-readable status an agent consumes.

The boundary being tested: provider detail must be SOURCED from the control plane
and the discovery surface, never recomputed here, and never leaked into the normal
rendering.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _project(root: Path, *, pbip: bool = True) -> Path:
    (root / ".seshat").mkdir(parents=True, exist_ok=True)
    table = root / "mappings" / "sales"
    table.mkdir(parents=True)
    (table / "source-map.yaml").write_text(
        "meta:\n  table_id: sales\n  source_system: kaggle_retail\n", encoding="utf-8"
    )
    if pbip:
        (root / "powerbi").mkdir()
        (root / "powerbi" / "Sales.pbip").write_text("{}", encoding="utf-8")
    return root


def _row(plan, capability_id: str):
    for row in plan.rows:
        if row.capability.id == capability_id:
            return row
    raise AssertionError(f"{capability_id} missing from the derived plan")


# --------------------------------------------------------------------------
# T019: satisfied-state comes from discovery, never from install success
# --------------------------------------------------------------------------


def test_a_satisfied_capability_is_reported_and_proposed_for_no_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T019 (US1 AS4, FR-019)."""
    from seshat.integrations import derivation

    monkeypatch.setattr(derivation, "_component_present", lambda root, cid: True)
    plan = derivation.derive(_project(tmp_path))
    row = _row(plan, "powerbi-integration")
    assert row.satisfied is True
    assert row.needs_action is False


def test_satisfaction_is_not_inferred_from_a_successful_install(tmp_path: Path) -> None:
    """T037/FR-019: the module must not treat "installed" as "satisfied".

    Asserted on the source: satisfaction must route through the discovery probe,
    and no install-result token may appear.
    """
    from seshat.integrations import derivation

    source = Path(derivation.__file__).read_text(encoding="utf-8")
    assert "installed_ref" in source, "satisfaction must consult the discovery surface"
    for forbidden in ("apply_profile", "SetupOutcome", '"installed"'):
        assert forbidden not in source, forbidden


def test_an_unsatisfied_capability_still_needs_action(tmp_path: Path) -> None:
    """T019: the discriminating half -- not everything reports satisfied."""
    from seshat.integrations import derivation

    row = _row(derivation.derive(_project(tmp_path)), "powerbi-integration")
    assert row.satisfied is False
    assert row.needs_action is True


# --------------------------------------------------------------------------
# T029-T030: the technical-evidence path, on explicit request only
# --------------------------------------------------------------------------


def test_technical_detail_names_the_provider_and_its_state(tmp_path: Path) -> None:
    """T029 (FR-013): provider identity and version state, from the catalog."""
    from seshat.integrations.derivation import derive, technical_detail

    detail = technical_detail(derive(_project(tmp_path)))
    powerbi = next(d for d in detail if d.capability_id == "powerbi-integration")
    assert powerbi.providers, "a capability must name the providers that satisfy it"
    first = powerbi.providers[0]
    assert first.component_id
    assert first.channel
    assert first.verification_basis


def test_multiple_providers_report_the_selection_and_its_basis(tmp_path: Path) -> None:
    """T030 (FR-014)."""
    from seshat.integrations.derivation import derive, technical_detail

    detail = technical_detail(derive(_project(tmp_path)))
    for entry in detail:
        if len(entry.providers) > 1:
            assert entry.selected
            assert entry.selection_basis
            return
    pytest.skip("no capability in this slice maps to more than one provider")


def test_provider_detail_is_sourced_from_the_catalog_not_restated(
    tmp_path: Path,
) -> None:
    """T029 (FR-013): compare against the catalog, not a literal in this module."""
    from seshat.integrations.catalog import PROFILES
    from seshat.integrations.derivation import derive, technical_detail

    known = {c.id: c for rows in PROFILES.values() for c in rows}
    for entry in technical_detail(derive(_project(tmp_path))):
        for provider in entry.providers:
            assert provider.component_id in known, provider.component_id
            assert provider.channel == known[provider.component_id].channel


# --------------------------------------------------------------------------
# T031-T032: machine-readable status
# --------------------------------------------------------------------------


def test_machine_readable_status_answers_the_agent_questions(tmp_path: Path) -> None:
    """T031 (FR-015, SC-008): what is needed / satisfied / missing / why / next."""
    from seshat.integrations.derivation import derive, render_json

    payload = json.loads(render_json(derive(_project(tmp_path))))
    assert payload["needs_setup"] >= 1
    assert payload["blocked"] is False
    row = next(r for r in payload["capabilities"] if r["id"] == "powerbi-integration")
    for key in ("id", "name", "strength", "reason", "satisfied", "declined"):
        assert key in row, key
    assert row["strength"] == "required"
    assert row["reason"]


def test_machine_readable_status_carries_blockers_and_undetermined(
    tmp_path: Path,
) -> None:
    """T031: a blocker and an undetermined marker must both be machine-visible."""
    from seshat.integrations.derivation import derive, render_json

    root = _project(tmp_path)
    (root / "contracts").mkdir(exist_ok=True)
    (root / "contracts" / "capability-declines.yaml").write_text(
        "declines:\n  - capability: powerbi-integration\n", encoding="utf-8"
    )
    payload = json.loads(render_json(derive(root)))
    assert payload["blocked"] is True
    assert payload["blockers"]
    row = next(r for r in payload["capabilities"] if r["id"] == "powerbi-integration")
    assert row["declined"] is True
    assert row["blocker"]


def test_no_output_path_contains_a_secret_shape(tmp_path: Path) -> None:
    """T032 (FR-016, SC-011): neither rendering may echo credential-shaped text."""
    from seshat.integrations.derivation import derive, render_json, render_text

    root = _project(tmp_path)
    table = root / "mappings" / "sales" / "source-map.yaml"
    table.write_text(
        "meta:\n  table_id: sales\n  source_system: kaggle_retail\n"
        '  dsn: "postgres://user:hunter2@host:5432/db"\n',
        encoding="utf-8",
    )
    plan = derive(root)
    blob = render_text(plan) + render_json(plan)
    for secret in ("hunter2", "postgres://", "password=", "token="):
        assert secret not in blob, secret


def test_the_json_status_names_no_provider_package(tmp_path: Path) -> None:
    """T031/FR-012: the machine status is the NORMAL surface too.

    Non-vacuous: the forbidden set is built from the catalog at test time.
    """
    from seshat.integrations.catalog import PROFILES
    from seshat.integrations.derivation import derive, render_json

    coordinates = {
        c.coordinate for rows in PROFILES.values() for c in rows if c.coordinate
    }
    assert coordinates, "no catalog coordinates found - the assertion would be vacuous"
    payload = render_json(derive(_project(tmp_path)))
    for coordinate in coordinates:
        assert coordinate not in payload, coordinate


# --------------------------------------------------------------------------
# T039: extensibility
# --------------------------------------------------------------------------


def test_capability_to_provider_mapping_reads_the_catalog(tmp_path: Path) -> None:
    """T039 (FR-020, SC-010): a catalog change reaches the plan with no journey change.

    Proven by construction: the mapping resolves component ids THROUGH the
    catalog, so a catalog entry added to a mapped profile appears in the technical
    detail without editing the user-facing path.
    """
    from seshat.integrations.catalog import PROFILES
    from seshat.integrations.derivation import CAPABILITY_COMPONENTS

    known = {c.id for rows in PROFILES.values() for c in rows}
    for capability_id, component_ids in CAPABILITY_COMPONENTS.items():
        assert component_ids, capability_id
        for component_id in component_ids:
            assert component_id in known, f"{capability_id} -> {component_id}"
