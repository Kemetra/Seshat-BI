"""TDD tests for pipelines/load_bronze_csv.py hardening (2026-06-25 Codex PR review).

`pipelines/` is an operational script dir, NOT part of the installed package
(`packages = ["src/retail"]`), so the module is loaded by path via importlib. The
fact that this import SUCCEEDS without the optional `db` extra installed is itself
the regression guard for defect #3 (psycopg2 must be lazy-loaded, not imported at
module top) -- if psycopg2 import moved back to module scope, collection would fail
in a db-less env.

Findings covered:
  #3 lazy psycopg2 import (module imports cleanly without the db extra)
  #5 header dedup reserves GENERATED names (no collision with a later real header)
  #6 ragged rows (more fields than header) FAIL LOUD, not silently truncated
  #8 reconciliation counts CSV RECORDS (csv.reader), not physical file lines
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# Load the script module by path (it is not importable as a package).
_MODULE_PATH = Path(__file__).resolve().parents[2] / "pipelines" / "load_bronze_csv.py"
_spec = importlib.util.spec_from_file_location("load_bronze_csv", _MODULE_PATH)
assert _spec and _spec.loader
lbc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lbc)  # #3: must not raise even without the db extra


# --- #5 header collision -----------------------------------------------------


def test_norm_headers_basic_snake_case() -> None:
    assert lbc.norm_headers(["Transaction ID", "Total Spent"]) == [
        "transaction_id",
        "total_spent",
    ]


def test_norm_headers_duplicate_gets_suffix() -> None:
    assert lbc.norm_headers(["amt", "amt"]) == ["amt", "amt_2"]


def test_norm_headers_generated_name_does_not_collide_with_real_header() -> None:
    """#5: a generated `a_2` must not collide with a later real `a_2` header.

    `["A", "A", "A_2"]` normalizes a, a -> a_2 (generated), then the real A_2 -> a_2
    again unless the generated name is reserved. Result must be all-unique.
    """
    out = lbc.norm_headers(["A", "A", "A_2"])
    assert len(out) == len(set(out)), f"headers must be unique, got: {out}"


def test_norm_headers_triple_collision_stays_unique() -> None:
    out = lbc.norm_headers(["x", "x", "x", "x_2", "x_3"])
    assert len(out) == len(set(out)), f"headers must be unique, got: {out}"


def test_norm_headers_reserves_lineage_column_names() -> None:
    """#2: a source header normalizing to a lineage column must NOT collide with it.

    The loader appends `_source_file` / `_loaded_at` lineage columns. A source header
    that normalizes to either would create the same PostgreSQL identifier twice ->
    CREATE TABLE fails. norm_headers must rename the colliding SOURCE header.
    """
    out = lbc.norm_headers(["_source_file", "amount", "_loaded_at"])
    assert "_source_file" not in out, (
        "the source header must not claim the lineage name"
    )
    assert "_loaded_at" not in out, "the source header must not claim the lineage name"
    assert len(out) == 3 and len(set(out)) == 3, f"all unique, got: {out}"


def test_norm_headers_leading_digit_is_downstream_safe() -> None:
    """#4: a header normalizing to a leading-digit name must be a valid unquoted ident.

    `2023 sales` -> `2023_sales` loads quoted in bronze but `profile._safe_identifier`
    (and generated SQL) only accept ^[A-Za-z_]. norm_headers must emit a name that
    starts with a letter/underscore so the rest of the toolchain can use it unquoted.
    """
    import re

    out = lbc.norm_headers(["2023 sales", "Total Amount"])
    ident = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    for name in out:
        assert ident.match(name), f"{name!r} is not a valid unquoted identifier"
    assert len(set(out)) == 2


# --- #8 record count, not physical lines -------------------------------------


def test_count_csv_records_ignores_embedded_newlines(tmp_path: Path) -> None:
    """#8: a quoted field with an embedded newline is ONE record, not two lines."""
    p = tmp_path / "embedded.csv"
    p.write_text(
        "id,note\n"
        '1,"line one\nline two"\n'  # ONE logical record spanning two physical lines
        '2,"plain"\n',
        encoding="utf-8",
    )
    # data records = 2 (header excluded), though the file has 4 physical lines
    assert lbc.count_csv_records(str(p)) == 2


def test_count_csv_records_plain(tmp_path: Path) -> None:
    p = tmp_path / "plain.csv"
    p.write_text("a,b\n1,2\n3,4\n5,6\n", encoding="utf-8")
    assert lbc.count_csv_records(str(p)) == 3


# --- #6 ragged rows fail loud ------------------------------------------------


def test_ragged_row_more_fields_than_header_raises(tmp_path: Path) -> None:
    """#6: a row with MORE fields than the header must fail loud, not truncate."""
    p = tmp_path / "ragged.csv"
    p.write_text(
        "a,b\n"
        "1,2\n"
        "3,4,EXTRA\n",  # 3 fields under a 2-col header -> data corruption risk
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="(?i)ragged|field|width|column"):
        # building the buffer must reject the ragged row rather than slice it
        lbc.csv_buffer(str(p), ncols=2, source_file="ragged.csv")


def test_short_row_is_padded_not_rejected(tmp_path: Path) -> None:
    """A row with FEWER fields than the header is faithful-padded (dirty bronze)."""
    p = tmp_path / "short.csv"
    p.write_text("a,b,c\n1,2\n", encoding="utf-8")  # 2 fields under 3 cols -> pad
    buf, n = lbc.csv_buffer(str(p), ncols=3, source_file="short.csv")
    assert n == 1  # the short row is kept (padded), not dropped
