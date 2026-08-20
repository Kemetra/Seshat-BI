"""Project-derived capability selection (spec 153).

The question every test here answers: does the derived plan follow the project's
committed evidence, or does it fall back to a fixed bundle?

Fixtures are built as real directory trees, because the derivation reads
committed artifacts -- a hand-written evidence dict would only prove the tests
agree with themselves.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _project(
    root: Path,
    *,
    source_map: bool = False,
    pbip: bool = False,
    dbt: bool = False,
    dagster: bool = False,
    unreadable_source_map: bool = False,
) -> Path:
    """A project tree carrying exactly the declared evidence."""
    (root / ".seshat").mkdir(parents=True, exist_ok=True)
    if source_map or unreadable_source_map:
        table = root / "mappings" / "sales"
        table.mkdir(parents=True)
        body = (
            "meta:\n  table_id: sales\n  source_system: kaggle_retail\n"
            if not unreadable_source_map
            else "meta:\n  source_system: [unclosed\n"
        )
        (table / "source-map.yaml").write_text(body, encoding="utf-8")
    if pbip:
        (root / "powerbi").mkdir()
        (root / "powerbi" / "Sales.pbip").write_text("{}", encoding="utf-8")
    if dbt:
        (root / "dbt").mkdir()
        (root / "dbt" / "dbt_project.yml").write_text("name: x\n", encoding="utf-8")
    if dagster:
        (root / "orchestration" / "dagster").mkdir(parents=True)
        (root / "orchestration" / "dagster" / "pyproject.toml").write_text(
            "[project]\n", encoding="utf-8"
        )
    return root


def _row(plan, capability_id: str):
    for row in plan.rows:
        if row.capability.id == capability_id:
            return row
    raise AssertionError(f"{capability_id} missing from the derived plan")


# --------------------------------------------------------------------------
# T009-T013: each capability follows its own evidence
# --------------------------------------------------------------------------


def test_declared_source_makes_database_connectivity_required(tmp_path: Path) -> None:
    """T009 (FR-001, FR-008): the reason must cite the artifact consulted."""
    from seshat.integrations.derivation import derive

    plan = derive(_project(tmp_path, source_map=True))
    row = _row(plan, "database-connectivity")
    assert row.strength == "required"
    assert "source-map.yaml" in row.reason


def test_a_pbip_project_makes_powerbi_integration_required(tmp_path: Path) -> None:
    """T010 (FR-001)."""
    from seshat.integrations.derivation import derive

    row = _row(derive(_project(tmp_path, pbip=True)), "powerbi-integration")
    assert row.strength == "required"


def test_no_pbip_means_powerbi_integration_is_not_required(tmp_path: Path) -> None:
    """T011 (US1 AS3): no declared destination, no required destination."""
    from seshat.integrations.derivation import derive

    row = _row(derive(_project(tmp_path, source_map=True)), "powerbi-integration")
    assert row.strength != "required"


def test_a_committed_dbt_project_drives_transformation_engine(tmp_path: Path) -> None:
    """T012 (US1 AS1): present -> needed; absent -> not-required, cited."""
    from seshat.integrations.derivation import derive

    present = _row(derive(_project(tmp_path / "a", dbt=True)), "transformation-engine")
    assert present.strength in {"required", "recommended"}

    absent = _row(
        derive(_project(tmp_path / "b", source_map=True)), "transformation-engine"
    )
    assert absent.strength == "not-required"
    # The reason must cite what was looked for WITHOUT naming the provider: an
    # earlier version of this assertion demanded "dbt_project.yml" in the text,
    # which the catalog-derived FR-012 check then rejected as a package-name leak.
    # The test was asking for the violation.
    assert "transformation project" in absent.reason
    assert "dbt" not in absent.reason


def test_absent_orchestration_is_not_required_not_undetermined(tmp_path: Path) -> None:
    """T013 (US1 AS1): the distinction the whole design turns on.

    Verified absence is a finding with a citable basis, not silence. If "not
    using it" collapsed into `undetermined`, `not-required` would be unreachable
    and this ratified acceptance scenario untestable.
    """
    from seshat.integrations.derivation import derive

    row = _row(derive(_project(tmp_path, source_map=True)), "orchestration")
    assert row.strength == "not-required"
    assert row.undetermined_evidence is None


# --------------------------------------------------------------------------
# T014-T017: derivation properties
# --------------------------------------------------------------------------


def test_projects_of_different_shape_derive_different_sets(tmp_path: Path) -> None:
    """T014 (SC-002): a test that passes for both shapes would prove nothing."""
    from seshat.integrations.derivation import derive

    bi = derive(_project(tmp_path / "bi", source_map=True, pbip=True))
    plain = derive(_project(tmp_path / "plain", source_map=True))

    bi_strengths = {r.capability.id: r.strength for r in bi.rows}
    plain_strengths = {r.capability.id: r.strength for r in plain.rows}
    assert bi_strengths != plain_strengths


def test_a_derived_set_is_never_every_capability_required(tmp_path: Path) -> None:
    """T015 (SC-002): the union-of-everything default is what this replaces."""
    from seshat.integrations.derivation import derive

    plan = derive(_project(tmp_path, source_map=True))
    assert not all(row.strength == "required" for row in plan.rows)


def test_derivation_is_repeatable_on_unchanged_evidence(tmp_path: Path) -> None:
    """T016 (FR-003)."""
    from seshat.integrations.derivation import derive

    root = _project(tmp_path, source_map=True, pbip=True)
    first = [(r.capability.id, r.strength, r.reason) for r in derive(root).rows]
    second = [(r.capability.id, r.strength, r.reason) for r in derive(root).rows]
    assert first == second


def test_derivation_module_makes_no_network_or_subprocess_call() -> None:
    """T017 (FR-004): read-only and network-free, asserted on the source."""
    from seshat.integrations import derivation

    source = Path(derivation.__file__).read_text(encoding="utf-8")
    for forbidden in ("subprocess", "urllib", "requests", "socket", "psycopg"):
        assert forbidden not in source, forbidden
    for writer in (".write_text(", ".mkdir(", "open("):
        assert writer not in source, writer


# --------------------------------------------------------------------------
# T018-T019: undetermined, and satisfied-state
# --------------------------------------------------------------------------


def test_unreadable_evidence_is_undetermined_never_required(tmp_path: Path) -> None:
    """T018 (FR-005): the no-fabricated-confidence rule applied to derivation."""
    from seshat.integrations.derivation import derive

    row = _row(
        derive(_project(tmp_path, unreadable_source_map=True)), "database-connectivity"
    )
    assert row.strength != "required"
    assert row.undetermined_evidence is not None
    assert "source-map" in row.undetermined_evidence


def test_undetermined_is_not_a_fifth_strength(tmp_path: Path) -> None:
    """T026 (FR-007): exactly four strengths, and `undetermined` is not one."""
    from seshat.integrations.derivation import STRENGTHS

    assert set(STRENGTHS) == {"required", "recommended", "optional", "not-required"}
    assert "undetermined" not in STRENGTHS


def test_every_row_carries_a_strength_and_a_reason(tmp_path: Path) -> None:
    """T021/T022 (FR-007, FR-008, SC-003): zero rows lack either."""
    from seshat.integrations.derivation import STRENGTHS, derive

    for row in derive(_project(tmp_path, source_map=True, pbip=True)).rows:
        assert row.strength in STRENGTHS
        assert row.reason.strip()


# --------------------------------------------------------------------------
# T028 / T034-T038: presentation and the delta boundaries
# --------------------------------------------------------------------------


def test_the_normal_rendering_names_no_provider_package(tmp_path: Path) -> None:
    """T028 (FR-012, SC-004): non-vacuous -- the forbidden set comes from the
    catalog itself at test time, so it cannot silently stop matching."""
    from seshat.integrations.catalog import PROFILES
    from seshat.integrations.derivation import derive, render_text

    coordinates = {
        c.coordinate for rows in PROFILES.values() for c in rows if c.coordinate
    }
    assert coordinates, "no catalog coordinates found - the assertion would be vacuous"

    rendered = render_text(derive(_project(tmp_path, source_map=True, pbip=True)))
    for coordinate in coordinates:
        assert coordinate not in rendered, coordinate
    for token in ("pip install", "npm install", "uvx", "@microsoft/"):
        assert token not in rendered, token


def test_derivation_holds_no_approval_decision(tmp_path: Path) -> None:
    """T034 (FR-018, permanent): the weak approval must be un-inheritable.

    #671 removed it, but this feature must still contain no authorization
    decision and no caller-supplied authorization boolean.
    """
    from seshat.integrations import derivation

    source = Path(derivation.__file__).read_text(encoding="utf-8")
    for forbidden in ("approved", "authorize", "--yes", "args.yes"):
        assert forbidden not in source, forbidden


def test_derivation_installs_resolves_and_locks_nothing(tmp_path: Path) -> None:
    """T035/T037 (FR-017, FR-019): no second installer, resolver or state store."""
    from seshat.integrations import derivation

    source = Path(derivation.__file__).read_text(encoding="utf-8")
    # Call sites, not prose: the module's docstring legitimately says what it does
    # NOT do, so a bare "install" substring would be a false positive and would
    # push the fix toward censoring documentation instead of code.
    for forbidden in (
        "apply_profile(",
        "live_resolvers(",
        "write_lock(",
        "install(",
        "pip ",
        "npm ",
    ):
        assert forbidden not in source, forbidden


def test_default_profile_is_unchanged_by_this_feature() -> None:
    """T038 (FR-002, spec 144 FR-006): derivation is an ADDITIONAL basis.

    `DEFAULT_PROFILE` is an exported constant whose value is contract, so the
    default selection behaviour is not displaced here.
    """
    from seshat.integrations.catalog import ANALYTICS_FULL, DEFAULT_PROFILE

    assert DEFAULT_PROFILE == ANALYTICS_FULL


def test_no_platform_specific_literal_in_derivation() -> None:
    """T041: a Windows literal would go vacuous on Linux CI."""
    from seshat.integrations import derivation

    assert ".exe" not in Path(derivation.__file__).read_text(encoding="utf-8")


def test_a_top_level_source_declaration_is_recognised(tmp_path: Path) -> None:
    """Two source-map shapes exist in committed artifacts, and both are evidence.

    Found by running the derivation against this repository, not against these
    fixtures: `mappings/retail_store_sales/source-map.yaml` nests the declaration
    under `meta.source_system`, while `mappings/demo_sample_orders/source-map.yaml`
    declares `source_id`/`source_kind` at the TOP level. Reading only the nested
    form reported a readable, committed file as unparseable -- a false
    `undetermined` on real data that 17 green fixture-based tests did not catch.
    """
    from seshat.integrations.derivation import derive

    table = tmp_path / "mappings" / "orders"
    table.mkdir(parents=True)
    (table / "source-map.yaml").write_text(
        'source_id: "demo_orders"\nsource_kind: "csv"\ngrain: "one order line"\n',
        encoding="utf-8",
    )
    row = _row(derive(tmp_path), "database-connectivity")
    assert row.strength == "required"
    assert row.undetermined_evidence is None


def test_a_parsing_source_map_with_no_declaration_is_absence_not_undetermined(
    tmp_path: Path,
) -> None:
    """A file that PARSES but declares nothing is decidable -- so `not-required`.

    `undetermined` is reserved for evidence that cannot be read at all.
    """
    from seshat.integrations.derivation import derive

    table = tmp_path / "mappings" / "empty"
    table.mkdir(parents=True)
    (table / "source-map.yaml").write_text('grain: "one row"\n', encoding="utf-8")
    row = _row(derive(tmp_path), "database-connectivity")
    assert row.strength == "not-required"
    assert row.undetermined_evidence is None
