"""M1.7: mode-aware build_context + the two new CLI flags."""

import subprocess
import sys
from pathlib import Path

import pytest

from retail.cli import _build_parser
from retail.runner import build_context
from tests.unit._gitfix import make_git_repo

pytestmark = pytest.mark.unit


def test_python_m_invokes_main_not_a_noop() -> None:
    """`python -m retail.cli` MUST run main(), not exit 0 as a silent no-op.

    Regression guard (2026-06-25 defect): without an `if __name__ == "__main__"`
    block the module imported and exited 0 without running, so `python -m retail.cli
    validate` looked like a pass while doing nothing. With the guard, a missing
    subcommand reaches argparse (required=True) and exits 2 -- proof main() ran.
    """
    repo_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "-m", "retail.cli"],
        cwd=repo_root / "src",
        capture_output=True,
        text=True,
    )
    # argparse with required subparser -> exit 2 (NOT the old silent 0 no-op).
    assert proc.returncode == 2, (
        f"python -m retail.cli should run main() and exit 2 on no subcommand, "
        f"got {proc.returncode} (stdout={proc.stdout!r} stderr={proc.stderr!r})"
    )


def test_build_context_defaults_both_none(tmp_path: Path) -> None:
    ctx = build_context(tmp_path)
    # Only the two v2 fields are asserted here — tracked_files behavior on a
    # tmp dir is out of scope for this test.
    assert ctx.commit_range is None
    assert ctx.commit_message is None


def test_build_context_populates_v2_fields(tmp_path: Path) -> None:
    ctx = build_context(
        tmp_path,
        commit_range="origin/main..HEAD",
        commit_message="feat: a thing",
    )
    assert ctx.commit_range == "origin/main..HEAD"
    assert ctx.commit_message == "feat: a thing"


def test_parser_default_flags_are_none() -> None:
    # The commit-aware flags live under the `check` subcommand.
    ns = _build_parser().parse_args(["check"])
    assert ns.commit_range is None
    assert ns.commit_msg_file is None
    assert ns.repo == "."  # M1.5's --repo is retained with its default


def test_parser_commit_range_flag() -> None:
    ns = _build_parser().parse_args(["check", "--commit-range", "origin/main..HEAD"])
    assert ns.commit_range == "origin/main..HEAD"


def test_parser_commit_msg_file_flag() -> None:
    ns = _build_parser().parse_args(["check", "--commit-msg-file", "/tmp/MSG"])
    assert ns.commit_msg_file == "/tmp/MSG"


def test_main_commit_msg_file_is_read_and_stripped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # git writes COMMIT_EDITMSG with a trailing newline; main must strip it.
    msg_file = tmp_path / "COMMIT_EDITMSG"
    msg_file.write_text("feat: real message\n", encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_build_context(repo_root, commit_range=None, commit_message=None):
        captured["commit_range"] = commit_range
        captured["commit_message"] = commit_message
        from retail.core import RuleContext

        return RuleContext(
            repo_root=repo_root,
            tracked_files=(),
            commit_range=commit_range,
            commit_message=commit_message,
        )

    # Patch where cli looks it up, and stub run so no rules execute.
    monkeypatch.setattr("retail.cli.build_context", fake_build_context)
    monkeypatch.setattr("retail.cli.run", lambda rules, ctx: 0)

    rc = main_under_test(["check", "--commit-msg-file", str(msg_file)])

    assert rc == 0
    assert captured["commit_message"] == "feat: real message"
    assert captured["commit_range"] is None


def test_main_commit_range_flag_threads_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_build_context(repo_root, commit_range=None, commit_message=None):
        captured["commit_range"] = commit_range
        captured["commit_message"] = commit_message
        from retail.core import RuleContext

        return RuleContext(repo_root=repo_root, tracked_files=())

    monkeypatch.setattr("retail.cli.build_context", fake_build_context)
    monkeypatch.setattr("retail.cli.run", lambda rules, ctx: 0)

    rc = main_under_test(["check", "--commit-range", "origin/main..HEAD"])

    assert rc == 0
    assert captured["commit_range"] == "origin/main..HEAD"
    assert captured["commit_message"] is None


def test_main_commit_msg_file_strips_crlf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # On Windows, COMMIT_EDITMSG can end in \r\n — rstrip must drop both, not
    # leave a trailing \r on the message.
    msg_file = tmp_path / "COMMIT_EDITMSG"
    msg_file.write_bytes(b"feat: windows line ending\r\n")

    captured: dict[str, object] = {}

    def fake_build_context(repo_root, commit_range=None, commit_message=None):
        captured["commit_message"] = commit_message
        from retail.core import RuleContext

        return RuleContext(repo_root=repo_root, tracked_files=())

    monkeypatch.setattr("retail.cli.build_context", fake_build_context)
    monkeypatch.setattr("retail.cli.run", lambda rules, ctx: 0)

    rc = main_under_test(["check", "--commit-msg-file", str(msg_file)])

    assert rc == 0
    assert captured["commit_message"] == "feat: windows line ending"


def test_main_missing_commit_msg_file_exits_1_with_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # A nonexistent --commit-msg-file must exit 1 with a readable message, not a
    # raw FileNotFoundError traceback.
    missing = tmp_path / "does-not-exist"
    monkeypatch.setattr("retail.cli.run", lambda rules, ctx: 0)

    with pytest.raises(SystemExit) as exc_info:
        main_under_test(["check", "--commit-msg-file", str(missing)])

    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "commit message file not found" in err
    assert str(missing) in err


# Imported at module scope after monkeypatch targets above are defined; aliased
# so the patch sites (retail.cli.build_context / retail.cli.run) are the ones
# main() actually calls.
from retail.cli import main as main_under_test  # noqa: E402, I001


# ---------------------------------------------------------------------------
# M6 follow-up: end-to-end --commit-range -> git path (P2).
# This integration path (CLI flag -> build_context -> P2 -> git log) was never
# tested before; the verbatim-range bug ("base..HEAD..HEAD") survived because
# no test drove the actual flag through to git.
# ---------------------------------------------------------------------------


def _commit(repo: Path, message: str) -> None:
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", message],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _rev_parse(repo: Path, ref: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", ref],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_main_commit_range_e2e_flags_bad_subject_in_range(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Real repo, real CLI flag, real git: a bad subject inside the supplied
    # VERBATIM range must be flagged by P2 (non-zero exit), and the verbatim
    # range must not be mangled into "<base>..HEAD..HEAD" (git error 128).
    repo = make_git_repo(tmp_path)
    _commit(repo, "feat: base")
    base = _rev_parse(repo, "HEAD")
    _commit(repo, "fix: good change")
    _commit(repo, "bad subject here")

    rc = main_under_test(
        ["check", "--repo", str(repo), "--commit-range", f"{base}..HEAD"]
    )
    out = capsys.readouterr().out

    assert rc == 1  # the bad subject makes P2 an ERROR -> non-zero exit
    assert "P2" in out
    assert "bad subject here" in out


def test_main_commit_range_e2e_good_range_no_p2_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A range whose every subject conforms yields no P2 finding for those
    # subjects (proving P2 scans exactly the supplied range, verbatim).
    repo = make_git_repo(tmp_path)
    _commit(repo, "feat: base")
    base = _rev_parse(repo, "HEAD")
    _commit(repo, "fix: good change one")
    _commit(repo, "docs: good change two")

    main_under_test(["check", "--repo", str(repo), "--commit-range", f"{base}..HEAD"])
    out = capsys.readouterr().out

    # No P2 finding should mention these conforming subjects.
    assert "fix: good change one" not in out
    assert "docs: good change two" not in out


def test_main_commit_range_e2e_malformed_range_no_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A malformed range must surface as a clean P2 ERROR finding, never a
    # RuntimeError traceback escaping to the user.
    repo = make_git_repo(tmp_path)
    _commit(repo, "feat: base")

    bad_range = "no-such-ref-aaa..no-such-ref-bbb"
    rc = main_under_test(["check", "--repo", str(repo), "--commit-range", bad_range])
    out = capsys.readouterr().out

    assert rc == 1
    assert "P2" in out
    assert bad_range in out
    assert "Traceback" not in out


# ---------------------------------------------------------------------------
# validate --source-map: the live-run wiring (one command from creds). The DB
# connection is monkeypatched so no real DB is touched.
# ---------------------------------------------------------------------------


def test_parser_validate_has_source_map_flag() -> None:
    ns = _build_parser().parse_args(
        ["validate", "--source-map", "mappings/x/source-map.yaml"]
    )
    assert ns.source_map == "mappings/x/source-map.yaml"


def test_validate_no_source_map_stays_deferred(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # With a DSN + driver but NO --source-map, the handler keeps the deferred
    # message (no targets to run) and returns 1.
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/db")
    monkeypatch.setattr("retail.cli._ensure_driver", lambda: True)
    rc = main_under_test(["validate"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "deferred" in err.lower()


def test_validate_with_source_map_runs_live_checks(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # DSN present + driver present + a --source-map -> the handler loads targets,
    # builds a runner (monkeypatched fake), runs the checks, prints findings, and
    # returns 0 when clean. No real DB is touched.
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/db")
    monkeypatch.setattr("retail.cli._ensure_driver", lambda: True)

    from retail.validate import (
        DateCoverageTarget,
        OrphanTarget,
        PkTarget,
        ReconcileTarget,
        ValidationTargets,
    )

    fake_targets = ValidationTargets(
        pk=PkTarget(table="silver.t", pk_columns=("a",)),
        date_coverage=DateCoverageTarget(
            fact="gold.f",
            fact_date="date_sk",
            date_dim="gold.dim_date",
            dim_date="date_sk",
        ),
        orphans=OrphanTarget(fact="gold.f", fks=()),
        reconcile=ReconcileTarget(silver="silver.t", gold="gold.f", measures=()),
    )
    monkeypatch.setattr("retail.cli._load_targets", lambda path: fake_targets)

    captured_sql: list[str] = []

    class FakeRunner:
        def run(self, sql, params=()):
            captured_sql.append(sql)
            # pk: (count, distinct, null) all clean; coverage: 0 missing
            if "DISTINCT (a)" in sql or "count(DISTINCT" in sql:
                return [(5, 5, 0)]
            return [(0,)]

    monkeypatch.setattr("retail.cli._make_runner", lambda dsn: FakeRunner())

    rc = main_under_test(["validate", "--source-map", "mappings/t/source-map.yaml"])
    assert rc == 0  # all checks clean
    assert captured_sql  # the runner was actually exercised


def test_validate_source_map_no_creds_errors_clearly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # --source-map but NO DSN -> clear actionable error, return 1, never a connect.
    for var in ("DATABASE_URL", "ANALYTICS_DB_HOST"):
        monkeypatch.delenv(var, raising=False)

    def _boom(dsn):  # pragma: no cover - must never be called
        raise AssertionError("must not build a runner without creds")

    monkeypatch.setattr("retail.cli._make_runner", _boom)
    rc = main_under_test(["validate", "--source-map", "mappings/t/source-map.yaml"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "no database connection" in err.lower()
