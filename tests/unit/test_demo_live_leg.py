"""US2: the live-leg logic, tested WITHOUT a real database (spec 083).

The real-DB apply (``load_demo_scoped``) opens a psycopg2 connection and is NOT
exercised in CI; its DDL logic is tested here via a fixture ``Writer`` (the same
discipline validate.py uses with a fixture QueryRunner). The demo-scoped safety
guard (FR-011) is a pure function, fully tested here.
"""

import pytest

from seshat.demo import DEMO_MARKER
from seshat.demo.live import apply_ddl, demo_scoped_ddl
from seshat.demo.load import target_is_demo_scoped

pytestmark = pytest.mark.unit


class _FixtureWriter:
    """A fixture Writer capturing executed SQL -- stands in for a psycopg2 cursor."""

    def __init__(self):
        self.statements = []

    def execute(self, sql: str) -> None:
        self.statements.append(sql)


def test_target_guard_allows_demo_scoped():
    """T022: a demo-scoped schema+table is allowed for a live write."""
    assert target_is_demo_scoped(f"gold{DEMO_MARKER}", f"fct_order_line{DEMO_MARKER}")
    assert target_is_demo_scoped("demo_gold", "demo_fct")


def test_target_guard_refuses_real_objects():
    """T022: a real (non-demo-scoped) schema/table is refused (FR-011)."""
    assert not target_is_demo_scoped("gold", "fct_sales")
    assert not target_is_demo_scoped("silver", "stg_order_line")
    # a demo-scoped table in a REAL schema is still refused (both must be scoped)
    assert not target_is_demo_scoped("gold", f"fct{DEMO_MARKER}")


def test_ddl_targets_only_the_demo_scoped_schema():
    """The generated DDL only ever names the demo-scoped schema."""
    schema = f"gold{DEMO_MARKER}"
    for stmt in demo_scoped_ddl(schema):
        assert schema in stmt
    # nothing touches a bare 'gold'/'silver' schema
    joined = " ".join(demo_scoped_ddl(schema))
    assert " gold." not in joined and " silver." not in joined


def test_apply_ddl_is_idempotent_shape():
    """T023: the DDL uses DROP+CREATE so a re-run converges (idempotent shape)."""
    writer = _FixtureWriter()
    apply_ddl(writer, f"gold{DEMO_MARKER}")
    joined = " ".join(writer.statements)
    assert "CREATE SCHEMA IF NOT EXISTS" in joined
    assert "DROP TABLE IF EXISTS" in joined
    assert "CREATE TABLE" in joined
