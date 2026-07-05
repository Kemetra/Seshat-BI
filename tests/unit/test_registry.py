import pytest

from retail import registry
from retail.core import Finding, RuleContext, Severity


@pytest.fixture(autouse=True)
def _clear_registry():
    # registry uses a module-global list; isolate each test, then RESTORE the
    # real registered rules on teardown. Without the restore, _RULES stays empty
    # for every test that runs after this module, so any later test driving the
    # real all_rules() path silently sees zero rules (mirrors test_cli.py).
    saved = list(registry._RULES)
    registry._RULES.clear()
    yield
    registry._RULES[:] = saved  # in-place restore preserves list identity


@pytest.mark.unit
def test_register_adds_rule_and_returns_function():
    @registry.register("X1", "example rule")
    def my_rule(ctx: RuleContext):
        return ()

    assert my_rule.__name__ == "my_rule"  # decorator returns fn unchanged
    rules = registry.all_rules()
    assert len(rules) == 1
    assert rules[0].id == "X1"
    assert rules[0].title == "example rule"
    assert rules[0].rule is my_rule


@pytest.mark.unit
def test_all_rules_preserves_registration_order():
    @registry.register("A", "first")
    def a(ctx: RuleContext):
        return ()

    @registry.register("B", "second")
    def b(ctx: RuleContext):
        return [Finding("B", Severity.INFO, "ok", "x")]

    assert [r.id for r in registry.all_rules()] == ["A", "B"]


@pytest.mark.unit
def test_all_rules_returns_tuple_snapshot():
    assert registry.all_rules() == ()
    assert isinstance(registry.all_rules(), tuple)
