"""Spec A -- graceful-degradation rule tier.

A KIT_SELF rule (a rule that checks the kit's own internal manifests) must SKIP
in a repo that is not kit-bootstrapped, emitting one INFO finding instead of its
usual ERROR. A WORK_REPO rule (the default) always runs. This is what lets the
kit be dropped into a foreign BI repo without hard-failing on manifests that repo
can't have. Mirrors kit_lint's already-proven "absence is not drift" pattern.
"""

from pathlib import Path

import pytest

from seshat.core import Finding, RegisteredRule, RuleContext, RuleTier, Severity
from seshat.runner import run, run_json


def _ctx() -> RuleContext:
    return RuleContext(repo_root=Path("."), tracked_files=())


def _erroring(rule_id: str):
    def rule(ctx: RuleContext):
        return [Finding(rule_id, Severity.ERROR, "kit manifest missing", "m.yaml:1")]

    return rule


@pytest.mark.unit
def test_registered_rule_defaults_to_work_repo_tier():
    r = RegisteredRule(id="X", rule=_erroring("X"), title="x")
    assert r.tier == RuleTier.WORK_REPO


@pytest.mark.unit
def test_register_threads_tier():
    from seshat import registry

    saved = list(registry._RULES)  # restore on teardown (see test_cli.py)
    registry._RULES.clear()
    try:

        @registry.register("K1", "kit rule", tier=RuleTier.KIT_SELF)
        def k(ctx: RuleContext):
            return ()

        assert registry.all_rules()[0].tier == RuleTier.KIT_SELF
    finally:
        registry._RULES[:] = saved  # in-place restore preserves list identity


@pytest.mark.unit
def test_kit_self_rule_skips_when_not_bootstrapped(capsys):
    rules = (
        RegisteredRule(
            id="A1", rule=_erroring("A1"), title="kit", tier=RuleTier.KIT_SELF
        ),
    )
    code = run(rules, _ctx(), bootstrapped=False)
    out = capsys.readouterr().out
    assert code == 0  # the ERROR did not fire -> no hard fail
    assert "[error] A1" not in out
    assert "[info] A1" in out and "skipped" in out


@pytest.mark.unit
def test_kit_self_rule_runs_when_bootstrapped(capsys):
    rules = (
        RegisteredRule(
            id="A1", rule=_erroring("A1"), title="kit", tier=RuleTier.KIT_SELF
        ),
    )
    code = run(rules, _ctx(), bootstrapped=True)
    out = capsys.readouterr().out
    assert code == 1  # bootstrapped -> the kit rule runs and its ERROR fires
    assert "[error] A1 kit manifest missing" in out


@pytest.mark.unit
def test_work_repo_rule_runs_regardless_of_bootstrap(capsys):
    rules = (
        RegisteredRule(
            id="S4a", rule=_erroring("S4a"), title="portable", tier=RuleTier.WORK_REPO
        ),
    )
    # A portable rule must gate even in a foreign (non-bootstrapped) repo.
    code = run(rules, _ctx(), bootstrapped=False)
    assert code == 1
    assert "[error] S4a" in capsys.readouterr().out


@pytest.mark.unit
def test_default_bootstrapped_true_preserves_existing_behavior(capsys):
    # No bootstrapped kwarg -> defaults True -> kit rule runs (kit's own repo path).
    rules = (
        RegisteredRule(
            id="A1", rule=_erroring("A1"), title="kit", tier=RuleTier.KIT_SELF
        ),
    )
    assert run(rules, _ctx()) == 1


@pytest.mark.unit
def test_run_json_honors_tier_skip(capsys):
    import json

    rules = (
        RegisteredRule(
            id="A1", rule=_erroring("A1"), title="kit", tier=RuleTier.KIT_SELF
        ),
    )
    code = run_json(rules, _ctx(), bootstrapped=False)
    doc = json.loads(capsys.readouterr().out)
    assert code == 0
    assert doc["exit_code"] == 0
    assert [f["rule_id"] for f in doc["findings"]] == ["A1"]
    assert doc["findings"][0]["severity"] == "info"
