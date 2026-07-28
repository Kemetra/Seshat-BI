"""Deterministic and fail-closed local CSV acquisition."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.statistical.providers.base import (
    DataRequest,
    ProviderUnavailable,
    ResourceLimits,
)
from seshat.statistical.providers.local_csv import LocalCsvProvider

pytestmark = pytest.mark.unit


def _write(path: Path, content: str | bytes) -> Path:
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


def _request(*columns: str, logical_types: tuple[str, ...] | None = None):
    return DataRequest(
        columns=columns,
        logical_types=logical_types or tuple("number" for _ in columns),
    )


def test_local_provider_returns_ordered_roles_and_digest(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path / "private-input.csv",
        "period,value\n2026-01,10\n2026-02,12\n",
    )

    data = LocalCsvProvider(path, ResourceLimits(max_rows=10, max_bytes=1024)).fetch(
        _request("period", "value", logical_types=("date", "number"))
    )

    assert data.columns == ("period", "value")
    assert data.rows == (("2026-01", "10"), ("2026-02", "12"))
    assert data.total_count == 2
    assert data.excluded_count == 0
    assert len(data.provenance.data_digest) == 64
    assert str(tmp_path) not in data.provenance.safe_label
    assert data.provenance.query_digest is None
    assert data.provenance.snapshot_id is None


def test_local_provider_digest_is_stable_for_selected_data(
    tmp_path: Path,
) -> None:
    first = _write(tmp_path / "first.csv", "unused,value\nx,1\ny,2\n")
    second = _write(tmp_path / "second.csv", "unused,value\nz,1\nq,2\n")
    limits = ResourceLimits(max_rows=10, max_bytes=1024)

    digest_1 = (
        LocalCsvProvider(first, limits).fetch(_request("value")).provenance.data_digest
    )
    digest_2 = (
        LocalCsvProvider(second, limits).fetch(_request("value")).provenance.data_digest
    )

    assert digest_1 == digest_2


def test_local_provider_refuses_silent_sampling(tmp_path: Path) -> None:
    path = _write(tmp_path / "input.csv", "value\n1\n2\n3\n")
    with pytest.raises(ProviderUnavailable, match="row ceiling") as exc_info:
        LocalCsvProvider(path, ResourceLimits(max_rows=2, max_bytes=1024)).fetch(
            _request("value")
        )
    assert exc_info.value.blocker.code == "STAT_PROVIDER_RESOURCE_LIMIT"


def test_local_provider_refuses_byte_ceiling(tmp_path: Path) -> None:
    path = _write(tmp_path / "input.csv", "value\n123456789\n")
    with pytest.raises(ProviderUnavailable, match="byte ceiling"):
        LocalCsvProvider(path, ResourceLimits(max_rows=10, max_bytes=4)).fetch(
            _request("value")
        )


@pytest.mark.parametrize(
    "content",
    (
        ",value\nperiod,1\n",
        "value,value\n1,2\n",
        " value,value\n1,2\n",
    ),
)
def test_local_provider_refuses_invalid_headers(tmp_path: Path, content: str) -> None:
    path = _write(tmp_path / "input.csv", content)
    with pytest.raises(ProviderUnavailable, match="header"):
        LocalCsvProvider(path).fetch(_request("value"))


def test_local_provider_refuses_ragged_rows(tmp_path: Path) -> None:
    path = _write(tmp_path / "input.csv", "period,value\n2026-01,1\n2026-02\n")
    with pytest.raises(ProviderUnavailable, match="ragged row"):
        LocalCsvProvider(path).fetch(_request("value"))


def test_local_provider_refuses_missing_role_column(tmp_path: Path) -> None:
    path = _write(tmp_path / "input.csv", "period,value\n2026-01,1\n")
    with pytest.raises(ProviderUnavailable, match="missing requested columns"):
        LocalCsvProvider(path).fetch(_request("private_value"))


def test_local_provider_refuses_invalid_utf8(tmp_path: Path) -> None:
    path = _write(tmp_path / "input.csv", b"value\n\xff\n")
    with pytest.raises(ProviderUnavailable, match="UTF-8"):
        LocalCsvProvider(path).fetch(_request("value"))


@pytest.mark.parametrize("token", ("NaN", "inf", "-Infinity"))
def test_local_provider_refuses_non_finite_numeric_tokens(
    tmp_path: Path, token: str
) -> None:
    path = _write(tmp_path / "input.csv", f"value\n{token}\n")
    with pytest.raises(ProviderUnavailable, match="non-finite"):
        LocalCsvProvider(path).fetch(_request("value"))


def test_local_provider_reads_utf8_bom_fixture() -> None:
    path = Path(__file__).parents[2] / "fixtures/statistical/weekly_metric.csv"
    data = LocalCsvProvider(path).fetch(
        _request("period", "metric_value", logical_types=("date", "number"))
    )
    assert data.total_count == 4
    assert data.rows[0] == ("2026-01-05", "10")
