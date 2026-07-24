"""``seshat.reset.plan_reset`` -- the pure planner (#433).

The planner enumerates the EXACT derived file-set for one table (no writes):
mappings/<table>/ (incl. dbt-evidence/), the exact-token silver/gold DDL
migrations, generated warehouse/gold + warehouse/schema outputs, the three
nested dbt model folders, the table's rows in the SHARED dbt files, and the
table-scoped dagster run evidence. It must never plan the bronze landing or
any other table's files -- the prefix-collision guard (``orders`` vs
``orders_archive``) is load-bearing.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from seshat.reset import ResetError, plan_reset
from tests.unit._reset_fixtures import (
    add_dagster_run,
    build_workspace,
)

pytestmark = pytest.mark.unit


def _all_planned(plan) -> set[str]:
    return set(plan.remove_dirs) | set(plan.remove_files)


# ---------------------------------------------------------------------------
# The exact derived set
# ---------------------------------------------------------------------------


def test_plan_enumerates_the_exact_derived_set(tmp_path: Path) -> None:
    build_workspace(tmp_path, ("orders",))
    add_dagster_run(tmp_path, "20260101T000000Z-aaaaaaaa", ("orders",))
    (tmp_path / "warehouse" / "gold").mkdir()
    (tmp_path / "warehouse" / "gold" / "gold_orders_star.sql").write_text(
        "SELECT 1;\n", encoding="utf-8"
    )
    (tmp_path / "warehouse" / "schema").mkdir()
    (tmp_path / "warehouse" / "schema" / "orders_schema.md").write_text(
        "# schema\n", encoding="utf-8"
    )

    plan = plan_reset(tmp_path, "orders")

    assert set(plan.remove_dirs) == {
        "mappings/orders",
        "dbt/models/staging/orders",
        "dbt/models/marts/orders",
        "dbt/models/audit/orders",
        ".seshat/dagster/runs/20260101T000000Z-aaaaaaaa",
    }
    assert set(plan.remove_files) == {
        "warehouse/migrations/0003_create_silver_orders.sql",
        "warehouse/migrations/0004_create_gold_orders_star.sql",
        "warehouse/gold/gold_orders_star.sql",
        "warehouse/schema/orders_schema.md",
    }
    edited = {edit.path for edit in plan.shared_edits}
    assert edited == {"dbt/selectors.yml", "dbt/models/sources/_sources.yml"}


def test_plan_excludes_bronze_landing_and_reports_it_preserved(
    tmp_path: Path,
) -> None:
    build_workspace(tmp_path, ("orders",))
    plan = plan_reset(tmp_path, "orders")
    assert "data/raw/orders.csv" not in _all_planned(plan)
    assert "data/raw/orders.csv" in plan.preserved


def test_plan_is_empty_when_nothing_is_onboarded(tmp_path: Path) -> None:
    plan = plan_reset(tmp_path, "orders")
    assert plan.is_empty
    assert plan.remove_dirs == ()
    assert plan.remove_files == ()
    assert plan.shared_edits == ()


# ---------------------------------------------------------------------------
# Prefix-collision guard (the load-bearing test from the brief)
# ---------------------------------------------------------------------------


def test_plan_for_orders_never_touches_orders_archive(tmp_path: Path) -> None:
    build_workspace(tmp_path, ("orders", "orders_archive"))
    plan = plan_reset(tmp_path, "orders")
    planned = _all_planned(plan)
    assert planned, "expected a non-empty plan for the onboarded table"
    assert not [path for path in planned if "orders_archive" in path]
    # The exact-token migrations for orders ARE included.
    assert "warehouse/migrations/0003_create_silver_orders.sql" in planned
    assert "warehouse/migrations/0004_create_gold_orders_star.sql" in planned
    # Shared-file edits never remove an orders_archive row.
    for edit in plan.shared_edits:
        assert "seshat_table_orders_archive" not in str(edit.removed_rows)
        assert not [row for row in edit.removed_rows if "orders_archive" in row]


def test_plan_for_orders_archive_never_touches_orders(tmp_path: Path) -> None:
    build_workspace(tmp_path, ("orders", "orders_archive"))
    plan = plan_reset(tmp_path, "orders_archive")
    planned = _all_planned(plan)
    assert "warehouse/migrations/0005_create_silver_orders_archive.sql" in planned
    assert "warehouse/migrations/0003_create_silver_orders.sql" not in planned
    assert "mappings/orders" not in plan.remove_dirs
    assert "mappings/orders_archive" in plan.remove_dirs


def test_generated_outputs_respect_the_token_guard(tmp_path: Path) -> None:
    build_workspace(tmp_path, ("orders", "orders_archive"))
    schema = tmp_path / "warehouse" / "schema"
    schema.mkdir()
    (schema / "orders_schema.md").write_text("# a\n", encoding="utf-8")
    (schema / "orders_archive_schema.md").write_text("# b\n", encoding="utf-8")
    plan = plan_reset(tmp_path, "orders")
    planned = _all_planned(plan)
    assert "warehouse/schema/orders_schema.md" in planned
    assert "warehouse/schema/orders_archive_schema.md" not in planned


# ---------------------------------------------------------------------------
# Shared dbt files -- surgical row removal, other tables byte-identical
# ---------------------------------------------------------------------------


def test_shared_edits_remove_only_this_tables_rows(tmp_path: Path) -> None:
    build_workspace(tmp_path, ("orders", "orders_archive"))
    plan = plan_reset(tmp_path, "orders")
    edits = {edit.path: edit for edit in plan.shared_edits}

    selectors = edits["dbt/selectors.yml"]
    assert "seshat_table_orders\n" not in selectors.new_text
    assert "seshat_table_orders_archive" in selectors.new_text
    # Other tables' rows survive byte-for-byte: the new text is exactly the
    # original minus the removed block.
    from tests.unit._reset_fixtures import selectors_text

    assert selectors.new_text == selectors_text("orders_archive")

    sources = edits["dbt/models/sources/_sources.yml"]
    assert "- name: fct_orders\n" not in sources.new_text
    assert "  - name: orders\n" not in sources.new_text
    assert "- name: fct_orders_archive" in sources.new_text
    assert "- name: orders_archive" in sources.new_text
    assert not sources.remove_file


def test_sources_file_is_removed_when_it_empties(tmp_path: Path) -> None:
    build_workspace(tmp_path, ("orders",))
    plan = plan_reset(tmp_path, "orders")
    edits = {edit.path: edit for edit in plan.shared_edits}
    assert edits["dbt/models/sources/_sources.yml"].remove_file
    # selectors.yml keeps an explicit empty list rather than a dangling key.
    assert edits["dbt/selectors.yml"].new_text == "selectors: []\n"


def test_malformed_shared_file_is_a_documented_refusal(tmp_path: Path) -> None:
    build_workspace(tmp_path, ("orders",))
    (tmp_path / "dbt" / "selectors.yml").write_text(
        "selectors: [unclosed\n", encoding="utf-8"
    )
    with pytest.raises(ResetError) as excinfo:
        plan_reset(tmp_path, "orders")
    assert excinfo.value.reason == "shared_file_unreadable"


# ---------------------------------------------------------------------------
# Dagster run evidence (Q2: only the table's runs; never the project)
# ---------------------------------------------------------------------------


def test_multi_table_dagster_run_is_preserved(tmp_path: Path) -> None:
    build_workspace(tmp_path, ("orders", "orders_archive"))
    add_dagster_run(tmp_path, "20260101T000000Z-aaaaaaaa", ("orders",))
    add_dagster_run(tmp_path, "20260102T000000Z-bbbbbbbb", ("orders", "orders_archive"))
    plan = plan_reset(tmp_path, "orders")
    assert ".seshat/dagster/runs/20260101T000000Z-aaaaaaaa" in plan.remove_dirs
    assert ".seshat/dagster/runs/20260102T000000Z-bbbbbbbb" not in plan.remove_dirs


def test_materialized_dagster_project_is_never_planned(tmp_path: Path) -> None:
    build_workspace(tmp_path, ("orders",))
    project = tmp_path / "orchestration" / "dagster"
    project.mkdir(parents=True)
    (project / "definitions.py").write_text("# defs\n", encoding="utf-8")
    plan = plan_reset(tmp_path, "orders")
    assert not [
        path for path in _all_planned(plan) if path.startswith("orchestration/")
    ]


# ---------------------------------------------------------------------------
# Table-name safety: documented refusal BEFORE any filesystem access
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_table",
    [
        "../../etc",
        "foo/bar",
        "foo\\bar",
        "..",
        "",
        "con",
        "orders ",
        "orders.",
        "ord\x07ers",
        "or:ders",
    ],
)
def test_unsafe_table_names_are_refused_before_fs_access(
    tmp_path: Path, bad_table: str
) -> None:
    # A root that does NOT exist proves no filesystem access precedes the
    # refusal -- any touch of the tree would raise something else.
    missing_root = tmp_path / "never-created"
    with pytest.raises(ResetError) as excinfo:
        plan_reset(missing_root, bad_table)
    assert excinfo.value.reason == "unsafe_table"


def test_symlinked_mapping_dir_is_refused(tmp_path: Path) -> None:
    build_workspace(tmp_path, ("orders",))
    outside = tmp_path.parent / "outside-victim"
    outside.mkdir(exist_ok=True)
    target = tmp_path / "mappings" / "linked"
    try:
        os.symlink(outside, target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this environment")
    (tmp_path / "mappings" / "orders").rename(tmp_path / "mappings" / "keep")
    target.rename(tmp_path / "mappings" / "orders")
    with pytest.raises(ResetError) as excinfo:
        plan_reset(tmp_path, "orders")
    assert excinfo.value.reason == "path_escape"
