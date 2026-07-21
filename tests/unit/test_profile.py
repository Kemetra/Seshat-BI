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
    from seshat.profile import profile

    runner = FakeRunner(
        [
            # information_schema.columns -> (name, data_type) per col
            [("net_amt", "text"), ("prod_cat", "text")],
            [(100,)],  # row count
            [(0, 50)],  # net_amt: 0 missing, 50 distinct
            [(8, 12)],  # prod_cat: 8 missing, 12 distinct
            [(100, 100, 0)],  # pk proof: total, distinct, null
        ]
    )
    result = profile(runner, "bronze.demo_orders", ("order_no", "line_no"))
    assert result.table == "bronze.demo_orders"
    assert result.row_count == 100
    assert result.column_count == 2
    assert tuple(c.name for c in result.columns) == ("net_amt", "prod_cat")


def test_non_text_column_uses_is_null_not_trim() -> None:
    """A non-text column (e.g. a TIMESTAMPTZ lineage column) must be profiled with
    IS NULL, NOT trim()/''.

    Regression guard (2026-06-25 defect): profile() ran trim() on EVERY discovered
    column; against a bronze table carrying a `_loaded_at TIMESTAMPTZ` lineage column
    this errored `function btrim(timestamp with time zone) does not exist`. trim() is
    text-only; a faithful all-TEXT bronze does not write '' into a timestamptz, so the
    correct missingness for a non-text column is plain IS NULL.
    """
    from seshat.profile import profile

    runner = FakeRunner(
        [
            # a text col + a timestamptz lineage col
            [("sku", "text"), ("_loaded_at", "timestamp with time zone")],
            [(100,)],  # rows
            [(4, 20)],  # sku: ''OR NULL missingness (text path)
            [(0, 100)],  # _loaded_at: IS NULL missingness (non-text path)
            [(100, 100, 0)],  # pk proof
        ]
    )
    result = profile(runner, "bronze.demo", ("sku",))
    # text column still uses the ''OR NULL measure
    assert "= ''" in runner.calls[2] and "trim" in runner.calls[2]
    # non-text column uses IS NULL and does NOT call trim() (which would crash live)
    nontext_sql = runner.calls[3]
    assert "IS NULL" in nontext_sql
    assert "trim" not in nontext_sql and "= ''" not in nontext_sql
    assert result.columns[1].name == "_loaded_at"
    assert result.columns[1].missing_count == 0


def test_missingness_uses_empty_or_null_not_is_null_alone() -> None:
    from seshat.profile import profile

    # A faithful landing wrote '' for missing values. The missingness query must
    # COUNT those '' rows; IS NULL alone would (wrongly) report 0 missing.
    runner = FakeRunner(
        [
            [("city", "text")],  # one column
            [(200,)],  # 200 rows
            [(30, 5)],  # city: 30 ''OR NULL missing, 5 distinct
            [(200, 200, 0)],  # pk proof
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
    from seshat.profile import profile

    runner = FakeRunner([[("id", "text")], [(100,)], [(0, 100)], [(100, 100, 0)]])
    pk = profile(runner, "bronze.demo", ("id",)).pk
    assert pk.is_unique is True


def test_pk_proof_not_unique_when_duplicates_or_nulls() -> None:
    from seshat.profile import profile

    # 100 rows, 98 distinct -> 2 dupes -> not unique
    dupes = FakeRunner([[("id", "text")], [(100,)], [(0, 100)], [(100, 98, 0)]])
    assert profile(dupes, "bronze.demo", ("id",)).pk.is_unique is False

    # 100 rows, 100 distinct, but 3 NULL pk -> not unique
    nulls = FakeRunner([[("id", "text")], [(100,)], [(0, 100)], [(100, 100, 3)]])
    assert profile(nulls, "bronze.demo", ("id",)).pk.is_unique is False


def test_pk_proof_uses_the_selected_dialects_tuple_distinct_form() -> None:
    """The PK count must route through ``dialect.distinct_tuple_count``, not a
    hardcoded Postgres ``count(DISTINCT (...))``. Postgres keeps that native
    form; a non-Postgres dialect (here SQL Server) needs a DISTINCT subquery, so
    the hardcoded form reached the real runner as invalid SQL (PR #409)."""
    from seshat.dialect import get_dialect
    from seshat.profile import profile

    sqlserver = get_dialect("sqlserver")
    runner = FakeRunner([[("id", "text")], [(100,)], [(0, 100)], [(100, 100, 0)]])
    profile(runner, "bronze.demo", ("id", "line_no"), dialect=sqlserver)
    pk_sql = runner.calls[-1]
    # SQL Server form: a DISTINCT subquery, NOT the Postgres row-value tuple.
    assert "SELECT DISTINCT" in pk_sql
    assert "count(DISTINCT (id, line_no))" not in pk_sql


def test_pk_null_proof_counts_empty_text_keys_not_just_null() -> None:
    """For a TEXT candidate key the null/empty proof must use the ''OR NULL
    measure (RC5), not IS NULL alone -- a faithful bronze landing writes '' for a
    missing key, so IS NULL alone would pass a blank-key grain as unique and make
    the emitted `NULLs/empty in PK` label dishonest (PR #409)."""
    from seshat.profile import profile

    runner = FakeRunner([[("code", "text")], [(100,)], [(0, 100)], [(100, 100, 0)]])
    profile(runner, "bronze.demo", ("code",))
    pk_sql = runner.calls[-1]
    assert "trim(code)" in pk_sql and "= ''" in pk_sql

    # A non-text key stays on plain IS NULL (trim() is text-only, would crash).
    runner2 = FakeRunner([[("id", "integer")], [(100,)], [(0, 100)], [(100, 100, 0)]])
    profile(runner2, "bronze.demo", ("id",))
    pk_sql2 = runner2.calls[-1]
    assert "id IS NULL" in pk_sql2 and "trim(" not in pk_sql2


def test_pk_is_not_unique_on_an_empty_table() -> None:
    """An empty source proves NOTHING: `(0, 0, 0)` must NOT pass a candidate PK.
    Without the `total > 0` guard, `0 == 0 and 0 == 0` wrongly returns unique --
    and disagrees with the file profiler, which already guards `row_count > 0`
    (`file_profile.py`). Both profilers must give the same empty-table verdict so
    a DB and a file source cannot record opposite PK results at the gate (#409)."""
    from seshat.profile import profile

    empty = FakeRunner([[("id", "text")], [(0,)], [(0, 0)], [(0, 0, 0)]])
    result = profile(empty, "bronze.demo", ("id",))
    assert result.row_count == 0
    assert result.pk.is_unique is False


def test_snowflake_lowercase_pk_matches_uppercased_catalog_type() -> None:
    """Snowflake's INFORMATION_SCHEMA reports an unquoted `id` as `ID`. A user's
    `--pk id` must still resolve to its real (numeric) type via the dialect's
    catalog normalization -- a case-sensitive lookup would miss it, default to
    `text`, and emit `trim(id) = ''` against a NUMBER column (a DB-boundary crash
    instead of a profile, #409)."""
    from seshat.dialect import get_dialect
    from seshat.profile import profile

    snowflake = get_dialect("snowflake")
    # Catalog returns UPPER names (as Snowflake does); the numeric PK is NUMBER.
    runner = FakeRunner([[("ID", "NUMBER")], [(100,)], [(0, 100)], [(100, 100, 0)]])
    profile(runner, "bronze.demo", ("id",), dialect=snowflake)
    pk_sql = runner.calls[-1]
    # Non-text key -> plain IS NULL, NEVER trim() (which errors on a NUMBER column).
    assert "id IS NULL" in pk_sql
    assert "trim(id)" not in pk_sql


def test_profile_rejects_unsafe_table_name() -> None:
    from seshat.profile import profile

    runner = FakeRunner([])
    with pytest.raises(ValueError, match="unsafe SQL identifier"):
        profile(runner, "public.x; DROP TABLE users", ("id",))


def test_profile_imports_without_psycopg2() -> None:
    import importlib
    import sys

    # If psycopg2 were imported at module scope this would already have failed at
    # the test's `from seshat.profile import profile`. Re-import to lock it in.
    # The guard relies on profile.py's module-scope import path being driver-free,
    # so importing it must not pull psycopg2 into sys.modules.
    mod = importlib.import_module("seshat.profile")
    assert hasattr(mod, "profile")
    assert "psycopg2" not in sys.modules


# --- audit fix (2026-06-26): _safe_identifier must use fullmatch ------------


def test_safe_identifier_rejects_embedded_newline() -> None:
    """A newline-terminated name must be rejected (was a `.match` bypass).

    `.match` anchors only at the start; with `$` not in MULTILINE it still allowed
    a trailing `\n...`. `.fullmatch` closes it. Defensive: profile.py interpolates
    identifiers into SQL text.
    """
    import pytest

    from seshat.profile import _safe_identifier

    with pytest.raises(ValueError):
        _safe_identifier("valid_id\nDROP TABLE x")


def test_safe_identifier_accepts_plain_dotted() -> None:
    from seshat.profile import _safe_identifier

    assert _safe_identifier("gold.fct_sales") == "gold.fct_sales"
