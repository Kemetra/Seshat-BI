# tests/unit/test_source_profile_reader.py
import pytest
from pathlib import Path

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]


def test_reads_template_conformant_profile():
    from retail.source_profile_reader import read_source_profile
    parsed = read_source_profile(_ROOT / "mappings" / "retail_store_sales" / "source-profile.md")
    assert parsed.uncomparable is None
    p = parsed.profile
    assert p.table == "retail_store_sales"
    names = {c.name for c in p.columns}
    assert "transaction_id" in names and "discount_applied" in names
    disc = next(c for c in p.columns if c.name == "discount_applied")
    assert disc.missing_pct == pytest.approx(33.39, abs=0.01)
    assert disc.distinct_cardinality == 3
    assert p.pk.is_unique is True
    assert p.pk.total == 12575


def test_nonconformant_profile_reported_uncomparable():
    from retail.source_profile_reader import read_source_profile
    parsed = read_source_profile(_ROOT / "mappings" / "demo_sample_orders" / "source-profile.md")
    assert parsed.uncomparable is not None
    assert "per-column" in parsed.uncomparable.lower() or "table" in parsed.uncomparable.lower()
    assert parsed.profile is None
