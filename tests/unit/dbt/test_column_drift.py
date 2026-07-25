"""The advisory column-shape comparison (issue #492).

The four parity assertions are value-only, so a shadow model whose column SET
diverges from its migrations counterpart passes every one of them. These tests pin
the advisory that makes that visible -- and pin that it stays ADVISORY: no
assertion class, no blocker code, no exit-code effect.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from seshat.dbt.column_drift import (
    ColumnShapeAdvisory,
    column_shape_advisories,
    migration_column_sets,
)

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class _Column:
    name: str


@dataclass(frozen=True)
class _Contract:
    name: str
    columns: tuple[_Column, ...]
    table_id: str = "t"


def _contract(name: str, *columns: str) -> _Contract:
    return _Contract(name=name, columns=tuple(_Column(c) for c in columns))


def _migration(root: Path, name: str, body: str) -> None:
    directory = root / "warehouse" / "migrations"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(body, encoding="utf-8")


_DATE_DDL = """
CREATE TABLE gold.dim_date_c086 (
  date_sk   INT PRIMARY KEY,
  full_date DATE,
  year      SMALLINT,
  month     SMALLINT,
  day       SMALLINT
);
"""


def test_divergent_column_set_raises_an_advisory(tmp_path: Path) -> None:
    """The exact live divergence from issue #492: the shadow date dimension carries
    `quarter` + `iso_week` that migrations does not, while the member count matches
    exactly (1096 = 1096) so `dimension_member_count` passes clean."""
    _migration(tmp_path, "0004_gold.sql", _DATE_DDL)

    advisories = column_shape_advisories(
        tmp_path,
        [
            _contract(
                "dim_date_c086",
                "date_sk",
                "full_date",
                "year",
                "quarter",
                "month",
                "day",
                "iso_week",
            )
        ],
    )

    assert len(advisories) == 1
    advisory = advisories[0]
    assert advisory.model == "dim_date_c086"
    assert advisory.shadow_only == ("iso_week", "quarter")
    assert advisory.migrations_only == ()
    assert "warehouse/migrations/0004_gold.sql" in advisory.message()
    assert "quarter" in advisory.message()


def test_identical_column_set_stays_silent(tmp_path: Path) -> None:
    """The same pair, aligned: no finding. An advisory that fired on a matching
    shape would be noise on every clean project."""
    _migration(tmp_path, "0004_gold.sql", _DATE_DDL)

    advisories = column_shape_advisories(
        tmp_path,
        [_contract("dim_date_c086", "date_sk", "full_date", "year", "month", "day")],
    )

    assert advisories == ()


def test_migrations_only_column_is_reported(tmp_path: Path) -> None:
    """Drift is symmetric: a column migrations builds and the shadow drops is just
    as invisible to the four value assertions."""
    _migration(tmp_path, "0004_gold.sql", _DATE_DDL)

    advisories = column_shape_advisories(
        tmp_path, [_contract("dim_date_c086", "date_sk", "full_date", "year")]
    )

    assert advisories[0].migrations_only == ("day", "month")
    assert advisories[0].shadow_only == ()
    assert "migrations-only" in advisories[0].message()


def test_renamed_column_is_reported_on_both_sides(tmp_path: Path) -> None:
    _migration(tmp_path, "0004_gold.sql", _DATE_DDL)

    advisories = column_shape_advisories(
        tmp_path,
        [_contract("dim_date_c086", "date_sk", "full_date", "year", "month", "dom")],
    )

    assert advisories[0].shadow_only == ("dom",)
    assert advisories[0].migrations_only == ("day",)


def test_model_without_a_migrations_counterpart_is_silent(tmp_path: Path) -> None:
    """A shadow-only star migrations never built is a normal state, not a defect."""
    _migration(tmp_path, "0004_gold.sql", _DATE_DDL)

    assert column_shape_advisories(tmp_path, [_contract("dim_brand_new", "a")]) == ()


def test_absent_migrations_directory_is_silent(tmp_path: Path) -> None:
    assert column_shape_advisories(tmp_path, [_contract("dim_x", "a")]) == ()
    assert migration_column_sets(tmp_path) == {}


def test_skip_suppresses_the_named_model(tmp_path: Path) -> None:
    """The parity audit model is derived evidence; migrations never build it."""
    _migration(
        tmp_path, "0004_gold.sql", "CREATE TABLE gold.audit_t_parity (\n  a INT\n);"
    )

    assert (
        column_shape_advisories(
            tmp_path,
            [_contract("audit_t_parity", "a", "b")],
            skip=frozenset({"audit_t_parity"}),
        )
        == ()
    )


def test_table_constraints_and_nested_commas_are_not_columns(tmp_path: Path) -> None:
    """`NUMERIC(12,2)` must not split into two columns, and a table-level
    PRIMARY KEY / FOREIGN KEY / UNIQUE clause is not a column."""
    _migration(
        tmp_path,
        "0004_gold.sql",
        """
CREATE TABLE gold.fct_x (
  fct_x_sk INT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  total_spent NUMERIC(12,2),
  qty NUMERIC(12,2),
  CONSTRAINT uq_x UNIQUE (fct_x_sk),
  PRIMARY KEY (fct_x_sk),
  FOREIGN KEY (fct_x_sk) REFERENCES gold.dim_y (y_sk)
);
""",
    )

    columns, _ = migration_column_sets(tmp_path)["fct_x"]
    assert columns == frozenset({"fct_x_sk", "total_spent", "qty"})
    assert (
        column_shape_advisories(
            tmp_path, [_contract("fct_x", "fct_x_sk", "total_spent", "qty")]
        )
        == ()
    )


def test_comments_are_stripped_before_parsing(tmp_path: Path) -> None:
    _migration(
        tmp_path,
        "0004_gold.sql",
        """
CREATE TABLE gold.dim_c (
  c_sk INT PRIMARY KEY,   -- surrogate, not a column named "surrogate"
  label TEXT              -- natural key
);
""",
    )

    columns, _ = migration_column_sets(tmp_path)["dim_c"]
    assert columns == frozenset({"c_sk", "label"})


def test_unparseable_definition_degrades_to_no_finding(tmp_path: Path) -> None:
    """Fail-SAFE: a body this narrow parser cannot classify yields no table entry,
    so it can never manufacture a bogus symmetric difference."""
    _migration(
        tmp_path,
        "0004_gold.sql",
        "CREATE TABLE gold.dim_weird (\n  (a + b) INT,\n  c TEXT\n);",
    )

    assert "dim_weird" not in migration_column_sets(tmp_path)
    assert column_shape_advisories(tmp_path, [_contract("dim_weird", "c")]) == ()


def test_case_insensitive_on_both_sides(tmp_path: Path) -> None:
    _migration(
        tmp_path, "0004_gold.sql", "create table GOLD.Dim_Case (\n  Date_SK int\n);"
    )

    assert column_shape_advisories(tmp_path, [_contract("dim_case", "DATE_SK")]) == ()


def test_last_definition_wins_when_a_table_is_recreated(tmp_path: Path) -> None:
    """A later migration reshaping a table is the shape the oracle ends up with."""
    _migration(tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_r (\n  a INT\n);")
    _migration(
        tmp_path, "0005_gold.sql", "CREATE TABLE gold.dim_r (\n  a INT,\n  b TEXT\n);"
    )

    columns, relpath = migration_column_sets(tmp_path)["dim_r"]
    assert columns == frozenset({"a", "b"})
    assert relpath == "warehouse/migrations/0005_gold.sql"


def test_advisory_carries_no_assertion_or_blocker_vocabulary() -> None:
    """The ruling: drift is a DISTINCT advisory finding, not a fifth parity
    assertion. Guard the shape so a later edit cannot quietly grow one."""
    fields = ColumnShapeAdvisory.__dataclass_fields__.keys()

    assert "assertion_class" not in fields
    assert "assertion_id" not in fields
    assert "passed" not in fields
    assert "code" not in fields
    assert "tolerance" not in fields


def test_advisory_message_never_uses_the_blocker_code_namespace(tmp_path: Path) -> None:
    """`DBT_[A-Z0-9_]+` is the blocking channel's namespace in the evidence schema."""
    import re

    _migration(tmp_path, "0004_gold.sql", _DATE_DDL)
    advisories = column_shape_advisories(
        tmp_path, [_contract("dim_date_c086", "date_sk")]
    )

    assert not re.search(r"DBT_[A-Z0-9_]+", advisories[0].message())


def test_committed_worked_example_is_no_finding() -> None:
    """The census requirement: the advisory must be silent on every committed
    worked-example model pair, or it would fire on a clean repo."""
    from seshat.dbt.gate import resolve_working_set
    from seshat.dbt.project import validate_project

    root = Path(__file__).resolve().parents[3]
    working_set = resolve_working_set(root, "retail_store_sales")
    project = validate_project(root, working_set, target_schema="seshat_dbt_shadow")

    advisories = column_shape_advisories(
        root,
        project.model_contracts,
        skip=frozenset({"audit_retail_store_sales_parity"}),
    )

    assert advisories == (), [a.message() for a in advisories]
