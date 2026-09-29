"""C2 committed-secret scan behavior and regression tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.core import RuleContext
from seshat.rules.git_meta import (
    _scan_line_for_secret,
    rule_c2_no_committed_secrets,
)
from tests.unit._gitfix import commit_all, context_for, make_git_repo


def _findings(rule, ctx: RuleContext) -> list:
    return list(rule(ctx))


def _secret_hit(line: str) -> bool:
    return _scan_line_for_secret(line)


def _gitignore_repo(tmp_path: Path, content: str) -> Path:
    repo = make_git_repo(tmp_path)
    (repo / ".gitignore").write_text(content, encoding="utf-8")
    return repo


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
        src_root / "rules" / "c2_scan.py",
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
