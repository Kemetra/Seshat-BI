"""TDD tests for B1 -- never-execute invariant guard.

Two layers:
* unit tests of ``module_scope_violations`` proving it flags MODULE-SCOPE DB/network
  imports while leaving lazy in-function imports alone (the main failure mode);
* a sentinel test asserting the real governed core modules are clean today, so a
  future module-scope DB/network import fails loud.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.never_execute import (
    _FORBIDDEN_ROOTS,
    _is_governed,
    check_no_module_scope_execution_imports,
    module_scope_violations,
)

pytestmark = pytest.mark.unit


# --- module_scope_violations: module-scope is flagged ----------------------


def test_module_scope_import_psycopg2_is_flagged():
    assert module_scope_violations("import psycopg2\n") == ["psycopg2"]


def test_module_scope_from_import_is_flagged():
    assert module_scope_violations("from sqlalchemy import create_engine\n") == [
        "sqlalchemy"
    ]


def test_dotted_module_scope_import_is_flagged_by_root():
    # http.client is connection-capable -> flagged via its root 'http'.
    assert module_scope_violations("import http.client\n") == ["http.client"]


def test_multiple_module_scope_violations_all_reported():
    src = "import psycopg2\nimport requests\n"
    assert module_scope_violations(src) == ["psycopg2", "requests"]


def test_module_scope_try_except_import_is_flagged():
    # Optional-dependency guard at module scope STILL executes on import.
    src = "try:\n    import psycopg2\nexcept ImportError:\n    psycopg2 = None\n"
    assert module_scope_violations(src) == ["psycopg2"]


def test_module_scope_plain_if_import_is_flagged():
    # A non-TYPE_CHECKING module-level `if` executes on import.
    src = "import os\nif os.environ.get('X'):\n    import requests\n"
    assert module_scope_violations(src) == ["requests"]


def test_urllib_request_is_flagged():
    # urllib.request opens sockets -> forbidden, even though urllib.parse is fine.
    assert module_scope_violations("import urllib.request\n") == ["urllib.request"]


# --- module_scope_violations: lazy / safe imports are NOT flagged -----------


def test_lazy_in_function_import_is_not_flagged():
    # The deliberate repo pattern: import the driver INSIDE the handler.
    src = "def connect():\n    import psycopg2\n    return psycopg2\n"
    assert module_scope_violations(src) == []


def test_lazy_import_inside_method_is_not_flagged():
    src = (
        "class Runner:\n"
        "    def run(self):\n"
        "        import requests\n"
        "        return requests\n"
    )
    assert module_scope_violations(src) == []


def test_lazy_import_inside_async_function_is_not_flagged():
    src = "async def connect():\n    import asyncpg\n    return asyncpg\n"
    assert module_scope_violations(src) == []


def test_type_checking_guard_import_is_not_flagged():
    # `if TYPE_CHECKING:` imports never execute at runtime -> allowed by design.
    src = "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import psycopg2\n"
    assert module_scope_violations(src) == []


def test_urllib_parse_is_not_flagged():
    # Pure stdlib string work (DSN/URL escaping); opens no socket.
    assert module_scope_violations("from urllib.parse import quote\n") == []


def test_stdlib_and_local_imports_are_not_flagged():
    src = (
        "from __future__ import annotations\n"
        "import ast\n"
        "from pathlib import Path\n"
        "from .core import Finding\n"
    )
    assert module_scope_violations(src) == []


def test_snowflake_and_mysql_connector_are_forbidden_roots() -> None:
    assert "snowflake" in _FORBIDDEN_ROOTS
    assert "mysql" in _FORBIDDEN_ROOTS


# --- governed-module selection ---------------------------------------------


def test_is_governed_matches_core_and_rules():
    assert _is_governed("src/seshat/cli/__init__.py")
    assert _is_governed("src/seshat/cli/parser.py")
    assert _is_governed("src/seshat/cli/commands/validate.py")
    assert _is_governed("src/seshat/runner.py")
    assert _is_governed("src/seshat/rules/sql.py")
    assert not _is_governed("src/seshat/validate.py")  # live validator, lazily imports
    assert not _is_governed("tests/unit/test_cli.py")
    assert not _is_governed("docs/routing/routes.yaml")


# --- the rule end-to-end ----------------------------------------------------


def test_rule_flags_a_governed_module_with_module_scope_driver(tmp_path: Path):
    rel = "src/seshat/cli/__init__.py"
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("import psycopg2\n", encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    findings = list(check_no_module_scope_execution_imports(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "B1"
    assert findings[0].severity is Severity.ERROR
    assert "psycopg2" in findings[0].message
    assert findings[0].locator == rel


def test_rule_ignores_lazy_import_in_governed_module(tmp_path: Path):
    rel = "src/seshat/rules/sql.py"
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "def handler():\n    import psycopg2\n    return psycopg2\n", encoding="utf-8"
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(check_no_module_scope_execution_imports(ctx)) == []


def test_rule_emits_finding_on_unparseable_governed_module(tmp_path: Path):
    # A governed module that won't parse fails loud as a Finding, never crashes.
    rel = "src/seshat/core.py"
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("def broken(:\n", encoding="utf-8")  # syntax error
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    findings = list(check_no_module_scope_execution_imports(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "B1"
    assert "could not parse" in findings[0].message.lower()


def test_rule_ignores_non_governed_module(tmp_path: Path):
    # A module-scope driver import in a NON-governed file (e.g. validate.py) is
    # out of scope for B1 (validate is the live path; it imports lazily anyway).
    rel = "src/seshat/validate.py"
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("import psycopg2\n", encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(check_no_module_scope_execution_imports(ctx)) == []


# --- sentinel: the REAL core modules are clean today ------------------------


def test_real_core_modules_have_no_module_scope_execution_imports():
    """Sentinel: every governed core module in the live repo is execution-free.

    If a future change adds a module-scope DB/network import to cli/runner/core/
    registry or any rule module, this fails loud.
    """
    repo_root = Path(__file__).resolve().parents[2]
    src_root = repo_root / "src" / "seshat"
    governed = [
        src_root / "runner.py",
        src_root / "core.py",
        src_root / "registry.py",
        *sorted((src_root / "rules").glob("*.py")),
        *sorted((src_root / "cli").rglob("*.py")),
    ]
    offenders: dict[str, list[str]] = {}
    for path in governed:
        violations = module_scope_violations(path.read_text(encoding="utf-8"))
        if violations:
            offenders[str(path.relative_to(repo_root))] = violations
    assert offenders == {}, f"module-scope DB/network imports found: {offenders}"
