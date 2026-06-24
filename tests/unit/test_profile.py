"""TDD tests for the mechanical profiling helper (profile.py).

Driver-free, mirroring test_validate.py: a scripted FakeRunner returns canned
rows so the logic is exercised with no database and no psycopg2. profile.py
computes MECHANICAL numbers only -- counts, ''OR NULL missingness, distinct
cardinality, and the candidate-PK proof. Semantic findings (code<->label, fan-out,
returns column) are NOT here -- they are Principle-V judgment calls the agent
proposes and a human confirms.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


class FakeRunner:
    """A QueryRunner whose results are scripted per-call (FIFO)."""

    def __init__(self, results: list[list[tuple]]) -> None:
        self._results = list(results)
        self.calls: list[str] = []

    def run(self, sql: str, params: tuple = ()) -> list[tuple]:
        self.calls.append(sql)
        return self._results.pop(0) if self._results else []


def test_profile_discovers_columns_and_counts_rows() -> None:
    from retail.profile import profile

    runner = FakeRunner(
        [
            [("net_amt",), ("prod_cat",)],   # information_schema.columns -> 2 cols
            [(100,)],                         # row count
            [(0, 50)],                        # net_amt: 0 missing, 50 distinct
            [(8, 12)],                        # prod_cat: 8 missing, 12 distinct
            [(100, 100, 0)],                  # pk proof: total, distinct, null
        ]
    )
    result = profile(runner, "bronze.demo_orders", ("order_no", "line_no"))
    assert result.table == "bronze.demo_orders"
    assert result.row_count == 100
    assert result.column_count == 2
    assert tuple(c.name for c in result.columns) == ("net_amt", "prod_cat")


def test_missingness_uses_empty_or_null_not_is_null_alone() -> None:
    from retail.profile import profile

    # A faithful landing wrote '' for missing values. The missingness query must
    # COUNT those '' rows; IS NULL alone would (wrongly) report 0 missing.
    runner = FakeRunner(
        [
            [("city",)],          # one column
            [(200,)],             # 200 rows
            [(30, 5)],            # city: 30 ''OR NULL missing, 5 distinct
            [(200, 200, 0)],      # pk proof
        ]
    )
    result = profile(runner, "bronze.demo", ("id",))
    city = result.columns[0]
    assert city.missing_count == 30
    assert city.missing_pct == pytest.approx(15.0)
    # Prove the query text uses the ''OR NULL measure, not IS NULL alone.
    missingness_sql = runner.calls[2]
    assert "= ''" in missingness_sql and "IS NULL" in missingness_sql


def test_pk_proof_unique_when_distinct_equals_total_and_no_nulls() -> None:
    from retail.profile import profile

    runner = FakeRunner(
        [[("id",)], [(100,)], [(0, 100)], [(100, 100, 0)]]
    )
    pk = profile(runner, "bronze.demo", ("id",)).pk
    assert pk.is_unique is True


def test_pk_proof_not_unique_when_duplicates_or_nulls() -> None:
    from retail.profile import profile

    # 100 rows, 98 distinct -> 2 dupes -> not unique
    dupes = FakeRunner([[("id",)], [(100,)], [(0, 100)], [(100, 98, 0)]])
    assert profile(dupes, "bronze.demo", ("id",)).pk.is_unique is False

    # 100 rows, 100 distinct, but 3 NULL pk -> not unique
    nulls = FakeRunner([[("id",)], [(100,)], [(0, 100)], [(100, 100, 3)]])
    assert profile(nulls, "bronze.demo", ("id",)).pk.is_unique is False


def test_profile_rejects_unsafe_table_name() -> None:
    from retail.profile import profile

    runner = FakeRunner([])
    with pytest.raises(ValueError, match="unsafe SQL identifier"):
        profile(runner, "public.x; DROP TABLE users", ("id",))


def test_profile_imports_without_psycopg2() -> None:
    import importlib
    import sys

    # If psycopg2 were imported at module scope this would already have failed at
    # the test's `from retail.profile import profile`. Re-import to lock it in.
    # The guard relies on profile.py's module-scope import path being driver-free,
    # so importing it must not pull psycopg2 into sys.modules.
    mod = importlib.import_module("retail.profile")
    assert hasattr(mod, "profile")
    assert "psycopg2" not in sys.modules
