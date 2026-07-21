"""CLI-level tests for `seshat profile` (#400).

The mechanical profiler is exercised in ``test_profile.py``; these tests cover
the CLI seam only -- flag parsing, config/driver resolution, the markdown/JSON
render, and the fail-closed messages -- with the DB seams monkeypatched so no
real database is touched (the same posture as ``test_cli_context.py``'s
validate tests).
"""

from __future__ import annotations

import json

import pytest

from seshat.cli import _build_parser
from seshat.cli import main as main_under_test

pytestmark = pytest.mark.unit


class _FakeRunner:
    """Scripts the FIFO query order of ``seshat.profile.profile``:

    discover columns -> row count -> per-column (missingness, distinct) -> PK.
    """

    def run(self, sql, params=()):
        if "information_schema" in sql:
            return [("a", "text"), ("amount", "numeric")]
        if sql.strip().lower().startswith("select count(*) from") and (
            "DISTINCT" not in sql
        ):
            return [(3,)]
        if "DISTINCT (a)" in sql or "DISTINCT (a, " in sql:
            # PK proof row: (total, distinct_pk, null_pk) -> unique, no nulls
            return [(3, 3, 0)]
        # per-column (missing, distinct)
        return [(0, 3)]


def _args_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/db")
    monkeypatch.setattr("seshat.cli._ensure_driver", lambda: True)
    monkeypatch.setattr("seshat.cli._make_runner", lambda dsn: _FakeRunner())


def test_parser_profile_flags() -> None:
    ns = _build_parser().parse_args(
        ["profile", "--table", "bronze.t", "--pk", "a,b", "--format", "json"]
    )
    assert ns.command == "profile"
    assert ns.table == "bronze.t"
    assert ns.pk == "a,b"
    assert ns.output_format == "json"


def test_profile_markdown_render(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _args_ok(monkeypatch)
    rc = main_under_test(["profile", "--table", "bronze.t", "--pk", "a"])
    out = capsys.readouterr().out
    assert rc == 0
    # The mechanical blocks the blank source-profile.md asks for:
    assert "## Shape" in out
    assert "## Per-column profile" in out
    assert "COUNT(DISTINCT pk)" in out
    assert "candidate PK holds" in out


def test_profile_json_render(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _args_ok(monkeypatch)
    rc = main_under_test(
        ["profile", "--table", "bronze.t", "--pk", "a", "--format", "json"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["table"] == "bronze.t"
    assert payload["row_count"] == 3
    assert payload["pk"]["is_unique"] is True
    assert [c["name"] for c in payload["columns"]] == ["a", "amount"]


def test_rendered_markdown_round_trips_as_a_drift_baseline(tmp_path) -> None:
    """The markdown the verb advertises ("paste into source-profile.md") must be
    parseable by ``read_source_profile`` as a conformant, comparable baseline: a
    NULL-caused PK failure and the candidate-PK columns have to survive a
    render->paste->read round-trip, or the live drift path refuses the baseline
    (PR #409). Guards the reader-accepted numeric format + the `Candidate PK:`
    line + the shared `NULLs/empty in PK` proof label."""
    from pathlib import Path

    from seshat.cli.commands.profile import _render_markdown
    from seshat.profile import ColumnProfile, PkProof, ProfileResult
    from seshat.source_profile_reader import read_source_profile

    result = ProfileResult(
        table="bronze.t",
        row_count=100,
        column_count=2,
        columns=(
            ColumnProfile("id", 0, 0.0, 100, landed_type="text"),
            ColumnProfile("amount", 4, 4.0, 90, landed_type="numeric"),
        ),
        # distinct == total but 3 NULL keys -> NOT unique; only recoverable if
        # the reader can read back the null count from the rendered label.
        pk=PkProof(total=100, distinct_pk=100, null_pk=3, is_unique=False),
    )
    rendered = _render_markdown(result, ("id", "line_no"))

    # Paste the emitted blocks under a minimal template header (Table id +
    # Landed location) -- exactly the scaffolded shape the verb targets.
    doc = (
        "## Header\n\n"
        "| Field | Value |\n|-------|-------|\n"
        "| Table id | `T` |\n"
        "| Landed location | `bronze.t` |\n\n" + rendered + "\n"
    )
    path = Path(tmp_path) / "source-profile.md"
    path.write_text(doc, encoding="utf-8")

    parsed = read_source_profile(path)
    assert parsed.uncomparable is None, parsed.uncomparable
    assert parsed.profile is not None
    assert parsed.profile.row_count == 100
    assert tuple(c.name for c in parsed.profile.columns) == ("id", "amount")
    assert parsed.profile.columns[1].missing_count == 4
    assert parsed.pk_columns == ("id", "line_no")
    assert parsed.profile.pk.null_pk == 3
    assert parsed.profile.pk.is_unique is False


def test_profile_no_creds_errors_clearly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for var in ("DATABASE_URL", "ANALYTICS_DB_HOST"):
        monkeypatch.delenv(var, raising=False)

    def _boom(dsn):  # pragma: no cover - must never be called without creds
        raise AssertionError("must not build a runner without creds")

    monkeypatch.setattr("seshat.cli._make_runner", _boom)
    rc = main_under_test(["profile", "--table", "bronze.t", "--pk", "a"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "no database connection" in err.lower()


def test_profile_empty_pk_is_refused(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _args_ok(monkeypatch)
    rc = main_under_test(["profile", "--table", "bronze.t", "--pk", " , "])
    err = capsys.readouterr().err
    assert rc == 1
    assert "--pk must name at least one column" in err


def test_profile_missing_driver_errors_clearly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/db")
    monkeypatch.setattr("seshat.cli._ensure_driver", lambda: False)
    rc = main_under_test(["profile", "--table", "bronze.t", "--pk", "a"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "optional DB driver" in err
    assert "Traceback" not in err


def test_safe_target_label_never_leaks_keyword_conninfo_password() -> None:
    """A libpq keyword conninfo (no `@` to split on) must NOT be echoed
    verbatim -- the status line prints this label to stderr before connecting,
    and it would otherwise leak the password (PR #409 P1)."""
    from seshat.cli import _safe_target_label

    # A keyword conninfo renders NO component (host/user/password can be quoted
    # or "@"-bearing, so no split/regex safely isolates the host) -- it falls
    # back to the bare engine label, guaranteeing nothing leaks.
    conninfo = "host=db.example user=svc password=s3cret dbname=x port=5432"
    assert _safe_target_label("postgres", conninfo) == "postgres"

    # password containing "@" -> never split on "@".
    assert _safe_target_label("postgres", "host=db user=svc password=@s3cret") == (
        "postgres"
    )
    # password quoting a host-shaped token -> never regex-extracted.
    quoted = "password='abc host=secret' host=db"
    label = _safe_target_label("postgres", quoted)
    assert label == "postgres"
    assert "secret" not in label

    # password quoting a "://" -> must NOT be misclassified as a URL (the
    # discriminator is the LEADING scheme, not "://" appearing anywhere).
    spoof = "host=db password='abc://u:s3cret@credential'"
    spoof_label = _safe_target_label("postgres", spoof)
    assert spoof_label == "postgres"
    assert "s3cret" not in spoof_label and "credential" not in spoof_label

    # URL form with credentials in the query string is scrubbed to host, even
    # when the query value contains a raw "@" (structural parse, not @-split).
    assert "s3cret" not in _safe_target_label(
        "postgres", "postgresql://h:5432/db?password=s3cret"
    )
    at_query = "postgresql://h/db?password=secret@tail"
    assert _safe_target_label("postgres", at_query) == "h/db"
    assert "tail" not in _safe_target_label("postgres", at_query)

    # The credential-bearing URL form yields the host-only label.
    assert _safe_target_label("postgres", "postgresql://u:p@h:5432/db") == "h:5432/db"
    assert _safe_target_label("postgres", "postgresql://h:5432/db") == "h:5432/db"

    # A non-numeric / out-of-range port makes urlsplit's lazy `.port` raise
    # ValueError; the label is computed before the DB-boundary try, so it must
    # be guarded and fall back to the engine label (no uncaught traceback, #409).
    assert _safe_target_label("postgres", "postgresql://h:notaport/db") == "postgres"
    assert _safe_target_label("postgres", "postgresql://h:99999/db") == "postgres"


@pytest.mark.parametrize("bad_table", ["orders", "a.b.c", "bronze.", ".orders"])
def test_profile_requires_exactly_schema_dot_table(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    bad_table: str,
) -> None:
    # Unqualified (mis-resolves across engines) AND 3-part `db.schema.table`
    # (SQL Server -- discovers 0 columns, exit-0 empty profile) are both refused.
    _args_ok(monkeypatch)
    rc = main_under_test(["profile", "--table", bad_table, "--pk", "id"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "must be exactly schema.table" in err


def test_db_extra_hint_is_engine_specific() -> None:
    """The driver remedy must name the SELECTED engine's driver/extra, not
    always psycopg2 (PR #409). Postgres stays the default (unchanged output)."""
    from seshat.cli import _db_extra_hint

    pg = _db_extra_hint()
    assert "psycopg2-binary" in pg and "seshat-bi[db]" in pg
    assert _db_extra_hint("postgres") == pg  # default is postgres, unchanged

    mssql = _db_extra_hint("sqlserver")
    assert "pyodbc" in mssql and "seshat-bi[mssql]" in mssql
    assert "mysql-connector-python" in _db_extra_hint("mysql")
    assert "snowflake-connector-python" in _db_extra_hint("snowflake")


def test_profile_db_boundary_error_is_clean(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/db")
    monkeypatch.setattr("seshat.cli._ensure_driver", lambda: True)

    class _Boom:
        def run(self, sql, params=()):
            raise RuntimeError("relation does not exist")

    monkeypatch.setattr("seshat.cli._make_runner", lambda dsn: _Boom())
    rc = main_under_test(["profile", "--table", "bronze.t", "--pk", "a"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "profiling failed at the DB boundary" in err
    assert "Traceback" not in err
