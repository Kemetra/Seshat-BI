"""TDD tests for the source-map.yaml -> validate-targets loader (feature 004 follow-up).

The four live checks take target dataclasses (PkTarget/DateCoverageTarget/
OrphanTarget/ReconcileTarget). This loader DERIVES those targets from a filled
`source-map.yaml`, so a real `retail validate` run is sourced per-table from the
mapping artifact instead of hardcoded params.

The loader lives in its own module (`seshat.validate_targets`) because it parses
YAML (pyyaml, a dev/optional dep) -- keeping `seshat.validate`'s import path
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
    from seshat.validate_targets import ValidationTargets, load_targets

    targets = load_targets(FIXTURE)
    assert isinstance(targets, ValidationTargets)
    assert targets.pk is not None
    assert targets.date_coverage is not None
    assert targets.orphans is not None
    assert targets.reconcile is not None


def test_pk_target_from_meta_primary_key() -> None:
    from seshat.validate_targets import load_targets

    pk = load_targets(FIXTURE).pk
    # table is silver.<table_id> by convention (PK verified on the transformed table)
    assert pk.table == "silver.demo_orders"
    assert pk.pk_columns == ("order_no", "line_no")


def test_reconcile_target_silver_gold_and_measures() -> None:
    from seshat.validate_targets import load_targets

    rec = load_targets(FIXTURE).reconcile
    assert rec.silver == "silver.demo_orders"
    assert rec.gold == "gold.fct_orders"
    assert rec.measures == ("net_amount", "tax_amount")


def test_date_coverage_target_from_date_dimension() -> None:
    from seshat.validate_targets import load_targets

    dc = load_targets(FIXTURE).date_coverage
    assert dc.fact == "gold.fct_orders"
    assert dc.date_dim == "gold.dim_date"
    # the date dim's join key is its surrogate_key; the fact carries the same column
    assert dc.dim_date == "date_sk"
    assert dc.fact_date == "date_sk"


def test_orphan_target_one_fk_per_dimension() -> None:
    from seshat.validate_targets import load_targets

    orphans = load_targets(FIXTURE).orphans
    assert orphans.fact == "gold.fct_orders"
    # RC14 convention: fact carries each dim's surrogate key; join dim.<sk> = fct.<sk>.
    # The date dim is covered by check_date_coverage, so it is NOT duplicated here.
    assert orphans.fks == (
        ("product_sk", "gold.dim_product", "product_sk"),
        ("customer_sk", "gold.dim_customer", "customer_sk"),
    )


def test_bare_gold_names_are_schema_qualified_to_gold() -> None:
    """A gold_star name WITHOUT a schema must be qualified to `gold.<name>`.

    Regression guard (2026-06-25 defect): the check SQL uses the fact/dim names
    VERBATIM (`FROM {target.fact}`), never prepending `gold.`. A source-map whose
    gold_star carries bare names (e.g. c086's `fct_sales`, `dim_product`) then
    produced `FROM fct_sales` -> UndefinedTable, and the CLI swallowed it. The loader
    must qualify a bare name to the `gold` schema, while leaving an already-qualified
    name (e.g. `gold.fct_sales_rss`) untouched -- so BOTH conventions work.
    """
    import tempfile

    from seshat.validate_targets import load_targets

    bare = (
        "meta:\n"
        "  table_id: demo\n"
        "  primary_key: [id]\n"
        "gold_star:\n"
        "  fact:\n"
        "    name: fct_demo\n"  # BARE -- no schema
        "    measures: [amt]\n"
        "  dimensions:\n"
        "    - name: dim_thing\n"  # BARE
        "      surrogate_key: thing_sk\n"
        "  date_dimension:\n"
        "    name: dim_date\n"  # BARE
        "    surrogate_key: date_sk\n"
    )
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "bare.source-map.yaml"
        p.write_text(bare, encoding="utf-8")
        t = load_targets(p)
    assert t.reconcile.gold == "gold.fct_demo"
    assert t.orphans.fact == "gold.fct_demo"
    assert t.date_coverage.fact == "gold.fct_demo"
    assert t.date_coverage.date_dim == "gold.dim_date"
    assert t.orphans.fks == (("thing_sk", "gold.dim_thing", "thing_sk"),)


def test_already_qualified_gold_names_are_left_untouched() -> None:
    """An already-`gold.`-qualified gold_star name must NOT be double-qualified."""
    import tempfile

    from seshat.validate_targets import load_targets

    qualified = (
        "meta:\n"
        "  table_id: demo\n"
        "  primary_key: [id]\n"
        "gold_star:\n"
        "  fact:\n"
        "    name: gold.fct_demo_rss\n"  # ALREADY qualified
        "    measures: [amt]\n"
        "  dimensions:\n"
        "    - name: gold.dim_thing_rss\n"
        "      surrogate_key: thing_sk\n"
        "  date_dimension:\n"
        "    name: gold.dim_date_rss\n"
        "    surrogate_key: date_sk\n"
    )
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "qual.source-map.yaml"
        p.write_text(qualified, encoding="utf-8")
        t = load_targets(p)
    assert t.reconcile.gold == "gold.fct_demo_rss"  # not gold.gold.fct_demo_rss
    assert t.orphans.fks == (("thing_sk", "gold.dim_thing_rss", "thing_sk"),)


def test_load_targets_missing_file_raises_clear_error() -> None:
    from seshat.validate_targets import load_targets

    with pytest.raises(FileNotFoundError):
        load_targets(FIXTURE.parent / "does_not_exist.source-map.yaml")


def test_load_targets_rejects_map_missing_gold_star(tmp_path: Path) -> None:
    # #21: stage into tmp_path instead of writing into the live fixture tree.
    from seshat.validate_targets import load_targets

    bad = tmp_path / "bad_no_gold_star.source-map.yaml"
    bad.write_text("meta:\n  table_id: x\n  primary_key: [a]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="gold_star"):
        load_targets(bad)


@pytest.mark.parametrize(
    ("yaml_text", "needle"),
    [
        (
            "meta:\n"
            '  table_id: "demo; DROP TABLE gold.fct_orders"\n'
            "  primary_key: [id]\n"
            "gold_star:\n"
            "  fact:\n"
            "    name: fct_demo\n"
            "    measures: [amt]\n"
            "  dimensions: []\n"
            "  date_dimension:\n"
            "    name: dim_date\n"
            "    surrogate_key: date_sk\n",
            "meta.table_id",
        ),
        (
            "meta:\n"
            "  table_id: demo\n"
            '  primary_key: ["id -- comment"]\n'
            "gold_star:\n"
            "  fact:\n"
            "    name: fct_demo\n"
            "    measures: [amt]\n"
            "  dimensions: []\n"
            "  date_dimension:\n"
            "    name: dim_date\n"
            "    surrogate_key: date_sk\n",
            "meta.primary_key",
        ),
        (
            "meta:\n"
            "  table_id: demo\n"
            "  primary_key: [id]\n"
            "gold_star:\n"
            "  fact:\n"
            '    name: "gold.fct_demo; DROP TABLE silver.demo"\n'
            "    measures: [amt]\n"
            "  dimensions: []\n"
            "  date_dimension:\n"
            "    name: dim_date\n"
            "    surrogate_key: date_sk\n",
            "gold_star object name",
        ),
        (
            "meta:\n"
            "  table_id: demo\n"
            "  primary_key: [id]\n"
            "gold_star:\n"
            "  fact:\n"
            "    name: fct_demo\n"
            '    measures: ["amt) FROM gold.fct_demo; SELECT password"]\n'
            "  dimensions: []\n"
            "  date_dimension:\n"
            "    name: dim_date\n"
            "    surrogate_key: date_sk\n",
            "gold_star.fact.measures",
        ),
        (
            "meta:\n"
            "  table_id: demo\n"
            "  primary_key: [id]\n"
            "gold_star:\n"
            "  fact:\n"
            "    name: fct_demo\n"
            "    measures: [amt]\n"
            "  dimensions:\n"
            "    - name: dim_thing\n"
            '      surrogate_key: "thing sk"\n'
            "  date_dimension:\n"
            "    name: dim_date\n"
            "    surrogate_key: date_sk\n",
            "surrogate_key",
        ),
    ],
)
def test_load_targets_rejects_unsafe_source_map_identifiers(
    tmp_path: Path, yaml_text: str, needle: str
) -> None:
    from seshat.validate_targets import load_targets

    p = tmp_path / "malicious.source-map.yaml"
    p.write_text(yaml_text, encoding="utf-8")

    with pytest.raises(ValueError, match="unsafe SQL identifier") as exc_info:
        load_targets(p)
    assert needle in str(exc_info.value)


def test_load_targets_rejects_invalid_yaml_cleanly(tmp_path: Path) -> None:
    from seshat.validate_targets import load_targets

    p = tmp_path / "bad.source-map.yaml"
    p.write_text("meta: [unterminated\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid YAML"):
        load_targets(p)


def test_validate_module_stays_stdlib_only() -> None:
    # The target LOADER may import yaml, but seshat.validate (the check logic)
    # must remain importable with no third-party deps. Guard: validate.py source
    # must not import yaml.
    import seshat.validate as v

    src = Path(v.__file__).read_text(encoding="utf-8")
    # The invariant is no third-party IMPORT (the word "yaml" may legitimately
    # appear in a comment naming the source-map.yaml filename).
    assert "import yaml" not in src
    assert "from yaml" not in src
