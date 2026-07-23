from pathlib import Path

import pytest

from seshat.core import Finding, RegisteredRule, RuleContext, Severity
from seshat.runner import build_context, run, run_json


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
def test_run_json_emits_parseable_document_and_matches_findings(capsys):
    import json

    def bad(ctx: RuleContext):
        return [Finding("E1", Severity.ERROR, "boom", "f.sql:1")]

    def warn(ctx: RuleContext):
        return [Finding("W1", Severity.WARNING, "heads up", "f.sql:2")]

    rules = (
        RegisteredRule(id="E1", rule=bad, title="bad"),
        RegisteredRule(id="W1", rule=warn, title="warn"),
    )
    code = run_json(rules, _ctx())
    assert code == 1  # an ERROR is present

    doc = json.loads(capsys.readouterr().out)
    assert doc["exit_code"] == 1
    assert doc["findings"] == [
        {"rule_id": "E1", "severity": "error", "message": "boom", "locator": "f.sql:1"},
        {
            "rule_id": "W1",
            "severity": "warning",
            "message": "heads up",
            "locator": "f.sql:2",
        },
    ]


@pytest.mark.unit
def test_run_json_preserves_within_rule_finding_order(capsys):
    import json

    # A single rule yielding multiple findings -> JSON array keeps yield order.
    def multi(ctx: RuleContext):
        return [
            Finding("M1", Severity.INFO, "first", "f:1"),
            Finding("M1", Severity.ERROR, "second", "f:2"),
            Finding("M1", Severity.WARNING, "third", "f:3"),
        ]

    rules = (RegisteredRule(id="M1", rule=multi, title="multi"),)
    assert run_json(rules, _ctx()) == 1  # an ERROR is present
    doc = json.loads(capsys.readouterr().out)
    assert [f["message"] for f in doc["findings"]] == ["first", "second", "third"]


@pytest.mark.unit
def test_run_json_warning_only_exit_0_with_findings_present(capsys):
    import json

    # run and run_json agree on exit code, AND the JSON document lists the warning.
    def warn(ctx: RuleContext):
        return [Finding("W1", Severity.WARNING, "heads up", "f.sql:2")]

    rules = (RegisteredRule(id="W1", rule=warn, title="warn"),)
    text_code = run(rules, _ctx())
    capsys.readouterr()  # drain the text output
    json_code = run_json(rules, _ctx())
    doc = json.loads(capsys.readouterr().out)
    assert text_code == json_code == 0  # WARNING only -> 0
    assert doc == {
        "findings": [
            {
                "rule_id": "W1",
                "severity": "warning",
                "message": "heads up",
                "locator": "f.sql:2",
            }
        ],
        "exit_code": 0,
    }


@pytest.mark.unit
def test_run_json_empty_findings(capsys):
    import json

    def clean(ctx: RuleContext):
        return ()

    rules = (RegisteredRule(id="C0", rule=clean, title="clean"),)
    assert run_json(rules, _ctx()) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc == {"findings": [], "exit_code": 0}


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
    from seshat.runner import _git_ls_files

    assert _git_ls_files(tmp_path) == ()


@pytest.mark.unit
def test_git_ls_files_raises_on_non_128_failure(monkeypatch, tmp_path):
    # Any non-zero exit OTHER than 128 (e.g. a broken/misconfigured git) must
    # fail LOUD with RuntimeError, never silently return () (vacuous green gate).
    import subprocess

    from seshat import runner

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
    # (composition root) owns `import seshat.rules`. Importing the runner alone
    # must not pull in the rules package as a side effect.
    import importlib
    import sys

    # Drop any cached rules modules, then import runner in isolation.
    for name in list(sys.modules):
        if name == "seshat.rules" or name.startswith("seshat.rules."):
            del sys.modules[name]
    sys.modules.pop("seshat.runner", None)

    importlib.import_module("seshat.runner")

    assert "seshat.rules" not in sys.modules


@pytest.mark.unit
def test_check_does_not_crash_on_git_tracked_but_unstaged_deletions(tmp_path):
    """Issue #430: `seshat check` must not raise FileNotFoundError when a
    tracked file is deleted on disk but the deletion is not staged/committed
    (i.e. still listed by `git ls-files`).

    Covers one committed fixture per known content-scanning family (G3 TMDL/
    JSON scan, the S1-S8 SQL family, B1 never-execute, G6 PBIP parameter scan,
    R1 PBIR reference scan) AND the presence-required governance-manifest
    families (SC2 rule-count-claims + its count source, A3 route-registry + its
    knowledge map, DF1 parked-on, SC1 status-claims, DR1 stale-phrase manifest)
    whose membership guards otherwise pass while the direct manifest read raises
    FileNotFoundError (Codex #443 P1). Proven across every reader, not just the
    single rule the issue happened to reproduce with.
    """
    import seshat.rules  # noqa: F401  (side effect: registers the real rule set)
    from seshat.registry import all_rules
    from seshat.runner import collect_findings
    from tests.unit._gitfix import commit_all, make_git_repo

    repo = make_git_repo(tmp_path)

    fixtures = {
        "model.tmdl": "table Sales\n",
        "warehouse/migrations/0001_init.sql": "create table bronze.x (a text);\n",
        "src/seshat/rules/fake_governed.py": "x = 1\n",
        "demo.SemanticModel/definition/expressions.tmdl": (
            'expression Host = "<your-db-host>" meta [IsParameterQuery=true];\n'
        ),
        "demo.Report/definition.pbir": (
            '{"datasetReference": {"byPath": {"path": "../demo.SemanticModel"}}}\n'
        ),
        # Presence-required governance manifests (+ their referenced sources): each
        # rule guards `path in tracked_files` then reads directly, so a tracked-but-
        # deleted manifest crashes the read unless routed through read_tracked_text.
        "docs/quality/rule-count-claims.yaml": "claims: []\n",  # SC2 manifest
        "docs/rules/rules-manifest.json": "[]\n",  # SC2 count source
        "docs/routing/routes.yaml": "routes: []\n",  # A3 manifest
        "docs/knowledge-map.md": "# Map\n\n## Route by task\n\n| Task |\n|---|\n",
        "docs/quality/parked-on.yaml": "edges: []\n",  # DF1 manifest
        "docs/quality/status-claims.yaml": "claims: []\n",  # SC1 manifest
        "docs/quality/design-stale-phrases.yaml": "phrases: []\n",  # DR1 manifest
    }
    for rel, body in fixtures.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    commit_all(repo, "chore: add fixtures")

    # Delete on disk WITHOUT `git rm` -- tracked-but-unstaged deletion, exactly
    # the scenario reported in #430.
    for rel in fixtures:
        (repo / rel).unlink()

    ctx = build_context(repo)
    for rel in fixtures:
        assert rel in ctx.tracked_files  # still enumerated (needed by AL1/AL2/HR11)

    # Must not raise -- this is the crash the issue reports.
    findings = collect_findings(all_rules(), ctx)
    assert isinstance(findings, list)
