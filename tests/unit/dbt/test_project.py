from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from seshat.dbt.contracts import WorkingSet

pytestmark = pytest.mark.unit

MAP_REVISION = "a" * 40


@dataclass(frozen=True)
class ProjectFixture:
    profile_literal: bool = False
    target_schema: str = "seshat_dbt_shadow"
    selector_name: str = "seshat_table_orders"
    citation_revision: str = MAP_REVISION
    cite_column: bool = True


def _working_set(root: Path) -> WorkingSet:
    mapping = root / "mappings/orders"
    mapping.mkdir(parents=True, exist_ok=True)
    source_map = mapping / "source-map.yaml"
    readiness = mapping / "readiness-status.yaml"
    questions = mapping / "unresolved-questions.md"
    source_map.write_text("meta:\n  table_id: orders\n", encoding="utf-8")
    readiness.write_text("stages: {}\n", encoding="utf-8")
    questions.write_text("Gate status: CLEARED\n", encoding="utf-8")
    return WorkingSet(
        repo_root=root,
        table_id="orders",
        mapping_dir=mapping,
        source_map=source_map,
        readiness_status=readiness,
        unresolved_questions=questions,
        source_map_revision=MAP_REVISION,
        source_map_sha256="b" * 64,
    )


def _project_yaml() -> str:
    return "\n".join(
        [
            "name: seshat_bi",
            "version: 1.0.0",
            "config-version: 2",
            "profile: seshat_bi_warehouse",
            "model-paths: [models]",
            "models:",
            "  seshat_bi:",
            "    staging:",
            "      +schema: silver",
            "",
        ]
    )


def _selectors_yaml(selector_name: str) -> str:
    return "\n".join(
        [
            "selectors:",
            f"  - name: {selector_name}",
            "    definition:",
            "      method: tag",
            "      value: seshat_table_orders",
            "",
        ]
    )


def _profile_yaml(fixture: ProjectFixture) -> str:
    host = (
        "private-host"
        if fixture.profile_literal
        else "{{ env_var('SESHAT_DBT_HOST') }}"
    )
    return "\n".join(
        [
            "seshat_bi_warehouse:",
            "  target: shadow",
            "  outputs:",
            "    shadow:",
            "      type: postgres",
            f'      host: "{host}"',
            "      port: \"{{ env_var('SESHAT_DBT_PORT', '5432') | int }}\"",
            "      user: \"{{ env_var('SESHAT_DBT_USER') }}\"",
            "      password: \"{{ env_var('SESHAT_DBT_PASSWORD') }}\"",
            "      dbname: \"{{ env_var('SESHAT_DBT_DBNAME') }}\"",
            "      schema: \"{{ env_var('SESHAT_DBT_SCHEMA', "
            f"'{fixture.target_schema}') }}}}\"",
            "      threads: 4",
            "      sslmode: \"{{ env_var('SESHAT_DBT_SSLMODE', 'prefer') }}\"",
            "",
        ]
    )


def _model_yaml(fixture: ProjectFixture) -> str:
    column_meta = (
        "\n".join(
            [
                "        meta:",
                "          seshat:",
                "            source_columns: [order_id]",
            ]
        )
        if fixture.cite_column
        else ""
    )
    return "\n".join(
        [
            "version: 2",
            "models:",
            "  - name: stg_orders",
            "    config:",
            "      tags: [seshat_table_orders]",
            "    meta:",
            "      seshat:",
            "        table_id: orders",
            "        source_map: mappings/orders/source-map.yaml",
            f"        source_map_revision: {fixture.citation_revision}",
            "        grain: one row per order",
            "        business_key: [order_id]",
            "        authority: derived",
            "    columns:",
            "      - name: order_id",
            column_meta,
            "",
        ]
    )


def _write_project(root: Path, fixture: ProjectFixture | None = None) -> WorkingSet:
    fixture = fixture or ProjectFixture()
    working_set = _working_set(root)
    project = root / "dbt"
    model_dir = project / "models/staging/orders"
    model_dir.mkdir(parents=True)
    (project / "dbt_project.yml").write_text(_project_yaml(), encoding="utf-8")
    (project / "selectors.yml").write_text(
        _selectors_yaml(fixture.selector_name), encoding="utf-8"
    )
    (root / "profiles.example.yml").write_text(_profile_yaml(fixture), encoding="utf-8")
    (model_dir / "stg_orders.sql").write_text(
        "select order_id from {{ source('bronze', 'orders') }}\n",
        encoding="utf-8",
    )
    (model_dir / "_models.yml").write_text(_model_yaml(fixture), encoding="utf-8")
    return working_set


def test_valid_project_returns_selector_schemas_and_contracts(tmp_path: Path) -> None:
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path)

    result = validate_project(tmp_path, working_set)

    assert result.valid is True
    assert result.selector_name == "seshat_table_orders"
    assert result.profile_name == "seshat_bi_warehouse"
    assert result.target_name == "shadow"
    assert result.schemas.silver == "seshat_dbt_shadow_silver"
    assert result.schemas.gold == "seshat_dbt_shadow_gold"
    assert result.schemas.audit == "seshat_dbt_shadow_audit"
    assert len(result.model_contracts) == 1
    contract = result.model_contracts[0]
    assert contract.name == "stg_orders"
    assert contract.table_id == "orders"
    assert contract.source_map == "mappings/orders/source-map.yaml"
    assert contract.source_map_revision == MAP_REVISION
    assert contract.grain == "one row per order"
    assert contract.business_key == ("order_id",)
    assert contract.authority == "derived"
    assert len(contract.columns) == 1
    assert contract.columns[0].name == "order_id"
    assert contract.columns[0].source_columns == ("order_id",)
    assert contract.columns[0].derivation is None
    assert result.blocking_reasons == ()


def test_project_fingerprint_is_content_based_and_ignores_runtime_dirs(
    tmp_path: Path,
) -> None:
    from seshat.dbt.project import fingerprint_project

    _write_project(tmp_path)
    first = fingerprint_project(tmp_path)
    os.utime(tmp_path / "dbt/dbt_project.yml", None)
    (tmp_path / "dbt/target").mkdir()
    (tmp_path / "dbt/target/manifest.json").write_text("changed", encoding="utf-8")
    (tmp_path / "dbt/logs").mkdir()
    (tmp_path / "dbt/logs/dbt.log").write_text("changed", encoding="utf-8")

    assert fingerprint_project(tmp_path) == first

    model = tmp_path / "dbt/models/staging/orders/stg_orders.sql"
    model.write_text(model.read_text(encoding="utf-8") + "-- changed\n")
    assert fingerprint_project(tmp_path) != first


def test_profile_rejects_literal_connection_values(tmp_path: Path) -> None:
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path, ProjectFixture(profile_literal=True))

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_PROFILE_LITERAL_VALUE" in {b.code for b in result.blocking_reasons}


@pytest.mark.parametrize(
    "target_schema",
    ["silver", "gold", "public", "Unsafe-Name", "1shadow", "shadow;drop"],
)
def test_unsafe_target_schema_is_rejected(tmp_path: Path, target_schema: str) -> None:
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path, ProjectFixture(target_schema=target_schema))

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_SHADOW_SCHEMA_UNSAFE" in {b.code for b in result.blocking_reasons}


def test_missing_governed_selector_is_rejected(tmp_path: Path) -> None:
    from seshat.dbt.project import validate_project

    working_set = _write_project(
        tmp_path, ProjectFixture(selector_name="another_selector")
    )

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_SELECTOR_MISSING" in {b.code for b in result.blocking_reasons}


def test_stale_model_citation_is_rejected(tmp_path: Path) -> None:
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path, ProjectFixture(citation_revision="c" * 40))

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_MODEL_CITATION_STALE" in {b.code for b in result.blocking_reasons}


def _append_model(root: Path, subdir: str, model_yaml: str) -> None:
    """Add a second model's _models.yml under dbt/models/<subdir>/."""
    model_dir = root / "dbt" / "models" / subdir
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "_models.yml").write_text(model_yaml, encoding="utf-8")


def _tagged_model_yaml(name: str, tag: str, table_id: str) -> str:
    return "\n".join(
        [
            "version: 2",
            "models:",
            f"  - name: {name}",
            "    config:",
            f"      tags: [{tag}]",
            "    meta:",
            "      seshat:",
            f"        table_id: {table_id}",
            f"        source_map: mappings/{table_id}/source-map.yaml",
            f"        source_map_revision: {MAP_REVISION}",
            "        grain: one row per thing",
            "        business_key: [thing_id]",
            "        authority: derived",
            "    columns:",
            "      - name: thing_id",
            "        meta:",
            "          seshat:",
            "            source_columns: [thing_id]",
            "",
        ]
    )


def test_model_tagged_for_nonexistent_table_is_orphan_rejected(tmp_path: Path) -> None:
    """A model tagged seshat_table_<bogus> (no committed mapping) must block.

    This is the only guard against a mistyped/phantom selector tag once validation
    is partitioned per table: such a model matches no real governed table, so no
    table's validate run would otherwise ever check it. It must be an orphan
    blocker, not silently skipped as "some other table's model".
    """
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path)  # governed table = orders
    _append_model(
        tmp_path,
        "staging/bogus",
        _tagged_model_yaml("stg_bogus", "seshat_table_bogus", "bogus"),
    )

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_MODEL_ORPHANED" in {b.code for b in result.blocking_reasons}


def test_model_for_another_governed_table_is_out_of_scope(tmp_path: Path) -> None:
    """A model belonging to a DIFFERENT real governed table is skipped, not flagged.

    When validating table X, a model tagged for table Y -- where Y has its own
    committed mapping working set -- is out of scope (it is validated when Y runs).
    It must NOT raise a selector/citation/orphan blocker against X.
    """
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path)  # validating table = orders
    # A second real governed table "widgets" with its own mapping working set.
    widgets = tmp_path / "mappings/widgets"
    widgets.mkdir(parents=True, exist_ok=True)
    (widgets / "source-map.yaml").write_text(
        "meta:\n  table_id: widgets\n", encoding="utf-8"
    )
    (widgets / "readiness-status.yaml").write_text("stages: {}\n", encoding="utf-8")
    _append_model(
        tmp_path,
        "staging/widgets",
        _tagged_model_yaml("stg_widgets", "seshat_table_widgets", "widgets"),
    )

    result = validate_project(tmp_path, working_set)

    # orders is fully valid; the widgets model neither validated here nor flagged.
    assert result.valid is True, [b.code for b in result.blocking_reasons]


def test_missing_column_citation_is_rejected(tmp_path: Path) -> None:
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path, ProjectFixture(cite_column=False))

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_COLUMN_CITATION_MISSING" in {b.code for b in result.blocking_reasons}


def test_generic_project_files_cannot_contain_worked_table_answers(
    tmp_path: Path,
) -> None:
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path)
    macros = tmp_path / "dbt/macros"
    macros.mkdir()
    (macros / "generic.sql").write_text(
        "{% macro generic() %}retail_store_sales{% endmacro %}\n",
        encoding="utf-8",
    )

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_GENERIC_EXAMPLE_LEAK" in {b.code for b in result.blocking_reasons}
