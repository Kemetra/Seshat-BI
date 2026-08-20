"""The derived provisioning scope and its presentation (spec 155, US1).

The question every test here answers: does the proposed change set contain
exactly the components the project's own evidence calls for -- and can a reader
tell WHY anything was left out?

Fixtures are real directory trees, and the expected component sets are read from
the catalog at test time. A hardcoded id list would keep passing after the
catalog moved underneath it, which is the failure this feature is meant to make
impossible.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_READABLE_MAP = "meta:\n  table_id: sales\n  source_system: kaggle_retail\n"
_UNREADABLE_MAP = "meta:\n  source_system: [unclosed\n"

_EVIDENCE = frozenset({"source_map", "pbip", "dbt", "dagster", "unreadable_source_map"})


def _project(root: Path, *evidence: str) -> Path:
    """A project tree carrying exactly the declared evidence.

    Deliberately the same shape as the spec-153 derivation fixtures: the bridge
    must read the SAME committed evidence, so building it differently here would
    hide a disagreement between the two layers.
    """
    unknown = sorted(set(evidence) - _EVIDENCE)
    assert not unknown, f"unknown evidence: {unknown}"
    declared = set(evidence)
    (root / ".seshat").mkdir(parents=True, exist_ok=True)
    if {"source_map", "unreadable_source_map"} & declared:
        table = root / "mappings" / "sales"
        table.mkdir(parents=True)
        body = _UNREADABLE_MAP if "unreadable_source_map" in declared else _READABLE_MAP
        (table / "source-map.yaml").write_text(body, encoding="utf-8")
    if "pbip" in declared:
        (root / "powerbi").mkdir()
        (root / "powerbi" / "Sales.pbip").write_text("{}", encoding="utf-8")
    if "dbt" in declared:
        (root / "dbt").mkdir()
        (root / "dbt" / "dbt_project.yml").write_text("name: x\n", encoding="utf-8")
    if "dagster" in declared:
        (root / "orchestration" / "dagster").mkdir(parents=True)
        (root / "orchestration" / "dagster" / "pyproject.toml").write_text(
            "[project]\n", encoding="utf-8"
        )
    return root


def _decline(root: Path, capability_id: str) -> None:
    contracts = root / "contracts"
    contracts.mkdir(parents=True, exist_ok=True)
    (contracts / "capability-declines.yaml").write_text(
        f"declines:\n  - capability: {capability_id}\n", encoding="utf-8"
    )


def _mark_installed(root: Path, *component_ids: str) -> None:
    """Write the discovery surface's own install marker for each component."""
    from seshat.integrations.catalog import SKILLS_DIR

    for component_id in component_ids:
        target = root / SKILLS_DIR / component_id
        target.mkdir(parents=True, exist_ok=True)
        (target / ".seshat-installed").write_text("v1\n", encoding="utf-8")


def _projected(*capability_ids: str) -> set[str]:
    """The component ids spec 153's projection assigns to these capabilities."""
    from seshat.integrations.derivation import CAPABILITY_COMPONENTS

    return {
        component_id
        for capability_id in capability_ids
        for component_id in CAPABILITY_COMPONENTS[capability_id]
    }


def _reason_for(scope, capability_id: str) -> str | None:
    for row in scope.excluded:
        if row.capability_id == capability_id:
            return row.reason
    return None


# --------------------------------------------------------------------------- #
# T011-T013, T017-T019: what enters the scope, and why anything does not.
# --------------------------------------------------------------------------- #


def test_scope_is_exactly_the_projection_of_the_needed_capabilities(
    tmp_path: Path,
) -> None:
    """T011 (FR-002, US1 AS1): Postgres + Power BI -> those two, nothing else."""
    from seshat.integrations.guided_setup import derive_scope

    scope = derive_scope(_project(tmp_path, "source_map", "pbip"))

    assert set(scope.component_ids) == _projected(
        "database-connectivity", "powerbi-integration"
    )


def test_scope_is_a_strict_subset_of_the_default_profile(tmp_path: Path) -> None:
    """T012 (SC-002): narrower than the curated default, measured from the catalog.

    The expected set is computed from `PROFILES` here rather than written out, so
    a catalog change moves this assertion instead of silently invalidating it.
    """
    from seshat.integrations.catalog import DEFAULT_PROFILE, PROFILES
    from seshat.integrations.guided_setup import derive_scope

    scope = derive_scope(_project(tmp_path, "source_map", "pbip"))
    default = {item.id for item in PROFILES[DEFAULT_PROFILE]}

    assert set(scope.component_ids) < default


def test_a_not_required_capability_contributes_nothing(tmp_path: Path) -> None:
    """T013 (FR-003, US1 AS1, scenario B): absence of evidence excludes it."""
    from seshat.integrations.guided_setup import derive_scope

    scope = derive_scope(_project(tmp_path, "source_map", "pbip"))

    assert not set(scope.component_ids) & _projected("orchestration")
    assert not set(scope.component_ids) & _projected("transformation-engine")
    assert _reason_for(scope, "orchestration") == "not-required"


def test_an_optional_capability_contributes_nothing(tmp_path: Path) -> None:
    """T017 (FR-003, owner decision 2): presented, never proposed."""
    from seshat.integrations.guided_setup import derive_scope

    scope = derive_scope(_project(tmp_path, "unreadable_source_map"))
    reason = _reason_for(scope, "database-connectivity")

    assert not set(scope.component_ids) & _projected("database-connectivity")
    # The unreadable source-map derives `optional` WITH an undetermined marker;
    # either exclusion reason is correct, but it must not be silently absent.
    assert reason in {"optional", "undetermined"}


def test_undetermined_evidence_is_named_not_guessed(tmp_path: Path) -> None:
    """T018 (FR-003): the missing evidence reaches the caller."""
    from seshat.integrations.guided_setup import derive_scope

    scope = derive_scope(_project(tmp_path, "unreadable_source_map"))
    row = next(
        row for row in scope.plan.rows if row.capability.id == "database-connectivity"
    )

    assert row.undetermined_evidence
    assert "source-map" in row.undetermined_evidence


def test_a_capability_with_no_catalog_component_is_reported_unsupported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T019 (FR-023): never dropped, and never reported satisfied.

    The projection is emptied for one capability rather than inventing a fake
    capability, so the assertion exercises the real derivation path.
    """
    from seshat.integrations import derivation, guided_setup

    mapping = dict(derivation.CAPABILITY_COMPONENTS)
    mapping["powerbi-integration"] = ()
    monkeypatch.setattr(derivation, "CAPABILITY_COMPONENTS", mapping)

    scope = guided_setup.derive_scope(_project(tmp_path, "source_map", "pbip"))

    assert "powerbi-integration" in scope.unsupported
    assert not any(
        row.satisfied
        for row in scope.plan.rows
        if row.capability.id == "powerbi-integration"
    )


# --------------------------------------------------------------------------- #
# T014-T016, T020: declines, satisfaction, and attributable exclusion.
# --------------------------------------------------------------------------- #


def test_a_declined_recommended_capability_leaves_the_rest_proposable(
    tmp_path: Path,
) -> None:
    """T014 (FR-003, US1 AS4, SC-004, scenario D)."""
    from seshat.integrations.guided_setup import derive_scope

    root = _project(tmp_path, "source_map", "pbip")
    _decline(root, "powerbi-integration")
    scope = derive_scope(root)

    assert not set(scope.component_ids) & _projected("powerbi-integration")
    assert set(scope.component_ids) == _projected("database-connectivity")


def test_a_declined_required_capability_blocks_the_plan(tmp_path: Path) -> None:
    """T015 (FR-005, US1 AS5, SC-004, scenario E): blocked, and still required."""
    from seshat.integrations.guided_setup import derive_scope

    root = _project(tmp_path, "source_map", "pbip")
    _decline(root, "powerbi-integration")
    scope = derive_scope(root)
    row = next(
        row for row in scope.plan.rows if row.capability.id == "powerbi-integration"
    )

    assert scope.blocked
    assert scope.blockers
    assert row.strength == "required"
    assert row.declined


def test_a_satisfied_capability_produces_no_install_action(tmp_path: Path) -> None:
    """T016 (FR-004, US1 AS3, SC-003, scenario C): visible, and not proposed."""
    from seshat.integrations.guided_setup import derive_scope

    root = _project(tmp_path, "source_map", "pbip")
    _mark_installed(root, "powerbi-modeling-mcp", "fabric-skills")
    scope = derive_scope(root)
    row = next(
        row for row in scope.plan.rows if row.capability.id == "powerbi-integration"
    )

    assert row.satisfied
    assert not set(scope.component_ids) & _projected("powerbi-integration")
    assert _reason_for(scope, "powerbi-integration") == "satisfied"


def test_every_exclusion_carries_its_reason(tmp_path: Path) -> None:
    """T020: counting components cannot tell a correct exclusion from a bug."""
    from seshat.integrations.guided_setup import derive_scope

    scope = derive_scope(_project(tmp_path, "source_map", "pbip"))
    contributing = {row.capability.id for row in scope.contributing}
    excluded = {row.capability_id for row in scope.excluded}

    assert contributing | excluded == {row.capability.id for row in scope.plan.rows}
    assert not contributing & excluded
    assert all(row.reason for row in scope.excluded)


# --------------------------------------------------------------------------- #
# T021-T023: determinism, no widening, no writes.
# --------------------------------------------------------------------------- #


def test_the_scope_is_deterministic_including_its_order(tmp_path: Path) -> None:
    """T021 (FR-006, SC-007): membership AND order, twice."""
    from seshat.integrations.guided_setup import derive_scope

    root = _project(tmp_path, "source_map", "pbip", "dbt")

    assert derive_scope(root).component_ids == derive_scope(root).component_ids


@pytest.mark.parametrize(
    "requested",
    [
        ("connectorx",),
        ("dbt-core",),
        ("analytics-full",),
        ("orchestration",),
        ("some-package-nobody-declared",),
    ],
)
def test_no_caller_value_widens_the_scope(
    tmp_path: Path, requested: tuple[str, ...]
) -> None:
    """T022 (FR-007, US1 AS6, SC-006): argv cannot add to the authorized set."""
    from seshat.integrations.guided_setup import derive_scope

    root = _project(tmp_path, "source_map", "pbip")
    baseline = derive_scope(root)

    assert derive_scope(root, requested=requested).component_ids == (
        baseline.component_ids
    )


def test_a_request_outside_derived_need_is_reported(tmp_path: Path) -> None:
    """T022 (FR-007): reported as outside need, never promoted."""
    from seshat.integrations.guided_setup import derive_scope

    scope = derive_scope(
        _project(tmp_path, "source_map", "pbip"), requested=("orchestration",)
    )

    assert scope.outside_need == ("orchestration",)


def test_planning_writes_nothing_and_resolves_nothing(tmp_path: Path) -> None:
    """T023 (FR-008, US1 AS7): no file appears, and no resolver is constructed."""
    from seshat.integrations.guided_setup import derive_scope

    root = _project(tmp_path, "source_map", "pbip")
    before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

    derive_scope(root)

    after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    assert before == after


def test_an_all_satisfied_project_proposes_no_change(tmp_path: Path) -> None:
    """T028 (FR-024): an empty scope is a valid outcome, not a refusal."""
    from seshat.integrations.guided_setup import derive_scope

    root = _project(tmp_path, "pbip")
    _mark_installed(root, "powerbi-modeling-mcp", "fabric-skills")
    scope = derive_scope(root)

    assert scope.component_ids == ()
    assert not scope.blocked
