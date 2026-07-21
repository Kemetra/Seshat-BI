"""End-to-end proof: `dbt init` + scaffold produces a project that validates.

Materializes a fresh governed workspace (``governed_projects.dbt_init``),
commits an approved mapping working set, runs ``scaffold_models``, then runs the
REAL ``validate_project`` on the result. A scaffold that trips any static gate
blocker (contract/authority/citation/orphan/selector) fails here. Driver-free:
no dbt, no live database -- only git + the static validators.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
TABLE_ID = "retail_store_sales"
EXPECTED_MODELS = {
    "stg_retail_store_sales",
    "dim_customer_rss",
    "dim_product_rss",
    "dim_payment_method_rss",
    "dim_location_rss",
    "dim_date_rss",
    "fct_sales_rss",
    "audit_retail_store_sales_parity",
}


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def _seed_workspace(tmp_path: Path) -> Path:
    from seshat.governed_projects import dbt_init

    dbt_init(tmp_path)
    (tmp_path / "schemas").mkdir(exist_ok=True)
    shutil.copy2(
        ROOT / "schemas" / "dbt-run-evidence.schema.json",
        tmp_path / "schemas" / "dbt-run-evidence.schema.json",
    )
    mapping = tmp_path / "mappings" / TABLE_ID
    mapping.mkdir(parents=True)
    for name in ("source-map.yaml", "readiness-status.yaml", "unresolved-questions.md"):
        shutil.copy2(ROOT / "mappings" / TABLE_ID / name, mapping / name)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "seed approved mapping")
    return tmp_path


def test_scaffold_output_passes_static_validation(tmp_path: Path) -> None:
    from seshat.dbt.gate import resolve_working_set
    from seshat.dbt.project import validate_project
    from seshat.dbt.scaffold import scaffold_models

    root = _seed_workspace(tmp_path)
    report = scaffold_models(root, TABLE_ID)

    sql_names = {path.stem for path in (root / "dbt/models").rglob("*.sql")}
    assert EXPECTED_MODELS <= sql_names
    assert "dbt/selectors.yml" in report.merged
    assert "dbt/models/sources/_sources.yml" in report.merged

    working_set = resolve_working_set(root, TABLE_ID)
    result = validate_project(root, working_set, target_schema="seshat_dbt_shadow")

    assert result.valid, [b.code for b in result.blocking_reasons]
    assert {c.name for c in result.model_contracts} == EXPECTED_MODELS

    # The now-complete fact carries EVERY governed column (fix #1): the non-money
    # measure `quantity` and the degenerate dim `discount_applied`, not only the
    # additive money measure -- and validation still passes with 0 blockers.
    fact = next(c for c in result.model_contracts if c.name == "fct_sales_rss")
    fact_columns = {column.name for column in fact.columns}
    assert {"quantity", "total_spent", "discount_applied"} <= fact_columns


def test_scaffold_is_non_destructive_on_rerun(tmp_path: Path) -> None:
    from seshat.dbt.scaffold import scaffold_models

    root = _seed_workspace(tmp_path)
    scaffold_models(root, TABLE_ID)
    second = scaffold_models(root, TABLE_ID)

    assert second.written == ()  # every model file already exists -> all kept
    assert second.merged == ()  # selector + sources already present
    assert second.kept


_SECOND_TABLE = "widgets"
_SECOND_MAP = """\
meta:
  table_id: widgets
  grain: one row = one widget order line
gold_star:
  fact:
    name: gold.fct_widgets
    grain: one row = one widget order line
    business_key: order_line_id
    measures: [amount]
    additive_money_measures: [amount]
  dimensions:
    - name: gold.dim_widget
      surrogate_key: widget_sk
      attributes: [widget_id]
columns:
  - source_name: order_line_id
    decision: keep
    rename_to: order_line_id
    silver_type: text
  - source_name: widget_id
    decision: keep
    rename_to: widget_id
    silver_type: text
  - source_name: amount
    decision: keep
    rename_to: amount
    silver_type: "numeric(12,2)"
"""
_SECOND_READINESS = """\
stages:
  mapping_ready:
    status: pass
approvals:
  - stage: mapping_ready
    owner: Owner (data_owner)
    at: '2026-07-16'
    note: approved
"""


def _seed_second_table(root: Path) -> None:
    mapping = root / "mappings" / _SECOND_TABLE
    mapping.mkdir(parents=True)
    (mapping / "source-map.yaml").write_text(_SECOND_MAP, encoding="utf-8")
    (mapping / "readiness-status.yaml").write_text(_SECOND_READINESS, encoding="utf-8")
    (mapping / "unresolved-questions.md").write_text(
        "Gate status: CLEARED\n", encoding="utf-8"
    )
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed second approved mapping")


def test_second_table_scaffold_extends_shared_sources_and_validates(
    tmp_path: Path,
) -> None:
    """A second onboarded table must UNION its tables into the shared
    _sources.yml groups (not be skipped because the group exists), or its
    staging/audit SQL would reference undeclared sources."""
    import yaml

    from seshat.dbt.gate import resolve_working_set
    from seshat.dbt.project import validate_project
    from seshat.dbt.scaffold import scaffold_models

    root = _seed_workspace(tmp_path)
    scaffold_models(root, TABLE_ID)
    _seed_second_table(root)
    scaffold_models(root, _SECOND_TABLE)

    sources = yaml.safe_load(
        (root / "dbt/models/sources/_sources.yml").read_text(encoding="utf-8")
    )["sources"]
    by_name = {s["name"]: {t["name"] for t in s["tables"]} for s in sources}
    assert {TABLE_ID, _SECOND_TABLE} <= by_name["bronze"]
    assert {"fct_sales_rss", "fct_widgets", "dim_widget"} <= by_name["migration_gold"]

    for table in (TABLE_ID, _SECOND_TABLE):
        working_set = resolve_working_set(root, table)
        result = validate_project(root, working_set, target_schema="seshat_dbt_shadow")
        assert result.valid, (table, [b.code for b in result.blocking_reasons])
