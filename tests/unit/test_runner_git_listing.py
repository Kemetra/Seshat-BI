"""The check runner's tracked-file corpus and per-rule failure handling.

Covers: non-ASCII tracked paths (git quotePath), exit-128 causes other than
"not a repository", git timeouts, case-insensitive ``.sql`` selection with a
census that agrees on every OS, non-UTF-8 tracked files, and one rule's crash
never hiding the others.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from seshat import cli, runner
from seshat.core import Finding, RegisteredRule, RuleContext, Severity
from seshat.rules.git_meta import _sql_placement_finding
from seshat.sql import WAREHOUSE_SQL_CORPUS, iter_sql_files
from tests.unit._gitfix import commit_all, make_git_repo

pytestmark = pytest.mark.unit


def _repo_with(tmp_path: Path, files: dict[str, bytes]) -> Path:
    repo = make_git_repo(tmp_path)
    for rel, data in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    commit_all(repo, "seed")
    return repo


# --------------------------------------------------------------------------
# F003 -- non-ASCII tracked paths reach the rules verbatim
# --------------------------------------------------------------------------


def test_non_ascii_tracked_path_is_listed_verbatim(tmp_path: Path) -> None:
    repo = _repo_with(
        tmp_path, {"sql/café.sql": b"select 1;\n", "sql/plain.sql": b"select 1;\n"}
    )

    tracked = runner._git_ls_files(repo)

    assert "sql/café.sql" in tracked
    flagged = {
        f.locator for p in tracked if (f := _sql_placement_finding(p)) is not None
    }
    assert flagged == {"sql/café.sql", "sql/plain.sql"}


def test_non_ascii_untracked_fallback_is_listed_verbatim(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    (repo / "mappings" / "مبيعات").mkdir(parents=True)
    (repo / "mappings" / "مبيعات" / "source-map.yaml").write_text("x: 1\n")

    assert "mappings/مبيعات/source-map.yaml" in runner._git_ls_files(repo)


# --------------------------------------------------------------------------
# F004 -- exit 128 is "not a repository" ONLY when it is not one
# --------------------------------------------------------------------------


def test_corrupt_index_fails_loud_not_empty(tmp_path: Path) -> None:
    repo = _repo_with(tmp_path, {"sql/bad.sql": b"select 1;\n"})
    index = repo / ".git" / "index"
    index.write_bytes(index.read_bytes()[:20])

    with pytest.raises(RuntimeError, match="ls-files"):
        runner._git_ls_files(repo)


def test_real_non_repository_is_still_empty(tmp_path: Path) -> None:
    assert runner._git_ls_files(tmp_path) == ()


def test_listing_pins_safe_directory(monkeypatch, tmp_path: Path) -> None:
    seen: list[list[str]] = []

    def fake_run(args, **kwargs):
        seen.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="a.sql\0", stderr="")

    monkeypatch.setattr(runner, "run_subprocess", fake_run)
    assert runner._git_ls_files(tmp_path) == ("a.sql",)
    assert any(arg.startswith("safe.directory=") for arg in seen[0])
    assert "-z" in seen[0]


# --------------------------------------------------------------------------
# F147 -- a git timeout is a clean error, never a traceback
# --------------------------------------------------------------------------


def _timeout(args, **kwargs):
    raise subprocess.TimeoutExpired(cmd=args, timeout=120)


def test_git_timeout_becomes_runtime_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(runner, "run_subprocess", _timeout)
    with pytest.raises(RuntimeError, match="timed out"):
        runner._git_ls_files(tmp_path)


@pytest.mark.parametrize("verb", ["check", "doctor"])
def test_git_timeout_is_a_clean_cli_error(
    monkeypatch, capsys, tmp_path: Path, verb: str
) -> None:
    monkeypatch.setattr(runner, "run_subprocess", _timeout)
    code = cli.main([verb, "--repo", str(tmp_path)])
    assert code != 0
    err = capsys.readouterr().err
    assert "timed out" in err and "Traceback" not in err


def test_subprocess_error_is_a_clean_check_error(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    def broken(ctx_root):
        raise subprocess.SubprocessError("pipe closed")

    monkeypatch.setattr(cli, "build_context", lambda *a, **k: broken(a))
    assert cli.main(["check", "--repo", str(tmp_path)]) == 1
    assert "pipe closed" in capsys.readouterr().err


# --------------------------------------------------------------------------
# F055 -- upper-case .SQL is selected, and the census agrees on every OS
# --------------------------------------------------------------------------


def test_upper_case_sql_is_iterated_and_placed(tmp_path: Path) -> None:
    ctx = RuleContext(
        repo_root=tmp_path,
        tracked_files=("warehouse/migrations/0001_drop.SQL", "sql/x.SQL"),
    )
    assert iter_sql_files(ctx) == ["warehouse/migrations/0001_drop.SQL"]
    assert _sql_placement_finding("sql/x.SQL") is not None


def test_census_matches_the_iterator_case_exactly() -> None:
    upper = ("warehouse/migrations/0001_drop.SQL",)
    assert runner._corpus_empty(upper, WAREHOUSE_SQL_CORPUS) is False
    # fnmatch normcases on Windows; the census must not: a directory spelled
    # differently from the pattern is not what the rules iterate.
    assert runner._corpus_empty(("WAREHOUSE/a.sql",), WAREHOUSE_SQL_CORPUS) is True


# --------------------------------------------------------------------------
# F043 / F157 -- unreadable input and rule crashes become structured findings
# --------------------------------------------------------------------------


def test_utf16_tracked_sql_yields_an_error_finding_and_valid_json(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    repo = _repo_with(
        tmp_path,
        {"warehouse/silver/vw_x.sql": "select 1;\n".encode("utf-16")},
    )
    monkeypatch.chdir(tmp_path)

    code = cli.main(["check", "--repo", str(repo), "--format", "json"])

    doc = json.loads(capsys.readouterr().out)
    assert code == 1
    unreadable = [
        f
        for f in doc["findings"]
        if f["locator"] == "warehouse/silver/vw_x.sql" and "UTF-8" in f["message"]
    ]
    assert unreadable and all(f["severity"] == "error" for f in unreadable)


def test_one_crashing_rule_does_not_hide_the_others(tmp_path: Path) -> None:
    def crashes(ctx: RuleContext):
        raise ValueError("boom")

    def speaks(ctx: RuleContext):
        return [Finding("OK1", Severity.WARNING, "still here", "x")]

    rules = (
        RegisteredRule(id="BAD1", rule=crashes, title="crashes"),
        RegisteredRule(id="OK1", rule=speaks, title="speaks"),
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=())

    findings = runner.collect_findings(rules, ctx)

    assert [f.rule_id for f in findings] == ["BAD1", "OK1"]
    assert findings[0].severity is Severity.ERROR
    assert "ValueError" in findings[0].message


def test_read_tracked_text_skips_a_directory(tmp_path: Path) -> None:
    from seshat.core import read_tracked_text

    (tmp_path / "submodule").mkdir()
    assert read_tracked_text(tmp_path / "submodule") is None


def test_malformed_pbir_is_an_r1_finding(tmp_path: Path) -> None:
    from seshat.rules.pbir import check_pbir_relative_reference

    rel = "powerbi/X.Report/definition.pbir"
    (tmp_path / "powerbi" / "X.Report").mkdir(parents=True)
    (tmp_path / rel).write_text('{"datasetReference": {},}', encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))

    findings = list(check_pbir_relative_reference(ctx))

    assert [f.rule_id for f in findings] == ["R1"]
    assert findings[0].severity is Severity.ERROR


def test_non_utf8_commit_message_file_is_a_clean_error(tmp_path: Path, capsys) -> None:
    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_bytes("fix: caf\xe9\n".encode("cp1252"))
    code = cli.main(["check", "--repo", str(tmp_path), "--commit-msg-file", str(msg)])
    assert code == 1
    err = capsys.readouterr().err
    assert "commit message file" in err and "Traceback" not in err


@pytest.mark.parametrize(
    "module_name, rule_name",
    [
        ("design_contrast", "check_contrast"),
        ("design_ramp_deltae", None),
        ("design_categorical_distinctness", None),
    ],
)
def test_cp1252_design_tokens_are_a_finding_not_a_crash(
    tmp_path: Path, module_name: str, rule_name: str | None
) -> None:
    import importlib

    module = importlib.import_module(f"seshat.rules.{module_name}")
    rel = "design/brand-design-tokens.yaml"
    (tmp_path / "design").mkdir()
    (tmp_path / rel).write_bytes("name: caf\xe9\n".encode("cp1252"))

    doc, err = module._load_yaml(tmp_path / rel)

    assert doc is None and err == "UnicodeDecodeError"
    if rule_name is not None:
        ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
        findings = list(getattr(module, rule_name)(ctx))
        assert [f.severity for f in findings] == [Severity.ERROR]
