"""Every live-DB CLI boundary error goes through ONE redaction chain.

Table-driven over the five sites (validate, profile, value-check, drift,
report --from-gold) and the four engines. The driver message a failing connect
raises names values the configured DSN never contained -- an ambient host, its
resolved IP, a user, a database, a Windows user path and a tenant GUID -- which
layer-one ``dialect.redact`` alone cannot see.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.cli import main
from seshat.cli.commands.report import build_report_parser, report_main
from tests.unit.test_cli_value_check import _SINGLE_CONTRACT, _write_contract
from tests.unit.test_report_cli_gold import _gold_workspace

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]
_BASELINE = _REPO / "mappings" / "retail_store_sales" / "source-profile.md"

_HOST = "db-prod-a1.example.com"
_AMBIENT_HOST = "db-prod-b2.example.com"
_IP = "10.20.30.40"
_USER = "doadmin"
_PASSWORD = "Hunter2Horse"
_DB = "payroll_prod"
_WIN_PATH = "C:\\Users\\alice\\AppData\\my.cnf"
_GUID = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"
_LEAKS = (_HOST, _AMBIENT_HOST, _IP, _USER, _PASSWORD, _DB, "alice", _GUID)

_DRIVER_MESSAGE = (
    f'connection to server at "{_AMBIENT_HOST}" ({_IP}), port 25060 failed: '
    f'FATAL: password authentication failed for user "{_USER}"; '
    f"Unknown database '{_DB}' while reading {_WIN_PATH}; tenant {_GUID}"
)

_ENV_KEYS = (
    "DATABASE_URL",
    "ANALYTICS_DB_ENGINE",
    "ANALYTICS_DB_HOST",
    "ANALYTICS_DB_PORT",
    "ANALYTICS_DB_NAME",
    "ANALYTICS_DB_USER",
    "ANALYTICS_DB_PASSWORD",
    "ANALYTICS_DB_ACCOUNT",
    "PGHOST",
    "PGUSER",
    "PGPASSWORD",
    "PGDATABASE",
    "PGSERVICE",
)


def _postgres_dsn() -> str:
    scheme = "postgresql:" + "//"
    return f"{scheme}{_USER}:{_PASSWORD}" + "@" + f"{_HOST}:25060/{_DB}"


def _configure(monkeypatch: pytest.MonkeyPatch, engine: str) -> None:
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    if engine == "postgres":
        monkeypatch.setenv("DATABASE_URL", _postgres_dsn())
    else:
        monkeypatch.setenv("ANALYTICS_DB_ENGINE", engine)
        monkeypatch.setenv("ANALYTICS_DB_HOST", _HOST)
        monkeypatch.setenv("ANALYTICS_DB_ACCOUNT", _HOST)
        monkeypatch.setenv("ANALYTICS_DB_NAME", _DB)
        monkeypatch.setenv("ANALYTICS_DB_USER", _USER)
        monkeypatch.setenv("ANALYTICS_DB_PASSWORD", _PASSWORD)

    def _explode(_config: object, **_kwargs: object) -> object:
        raise RuntimeError(_DRIVER_MESSAGE)

    monkeypatch.setattr("seshat.cli._ensure_driver", lambda: True)
    monkeypatch.setattr("seshat.cli._make_runner", _explode)
    monkeypatch.setattr("seshat.cli._load_targets", lambda _path: object())


def _run_site(site: str, engine: str, tmp_path: Path) -> int:
    repo = ["--repo", str(tmp_path)]
    if site == "validate":
        return main(["validate", "--source-map", "x/source-map.yaml", *repo])
    if site == "profile":
        return main(["profile", "--table", "bronze.t", "--pk", "a", *repo])
    if site == "value-check":
        _write_contract(tmp_path, "TotalSales", _SINGLE_CONTRACT)
        return main(["value-check", "--metrics-dir", str(tmp_path), *repo])
    if site == "drift":
        dsn = _postgres_dsn() if engine == "postgres" else "unused"
        return main(["drift", "--baseline", str(_BASELINE), "--dsn", dsn, *repo])
    table, plan = _gold_workspace(tmp_path)
    args = build_report_parser().parse_args(
        [
            "--table",
            table,
            "--format",
            "html",
            "--repo-root",
            str(tmp_path),
            "--output",
            str(tmp_path / "out"),
            "--from-gold",
            "--figure-plan",
            str(plan),
        ]
    )
    return report_main(args)


_SITES = ("validate", "profile", "value-check", "drift", "report")
_ENGINES = ("postgres", "sqlserver", "mysql", "snowflake")


@pytest.mark.parametrize(
    "case",
    [(site, engine) for site in _SITES for engine in _ENGINES],
    ids=lambda case: "-".join(case),
)
def test_every_live_site_and_engine_redacts_the_driver_message(
    case: tuple[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    site, engine = case
    monkeypatch.chdir(tmp_path)
    _configure(monkeypatch, engine)

    code = _run_site(site, engine, tmp_path)

    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert code != 0
    assert "DB boundary" in text, text
    leaked = [value for value in _LEAKS if value in text]
    assert leaked == [], text


def test_a_service_dsn_loses_the_ambient_host_ip_and_user() -> None:
    """``service=prod`` names no host or user, so layer one derives nothing; the
    connection-context shapes still remove what libpq printed."""
    from seshat.db_boundary import boundary_error_text
    from seshat.dialect import get_dialect

    message = (
        f'connection to server at "{_AMBIENT_HOST}" ({_IP}), port 25060 failed: '
        f'FATAL: password authentication failed for user "{_USER}"'
    )

    text = boundary_error_text(
        get_dialect("postgres"), RuntimeError(message), "service=prod"
    )

    for value in (_AMBIENT_HOST, _IP, _USER):
        assert value not in text, text
    assert "port 25060 failed" in text  # no fragment shredding of benign words


def test_ambient_libpq_variables_are_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    from seshat.db_boundary import boundary_error_text
    from seshat.dialect import get_dialect

    monkeypatch.setenv("PGUSER", "svc_ambient")
    monkeypatch.setenv("PGHOST", "pg-ambient.example.com")

    text = boundary_error_text(
        get_dialect("postgres"),
        RuntimeError("could not connect to pg-ambient.example.com as svc_ambient"),
        "service=prod",
    )

    assert "svc_ambient" not in text and "pg-ambient" not in text, text


def test_an_unquoted_multi_word_password_never_leaks_a_word() -> None:
    from seshat.db_boundary import boundary_error_text
    from seshat.dialect import get_dialect

    conninfo = "host=db user=u password=correct horse battery dbname=d"
    message = 'invalid dsn: missing "=" after "horse" in connection info string'

    text = boundary_error_text(get_dialect("postgres"), RuntimeError(message), conninfo)

    assert "horse" not in text and "battery" not in text, text


def test_a_short_value_does_not_shred_unrelated_words() -> None:
    from seshat.db_boundary import boundary_error_text
    from seshat.dialect import get_dialect

    text = boundary_error_text(
        get_dialect("mysql"),
        RuntimeError("port 3306 refused the connection"),
        {"host": "h", "password": "p", "user": "u"},
    )

    assert "port 3306 refused the connection" in text


def test_a_redactor_that_raises_withholds_the_whole_message() -> None:
    from seshat.db_boundary import boundary_error_text

    class _Broken:
        def redact(self, message: object, config: object) -> str:
            raise ValueError("boom")

    text = boundary_error_text(_Broken(), RuntimeError(_DRIVER_MESSAGE), "x")

    assert "details redacted" in text
    assert all(value not in text for value in _LEAKS)


def test_dict_config_redaction_replaces_the_longest_value_first() -> None:
    from seshat.dialect import get_dialect

    config = {
        "account": "xy123",
        "user": "analytics",
        "host": "analytics-db.example.com",
    }
    text = get_dialect("snowflake").redact(
        "could not connect to analytics-db.example.com as analytics", config
    )

    assert "-db.example.com" not in text, text


@pytest.mark.parametrize(
    ("engine", "key"),
    [("mysql", "database"), ("snowflake", "database"), ("snowflake", "warehouse")],
)
def test_dict_config_engines_redact_the_database_like_postgres(
    engine: str, key: str
) -> None:
    from seshat.dialect import get_dialect

    text = get_dialect(engine).redact(f"unknown {key} {_DB}", {key: _DB})

    assert _DB not in text


_DRIVERS = (
    ("sqlserver", "pyodbc"),
    ("mysql", "mysql-connector-python"),
    ("snowflake", "snowflake-connector-python"),
)


@pytest.mark.parametrize(
    "case",
    [
        (site, engine, driver)
        for site in ("validate", "value-check", "drift")
        for engine, driver in _DRIVERS
    ],
    ids=lambda case: "-".join(case[:2]),
)
def test_the_missing_driver_hint_names_the_engines_own_driver(
    case: tuple[str, str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    site, engine, driver = case
    monkeypatch.chdir(tmp_path)
    _configure(monkeypatch, engine)
    monkeypatch.setattr("seshat.cli._ensure_driver", lambda: False)

    code = _run_site(site, engine, tmp_path)

    err = capsys.readouterr().err
    assert code == 1
    assert driver in err, err
    assert "psycopg2" not in err, err
    assert "'seshat-bi[" not in err, err  # cmd.exe passes apostrophes literally


def test_live_drift_profiles_with_the_configured_engines_dialect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def _profile(runner: object, table: str, pk: tuple, **kwargs: object) -> object:
        captured.update(kwargs)
        raise RuntimeError("stop after capture")

    monkeypatch.chdir(tmp_path)
    _configure(monkeypatch, "sqlserver")
    monkeypatch.setattr("seshat.cli._make_runner", lambda _config, **_kw: object())
    monkeypatch.setattr("seshat.profile.profile", _profile)

    _run_site("drift", "sqlserver", tmp_path)

    dialect = captured.get("dialect")
    assert getattr(dialect, "name", None) == "sqlserver"
    assert "FILTER" not in dialect.count_where("x = 1")


def test_the_target_banner_names_no_host_or_database() -> None:
    from seshat.cli import _safe_target_label

    label = _safe_target_label("postgres", _postgres_dsn())

    assert label.startswith("postgres (target ")
    assert _HOST not in label and _DB not in label
