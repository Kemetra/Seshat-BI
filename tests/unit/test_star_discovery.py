"""Shared star-discovery primitives (seshat/star_discovery.py) -- pure, driver-free."""

from __future__ import annotations

import pytest

from seshat import star_discovery as stars

pytestmark = pytest.mark.unit


def test_bare_dim_name_strips_schema_and_lowercases() -> None:
    assert stars.bare_dim_name("gold.Dim_Customer") == "dim_customer"
    assert stars.bare_dim_name("dim_customer") == "dim_customer"
    assert stars.bare_dim_name("") is None
    assert stars.bare_dim_name(None) is None


def test_star_id_resolution_order() -> None:
    assert stars.star_id({"meta": {"table_id": "t"}}, "dir") == "t"
    assert stars.star_id({"source_id": "sid"}, "dir") == "sid"
    assert stars.star_id({"meta": {}}, "dir") == "dir"


def test_is_star_requires_gold_star_fact() -> None:
    assert stars.is_star({"gold_star": {"fact": {"name": "f"}}}) is True
    assert stars.is_star({"gold_star": {}}) is False
    assert stars.is_star({}) is False


def test_star_dimensions_collects_dims_and_date_excludes_degenerate() -> None:
    doc = {
        "gold_star": {
            "dimensions": [
                {"name": "gold.dim_customer", "surrogate_key": "customer_sk"},
                {"name": "gold.dim_product", "surrogate_key": "product_sk"},
            ],
            "date_dimension": {"name": "dim_date", "surrogate_key": "date_sk"},
            "degenerate_dimensions": ["transaction_id"],
        }
    }
    dims = stars.star_dimensions(doc)
    assert set(dims) == {"dim_customer", "dim_product", "dim_date"}
    assert "transaction_id" not in dims


def test_discover_stars_keys_on_governed_star_id_via_injected_load() -> None:
    docs = {
        "mappings/dir_a/source-map.yaml": {
            "meta": {"table_id": "sales"},
            "gold_star": {"fact": {"name": "fct_sales"}},
        },
        "mappings/dir_b/source-map.yaml": {
            "source_id": "returns",
            "gold_star": {"fact": {"name": "fct_returns"}},
        },
        "mappings/dir_c/source-map.yaml": {"gold_star": {}},  # not a star
    }
    tracked = list(docs) + ["docs/quality/conformed-dimension-map.yaml"]
    found = stars.discover_stars(tracked, docs.get)
    # keyed on GOVERNED id (meta.table_id / source_id), not the directory
    assert set(found) == {"sales", "returns"}


def test_discover_stars_skips_test_paths_and_load_failures() -> None:
    docs = {
        "mappings/real/source-map.yaml": {
            "meta": {"table_id": "real"},
            "gold_star": {"fact": {"name": "f"}},
        },
        "mappings/broken/source-map.yaml": None,  # load returned None
    }
    tracked = list(docs) + ["tests/fixtures/mappings/x/source-map.yaml"]
    found = stars.discover_stars(tracked, docs.get)
    assert set(found) == {"real"}
