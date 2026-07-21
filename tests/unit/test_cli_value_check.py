"""TDD tests for the `retail value-check` CLI handler (L4 value proxy wiring).

Mirrors the validate handler's discipline: the DB connection is monkeypatched so
no real database is touched. Proves the handler resolves a DSN, gates on the lazy
driver, discovers metric contracts, recomputes each contract's expected_value
against a fake runner, prints findings, and returns 1 iff any L4 ERROR.

A contract with no expected_value block is skipped. No DSN / no driver => an
actionable error and return 1, never a connect, never a traceback.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.cli import _build_parser
from seshat.cli import main as main_under_test

pytestmark = pytest.mark.unit


def _write_contract(metrics_dir: Path, name: str, body: str) -> None:
    d = metrics_dir / "retail_store_sales" / "metrics"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.yaml").write_text(body, encoding="utf-8")


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------


def test_parser_value_check_has_metrics_dir_and_dsn() -> None:
    ns = _build_parser().parse_args(
        ["value-check", "--repo", ".", "--metrics-dir", "mappings", "--dsn", "x"]
    )
    assert ns.command == "value-check"
    assert ns.metrics_dir == "mappings"
    assert ns.dsn == "x"


# ---------------------------------------------------------------------------
# no DSN / no driver => clean error, no connect
# ---------------------------------------------------------------------------


def test_value_check_no_dsn_errors_clearly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for var in ("DATABASE_URL", "ANALYTICS_DB_HOST"):
        monkeypatch.delenv(var, raising=False)

    def _boom(dsn):  # pragma: no cover - must never be called
        raise AssertionError("must not build a runner without creds")

    monkeypatch.setattr("seshat.cli._make_runner", _boom)
    rc = main_under_test(["value-check"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "no database connection" in err.lower()


def test_value_check_driver_missing_errors_clearly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/db")
    monkeypatch.setattr("seshat.cli._ensure_driver", lambda: False)
    rc = main_under_test(["value-check"])
    err = capsys.readouterr().err
    assert rc == 1
    # #399: names the real distribution (seshat-bi) + the pipx remedy, not retail.
    assert "db driver" in err.lower()
    assert "seshat-bi[db]" in err and "retail[db]" not in err
    assert "pipx inject" in err


# ---------------------------------------------------------------------------
# live wiring against a fake runner (no real DB)
# ---------------------------------------------------------------------------

_SINGLE_CONTRACT = """\
name: "TotalSales"
binds_to:
  gold_table: "gold.fct_sales_rss"
  columns: ["total_spent"]
definition:
  expected_value:
    value: "1552071.00"
    tolerance_abs: "0.00"
    aggregation: sum
    column: total_spent
"""

_RATIO_CONTRACT = """\
name: "DiscountedTransactionRate"
binds_to:
  gold_table: "gold.fct_sales_rss"
  columns: ["discount_applied"]
definition:
  additive: false
  numerator:
    aggregation: count_rows
    filter:
      - column: discount_applied
        op: is_true
  denominator:
    aggregation: count_rows
    filter:
      - column: discount_applied
        op: is_not_null
  expected_value:
    value: "0.5037"
    tolerance_abs: "0.0001"
    aggregation: ratio
"""

_NO_EXPECTED_CONTRACT = """\
name: "TransactionCount"
binds_to:
  gold_table: "gold.fct_sales_rss"
  columns: ["transaction_id"]
definition:
  additive: true
"""


def _setup_live(monkeypatch: pytest.MonkeyPatch, runner) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/db")
    monkeypatch.setattr("seshat.cli._ensure_driver", lambda: True)
    monkeypatch.setattr("seshat.cli._make_runner", lambda dsn: runner)


def test_value_check_single_aggregate_match_returns_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from decimal import Decimal

    _write_contract(tmp_path, "TotalSales", _SINGLE_CONTRACT)

    class FakeRunner:
        def run(self, sql, params=()):
            return [(Decimal("1552071.00"),)]

    _setup_live(monkeypatch, FakeRunner())
    rc = main_under_test(
        ["value-check", "--repo", str(tmp_path), "--metrics-dir", str(tmp_path)]
    )
    assert rc == 0


def test_value_check_single_aggregate_regression_returns_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from decimal import Decimal

    _write_contract(tmp_path, "TotalSales", _SINGLE_CONTRACT)

    class FakeRunner:
        def run(self, sql, params=()):
            return [(Decimal("1400000.00"),)]  # regressed value

    _setup_live(monkeypatch, FakeRunner())
    rc = main_under_test(
        ["value-check", "--repo", str(tmp_path), "--metrics-dir", str(tmp_path)]
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "V-L4" in out
    assert "TotalSales" in out


def test_value_check_ratio_match_returns_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_contract(tmp_path, "DiscountedTransactionRate", _RATIO_CONTRACT)

    class FakeRunner:
        def __init__(self):
            self.calls = []

        def run(self, sql, params=()):
            self.calls.append(sql)
            # numerator count then denominator count -> 4219 / 8376 = 0.50370...
            if "IS NOT NULL" in sql:
                return [(8376,)]
            return [(4219,)]

    runner = FakeRunner()
    _setup_live(monkeypatch, runner)
    rc = main_under_test(
        ["value-check", "--repo", str(tmp_path), "--metrics-dir", str(tmp_path)]
    )
    assert rc == 0
    # the ratio path translated the L3 filter ops into SQL predicates
    joined = " ".join(runner.calls)
    assert "IS NOT NULL" in joined
    assert "TRUE" in joined


def test_value_check_skips_contract_without_expected_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_contract(tmp_path, "TransactionCount", _NO_EXPECTED_CONTRACT)

    class FakeRunner:
        def run(self, sql, params=()):  # pragma: no cover - must not be called
            raise AssertionError("a contract with no expected_value must not query")

    _setup_live(monkeypatch, FakeRunner())
    rc = main_under_test(
        ["value-check", "--repo", str(tmp_path), "--metrics-dir", str(tmp_path)]
    )
    # nothing to check -> clean exit 0
    assert rc == 0


def test_value_check_malformed_block_is_error_not_skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = _SINGLE_CONTRACT.replace("aggregation: sum", "aggregation: median")
    _write_contract(tmp_path, "TotalSales", bad)

    class FakeRunner:
        def run(self, sql, params=()):  # pragma: no cover
            raise AssertionError("must not query a malformed contract")

    _setup_live(monkeypatch, FakeRunner())
    rc = main_under_test(
        ["value-check", "--repo", str(tmp_path), "--metrics-dir", str(tmp_path)]
    )
    err = capsys.readouterr().err
    assert rc == 1
    assert "aggregation" in err.lower()
    assert "Traceback" not in err


# ---------------------------------------------------------------------------
# .env loading (#340) -- rooted at --repo, and malformed .env fails clean
# ---------------------------------------------------------------------------


def test_value_check_loads_dotenv_from_repo_not_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """P2 (#344): with `--repo <workspace>`, `.env` is read from THAT workspace,
    not the caller's cwd. The workspace .env supplies the connection; no
    exported vars and no contracts -> a clean 'nothing to verify' (exit 0),
    proving the connection resolved from the repo's .env."""
    for var in ("DATABASE_URL", "ANALYTICS_DB_HOST", "ANALYTICS_DB_ENGINE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("seshat.cli._ensure_driver", lambda: True)
    workspace = tmp_path / "ws"
    (workspace / "retail_store_sales" / "metrics").mkdir(parents=True)
    (workspace / ".env").write_text(
        "ANALYTICS_DB_HOST=repo.example\n"
        "ANALYTICS_DB_NAME=warehouse\n"
        "ANALYTICS_DB_USER=reader\n",
        encoding="utf-8",
    )
    # Run from a DIFFERENT cwd that has NO .env.
    monkeypatch.chdir(tmp_path)

    rc = main_under_test(
        ["value-check", "--repo", str(workspace), "--metrics-dir", str(workspace)]
    )

    # Connection resolved (from the repo .env) and no contracts -> exit 0.
    assert rc == 0
    assert "nothing to verify" in capsys.readouterr().err


def test_value_check_malformed_dotenv_exits_1_without_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """P2 (#344): a malformed workspace .env yields a clean exit-1 with an
    actionable message, never a raw traceback."""
    for var in ("DATABASE_URL", "ANALYTICS_DB_HOST"):
        monkeypatch.delenv(var, raising=False)
    (tmp_path / "retail_store_sales" / "metrics").mkdir(parents=True)
    (tmp_path / ".env").write_text(
        "ANALYTICS_DB_HOST=a\nANALYTICS_DB_HOST=b\n", encoding="utf-8"
    )  # duplicate key -> EnvironmentConfigError

    rc = main_under_test(
        ["value-check", "--repo", str(tmp_path), "--metrics-dir", str(tmp_path)]
    )

    assert rc == 1
    assert "could not read the workspace .env" in capsys.readouterr().err
