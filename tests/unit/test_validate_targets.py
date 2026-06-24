"""TDD tests for the source-map.yaml -> validate-targets loader (feature 004 follow-up).

The four live checks take target dataclasses (PkTarget/DateCoverageTarget/
OrphanTarget/ReconcileTarget). This loader DERIVES those targets from a filled
`source-map.yaml`, so a real `retail validate` run is sourced per-table from the
mapping artifact instead of hardcoded params.

The loader lives in its own module (`retail.validate_targets`) because it parses
YAML (pyyaml, a dev/optional dep) -- keeping `retail.validate`'s import path
stdlib-only so the static core's `dependencies = []` invariant holds.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "sourcemap"
    / "filled_orders.source-map.yaml"
)


def test_load_targets_returns_all_four() -> None:
    from retail.validate_targets import ValidationTargets, load_targets

    targets = load_targets(FIXTURE)
    assert isinstance(targets, ValidationTargets)
    assert targets.pk is not None
    assert targets.date_coverage is not None
    assert targets.orphans is not None
    assert targets.reconcile is not None


def test_pk_target_from_meta_primary_key() -> None:
    from retail.validate_targets import load_targets

    pk = load_targets(FIXTURE).pk
    # table is silver.<table_id> by convention (PK verified on the transformed table)
    assert pk.table == "silver.demo_orders"
    assert pk.pk_columns == ("order_no", "line_no")


def test_reconcile_target_silver_gold_and_measures() -> None:
    from retail.validate_targets import load_targets

    rec = load_targets(FIXTURE).reconcile
    assert rec.silver == "silver.demo_orders"
    assert rec.gold == "gold.fct_orders"
    assert rec.measures == ("net_amount", "tax_amount")


def test_date_coverage_target_from_date_dimension() -> None:
    from retail.validate_targets import load_targets

    dc = load_targets(FIXTURE).date_coverage
    assert dc.fact == "gold.fct_orders"
    assert dc.date_dim == "gold.dim_date"
    # the date dim's join key is its surrogate_key; the fact carries the same column
    assert dc.dim_date == "date_sk"
    assert dc.fact_date == "date_sk"


def test_orphan_target_one_fk_per_dimension() -> None:
    from retail.validate_targets import load_targets

    orphans = load_targets(FIXTURE).orphans
    assert orphans.fact == "gold.fct_orders"
    # RC14 convention: fact carries each dim's surrogate key; join dim.<sk> = fct.<sk>.
    # The date dim is covered by check_date_coverage, so it is NOT duplicated here.
    assert orphans.fks == (
        ("product_sk", "gold.dim_product", "product_sk"),
        ("customer_sk", "gold.dim_customer", "customer_sk"),
    )


def test_load_targets_missing_file_raises_clear_error() -> None:
    from retail.validate_targets import load_targets

    with pytest.raises(FileNotFoundError):
        load_targets(FIXTURE.parent / "does_not_exist.source-map.yaml")


def test_load_targets_rejects_map_missing_gold_star() -> None:
    from retail.validate_targets import load_targets

    bad = FIXTURE.parent / "bad_no_gold_star.source-map.yaml"
    bad.write_text("meta:\n  table_id: x\n  primary_key: [a]\n", encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="gold_star"):
            load_targets(bad)
    finally:
        bad.unlink()


def test_validate_module_stays_stdlib_only() -> None:
    # The target LOADER may import yaml, but retail.validate (the check logic)
    # must remain importable with no third-party deps. Guard: validate.py source
    # must not import yaml.
    import retail.validate as v

    src = Path(v.__file__).read_text(encoding="utf-8")
    # The invariant is no third-party IMPORT (the word "yaml" may legitimately
    # appear in a comment naming the source-map.yaml filename).
    assert "import yaml" not in src
    assert "from yaml" not in src
