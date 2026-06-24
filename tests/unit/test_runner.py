from pathlib import Path

import pytest

from retail.core import Finding, RegisteredRule, RuleContext, Severity
from retail.runner import build_context, run


def _ctx() -> RuleContext:
    return RuleContext(repo_root=Path("."), tracked_files=())


@pytest.mark.unit
def test_run_exits_1_when_any_error_finding(capsys):
    def bad(ctx: RuleContext):
        return [Finding("E1", Severity.ERROR, "boom", "f.sql:1")]

    rules = (RegisteredRule(id="E1", rule=bad, title="bad"),)
    code = run(rules, _ctx())
    assert code == 1
    out = capsys.readouterr().out
    assert "[error] E1 boom (f.sql:1)" in out


@pytest.mark.unit
def test_run_exits_0_when_no_error_findings(capsys):
    def warn(ctx: RuleContext):
        return [Finding("W1", Severity.WARNING, "heads up", "f.sql:2")]

    def clean(ctx: RuleContext):
        return ()

    rules = (
        RegisteredRule(id="W1", rule=warn, title="warn"),
        RegisteredRule(id="C0", rule=clean, title="clean"),
    )
    code = run(rules, _ctx())
    assert code == 0
    out = capsys.readouterr().out
    assert "[warning] W1 heads up (f.sql:2)" in out


@pytest.mark.unit
def test_run_exits_0_when_no_findings_at_all(capsys):
    def clean(ctx: RuleContext):
        return ()

    rules = (RegisteredRule(id="C0", rule=clean, title="clean"),)
    assert run(rules, _ctx()) == 0


@pytest.mark.unit
def test_build_context_uses_git_ls_files(tmp_path):
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "a.sql").write_text("select 1\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.tmdl").write_text("table T\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)

    ctx = build_context(tmp_path)
    assert ctx.repo_root == tmp_path
    # POSIX-separated, repo-relative, regardless of OS.
    assert "a.sql" in ctx.tracked_files
    assert "sub/b.tmdl" in ctx.tracked_files


@pytest.mark.unit
def test_git_ls_files_returns_empty_on_not_a_repo(tmp_path):
    # A bare, non-git directory: git exits 128 -> () (the expected non-repo case).
    from retail.runner import _git_ls_files

    assert _git_ls_files(tmp_path) == ()


@pytest.mark.unit
def test_git_ls_files_raises_on_non_128_failure(monkeypatch, tmp_path):
    # Any non-zero exit OTHER than 128 (e.g. a broken/misconfigured git) must
    # fail LOUD with RuntimeError, never silently return () (vacuous green gate).
    import subprocess

    from retail import runner

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="fatal: something broke"
        )

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as exc_info:
        runner._git_ls_files(tmp_path)
    assert "git ls-files failed (exit 1)" in str(exc_info.value)
    assert "something broke" in str(exc_info.value)


@pytest.mark.unit
def test_importing_runner_does_not_import_rules_package():
    # The low-level runner must NOT depend on the rules package; the CLI
    # (composition root) owns `import retail.rules`. Importing the runner alone
    # must not pull in the rules package as a side effect.
    import importlib
    import sys

    # Drop any cached rules modules, then import runner in isolation.
    for name in list(sys.modules):
        if name == "retail.rules" or name.startswith("retail.rules."):
            del sys.modules[name]
    sys.modules.pop("retail.runner", None)

    importlib.import_module("retail.runner")

    assert "retail.rules" not in sys.modules
