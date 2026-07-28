"""Count-first, SELECT-only Gold statistical provider."""

from __future__ import annotations

import pytest

from seshat.dialect import get_dialect
from seshat.statistical.providers.base import (
    DataRequest,
    ProviderUnavailable,
    ResourceLimits,
)
from seshat.statistical.providers.gold import GoldProvider

pytestmark = pytest.mark.unit


class FakeRunner:
    def __init__(self, results: list[list[tuple]]) -> None:
        self.results = list(results)
        self.statements: list[tuple[str, tuple]] = []

    def run(self, sql: str, params: tuple = ()) -> list[tuple]:
        self.statements.append((sql, params))
        return self.results.pop(0)


def _request() -> DataRequest:
    return DataRequest(
        table="gold.weekly_sales",
        columns=("period", "metric_value"),
        logical_types=("date", "number"),
        roles={"time": "period", "response": "metric_value"},
    )


def test_gold_provider_counts_first_and_returns_rectangular_data() -> None:
    runner = FakeRunner([[(2,)], [("2026-01", 10), ("2026-02", 12)]])

    data = GoldProvider(
        runner,
        get_dialect("postgres"),
        ResourceLimits(max_rows=10, max_bytes=1024),
    ).fetch(_request())

    assert data.columns == ("period", "metric_value")
    assert data.rows == (("2026-01", 10), ("2026-02", 12))
    assert data.total_count == 2
    assert data.provenance.kind == "gold"
    assert len(data.provenance.data_digest) == 64
    assert len(data.provenance.query_digest or "") == 64
    assert len(runner.statements) == 2


def test_gold_provider_refuses_measured_row_ceiling_before_data_query() -> None:
    runner = FakeRunner([[(3,)]])
    with pytest.raises(ProviderUnavailable, match=r"3.*row ceiling") as exc_info:
        GoldProvider(
            runner,
            get_dialect("postgres"),
            ResourceLimits(max_rows=2, max_bytes=1024),
        ).fetch(_request())
    assert exc_info.value.blocker.code == "STAT_PROVIDER_RESOURCE_LIMIT"
    assert len(runner.statements) == 1


def test_gold_provider_refuses_oversized_returned_bytes() -> None:
    runner = FakeRunner([[(1,)], [("2026-01", "x" * 100)]])
    with pytest.raises(ProviderUnavailable, match="byte ceiling"):
        GoldProvider(
            runner,
            get_dialect("postgres"),
            ResourceLimits(max_rows=10, max_bytes=16),
        ).fetch(_request())


def test_gold_provider_refuses_incorrect_return_width() -> None:
    runner = FakeRunner([[(1,)], [("2026-01",)]])
    with pytest.raises(ProviderUnavailable, match="width"):
        GoldProvider(runner, get_dialect("postgres")).fetch(_request())


def test_gold_provider_refuses_count_data_mismatch() -> None:
    runner = FakeRunner([[(2,)], [("2026-01", 10)]])
    with pytest.raises(ProviderUnavailable, match="count mismatch"):
        GoldProvider(runner, get_dialect("postgres")).fetch(_request())


def test_gold_provider_emits_select_only() -> None:
    runner = FakeRunner([[(1,)], [("2026-01", 10)]])
    GoldProvider(runner, get_dialect("postgres")).fetch(_request())

    assert runner.statements
    assert all(
        sql.lstrip().upper().startswith("SELECT") for sql, _ in runner.statements
    )
    assert all(
        all(token not in sql for token in (";", "--", "/*", "*/"))
        for sql, _ in runner.statements
    )


def test_gold_provider_converts_runner_failure_to_unavailable() -> None:
    class BrokenRunner:
        def run(self, sql: str, params: tuple = ()) -> list[tuple]:
            raise RuntimeError("host=private.example password=secret")

    with pytest.raises(ProviderUnavailable, match="Gold data acquisition failed"):
        GoldProvider(BrokenRunner(), get_dialect("postgres")).fetch(_request())
