"""M1.6 wiring smoke test: importing retail.rules must load every submodule."""

import importlib

import pytest

pytestmark = pytest.mark.unit


def test_import_retail_rules_succeeds() -> None:
    # Importing the package must not raise — every submodule import resolves.
    pkg = importlib.import_module("retail.rules")
    assert pkg is not None


def test_all_submodules_importable() -> None:
    for sub in ("git_meta", "sql", "dax", "pbir"):
        mod = importlib.import_module(f"retail.rules.{sub}")
        assert mod is not None


def test_all_rules_returns_a_tuple() -> None:
    import retail.rules  # noqa: F401  (import for the registration side effect)
    from retail.registry import all_rules

    rules = all_rules()
    assert isinstance(rules, tuple)
    # Every entry carries a non-empty string id (RegisteredRule.id).
    assert all(isinstance(r.id, str) and r.id for r in rules)
