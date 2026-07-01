"""TDD tests for the mechanical FILE profiler (file_profile.py).

Driver-free, mirroring test_profile.py: a canned ``_MaterializedReader`` returns
in-memory (header, rows) so the profiling math is exercised with NO file and NO
optional file library. file_profile.py computes MECHANICAL numbers only -- counts,
''OR NULL missingness (RC5), distinct cardinality, and the candidate-PK proof.
Semantic findings are NOT here -- Principle-V judgment calls the agent proposes and a
human confirms. The stdlib CSV reader is exercised over a real tmp file (no extra);
the Excel reader (lazy openpyxl) is not unit-tested here to keep CI extra-free.
"""

from __future__ import annotations

import pytest

from retail.file_profile import (
    _MaterializedReader,
    make_csv_reader,
    profile_file,
)

pytestmark = pytest.mark.unit


def _reader(header, rows):
    return _MaterializedReader(tuple(header), tuple(tuple(r) for r in rows))


def test_profile_counts_rows_columns_and_names() -> None:
    reader = _reader(
        ["order_no", "line_no", "amount"],
        [("A1", "1", "10.00"), ("A1", "2", "20.00"), ("A2", "1", "5.00")],
    )
    result = profile_file(reader, "orders.csv", ("order_no", "line_no"))
    assert result.source == "orders.csv"
    assert result.row_count == 3
    assert result.column_count == 3
    assert tuple(c.name for c in result.columns) == ("order_no", "line_no", "amount")


def test_missingness_is_blank_or_null_not_none_alone() -> None:
    """RC5: a blank cell '' counts as missing, exactly like a DB '' landing. A reader
    that yields '' for blanks must be measured with strip()=='' -- an is-None check
    alone would report 0 missing and hide the gap (the file form of the IS NULL trap).
    """
    reader = _reader(
        ["code", "note"],
        [
            ("X", "hello"),
            ("Y", ""),  # blank -> missing
            ("Z", "   "),  # whitespace-only -> missing (trim)
            ("W", "world"),
        ],
    )
    result = profile_file(reader, "f.csv", ("code",))
    note = next(c for c in result.columns if c.name == "note")
    assert note.missing_count == 2
    assert note.missing_pct == pytest.approx(50.0)
    code = next(c for c in result.columns if c.name == "code")
    assert code.missing_count == 0


def test_distinct_cardinality_folds_whitespace_variants() -> None:
    reader = _reader(
        ["cat"],
        [("web",), (" web ",), ("app",), ("app",), ("store",)],
    )
    result = profile_file(reader, "f.csv", ("cat",))
    # 'web' and ' web ' fold to one; app dedups -> {web, app, store} = 3
    assert result.columns[0].distinct_cardinality == 3


def test_pk_proof_unique() -> None:
    reader = _reader(
        ["order_no", "line_no"],
        [("A1", "1"), ("A1", "2"), ("A2", "1")],
    )
    result = profile_file(reader, "f.csv", ("order_no", "line_no"))
    assert result.pk.total == 3
    assert result.pk.distinct_pk == 3
    assert result.pk.null_pk == 0
    assert result.pk.is_unique is True


def test_pk_proof_duplicate_key_is_not_unique() -> None:
    reader = _reader(
        ["order_no", "line_no"],
        [("A1", "1"), ("A1", "1"), ("A2", "1")],  # (A1,1) twice
    )
    result = profile_file(reader, "f.csv", ("order_no", "line_no"))
    assert result.pk.distinct_pk == 2
    assert result.pk.is_unique is False


def test_pk_proof_null_key_is_not_unique() -> None:
    reader = _reader(
        ["order_no", "line_no"],
        [("A1", "1"), ("", "2"), ("A2", "1")],  # blank key part
    )
    result = profile_file(reader, "f.csv", ("order_no", "line_no"))
    assert result.pk.null_pk == 1
    assert result.pk.is_unique is False


def test_blank_header_name_raises() -> None:
    """A phantom/blank header column (misread header row, merged Excel header) is a
    profiling error, not a silent pass (PY-CN-084/085)."""
    reader = _reader(["id", ""], [("A1", "x")])
    with pytest.raises(ValueError, match="blank header name"):
        profile_file(reader, "f.csv", ("id",))


def test_candidate_pk_not_in_header_raises() -> None:
    reader = _reader(["id", "amount"], [("A1", "10")])
    with pytest.raises(ValueError, match="candidate-PK column"):
        profile_file(reader, "f.csv", ("order_no",))


def test_duplicate_header_name_raises() -> None:
    """Two columns named the same alias in columns.index -> a PK proof against the
    wrong column. Fail loud (misread header row / merged cells), not silent."""
    reader = _reader(["id", "amount", "id"], [("A1", "10", "B1")])
    with pytest.raises(ValueError, match="duplicate header name"):
        profile_file(reader, "f.csv", ("id",))


def test_ragged_short_row_counts_missing_and_is_flagged() -> None:
    """A short row (ragged file) pads to header width -> the gap reads as missing,
    the pass completes rather than crashing mid-file, AND the row is counted ragged."""
    reader = _reader(
        ["a", "b", "c"],
        [("1", "2", "3"), ("4", "5")],  # second row short one cell
    )
    result = profile_file(reader, "f.csv", ("a",))
    assert result.row_count == 2
    c = next(col for col in result.columns if col.name == "c")
    assert c.missing_count == 1
    assert result.ragged_row_count == 1


def test_ragged_long_row_is_flagged_not_silently_truncated() -> None:
    """A long row (more cells than the header -- the signature of a delimiter
    mismatch) is truncated to header width but COUNTED, never silently dropped."""
    reader = _reader(
        ["a", "b"],
        [("1", "2"), ("3", "4", "5")],  # second row one cell too many
    )
    result = profile_file(reader, "f.csv", ("a",))
    assert result.row_count == 2
    assert result.ragged_row_count == 1


def test_no_ragged_rows_when_all_match_header() -> None:
    reader = _reader(["a", "b"], [("1", "2"), ("3", "4")])
    result = profile_file(reader, "f.csv", ("a",))
    assert result.ragged_row_count == 0


def test_empty_file_no_rows() -> None:
    reader = _reader(["id"], [])
    result = profile_file(reader, "f.csv", ("id",))
    assert result.row_count == 0
    assert result.columns[0].missing_pct == 0.0
    assert result.pk.is_unique is False  # 0 == 0 rows but no proof of a key


def test_csv_reader_preserves_blanks_over_a_real_file(tmp_path) -> None:
    """The stdlib CSV reader yields '' for a blank field (no NA coercion), so the
    RC5 measure survives a real round-trip -- no optional dependency needed."""
    p = tmp_path / "orders.csv"
    p.write_text("order_no,line_no,note\nA1,1,hi\nA1,2,\n", encoding="utf-8")
    reader = make_csv_reader(str(p), encoding="utf-8")
    result = profile_file(reader, str(p), ("order_no", "line_no"))
    assert result.row_count == 2
    note = next(c for c in result.columns if c.name == "note")
    assert note.missing_count == 1  # the empty trailing field is '' -> missing


def test_csv_reader_semicolon_delimiter_and_header_row(tmp_path) -> None:
    """A ';'-delimited file with a banner row above the header -- the reader honors
    the detected delimiter and header_row rather than assuming comma / row 0."""
    p = tmp_path / "export.csv"
    p.write_text(
        "Sales Export Q2;;\norder_no;line_no;amt\nA1;1;10\nA2;1;20\n",
        encoding="utf-8",
    )
    reader = make_csv_reader(str(p), encoding="utf-8", delimiter=";", header_row=1)
    result = profile_file(reader, str(p), ("order_no", "line_no"))
    assert result.column_count == 3
    assert result.row_count == 2
    assert tuple(c.name for c in result.columns) == ("order_no", "line_no", "amt")


def test_csv_reader_streams_lazily_and_rows_is_recallable(tmp_path) -> None:
    """The CSV reader does not materialize the file: rows() re-opens and streams each
    call, so it is re-callable and yields the same data twice (proves lazy re-open)."""
    p = tmp_path / "d.csv"
    p.write_text("id,v\nA,1\nB,2\nC,3\n", encoding="utf-8")
    reader = make_csv_reader(str(p), encoding="utf-8")
    first = list(reader.rows())
    second = list(reader.rows())
    assert first == second == [("A", "1"), ("B", "2"), ("C", "3")]
    # header known without consuming rows()
    assert reader.columns == ("id", "v")


def test_csv_reader_header_row_beyond_file_raises(tmp_path) -> None:
    p = tmp_path / "d.csv"
    p.write_text("id,v\n", encoding="utf-8")
    with pytest.raises(ValueError, match="header_row=5 is beyond"):
        make_csv_reader(str(p), encoding="utf-8", header_row=5)
