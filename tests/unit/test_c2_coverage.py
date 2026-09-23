"""C2 coverage: env files at any depth, env-template content, case/ADO credential
shapes, and non-UTF-8 text files.

Every file here is committed into a throwaway git repo under ``tmp_path`` (never
the live tree), and the fake credentials are the same obviously synthetic values
the sibling ``test_git_meta.py`` C2 tests use.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.rules.git_meta import _scan_line_for_secret, rule_c2_no_committed_secrets
from tests.unit._gitfix import commit_all, context_for, make_git_repo

pytestmark = pytest.mark.unit

_GOOD_ENV_EXAMPLE = (
    "ANALYTICS_DB_HOST=\n"
    "ANALYTICS_DB_PORT=25060\n"
    "ANALYTICS_DB_NAME=\n"
    "ANALYTICS_DB_USER=\n"
    "ANALYTICS_DB_PASSWORD=\n"
    "ANALYTICS_DB_SSLMODE=require\n"
)
_URI = "postgresql://u:pw@db.example.com/x"


def _repo(tmp_path: Path) -> Path:
    repo = make_git_repo(tmp_path)
    (repo / ".gitignore").write_text(".env\n", encoding="utf-8")
    (repo / ".env.example").write_text(_GOOD_ENV_EXAMPLE, encoding="utf-8")
    return repo


def _force_add(repo: Path, rel: str) -> None:
    subprocess.run(["git", "add", "-f", rel], cwd=repo, check=True, capture_output=True)


def _c2_locators(repo: Path) -> list[str]:
    commit_all(repo, "chore: seed")
    return [f.locator for f in rule_c2_no_committed_secrets(context_for(repo))]


def _write(repo: Path, rel: str, data: bytes) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_nested_env_file_is_flagged(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo, "warehouse/.env", b"ANALYTICS_DB_HOST=10.9.8.7\n")
    _force_add(repo, "warehouse/.env")
    assert "warehouse/.env" in _c2_locators(repo)


def test_suffixed_env_file_is_flagged(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo, ".env.production", b"ANALYTICS_DB_HOST=10.9.8.7\n")
    assert ".env.production" in _c2_locators(repo)


def test_env_template_is_not_flagged_as_a_tracked_env(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    assert _c2_locators(repo) == []


def test_dsn_in_env_example_is_flagged(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    text = _GOOD_ENV_EXAMPLE + f"DATABASE_URL={_URI}\n"
    _write(repo, ".env.example", text.encode("utf-8"))
    assert ".env.example:7" in _c2_locators(repo)


def test_filled_secret_key_in_env_example_is_flagged(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    text = _GOOD_ENV_EXAMPLE + "REPORTING_API_TOKEN=abc123def\n"
    _write(repo, ".env.example", text.encode("utf-8"))
    assert ".env.example:7" in _c2_locators(repo)


def test_empty_or_placeholder_secret_key_in_env_example_passes(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    text = _GOOD_ENV_EXAMPLE + "REPORTING_API_TOKEN=\nOTHER_SECRET=<your-secret>\n"
    _write(repo, ".env.example", text.encode("utf-8"))
    assert _c2_locators(repo) == []


def test_utf16_file_is_scanned(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo, "warehouse/notes_utf16.txt", f"conn {_URI}\n".encode("utf-16"))
    assert "warehouse/notes_utf16.txt:1" in _c2_locators(repo)


def test_cp1252_file_is_scanned(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    data = f"café {_URI}\n".encode("cp1252")
    _write(repo, "warehouse/notes_cp1252.txt", data)
    assert "warehouse/notes_cp1252.txt:1" in _c2_locators(repo)


def test_binary_file_is_skipped_without_error(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo, "img.png", b"\x89PNG\r\n\x1a\n\x00\x00" + _URI.encode("ascii"))
    assert _c2_locators(repo) == []


def test_lower_case_and_ado_credentials_are_flagged(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(
        repo,
        "odbc.txt",
        b"Driver=x;Server=h;uid=sa;pwd=Secret123\nUser Id=sa;Password=Secret123\n",
    )
    locators = _c2_locators(repo)
    assert "odbc.txt:1" in locators
    assert "odbc.txt:2" in locators


@pytest.mark.parametrize(
    "line",
    [
        "uid=sa;pwd=Secret123",
        "Server=h;User Id=sa;Password=Secret123",
        'conn = "Server=h;password=Secret123;"',
        "PWD=realpw;",
    ],
)
def test_connection_string_credentials_hit(line: str) -> None:
    assert _scan_line_for_secret(line) is True


@pytest.mark.parametrize(
    "line",
    [
        "connect(uid=uid, pwd=pwd)",
        "pwd=$(pwd)",
        'password=os.environ["ANALYTICS_DB_PASSWORD"]',
        "Server=h;Password=<your-password>;",
        'parts.append(f"Password={password};")',
        "the ODBC keywords uid/pwd carry the user and password",
    ],
)
def test_code_and_placeholders_do_not_hit(line: str) -> None:
    assert _scan_line_for_secret(line) is False


def test_seven_file_scratch_repo_each_file_flagged(tmp_path: Path) -> None:
    """The audit's scratch repo: every one of the seven files yields a C2 hit."""
    repo = _repo(tmp_path)
    _write(
        repo,
        ".env.example",
        (_GOOD_ENV_EXAMPLE + f"DATABASE_URL={_URI}\n").encode("utf-8"),
    )
    _write(repo, ".env.production", b"ANALYTICS_DB_PASSWORD=hunter2\n")
    _write(repo, "warehouse/.env", b"ANALYTICS_DB_PASSWORD=hunter2\n")
    _force_add(repo, "warehouse/.env")
    _write(repo, "warehouse/notes_utf16.txt", f"{_URI}\n".encode("utf-16"))
    _write(repo, "warehouse/notes_cp1252.txt", f"é {_URI}\n".encode("cp1252"))
    _write(repo, "odbc.txt", b"uid=sa;pwd=Secret123\nUser Id=sa;Password=Secret123\n")
    files = {loc.split(":", 1)[0] for loc in _c2_locators(repo)}
    assert files >= {
        ".env.example",
        ".env.production",
        "warehouse/.env",
        "warehouse/notes_utf16.txt",
        "warehouse/notes_cp1252.txt",
        "odbc.txt",
    }
