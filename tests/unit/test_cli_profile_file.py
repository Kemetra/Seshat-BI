"""CLI-level tests for the FILE surface of `seshat profile` (--file).

The mechanical file profiler is exercised in ``test_file_profile.py``; these
tests cover the CLI seam only -- flag parsing, reader selection by extension,
the markdown/JSON render, and the fail-closed messages.

Unlike the DB surface (``test_cli_profile.py``), nothing is monkeypatched: a
file source needs no driver and no connection, so these tests drive the real
reader over a real temp file. That is the point of the surface -- CSV profiling
runs on the stdlib alone.
"""

from __future__ import annotations

import json

import pytest

from seshat.cli import main as main_under_test

pytestmark = pytest.mark.unit


def _write_csv(tmp_path, name: str = "orders.csv") -> str:
    """A 3-row CSV with one blank cell, so ''-missingness is observable."""
    path = tmp_path / name
    path.write_text(
        "order_id,amount,note\n1,10,ok\n2,20,\n3,30,ok\n",
        encoding="utf-8",
    )
    return str(path)


def test_profile_file_csv_markdown_render(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--file profiles a CSV and emits the same source-profile.md blocks."""
    csv_path = _write_csv(tmp_path)

    rc = main_under_test(["profile", "--file", csv_path, "--pk", "order_id"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "## Shape" in out
    assert "## Per-column profile" in out
    assert "candidate PK holds" in out


def test_profile_file_blank_cell_counts_as_missing(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """RC5: a blank cell is missing (`'' OR NULL`), so `note` is 1 of 3.

    The load-bearing invariant of the whole profiler. If the CLI seam ever
    coerced blanks to a null sentinel, the '' half of the measure would vanish
    and missingness would be UNDER-reported -- the exact trap the module
    docstring names.
    """
    csv_path = _write_csv(tmp_path)

    rc = main_under_test(["profile", "--file", csv_path, "--pk", "order_id"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "| `note` | TEXT | 1 / 33.33% | 2 |" in out


def test_profile_file_tsv_is_tab_delimited(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A .tsv is split on tabs -- two columns, not one comma-joined column."""
    path = tmp_path / "orders.tsv"
    path.write_text("order_id\tamount\n1\t10\n2\t20\n", encoding="utf-8")

    rc = main_under_test(
        ["profile", "--file", str(path), "--pk", "order_id", "--format", "json"]
    )

    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["column_count"] == 2
    assert [c["name"] for c in payload["columns"]] == ["order_id", "amount"]


def test_profile_file_json_reports_landed_type_null(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file's cells are raw strings, so `landed_type` is null, never invented."""
    csv_path = _write_csv(tmp_path)

    rc = main_under_test(
        ["profile", "--file", csv_path, "--pk", "order_id", "--format", "json"]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert all(col["landed_type"] is None for col in payload["columns"])


def test_profile_file_missing_path_exits_1(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A nonexistent --file fails closed with a message, not a traceback."""
    rc = main_under_test(
        ["profile", "--file", str(tmp_path / "nope.csv"), "--pk", "order_id"]
    )

    err = capsys.readouterr().err
    assert rc == 1
    assert "not a readable file" in err


def test_profile_file_unsupported_extension_exits_1(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unsupported extension names the supported ones instead of guessing."""
    path = tmp_path / "orders.parquet"
    path.write_bytes(b"PAR1")

    rc = main_under_test(["profile", "--file", str(path), "--pk", "order_id"])

    err = capsys.readouterr().err
    assert rc == 1
    assert "unsupported --file extension" in err
    assert ".csv" in err and ".tsv" in err


def test_profile_file_pk_absent_from_header_exits_1(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A --pk naming no real column fails closed, never a silent empty proof."""
    csv_path = _write_csv(tmp_path)

    rc = main_under_test(["profile", "--file", csv_path, "--pk", "not_a_column"])

    err = capsys.readouterr().err
    assert rc == 1
    assert "could not profile" in err


def test_profile_file_empty_pk_exits_1(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--pk that parses to nothing is rejected before the file is opened."""
    csv_path = _write_csv(tmp_path)

    rc = main_under_test(["profile", "--file", csv_path, "--pk", " , "])

    err = capsys.readouterr().err
    assert rc == 1
    assert "--pk must name at least one column" in err


def test_profile_table_and_file_are_mutually_exclusive(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--table and --file resolve through different seams; one run, one source.

    ``main`` RETURNS the usage code (2) rather than propagating SystemExit, so
    assert on the return value -- the same contract ``test_cli_profile.py`` uses.
    """
    rc = main_under_test(
        ["profile", "--table", "bronze.t", "--file", "x.csv", "--pk", "a"]
    )

    assert rc == 2
    assert "not allowed with argument" in capsys.readouterr().err


def test_profile_requires_one_source(capsys: pytest.CaptureFixture[str]) -> None:
    """Neither --table nor --file is a usage error, not a silent no-op."""
    rc = main_under_test(["profile", "--pk", "a"])

    assert rc == 2
    assert "one of the arguments --table --file is required" in capsys.readouterr().err


def _write_xlsx(tmp_path, name: str = "orders.xlsx", sheet: str = "Orders") -> str:
    """A 3-row single-sheet workbook with one blank cell (mirrors the CSV fixture)."""
    openpyxl = pytest.importorskip("openpyxl")  # the optional `files` extra

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = sheet
    worksheet.append(["order_id", "amount", "note"])
    worksheet.append(["1", "10", "ok"])
    worksheet.append(["2", "20", None])
    worksheet.append(["3", "30", "ok"])
    path = tmp_path / name
    workbook.save(str(path))
    return str(path)


def test_profile_file_xlsx_with_sheet_renders(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An .xlsx profiles through the named sheet; a blank cell stays missing."""
    xlsx_path = _write_xlsx(tmp_path)

    rc = main_under_test(
        ["profile", "--file", xlsx_path, "--pk", "order_id", "--sheet", "Orders"]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "## Shape" in out
    assert "| `note` | TEXT | 1 / 33.33% | 2 |" in out


def test_profile_file_xlsx_without_sheet_exits_1(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Excel needs an EXPLICIT --sheet; sheet 0 is never assumed (PY-CN-085).

    Guessing the first sheet would silently profile whichever tab happens to be
    first, so the surface refuses instead of choosing for the analyst.
    """
    xlsx_path = _write_xlsx(tmp_path)

    rc = main_under_test(["profile", "--file", xlsx_path, "--pk", "order_id"])

    err = capsys.readouterr().err
    assert rc == 1
    assert "--sheet" in err


def test_profile_file_sheet_rejected_for_csv(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--sheet on a CSV is a mistake worth naming, not silently ignoring."""
    csv_path = _write_csv(tmp_path)

    rc = main_under_test(
        ["profile", "--file", csv_path, "--pk", "order_id", "--sheet", "Orders"]
    )

    err = capsys.readouterr().err
    assert rc == 1
    assert "--sheet" in err


def test_profile_sheet_rejected_for_table(capsys: pytest.CaptureFixture[str]) -> None:
    """--sheet is file-only; on --table it is refused BEFORE any DB resolution.

    Rejecting early is what keeps this test hermetic -- it must not reach driver
    or DSN resolution, so no database is touched.
    """
    rc = main_under_test(
        ["profile", "--table", "bronze.t", "--pk", "a", "--sheet", "Orders"]
    )

    err = capsys.readouterr().err
    assert rc == 1
    assert "--sheet" in err
