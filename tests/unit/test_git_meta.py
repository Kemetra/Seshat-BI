from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path

import pytest

from seshat import gitutil
from seshat.core import RuleContext, Severity
from seshat.rules.git_meta import (
    _read_leading_bytes,
    _scan_contents,
    _scan_line_for_secret,
    check_gitattributes_eol,
    rule_c2_no_committed_secrets,
    rule_g1_gitignore_correctness,
    rule_g2_definition_committed,
    rule_g3_no_bom,
    rule_g5_path_length,
    rule_p1_layout,
    rule_p2_commit_subjects,
)
from tests.unit._gitfix import commit_all, context_for, make_git_repo

# ---------------------------------------------------------------------------
# Shared local helpers — call-coupled by the tests below so the file reads as a
# single cohesive git-metadata suite rather than isolated fragments.
# ---------------------------------------------------------------------------


def _empty_commit(repo: Path, message: str) -> None:
    """Record an empty commit with the given subject."""
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", message],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _head_sha(repo: Path) -> str:
    """Return the current HEAD commit sha."""
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _ctx_with(repo: Path, **overrides: object) -> RuleContext:
    """context_for(repo) with the given RuleContext fields replaced."""
    return dataclasses.replace(context_for(repo), **overrides)


def _findings(rule, ctx: RuleContext) -> list:
    """Materialize a rule's findings for a context (rules yield generators)."""
    return list(rule(ctx))


def _secret_hit(line: str) -> bool:
    """Whether the C2 line scanner flags a single line as a secret."""
    return _scan_line_for_secret(line)


def _gitignore_repo(tmp_path: Path, content: str) -> Path:
    """A fresh git repo whose .gitignore holds the given content."""
    repo = make_git_repo(tmp_path)
    (repo / ".gitignore").write_text(content, encoding="utf-8")
    return repo


# ---------------------------------------------------------------------------
# M2.1 — gitutil
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_git_check_ignore_respects_gitignore(tmp_path: Path) -> None:
    repo = _gitignore_repo(tmp_path, ".env\n")
    (repo / ".env").write_text("SECRET=x\n", encoding="utf-8")
    (repo / "keep.txt").write_text("ok\n", encoding="utf-8")
    assert gitutil.git_check_ignore(repo, ".env") is True
    assert gitutil.git_check_ignore(repo, "keep.txt") is False


# ---------------------------------------------------------------------------
# M2.2 — G5
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_g5_flags_long_path() -> None:
    long_path = "warehouse/migrations/" + ("x" * 201) + ".sql"
    assert len(long_path) > 200
    ctx = RuleContext(repo_root=Path("."), tracked_files=(long_path, "ok.sql"))
    findings = _findings(rule_g5_path_length, ctx)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "G5"
    assert f.severity is Severity.ERROR
    assert f.locator == long_path


@pytest.mark.unit
def test_g5_passes_short_paths() -> None:
    ctx = RuleContext(repo_root=Path("."), tracked_files=("warehouse/x.sql",))
    assert _findings(rule_g5_path_length, ctx) == []


# ---------------------------------------------------------------------------
# M2.3 — P1
# ---------------------------------------------------------------------------

GOOD_LAYOUT = (
    "README.md",
    "warehouse/README.md",
    "powerbi/README.md",
    "warehouse/migrations/0001_init.sql",
    "powerbi/Sales.pbip",
)


@pytest.mark.unit
def test_p1_accepts_good_layout() -> None:
    ctx = RuleContext(repo_root=Path("."), tracked_files=GOOD_LAYOUT)
    assert _findings(rule_p1_layout, ctx) == []


@pytest.mark.unit
def test_p1_flags_misplaced_sql_and_pbip() -> None:
    tracked = GOOD_LAYOUT + ("scripts/adhoc.sql", "reports/Sales.pbip")
    ctx = RuleContext(repo_root=Path("."), tracked_files=tracked)
    ids = {f.locator for f in _findings(rule_p1_layout, ctx)}
    assert "scripts/adhoc.sql" in ids
    assert "reports/Sales.pbip" in ids


@pytest.mark.unit
def test_p1_flags_missing_required_dir() -> None:
    tracked = ("README.md", "warehouse/README.md")  # no powerbi/README.md
    ctx = RuleContext(repo_root=Path("."), tracked_files=tracked)
    findings = _findings(rule_p1_layout, ctx)
    assert any(f.locator == "powerbi/README.md" for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)


@pytest.mark.unit
def test_p1_exempts_pbip_under_tests() -> None:
    # A committed test fixture .pbip under tests/ is NOT the live model -> skipped.
    tracked = GOOD_LAYOUT + ("tests/fixtures/golden_pbip/RetailGold.pbip",)
    ctx = RuleContext(repo_root=Path("."), tracked_files=tracked)
    locators = {f.locator for f in _findings(rule_p1_layout, ctx)}
    assert "tests/fixtures/golden_pbip/RetailGold.pbip" not in locators


@pytest.mark.unit
def test_p1_still_flags_pbip_outside_powerbi_and_tests() -> None:
    # A .pbip outside both powerbi/ and tests/ IS still flagged.
    tracked = GOOD_LAYOUT + ("reports/Sales.pbip",)
    ctx = RuleContext(repo_root=Path("."), tracked_files=tracked)
    locators = {f.locator for f in _findings(rule_p1_layout, ctx)}
    assert "reports/Sales.pbip" in locators


@pytest.mark.unit
def test_p1_exempts_sql_under_tests() -> None:
    # A .sql under tests/ is NOT forced under warehouse/ -> skipped.
    tracked = GOOD_LAYOUT + ("tests/fixtures/seed.sql",)
    ctx = RuleContext(repo_root=Path("."), tracked_files=tracked)
    locators = {f.locator for f in _findings(rule_p1_layout, ctx)}
    assert "tests/fixtures/seed.sql" not in locators


@pytest.mark.unit
def test_p1_still_flags_sql_outside_warehouse_and_tests() -> None:
    # A .sql outside both warehouse/ and tests/ IS still flagged.
    tracked = GOOD_LAYOUT + ("scripts/adhoc.sql",)
    ctx = RuleContext(repo_root=Path("."), tracked_files=tracked)
    locators = {f.locator for f in _findings(rule_p1_layout, ctx)}
    assert "scripts/adhoc.sql" in locators


# ---------------------------------------------------------------------------
# M2.4 — G1
# ---------------------------------------------------------------------------

GOOD_GITIGNORE = (
    "**/.pbi/localSettings.json\n"
    "**/.pbi/cache.abf\n"
    ".env\n"
    "__pycache__/\n"  # extra entry — permitted
)


@pytest.mark.unit
def test_g1_accepts_correct_gitignore(tmp_path: Path) -> None:
    repo = _gitignore_repo(tmp_path, GOOD_GITIGNORE)
    commit_all(repo, "chore: add gitignore")
    assert _findings(rule_g1_gitignore_correctness, context_for(repo)) == []


@pytest.mark.unit
def test_g1_flags_missing_required_entry(tmp_path: Path) -> None:
    repo = _gitignore_repo(tmp_path, "**/.pbi/cache.abf\n.env\n")
    commit_all(repo, "chore: add gitignore")
    findings = _findings(rule_g1_gitignore_correctness, context_for(repo))
    assert any("localSettings.json" in f.message for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)


@pytest.mark.unit
def test_g1_flags_ignored_definition_path(tmp_path: Path) -> None:
    repo = _gitignore_repo(tmp_path, GOOD_GITIGNORE + "definition/\n")
    commit_all(repo, "chore: add gitignore")
    findings = _findings(rule_g1_gitignore_correctness, context_for(repo))
    assert any("definition" in f.locator for f in findings)


# ---------------------------------------------------------------------------
# M2.5 — G2
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_g2_clean_pbip_passes(tmp_path: Path) -> None:
    """#19: a PBIP repo with no forbidden tracked paths produces NO G2 findings.

    A clean PBIP has definition/ committed (model.tmdl present) and the Desktop-local
    cache files (.pbi/cache.abf, .pbi/localSettings.json) are NOT tracked.
    G2 must return an empty findings list (not the INFO branch, not an ERROR).
    """
    # Use a .gitignore that covers the forbidden paths so git_check_ignore won't fire.
    repo = _gitignore_repo(tmp_path, GOOD_GITIGNORE)
    pbip_dir = repo / "powerbi" / "Sales.SemanticModel" / "definition"
    pbip_dir.mkdir(parents=True)
    (pbip_dir / "model.tmdl").write_text("model\n", encoding="utf-8")
    (repo / "powerbi" / "Sales.pbip").write_text("{}\n", encoding="utf-8")
    # No .pbi/cache.abf or .pbi/localSettings.json is committed.
    commit_all(repo, "feat: clean pbip")
    findings = _findings(rule_g2_definition_committed, context_for(repo))
    # Not the INFO branch (real PBIP is present) and no ERROR (no forbidden files).
    assert findings == [], f"expected no G2 findings on a clean PBIP, got: {findings}"


@pytest.mark.unit
def test_g2_emits_info_when_no_pbip(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    (repo / "README.md").write_text("hi\n", encoding="utf-8")
    commit_all(repo, "docs: readme")
    findings = _findings(rule_g2_definition_committed, context_for(repo))
    assert len(findings) == 1
    assert findings[0].severity is Severity.INFO
    assert findings[0].message == "no PBIP project present"


@pytest.mark.unit
def test_g2_flags_tracked_cache_abf(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    pbip_dir = repo / "powerbi" / "Sales.SemanticModel" / "definition"
    pbip_dir.mkdir(parents=True)
    (pbip_dir / "model.tmdl").write_text("model\n", encoding="utf-8")
    (repo / "powerbi" / "Sales.pbip").write_text("{}\n", encoding="utf-8")
    pbi_dir = repo / "powerbi" / "Sales.SemanticModel" / ".pbi"
    pbi_dir.mkdir(parents=True)
    (pbi_dir / "cache.abf").write_text("x\n", encoding="utf-8")
    commit_all(repo, "feat: add pbip with stray cache")
    findings = _findings(rule_g2_definition_committed, context_for(repo))
    assert any(
        "cache.abf" in f.locator and f.severity is Severity.ERROR for f in findings
    )


# ---------------------------------------------------------------------------
# M2.6 — P2
# ---------------------------------------------------------------------------


def _build_p2_history(repo: Path) -> str:
    _empty_commit(repo, "feat: base")
    base = _head_sha(repo)
    _empty_commit(repo, "fix: ok change")
    _empty_commit(repo, "bad subject here")
    return base


@pytest.mark.unit
def test_p2_flags_bad_subject(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    base = _build_p2_history(repo)
    # CI mode: --commit-range is a VERBATIM revision range (contract v2),
    # e.g. "origin/main..HEAD"; here "<base-sha>..HEAD".
    ctx = _ctx_with(repo, commit_range=f"{base}..HEAD")
    findings = _findings(rule_p2_commit_subjects, ctx)
    assert len(findings) == 1
    assert findings[0].rule_id == "P2"
    assert findings[0].locator == "bad subject here"
    assert findings[0].severity is Severity.ERROR


@pytest.mark.unit
def test_p2_local_fallback_scopes_to_current_commit_only(tmp_path: Path) -> None:
    """Bare `retail check` (no --commit-range, no commit-msg) scans only the
    current/incoming commit via DEFAULT_RANGE, so an aged-out non-conforming
    subject one commit back does NOT trip the local gate (#112). Locks Option A:
    a future widening of DEFAULT_RANGE back to a multi-commit window fails here."""
    repo = make_git_repo(tmp_path)
    # HEAD~1 is non-conforming; HEAD is compliant. This mirrors the real repo,
    # where a historical scoped subject sat behind a clean current commit.
    _empty_commit(repo, "feat(046): scoped historical subject")
    _empty_commit(repo, "feat: current compliant change")
    # Bare-fallback mode: neither commit_range nor commit_message is supplied, so
    # rule_p2 falls back to DEFAULT_RANGE (HEAD~1..HEAD) -> only the compliant tip.
    ctx = _ctx_with(repo, commit_range=None, commit_message=None)
    assert _findings(rule_p2_commit_subjects, ctx) == []


@pytest.mark.unit
def test_p2_validates_single_commit_message(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    # commit-msg-hook mode: a single incoming subject via ctx.commit_message.
    ctx = _ctx_with(repo, commit_message="bad subject here")
    findings = _findings(rule_p2_commit_subjects, ctx)
    assert len(findings) == 1
    assert findings[0].locator == "bad subject here"
    # A conforming message yields no findings.
    ok = _ctx_with(repo, commit_message="feat: a thing")
    assert _findings(rule_p2_commit_subjects, ok) == []


@pytest.mark.unit
def test_p2_accepts_extended_types_bot_prefix_and_rejects_scopes(
    tmp_path: Path,
) -> None:
    """P2 accepts extended types + optional [bot] prefix; still rejects scopes."""
    repo = make_git_repo(tmp_path)

    def findings_for(subject: str) -> list:
        ctx = _ctx_with(repo, commit_message=subject)
        return _findings(rule_p2_commit_subjects, ctx)

    # Newly-allowed: conventional types, the project `brand` type, and an
    # optional automation prefix carried by squash merges of bot PRs.
    accepted = [
        "brand: add seven-point Seshat star svg",
        "[codex] harden live sql validation (#26)",
        "build: pin python 3.13",
        "ci: scope P2 to the branch range",
        "perf: prefilter the secret scan",
        "test: cover the extended P2 types",
        "style: format with ruff",
        "revert: undo the bad migration",
        "[bot] chore: bump deps",
    ]
    for subject in accepted:
        assert findings_for(subject) == [], f"expected accepted: {subject!r}"

    # Still rejected: a parenthesized scope (P2 is deliberately scope-free) and
    # an unknown type. The no-scope discipline must survive the type widening.
    for subject in ("docs(018): scoped subject", "wip: not a type", "no type at all"):
        assert len(findings_for(subject)) == 1, f"expected rejected: {subject!r}"
        assert findings_for(subject)[0].rule_id == "P2"


@pytest.mark.unit
def test_p2_exempts_merge_commits(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    _empty_commit(repo, "feat: base")
    base = _head_sha(repo)
    subprocess.run(
        ["git", "checkout", "-b", "side"], cwd=repo, check=True, capture_output=True
    )
    _empty_commit(repo, "feat: side work")
    subprocess.run(
        ["git", "checkout", "main"], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "merge", "--no-ff", "side", "-m", "Merge branch 'side'"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    ctx = _ctx_with(repo, commit_range=f"{base}..HEAD")
    assert _findings(rule_p2_commit_subjects, ctx) == []


# ---------------------------------------------------------------------------
# M2.7 — C2
# ---------------------------------------------------------------------------

GOOD_ENV_EXAMPLE = (
    "ANALYTICS_DB_HOST=\n"
    "ANALYTICS_DB_PORT=25060\n"
    "ANALYTICS_DB_NAME=\n"
    "ANALYTICS_DB_USER=\n"
    "ANALYTICS_DB_PASSWORD=\n"
    "ANALYTICS_DB_SSLMODE=require\n"
)


def _seed_c2_repo(tmp_path: Path) -> Path:
    """A repo with .env ignored and a clean .env.example -- the C2 baseline."""
    repo = _gitignore_repo(tmp_path, ".env\n")
    (repo / ".env.example").write_text(GOOD_ENV_EXAMPLE, encoding="utf-8")
    return repo


@pytest.mark.unit
def test_c2_clean_repo_passes(tmp_path: Path) -> None:
    repo = _seed_c2_repo(tmp_path)
    commit_all(repo, "chore: seed env example")
    assert _findings(rule_c2_no_committed_secrets, context_for(repo)) == []


@pytest.mark.unit
def test_c2_flags_real_endpoint_in_scanned_file(tmp_path: Path) -> None:
    repo = _seed_c2_repo(tmp_path)
    (repo / "config.txt").write_text(
        "host = db-prod-01.db.ondigitalocean.com\n", encoding="utf-8"
    )
    commit_all(repo, "chore: add config")
    findings = _findings(rule_c2_no_committed_secrets, context_for(repo))
    assert any(f.locator.startswith("config.txt:") for f in findings)


@pytest.mark.unit
def test_c2_ignores_angle_bracket_placeholder_in_scanned_file(tmp_path: Path) -> None:
    repo = _seed_c2_repo(tmp_path)
    # ROOT-level scanned file (not docs/, not *.example) — exercises the REGEX
    # exclusion, not the path exclusion.
    (repo / "config.txt").write_text(
        "host = <your-db-host>.db.ondigitalocean.com\n", encoding="utf-8"
    )
    commit_all(repo, "chore: add placeholder config")
    assert _findings(rule_c2_no_committed_secrets, context_for(repo)) == []


@pytest.mark.unit
def test_c2_skips_superpowers_scratch_and_example_files(tmp_path: Path) -> None:
    """docs/superpowers/ (SDD scratch that quotes fixture DSNs) and *.example are
    excluded from the content scan (audit #8: the exclusion is scoped, not all of
    docs/)."""
    repo = _seed_c2_repo(tmp_path)
    scratch = repo / "docs" / "superpowers" / "plans"
    scratch.mkdir(parents=True)
    (scratch / "plan.md").write_text(
        "postgresql://user:pw@real-host.db.ondigitalocean.com:25060/db\n",
        encoding="utf-8",
    )
    (repo / "settings.example").write_text(
        "postgresql://user:pw@real-host.db.ondigitalocean.com/db\n",
        encoding="utf-8",
    )
    commit_all(repo, "docs: add connection placeholders")
    assert _findings(rule_c2_no_committed_secrets, context_for(repo)) == []


@pytest.mark.unit
def test_c2_scans_real_docs_runbook(tmp_path: Path) -> None:
    """A real DSN in an operational doc/runbook (docs/ outside superpowers/) MUST
    be flagged -- this is exactly the gap audit #8 says the old broad docs/
    exclusion left invisible."""
    repo = _seed_c2_repo(tmp_path)
    runbook = repo / "docs" / "operations"
    runbook.mkdir(parents=True)
    (runbook / "deploy.md").write_text(
        "Connect with postgresql://admin:s3cret@db-prod-01.db.ondigitalocean.com/db\n",
        encoding="utf-8",
    )
    commit_all(repo, "docs: add runbook")
    findings = _findings(rule_c2_no_committed_secrets, context_for(repo))
    assert any(f.locator.startswith("docs/operations/deploy.md:") for f in findings)


@pytest.mark.unit
def test_c2_skips_tests_path_fixtures(tmp_path: Path) -> None:
    # Test fixtures under tests/ intentionally carry secret-LOOKING literals to
    # exercise the scanner itself; the C2 content scan must not flag them.
    repo = _seed_c2_repo(tmp_path)
    fixtures = repo / "tests" / "unit"
    fixtures.mkdir(parents=True)
    (fixtures / "test_scanner.py").write_text(
        "BAD = 'host = db-prod-01.db.ondigitalocean.com'\n"
        "URI = 'postgresql://user:pw@real-host.db.ondigitalocean.com/db'\n",
        encoding="utf-8",
    )
    commit_all(repo, "test: add scanner fixtures")
    assert _findings(rule_c2_no_committed_secrets, context_for(repo)) == []


@pytest.mark.unit
def test_c2_flags_tracked_env(tmp_path: Path) -> None:
    repo = _seed_c2_repo(tmp_path)
    (repo / ".env").write_text("ANALYTICS_DB_PASSWORD=hunter2\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "-f", ".env"], cwd=repo, check=True, capture_output=True
    )
    commit_all(repo, "chore: oops env")
    findings = _findings(rule_c2_no_committed_secrets, context_for(repo))
    assert any(f.locator == ".env" for f in findings)


@pytest.mark.unit
def test_c2_flags_env_example_with_filled_secret(tmp_path: Path) -> None:
    repo = _gitignore_repo(tmp_path, ".env\n")
    bad = GOOD_ENV_EXAMPLE.replace(
        "ANALYTICS_DB_PASSWORD=\n", "ANALYTICS_DB_PASSWORD=secret\n"
    )
    (repo / ".env.example").write_text(bad, encoding="utf-8")
    commit_all(repo, "chore: bad example")
    findings = _findings(rule_c2_no_committed_secrets, context_for(repo))
    assert any("ANALYTICS_DB_PASSWORD" in f.message for f in findings)


# ---------------------------------------------------------------------------
# Task 11 -- C2 multi-engine extension: _scan_line_for_secret catches an ODBC
# keyword string, a mysql:// URI, and a Snowflake account+password kwargs
# pair, while keeping the existing <...>-placeholder exemption.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_c2_flags_odbc_password_string() -> None:
    hit = _secret_hit("DRIVER={ODBC Driver 18 for SQL Server};PWD=realpw;")
    assert hit is True


@pytest.mark.unit
def test_c2_ignores_placeholder_odbc() -> None:
    assert _secret_hit("DRIVER={...};PWD=<your-password>;") is False


@pytest.mark.unit
def test_c2_flags_odbc_uid_string() -> None:
    assert _secret_hit("SERVER=h;UID=realuser;PWD=<placeholder>") is True


@pytest.mark.unit
def test_c2_ignores_fstring_interpolated_pwd_uid() -> None:
    # dialect.py's own SqlServerDialect.resolve_config builds these lines --
    # the scanner must not self-trip on the source that CONSTRUCTS the string.
    assert _secret_hit("parts.append(f\"PWD={env['ANALYTICS_DB_PASSWORD']}\")") is False
    assert _secret_hit("parts.append(f\"UID={env['ANALYTICS_DB_USER']}\")") is False


@pytest.mark.unit
def test_c2_flags_mysql_uri() -> None:
    assert _secret_hit("mysql://user:pw@real-host.example.com/db") is True


@pytest.mark.unit
def test_c2_ignores_mysql_uri_placeholder() -> None:
    assert _secret_hit("mysql://<user>:<pw>@<host>/db") is False


@pytest.mark.unit
def test_c2_flags_snowflake_account_password_pair() -> None:
    line = 'cfg = {"account": "acme-prod", "password": "hunter2"}'
    assert _secret_hit(line) is True


@pytest.mark.unit
def test_c2_ignores_snowflake_account_alone() -> None:
    # account with no password is not connection context on its own.
    assert _secret_hit('cfg = {"account": "acme-prod"}') is False


@pytest.mark.unit
def test_c2_ignores_snowflake_env_lookup_source() -> None:
    # dialect.py's own SnowflakeDialect.resolve_config builds config from env
    # lookups -- must not self-trip on the source that CONSTRUCTS the dict.
    line = (
        'config["account"] = env.get("ANALYTICS_DB_ACCOUNT")\n'
        'config["password"] = env.get("ANALYTICS_DB_PASSWORD")'
    )
    assert _secret_hit(line) is False


@pytest.mark.unit
def test_c2_end_to_end_flags_committed_odbc_secret(tmp_path: Path) -> None:
    repo = _seed_c2_repo(tmp_path)
    (repo / "config.txt").write_text(
        "DRIVER={ODBC Driver 18 for SQL Server};SERVER=h;UID=admin;PWD=realsecret;\n",
        encoding="utf-8",
    )
    commit_all(repo, "chore: add sqlserver config")
    findings = _findings(rule_c2_no_committed_secrets, context_for(repo))
    assert any(f.locator.startswith("config.txt:") for f in findings)


@pytest.mark.unit
def test_c2_sentinel_real_repo_source_does_not_self_trip() -> None:
    """The scanner's own extension must not flag the real dialect.py / cli/ package /
    git_meta.py source it lives in -- those modules build ODBC/mysql/Snowflake
    config strings from env lookups, never literal secrets. This is the C2
    analog of the B3 real-file sentinel: a pre-merge guard the live gate
    (which runs main's ruleset, per the editable install) cannot provide.
    """
    repo_root = Path(__file__).resolve().parents[2]
    src_root = repo_root / "src" / "seshat"
    targets = [
        src_root / "dialect.py",
        *sorted((src_root / "cli").rglob("*.py")),
        src_root / "rules" / "git_meta.py",
    ]
    offenders: dict[str, list[str]] = {}
    for path in targets:
        text = path.read_text(encoding="utf-8")
        hits = [
            f"{lineno}: {line}"
            for lineno, line in enumerate(text.splitlines(), start=1)
            if _secret_hit(line)
        ]
        if hits:
            offenders[str(path.relative_to(repo_root))] = hits
    assert offenders == {}, f"C2 self-trip on real source: {offenders}"


# ---------------------------------------------------------------------------
# M2.G3 — G3 UTF-8 without BOM
# ---------------------------------------------------------------------------

BOM = b"\xef\xbb\xbf"


def _write(path: Path, prefix: bytes, text: str) -> None:
    path.write_bytes(prefix + text.encode("utf-8"))


@pytest.mark.unit
def test_read_leading_bytes_returns_first_three_bytes(tmp_path: Path) -> None:
    f = tmp_path / "x.tmdl"
    _write(f, BOM, "table Sales")
    assert _read_leading_bytes(f) == BOM


@pytest.mark.unit
def test_read_leading_bytes_short_file_returns_fewer(tmp_path: Path) -> None:
    f = tmp_path / "x.tmdl"
    _write(f, b"ab", "")
    assert _read_leading_bytes(f) == b"ab"


@pytest.mark.unit
def test_g3_flags_tmdl_with_bom(tmp_path: Path) -> None:
    _write(tmp_path / "withbom.tmdl", BOM, "table Sales")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=("withbom.tmdl",))
    findings = _findings(rule_g3_no_bom, ctx)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "G3"
    assert f.severity is Severity.ERROR
    assert f.locator == "withbom.tmdl"


@pytest.mark.unit
def test_g3_passes_tmdl_without_bom(tmp_path: Path) -> None:
    _write(tmp_path / "clean.tmdl", b"", "table Sales")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=("clean.tmdl",))
    assert _findings(rule_g3_no_bom, ctx) == []


@pytest.mark.unit
def test_g3_ignores_non_target_extension_with_bom(tmp_path: Path) -> None:
    # A .sql file WITH a BOM must NOT be flagged: G3 only covers
    # *.tmdl/*.pbir/*.json/*.pbism. This keeps the extension filter load-bearing.
    _write(tmp_path / "ddl.sql", BOM, "select 1")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=("ddl.sql",))
    assert _findings(rule_g3_no_bom, ctx) == []


# ---------------------------------------------------------------------------
# M2.G4 — G4 .gitattributes EOL policy
# ---------------------------------------------------------------------------


def _ctx_g4(tmp_path: Path) -> RuleContext:
    return RuleContext(repo_root=tmp_path, tracked_files=(".gitattributes",))


_PASSING_GITATTRIBUTES = """\
# Normalize line endings; Power BI Desktop writes CRLF for PBIP text files.
* text=auto

*.tmdl   text eol=crlf
*.pbir   text eol=crlf
*.pbism  text eol=crlf
*.json   text eol=crlf
*.sql    text eol=lf
*.md     text eol=lf
*.py     text eol=lf

*.pbix   binary
*.abf    binary
*.png    binary
*.svg    text eol=lf
*.toml   text eol=lf
*.yml    text eol=lf
"""


@pytest.mark.unit
def test_g4_passes_when_all_required_mappings_present(tmp_path: Path) -> None:
    (tmp_path / ".gitattributes").write_text(_PASSING_GITATTRIBUTES, encoding="utf-8")
    findings = _findings(check_gitattributes_eol, _ctx_g4(tmp_path))
    assert findings == []


@pytest.mark.unit
def test_g4_flags_missing_tmdl_crlf(tmp_path: Path) -> None:
    # Drop the *.tmdl line entirely -> required glob absent.
    content = _PASSING_GITATTRIBUTES.replace("*.tmdl   text eol=crlf\n", "")
    (tmp_path / ".gitattributes").write_text(content, encoding="utf-8")
    findings = _findings(check_gitattributes_eol, _ctx_g4(tmp_path))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "G4"
    assert f.severity is Severity.ERROR
    assert "*.tmdl" in f.message
    assert "eol=crlf" in f.message
    # Glob absent -> locator is the bare file, no line number.
    assert f.locator == ".gitattributes"


@pytest.mark.unit
def test_g4_flags_contradicting_token_with_line_locator(tmp_path: Path) -> None:
    # *.sql present but declared eol=crlf instead of required eol=lf.
    content = _PASSING_GITATTRIBUTES.replace(
        "*.sql    text eol=lf", "*.sql    text eol=crlf"
    )
    (tmp_path / ".gitattributes").write_text(content, encoding="utf-8")
    findings = _findings(check_gitattributes_eol, _ctx_g4(tmp_path))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "G4"
    assert f.severity is Severity.ERROR
    assert "*.sql" in f.message
    # Line exists -> most-specific locator carries the line number.
    assert f.locator.startswith(".gitattributes:")


@pytest.mark.unit
def test_g4_flags_all_when_file_absent(tmp_path: Path) -> None:
    # No .gitattributes at all -> every required glob missing, no silent pass.
    findings = _findings(check_gitattributes_eol, _ctx_g4(tmp_path))
    assert len(findings) == 10
    assert all(f.severity is Severity.ERROR for f in findings)
    assert all(f.locator == ".gitattributes" for f in findings)


# ---------------------------------------------------------------------------
# Whole-branch-review fixes (M6 follow-up): G2 must not treat tests/ fixtures as
# a real model; G3 same exemption; C2 ReDoS prefilter.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_g2_only_test_fixtures_emit_info(tmp_path: Path) -> None:
    # PBIP-shaped files exist ONLY under tests/fixtures -> they are not the live
    # model, so G2 must fall into the empty-case INFO branch (spec 5.5/11: it
    # must NOT silently pass as if a model were verified). Synthetic context: the
    # INFO branch returns before any git_check_ignore call, so no git needed.
    ctx = RuleContext(
        repo_root=tmp_path,
        tracked_files=(
            "tests/fixtures/golden_pbip/RetailGold.pbip",
            "tests/fixtures/golden_pbip/RetailGold.Report/definition.pbir",
            "tests/fixtures/golden_pbip/RetailGold.SemanticModel/definition/model.tmdl",
        ),
    )
    findings = _findings(rule_g2_definition_committed, ctx)
    assert len(findings) == 1
    assert findings[0].severity is Severity.INFO
    assert findings[0].message == "no PBIP project present"


@pytest.mark.unit
def test_g2_real_non_tests_pbip_is_validated(tmp_path: Path) -> None:
    # A real (non-tests/) PBIP with a tracked Desktop-local cache.abf is still
    # validated and flagged -> the fixture filter does not weaken real checks.
    repo = make_git_repo(tmp_path)
    pbip_dir = repo / "powerbi" / "Sales.SemanticModel" / "definition"
    pbip_dir.mkdir(parents=True)
    (pbip_dir / "model.tmdl").write_text("model\n", encoding="utf-8")
    (repo / "powerbi" / "Sales.pbip").write_text("{}\n", encoding="utf-8")
    pbi_dir = repo / "powerbi" / "Sales.SemanticModel" / ".pbi"
    pbi_dir.mkdir(parents=True)
    (pbi_dir / "cache.abf").write_text("x\n", encoding="utf-8")
    commit_all(repo, "feat: real pbip with stray cache")
    findings = _findings(rule_g2_definition_committed, context_for(repo))
    # Not the INFO branch: a real model is present and validated.
    assert not any(f.severity is Severity.INFO for f in findings)
    assert any(
        "cache.abf" in f.locator and f.severity is Severity.ERROR for f in findings
    )


@pytest.mark.unit
def test_g3_exempts_tests_fixture_with_bom(tmp_path: Path) -> None:
    # A BOM-prefixed JSON under tests/ is an intentional fixture; G3 must skip it
    # (consistency with G2 / the other file-scanning rules), while a NON-tests/
    # BOM file is still flagged.
    fixture = tmp_path / "tests" / "fixtures" / "bom.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_bytes(b"\xef\xbb\xbf{}\n")
    real = tmp_path / "powerbi" / "model.json"
    real.parent.mkdir(parents=True)
    real.write_bytes(b"\xef\xbb\xbf{}\n")
    ctx = RuleContext(
        repo_root=tmp_path,
        tracked_files=("tests/fixtures/bom.json", "powerbi/model.json"),
    )
    findings = _findings(rule_g3_no_bom, ctx)
    assert len(findings) == 1
    assert findings[0].rule_id == "G3"
    assert findings[0].locator == "powerbi/model.json"


@pytest.mark.unit
def test_c2_long_benign_line_is_not_flagged(tmp_path: Path) -> None:
    # A long benign alnum/hyphen line (no `.db.ondigitalocean.com` literal and no
    # postgres URI) must yield no C2 content finding. The O(n) substring
    # prefilter skips the ReDoS-prone DO_ENDPOINT_RE entirely, so this returns
    # fast; we assert the BEHAVIOR (no false positive), not wall-clock time.
    # _scan_contents is exercised directly (it carries the prefilter); the
    # .env/.env.example sub-checks are out of scope here.
    long_line = "a-" * 100_000  # 200k chars of the prefilter's pathological class
    target = tmp_path / "warehouse" / "big.sql"
    target.parent.mkdir(parents=True)
    target.write_text(f"-- {long_line}\nselect 1;\n", encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=("warehouse/big.sql",))
    assert _findings(_scan_contents, ctx) == []


@pytest.mark.unit
def test_c2_real_do_endpoint_still_flagged(tmp_path: Path) -> None:
    # The ReDoS prefilter must not weaken detection: a real DigitalOcean endpoint
    # (contains the literal `.db.ondigitalocean.com`) is still flagged.
    target = tmp_path / "warehouse" / "leak.sql"
    target.parent.mkdir(parents=True)
    target.write_text(
        "-- host = dbcluster-1.db.ondigitalocean.com\nselect 1;\n", encoding="utf-8"
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=("warehouse/leak.sql",))
    findings = _findings(_scan_contents, ctx)
    assert len(findings) == 1
    assert findings[0].rule_id == "C2"
    assert findings[0].locator == "warehouse/leak.sql:1"


@pytest.mark.unit
def test_c2_pathological_label_then_literal_returns_fast(tmp_path: Path) -> None:
    # The case the substring prefilter alone did NOT close: a long alnum/hyphen
    # run IMMEDIATELY followed by `.db.ondigitalocean.com`. The literal IS present
    # so the prefilter passes and DO_ENDPOINT_RE actually runs. With the unbounded
    # `[A-Za-z0-9-]*` this backtracked catastrophically (minutes); the bounded
    # {0,253} quantifier makes it O(n). Assert a GENEROUS wall-clock bound (the
    # failure mode is minutes vs. milliseconds, so a few seconds is safe and not
    # flaky), plus that the trailing real endpoint is still detected.
    import time

    pathological = "a" * 300_000  # 300k alnum run directly before the literal
    target = tmp_path / "warehouse" / "evil.sql"
    target.parent.mkdir(parents=True)
    target.write_text(
        f"-- {pathological}.db.ondigitalocean.com\nselect 1;\n", encoding="utf-8"
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=("warehouse/evil.sql",))
    start = time.monotonic()
    findings = _findings(_scan_contents, ctx)
    elapsed = time.monotonic() - start
    assert elapsed < 5.0, f"DO_ENDPOINT_RE backtracked ({elapsed:.2f}s) — ReDoS"
    # The line does contain a valid endpoint (label + literal), so it IS flagged.
    assert any(f.rule_id == "C2" for f in findings)


# ---------------------------------------------------------------------------
# C17 remediation: a committed DO cluster SLUG (real connection context, invisible
# to the FQDN/URI patterns) is flagged; documented placeholders are not.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_c2_flags_do_cluster_slug(tmp_path: Path) -> None:
    # A cluster slug (db-<engine>-<region><n>-<id>) committed in a scanned
    # file must be flagged even without a full FQDN or postgres:// URI. The
    # fixture slug is SYNTHETIC (same shape as a real one) -- the guard test
    # must not itself carry the real client cluster id it exists to keep out.
    target = tmp_path / "docs" / "runbook.md"
    target.parent.mkdir(parents=True)
    target.write_text("cluster db-pgsql-ams3-10101 holds the data\n", encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=("docs/runbook.md",))
    findings = _findings(_scan_contents, ctx)
    assert len(findings) == 1
    assert findings[0].rule_id == "C2"
    assert findings[0].locator == "docs/runbook.md:1"
    assert "cluster slug" in findings[0].message


@pytest.mark.unit
def test_c2_cluster_slug_placeholder_not_flagged(tmp_path: Path) -> None:
    # A documented placeholder (angle brackets cannot sit inside the slug class)
    # and ordinary hyphenated identifiers must NOT trip the slug detector.
    target = tmp_path / "docs" / "conn.md"
    target.parent.mkdir(parents=True)
    target.write_text(
        "cluster db-<engine>-<region>-<id> from .env; see dim-product, fct-sales.\n",
        encoding="utf-8",
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=("docs/conn.md",))
    assert _findings(_scan_contents, ctx) == []
