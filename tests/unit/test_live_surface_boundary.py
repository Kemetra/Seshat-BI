"""TDD tests for B3 -- live-surface import boundary guard.

B3 is the live-surface half of the never-execute guard. B1 (``never_execute.py``)
forbids module-scope connection-capable imports in the STATIC-CORE modules
(cli/runner/core/registry/rules); B3 forbids the same in the LIVE-SURFACE modules
(validate/value_proxy/semantic/dax_gen), which must keep their driver imports lazy
so importing them never opens a connection. B3 reuses B1's ``module_scope_violations``
AST helper unchanged (parse-not-import -- the guard never executes), and emits ERROR
(matching B1's posture for the identical defect class).

The four live-surface modules are lazy today, so B3 is green on the current tree and
fires only on a regression. Fixtures use synthetic source strings + generic module
paths only (no domain artifact).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules import never_execute
from retail.rules.live_surface_boundary import (
    _LIVE_SURFACE,
    check_live_surface_imports,
)
from retail.rules.never_execute import module_scope_violations

pytestmark = pytest.mark.unit


def _stage(tmp_path, files: dict[str, str]) -> RuleContext:
    """Write {repo-relative path: source} under tmp_path and track them all."""
    tracked = []
    for rel, src in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(src, encoding="utf-8")
        tracked.append(rel)
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(tracked))


# A live-surface module path to plant fixtures into (must be a real member of the set).
_TARGET = sorted(_LIVE_SURFACE)[0]


# --- C1: module-scope forbidden import in a live surface -> ERROR -------------


def test_module_scope_driver_import_fails(tmp_path) -> None:
    ctx = _stage(tmp_path, {_TARGET: "import psycopg2\n\n\ndef run():\n    pass\n"})
    findings = list(check_live_surface_imports(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "B3"
    assert findings[0].severity is Severity.ERROR
    assert "psycopg2" in findings[0].message
    assert findings[0].locator == _TARGET


def test_module_scope_from_import_fails(tmp_path) -> None:
    ctx = _stage(tmp_path, {_TARGET: "from requests import get\n"})
    findings = list(check_live_surface_imports(ctx))
    assert len(findings) == 1
    assert "requests" in findings[0].message


# --- C2: lazy / TYPE_CHECKING imports are allowed -> no Finding ---------------


def test_lazy_import_inside_function_passes(tmp_path) -> None:
    ctx = _stage(
        tmp_path,
        {_TARGET: "def run():\n    import psycopg2\n    return psycopg2\n"},
    )
    assert list(check_live_surface_imports(ctx)) == []


def test_type_checking_import_passes(tmp_path) -> None:
    ctx = _stage(
        tmp_path,
        {
            _TARGET: (
                "from typing import TYPE_CHECKING\n"
                "if TYPE_CHECKING:\n"
                "    import psycopg2\n"
            )
        },
    )
    assert list(check_live_surface_imports(ctx)) == []


# --- C3: module-scope try/if forbidden imports are flagged --------------------


def test_module_scope_try_import_fails(tmp_path) -> None:
    src = "try:\n    import psycopg2\nexcept ImportError:\n    psycopg2 = None\n"
    ctx = _stage(tmp_path, {_TARGET: src})
    findings = list(check_live_surface_imports(ctx))
    assert len(findings) == 1
    assert "psycopg2" in findings[0].message


# --- C4: unparseable source -> fail-loud ERROR (never a vacuous green) --------


def test_unparseable_source_fails_loud(tmp_path) -> None:
    ctx = _stage(tmp_path, {_TARGET: "def (:\n  oops\n"})
    findings = list(check_live_surface_imports(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert findings[0].locator == _TARGET


def test_tracked_but_missing_file_fails_loud(tmp_path) -> None:
    # A live-surface path tracked but absent on disk must fail loud (an ERROR
    # Finding), never crash the gate and never pass vacuously.
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(_TARGET,))
    findings = list(check_live_surface_imports(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "B3"
    assert findings[0].severity is Severity.ERROR
    assert findings[0].locator == _TARGET


# --- C5: allowed stdlib string work (urllib.parse) -> no Finding --------------


def test_urllib_parse_import_passes(tmp_path) -> None:
    ctx = _stage(tmp_path, {_TARGET: "from urllib.parse import quote\n"})
    assert list(check_live_surface_imports(ctx)) == []


# --- scope: only live-surface files are scanned -------------------------------


def test_non_live_surface_file_is_not_scanned(tmp_path) -> None:
    # A bad import in a NON-live-surface file must not be flagged by B3.
    ctx = _stage(tmp_path, {"src/retail/some_other.py": "import psycopg2\n"})
    assert list(check_live_surface_imports(ctx)) == []


def test_multiple_live_surfaces_each_flagged(tmp_path) -> None:
    members = sorted(_LIVE_SURFACE)
    ctx = _stage(tmp_path, {m: "import psycopg2\n" for m in members})
    findings = list(check_live_surface_imports(ctx))
    assert len(findings) == len(members)
    assert {f.locator for f in findings} == set(members)


# --- US3: the set is explicit, closed, disjoint from B1, schema-agnostic ------


def test_live_surface_set_is_disjoint_from_b1_governed(tmp_path) -> None:
    assert _LIVE_SURFACE.isdisjoint(never_execute._GOVERNED_MODULES)
    for member in _LIVE_SURFACE:
        assert not member.startswith(never_execute._GOVERNED_PREFIX)


def test_live_surface_set_is_generic_module_paths(tmp_path) -> None:
    # Only generic src/retail/*.py module paths -- no domain table/column/KPI token.
    for member in _LIVE_SURFACE:
        assert member.startswith("src/retail/")
        assert member.endswith(".py")


def test_dialect_module_is_a_live_surface() -> None:
    assert "src/retail/dialect.py" in _LIVE_SURFACE


# --- sentinel: the REAL dialect.py module is import-lazy today (Task 11) -----


def test_real_dialect_module_has_no_module_scope_driver_imports() -> None:
    """Sentinel: the real ``src/retail/dialect.py`` on disk is execution-free.

    Task 11 adds per-engine ``connect()`` methods that import pyodbc /
    mysql.connector / snowflake.connector -- this proves those imports are
    LAZY (inside the connect methods), not module-scope, mirroring B1's
    ``test_real_core_modules_have_no_module_scope_execution_imports`` sentinel
    (test_never_execute.py). This is the pre-merge guard: the editable
    ``retail`` install used for a live ``retail check`` run points at main's
    checkout, so main's B3 rule instance never sees this worktree's edits --
    only this test (running against THIS worktree's source) does.
    """
    repo_root = Path(__file__).resolve().parents[2]
    dialect_path = repo_root / "src" / "retail" / "dialect.py"
    source = dialect_path.read_text(encoding="utf-8")
    assert module_scope_violations(source) == []
