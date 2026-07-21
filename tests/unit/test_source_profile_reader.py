# tests/unit/test_source_profile_reader.py
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]


def test_reads_template_conformant_profile():
    from seshat.source_profile_reader import read_source_profile

    parsed = read_source_profile(
        _ROOT / "mappings" / "retail_store_sales" / "source-profile.md"
    )
    assert parsed.uncomparable is None
    p = parsed.profile
    assert p.table == "retail_store_sales"
    names = {c.name for c in p.columns}
    assert "transaction_id" in names and "discount_applied" in names
    disc = next(c for c in p.columns if c.name == "discount_applied")
    assert disc.missing_pct == pytest.approx(33.39, abs=0.01)
    assert disc.distinct_cardinality == 3
    # the "Type as landed" column is parsed into landed_type (all-TEXT bronze)
    assert disc.landed_type == "TEXT"
    assert p.pk.is_unique is True
    assert p.pk.total == 12575


def test_reads_stated_candidate_pk_columns():
    # The baseline STATES its PK ("**Candidate PK:** `( transaction_id )`"); the
    # live re-profile must run against that exact column, not a guessed first
    # column (guessing profiles observed.pk on a DIFFERENT column than the
    # baseline proof describes -> an invalid comparison that fabricates a false
    # blocked grain_pk_drift).
    from seshat.source_profile_reader import read_source_profile

    parsed = read_source_profile(
        _ROOT / "mappings" / "retail_store_sales" / "source-profile.md"
    )
    assert parsed.pk_columns == ("transaction_id",)


def test_landed_table_is_schema_qualified_not_the_bare_display_id():
    # The live re-profile must connect to the LANDED object (schema-qualified,
    # from "Landed location: `bronze.retail_store_sales`"), NOT the bare display
    # "Table id" (`retail_store_sales`) -- a dotless name makes profile()
    # default to schema `public` and mistarget (wrong table / UndefinedTable).
    # ProfileResult.table stays the display id (the emitted doc's "table" field);
    # landed_table carries the connectable identity.
    from seshat.source_profile_reader import read_source_profile

    parsed = read_source_profile(
        _ROOT / "mappings" / "retail_store_sales" / "source-profile.md"
    )
    assert parsed.profile.table == "retail_store_sales"  # display id unchanged
    assert parsed.landed_table == "bronze.retail_store_sales"  # connectable target


def test_nonconformant_profile_reported_uncomparable():
    from seshat.source_profile_reader import read_source_profile

    parsed = read_source_profile(
        _ROOT / "mappings" / "demo_sample_orders" / "source-profile.md"
    )
    assert parsed.uncomparable is not None
    assert (
        "per-column" in parsed.uncomparable.lower()
        or "table" in parsed.uncomparable.lower()
    )
    assert parsed.profile is None
    # A non-conformant baseline carries no usable PK column set either.
    assert parsed.pk_columns is None
    # ...nor a connectable landed-table identity.
    assert parsed.landed_table is None


def test_empty_table_pk_proof_round_trips_as_not_unique():
    """An empty-table proof (`0 = 0`, `0`, `0`) must reconstruct as NOT unique,
    mirroring profile.py's `total > 0` guard -- otherwise a pasted empty-table
    baseline round-trips to is_unique=True and a later drift run treats an
    unproven grain as valid (#409)."""
    from seshat.source_profile_reader import _parse_pk

    proof = (
        "- **Candidate PK:** `( id )`.\n"
        "- **Uniqueness proof (on the landed data):**\n"
        "  - `COUNT(*)            = 0`\n"
        "  - `COUNT(DISTINCT pk)  = 0`\n"
        "  - `NULLs/empty in PK   = 0`\n"
    )
    pk = _parse_pk(proof, row_count=0)
    assert pk.total == 0
    assert pk.is_unique is False
