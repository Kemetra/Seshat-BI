"""DSN-safe tests for the mandatory portfolio DB enumeration boundary."""

from __future__ import annotations

import pytest

from seshat import portfolio_enumerate

SECRET_DSN = "postgresql://portfolio_user:portfolio_secret@private-db/warehouse"


class _Dialect:
    def __init__(
        self,
        *,
        resolve_error: Exception | None = None,
        redact_error: Exception | None = None,
    ):
        self.resolve_error = resolve_error
        self.redact_error = redact_error

    def resolve_config(self, env):
        if self.resolve_error:
            raise self.resolve_error
        return env["DATABASE_URL"]

    def redact(self, error, config):
        if self.redact_error:
            raise self.redact_error
        return str(error).replace(config, "<redacted DSN>")

    def placeholder(self):
        return "%s"

    def translate_params(self, sql):
        return sql


def _assert_redacted(result) -> None:
    assert result.tables == ()
    assert result.error
    assert SECRET_DSN not in result.error
    assert "portfolio_user" not in result.error
    assert "portfolio_secret" not in result.error
    assert "private-db" not in result.error


def test_config_resolve_failure_never_leaks_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dialect = _Dialect(resolve_error=RuntimeError(f"bad config {SECRET_DSN}"))
    monkeypatch.setattr(portfolio_enumerate, "get_dialect", lambda _engine: dialect)

    result = portfolio_enumerate.enumerate_tables(
        "analytics", env={"DATABASE_URL": SECRET_DSN}
    )

    _assert_redacted(result)


def test_driver_gate_failure_never_leaks_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    dialect = _Dialect()
    monkeypatch.setattr(portfolio_enumerate, "get_dialect", lambda _engine: dialect)
    monkeypatch.setattr(
        "seshat.cli._ensure_driver",
        lambda: (_ for _ in ()).throw(RuntimeError(f"driver failed {SECRET_DSN}")),
    )

    result = portfolio_enumerate.enumerate_tables(
        "analytics", env={"DATABASE_URL": SECRET_DSN}
    )

    _assert_redacted(result)


def test_redactor_failure_falls_back_without_leaking_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dialect = _Dialect(redact_error=RuntimeError(f"redactor failed {SECRET_DSN}"))
    monkeypatch.setattr(portfolio_enumerate, "get_dialect", lambda _engine: dialect)
    monkeypatch.setattr("seshat.cli._ensure_driver", lambda: True)
    monkeypatch.setattr(
        "seshat.cli._make_runner",
        lambda _config: (_ for _ in ()).throw(
            RuntimeError(f"connection refused for {SECRET_DSN}")
        ),
    )

    result = portfolio_enumerate.enumerate_tables(
        "analytics", env={"DATABASE_URL": SECRET_DSN}
    )

    _assert_redacted(result)


def test_success_returns_every_table(monkeypatch: pytest.MonkeyPatch) -> None:
    dialect = _Dialect()
    monkeypatch.setattr(portfolio_enumerate, "get_dialect", lambda _engine: dialect)
    monkeypatch.setattr("seshat.cli._ensure_driver", lambda: True)
    runner = type(
        "Runner", (), {"run": lambda self, sql, params=(): [("orders",), ("products",)]}
    )()
    monkeypatch.setattr("seshat.cli._make_runner", lambda _config: runner)

    result = portfolio_enumerate.enumerate_tables(
        "analytics", env={"DATABASE_URL": SECRET_DSN}
    )

    assert result.error is None
    assert result.tables == ("analytics.orders", "analytics.products")
