"""Shared builders for the column-drift advisory tests (issue #492).

Split out so the advisory-semantics tests and the migration-DDL-reading tests can
live in separate modules without duplicating these three helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# The gold shapes the committed migrations define, asserted BY COUNT so a parser
# regression that silently empties the comparison cannot hide behind "0 advisories"
# (#501 review, finding B: every DROP in 0004 precedes every CREATE).
#
# Spec 137 (finance GL genericity proof) added 0008_create_gold_finance_gl_star.sql,
# a second idempotent gold migration with the same every-DROP-before-every-CREATE
# shape as 0004 (its own census guard: 0008's DROPs at lines ~59-65 precede all its
# CREATEs). The seven `_fgl` entries below are that migration's tables.
REAL_MIGRATION_SHAPES = {
    "dim_customer_rss": 2,
    "dim_date_rss": 10,
    "dim_location_rss": 2,
    "dim_payment_method_rss": 2,
    "dim_product_rss": 3,
    "fct_sales_rss": 11,
    "dim_account_fgl": 5,
    "dim_cost_center_fgl": 4,
    "dim_date_fgl": 10,
    "dim_department_fgl": 3,
    "dim_fiscal_period_fgl": 5,
    "fct_gl_actuals_fgl": 12,
    "fct_gl_budget_fgl": 7,
}

DATE_DDL = """
CREATE TABLE gold.dim_date_c086 (
  date_sk   INT PRIMARY KEY,
  full_date DATE,
  year      SMALLINT,
  month     SMALLINT,
  day       SMALLINT
);
"""


@dataclass(frozen=True)
class Column:
    name: str


@dataclass(frozen=True)
class Contract:
    name: str
    columns: tuple[Column, ...]
    table_id: str = "t"


def contract(name: str, *columns: str) -> Contract:
    """A stand-in for one ``ModelContract`` with the named declared columns."""
    return Contract(name=name, columns=tuple(Column(c) for c in columns))


def migration(root: Path, name: str, body: str) -> None:
    """Write one committed-looking migration under ``warehouse/migrations``."""
    directory = root / "warehouse" / "migrations"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(body, encoding="utf-8")


def repo_root() -> Path:
    """The real repository root, for the census tests that read committed files."""
    return Path(__file__).resolve().parents[3]
