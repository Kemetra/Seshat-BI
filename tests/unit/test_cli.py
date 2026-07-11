import subprocess
from pathlib import Path

import pytest

from seshat import cli, registry


@pytest.fixture(autouse=True)
def _clear_registry():
    # Start each of these tests from an empty registry, then RESTORE the real
    # registered rules on teardown. Without the restore, the global
    # registry._RULES stays empty for every test that runs after this module,
    # so any later test that drives the real main()->all_rules() path (e.g. the
    # P2 --commit-range e2e tests) silently sees zero rules. A test that mutates
    # global state must put it back.
    saved = list(registry._RULES)
    registry._RULES.clear()
    yield
    registry._RULES[:] = saved  # in-place restore preserves list identity


def _init_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "a.sql").write_text("select 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)


@pytest.mark.unit
def test_check_returns_0_when_no_rules(tmp_path):
    _init_repo(tmp_path)
    assert cli.main(["check", "--repo", str(tmp_path)]) == 0


@pytest.mark.unit
def test_check_returns_1_when_a_rule_errors(tmp_path):
    _init_repo(tmp_path)
    from seshat.core import Finding, RuleContext, Severity

    @registry.register("E9", "always errors")
    def boom(ctx: RuleContext):
        return [Finding("E9", Severity.ERROR, "nope", "a.sql:1")]

    assert cli.main(["check", "--repo", str(tmp_path)]) == 1


@pytest.mark.unit
def test_no_subcommand_returns_2(capsys):
    # argparse error path: missing required subcommand.
    assert cli.main([]) == 2


@pytest.mark.unit
def test_check_default_format_is_text_and_unchanged(tmp_path, capsys):
    # B2 backward-compat guard: `check` with NO --format must produce the exact
    # legacy text line, byte-for-byte. A regression here breaks existing consumers.
    _init_repo(tmp_path)
    from seshat.core import Finding, RuleContext, Severity

    @registry.register("E9", "always errors")
    def boom(ctx: RuleContext):
        return [Finding("E9", Severity.ERROR, "nope", "a.sql:1")]

    code = cli.main(["check", "--repo", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 1
    assert out == "[error] E9 nope (a.sql:1)\n"


@pytest.mark.unit
def test_check_format_text_explicit_equals_default(tmp_path, capsys):
    # --format text is identical to omitting the flag.
    _init_repo(tmp_path)
    from seshat.core import Finding, RuleContext, Severity

    @registry.register("E9", "always errors")
    def boom(ctx: RuleContext):
        return [Finding("E9", Severity.ERROR, "nope", "a.sql:1")]

    assert cli.main(["check", "--repo", str(tmp_path), "--format", "text"]) == 1
    assert capsys.readouterr().out == "[error] E9 nope (a.sql:1)\n"


@pytest.mark.unit
def test_check_format_json_emits_structured_output(tmp_path, capsys):
    import json

    _init_repo(tmp_path)
    from seshat.core import Finding, RuleContext, Severity

    @registry.register("E9", "always errors")
    def boom(ctx: RuleContext):
        return [Finding("E9", Severity.ERROR, "nope", "a.sql:1")]

    code = cli.main(["check", "--repo", str(tmp_path), "--format", "json"])
    assert code == 1
    doc = json.loads(capsys.readouterr().out)
    # Exact match: the test registers exactly one rule with exactly one finding.
    assert doc == {
        "findings": [
            {
                "rule_id": "E9",
                "severity": "error",
                "message": "nope",
                "locator": "a.sql:1",
            }
        ],
        "exit_code": 1,
    }


@pytest.mark.unit
def test_check_rejects_unknown_format(tmp_path):
    # argparse rejects an out-of-choices --format value with exit 2.
    _init_repo(tmp_path)
    assert cli.main(["check", "--repo", str(tmp_path), "--format", "xml"]) == 2
