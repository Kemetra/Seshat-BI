import dataclasses
from pathlib import Path

import pytest

from seshat.core import Finding, RegisteredRule, RuleContext, Severity


@pytest.mark.unit
def test_severity_values():
    assert Severity.ERROR.value == "error"
    assert Severity.WARNING.value == "warning"
    assert Severity.INFO.value == "info"


@pytest.mark.unit
def test_finding_to_dict_renders_severity_as_value():
    f = Finding("D8", Severity.ERROR, "boom", "f.tmdl:3")
    assert f.to_dict() == {
        "rule_id": "D8",
        "severity": "error",
        "message": "boom",
        "locator": "f.tmdl:3",
    }


@pytest.mark.unit
def test_finding_to_dict_round_trips_via_severity_enum():
    # The "error" string must reconstruct the same Severity (JSON round-trip).
    f = Finding("W1", Severity.WARNING, "heads up", "f.sql:2")
    d = f.to_dict()
    assert Severity(d["severity"]) is Severity.WARNING
    assert (
        Finding(d["rule_id"], Severity(d["severity"]), d["message"], d["locator"]) == f
    )


@pytest.mark.unit
def test_finding_is_frozen_dataclass():
    f = Finding(
        rule_id="D8",
        severity=Severity.ERROR,
        message="reads bronze",
        locator="model.tmdl:12",
    )
    assert f.rule_id == "D8"
    assert f.severity is Severity.ERROR
    assert dataclasses.is_dataclass(f)
    with pytest.raises(dataclasses.FrozenInstanceError):
        f.rule_id = "S2"  # type: ignore[misc]


@pytest.mark.unit
def test_rule_context_holds_root_and_tracked_files():
    ctx = RuleContext(repo_root=Path("/repo"), tracked_files=("a.sql", "b.tmdl"))
    assert ctx.repo_root == Path("/repo")
    assert ctx.tracked_files == ("a.sql", "b.tmdl")


@pytest.mark.unit
def test_rule_context_v2_fields_default_to_none():
    # Built with only the two required fields: the contract-v2 invocation
    # fields default to None (the local `retail check` mode).
    ctx = RuleContext(repo_root=Path("/repo"), tracked_files=("a.sql",))
    assert ctx.commit_range is None
    assert ctx.commit_message is None


@pytest.mark.unit
def test_rule_context_v2_fields_preserved_when_supplied():
    # Built with all four fields: commit_range and commit_message round-trip.
    ctx = RuleContext(
        repo_root=Path("/repo"),
        tracked_files=("a.sql",),
        commit_range="origin/main..HEAD",
        commit_message="feat: a thing",
    )
    assert ctx.commit_range == "origin/main..HEAD"
    assert ctx.commit_message == "feat: a thing"


@pytest.mark.unit
def test_registered_rule_holds_id_callable_title():
    def dummy(ctx: RuleContext):
        return ()

    rr = RegisteredRule(id="X1", rule=dummy, title="dummy")
    assert rr.id == "X1"
    assert rr.title == "dummy"
    assert rr.rule is dummy
