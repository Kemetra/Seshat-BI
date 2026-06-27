"""M1.6 wiring smoke test: importing retail.rules must load every submodule."""

import importlib
import pkgutil

import pytest

pytestmark = pytest.mark.unit


def test_import_retail_rules_succeeds() -> None:
    # Importing the package must not raise — every submodule import resolves.
    pkg = importlib.import_module("retail.rules")
    assert pkg is not None


def test_all_submodules_importable() -> None:
    # #49: derive the submodule list dynamically via pkgutil instead of a
    # hardcoded tuple so an added or removed rule submodule is caught immediately.
    import retail.rules as rules_pkg

    submodule_names = [m.name for m in pkgutil.iter_modules(rules_pkg.__path__)]
    assert submodule_names, "retail.rules must have at least one submodule"
    for sub in submodule_names:
        mod = importlib.import_module(f"retail.rules.{sub}")
        assert mod is not None


def test_all_rules_returns_a_tuple() -> None:
    import retail.rules  # noqa: F401  (import for the registration side effect)
    from retail.registry import all_rules

    rules = all_rules()
    assert isinstance(rules, tuple)
    # Every entry carries a non-empty string id (RegisteredRule.id).
    assert all(isinstance(r.id, str) and r.id for r in rules)


# The single source of truth for the registered rule-id set. Any add/remove of a
# rule MUST update this set in the same change -- the test keys the count to
# len(EXPECTED_RULE_IDS), never a hard-coded number, so it catches silent drift.
EXPECTED_RULE_IDS = frozenset(
    {
        "S1",
        "S2",
        "S3",
        "S4a",
        "S4b",
        "S5",
        "S6",
        "S7",
        "S8",  # SQL family (S8: marked date table has no -1/NULL member)
        "D1",
        "D2",
        "D3",
        "D4",
        "D5",
        "D6",
        "D7",
        "D8",  # TMDL/DAX
        "D9",  # TMDL/DAX hygiene: no hardcoded date literals
        "D10",  # TMDL/DAX hygiene: no FILTER(ALL(...)) anti-pattern
        "D11",  # TMDL/DAX hygiene: every measure documented (///)
        "R1",  # PBIR
        "A1",  # route registry: every route target resolves or is marked planned
        "C1",
        "C2",  # connection/secrets
        "G1",
        "G2",
        "G3",
        "G4",
        "G5",  # git hygiene
        "G6",  # PBIP parameter hygiene (no real host/value in committed params)
        "P1",
        "P2",  # process
    }
)


def test_registered_rule_ids_match_expected_set() -> None:
    # Force a clean re-registration so this test does not depend on global
    # registry state left by other tests (e.g. test_registry.py clears _RULES
    # in an autouse fixture). Reloading the rule submodules re-fires every
    # @register decorator against a freshly-cleared registry.
    import importlib

    import retail.rules as rules_pkg
    from retail import registry

    registry._RULES.clear()
    # #49: derive submodule list from pkgutil instead of a hardcoded tuple.
    for info in pkgutil.iter_modules(rules_pkg.__path__):
        importlib.reload(importlib.import_module(f"retail.rules.{info.name}"))

    actual = {r.id for r in registry.all_rules()}
    assert actual == EXPECTED_RULE_IDS, (
        f"rule-id drift: missing={EXPECTED_RULE_IDS - actual}, "
        f"unexpected={actual - EXPECTED_RULE_IDS}"
    )
    # No duplicate registrations: tuple length equals the unique-id count.
    assert len(registry.all_rules()) == len(EXPECTED_RULE_IDS)
