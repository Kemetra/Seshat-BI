from __future__ import annotations

from pathlib import Path

import pytest

from scripts.adopter_sim.fixtures import assert_clean, assert_messy
from scripts.adopter_sim.model import AdopterSimError

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]
_MESSY = _REPO / "benchmark/journeys/datasets/messy/orders.csv"
_CLEAN = _REPO / "benchmark/journeys/datasets/clean/orders.csv"

_HEADER = "transaction_id,order_date,line_amount,customer_contact\n"


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "orders.csv"
    path.write_text(_HEADER + body, encoding="utf-8")
    return path


def test_shipped_messy_fixture_holds_every_property() -> None:
    properties = assert_messy(_MESSY)
    assert {p.name for p in properties} == {
        "repeated_grain_key",
        "null_measure",
        "mixed_date_formats",
        "pii_shaped_column",
        "no_returns_column",
    }
    assert all(p.holds for p in properties)


def test_shipped_clean_fixture_is_clean() -> None:
    assert assert_clean(_CLEAN) is None


def test_tidied_grain_key_fails(tmp_path: Path) -> None:
    body = "T1,2026-01-01,10.00,contact-0001\nT2,01/02/2026,,contact-0002\n"
    with pytest.raises(AdopterSimError, match="repeated_grain_key"):
        assert_messy(_write(tmp_path, body))


def test_filled_null_measure_fails(tmp_path: Path) -> None:
    body = "T1,2026-01-01,10.00,contact-0001\nT1,01/02/2026,12.00,contact-0002\n"
    with pytest.raises(AdopterSimError, match="null_measure"):
        assert_messy(_write(tmp_path, body))


def test_single_date_format_fails(tmp_path: Path) -> None:
    body = "T1,2026-01-01,10.00,contact-0001\nT1,2026-01-02,,contact-0002\n"
    with pytest.raises(AdopterSimError, match="mixed_date_formats"):
        assert_messy(_write(tmp_path, body))


def test_missing_pii_column_fails(tmp_path: Path) -> None:
    path = tmp_path / "orders.csv"
    path.write_text(
        "transaction_id,order_date,line_amount\nT1,2026-01-01,10.00\nT1,01/02/2026,\n",
        encoding="utf-8",
    )
    with pytest.raises(AdopterSimError, match="pii_shaped_column"):
        assert_messy(path)


def test_returns_column_present_fails(tmp_path: Path) -> None:
    path = tmp_path / "orders.csv"
    path.write_text(
        "transaction_id,order_date,line_amount,customer_contact,return_flag\n"
        "T1,2026-01-01,10.00,contact-0001,N\n"
        "T1,01/02/2026,,contact-0002,Y\n",
        encoding="utf-8",
    )
    with pytest.raises(AdopterSimError, match="no_returns_column"):
        assert_messy(path)


def test_clean_fixture_with_duplicate_key_is_rejected(tmp_path: Path) -> None:
    body = "T1,2026-01-01,10.00,contact-0001\nT1,2026-01-02,12.00,contact-0002\n"
    with pytest.raises(AdopterSimError, match="repeated"):
        assert_clean(_write(tmp_path, body))
