"""Regression lock on the committed exemplar warehouse migration SQL (spec 100).

`test_sql.py` asserts the S1-S4b static SQL rules correctly PASS or FAIL
hand-authored fixture SQL -- "does the checker correctly judge SQL." This module
is the other half named in gap #12: "does the SQL the warehouse builder actually
wrote stay the same." The warehouse builder
(`.claude/skills/retail-build-warehouse/SKILL.md`) is an agent-authored skill with
no callable Python entry point (see spec Assumptions) -- so this is a REGRESSION
LOCK on already-committed migration text against a committed golden copy, not a
"regenerate from source-map and compare" golden test.

Normalization (FR-006), identical to test_dax_golden.py: replace every "\\r\\n"
with "\\n" in both sides, then strip at most one trailing "\\n" from each side,
before an exact string-equality comparison. Stable across a CRLF checkout
(`core.autocrlf=true` on Windows) and an LF checkout of the same commit.

SCOPE GUARD (FR-004, FR-005; Principle VIII): this module opens no database
connection, invokes no `retail-build-warehouse` skill step, and calls no CLI --
it only reads two already-committed migration files and their golden copies as
plain text. That is a structural property of the module as written: no
`psycopg2`/`retail.validate`/subprocess import appears anywhere below.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATIONS_DIR = _REPO_ROOT / "warehouse" / "migrations"
_GOLDEN_SQL_DIR = Path(__file__).parent.parent / "fixtures" / "golden" / "sql"

# Fixed pair (spec Assumptions): the two already-committed C086 exemplar
# migrations, cited per Principle VII / FR-010 as the filled instance, not a
# template default. This module itself is fully generic -- it would work
# unchanged against any future (migration, golden) filename pair.
_LOCKED_MIGRATIONS = (
    "0003_create_silver_retail_store_sales.sql",
    "0004_create_gold_retail_store_sales_star.sql",
)


def _normalize(text: str) -> str:
    """FR-006: CRLF -> LF, then strip at most one trailing '\\n'."""
    text = text.replace("\r\n", "\n")
    if text.endswith("\n"):
        text = text[:-1]
    return text


def _read_text(path: Path) -> str:
    # FR-007: a missing/unreadable file (migration or golden) fails explicitly,
    # naming the path -- never a silent skip, never a pass-by-default.
    if not path.is_file():
        pytest.fail(f"missing file (never a skip): {path}")
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        pytest.fail(f"could not read {path}: {exc}")


@pytest.mark.parametrize("filename", _LOCKED_MIGRATIONS)
def test_migration_matches_golden_copy(filename: str) -> None:
    migration_path = _MIGRATIONS_DIR / filename
    golden_path = _GOLDEN_SQL_DIR / filename

    actual = _normalize(_read_text(migration_path))
    expected = _normalize(_read_text(golden_path))

    if actual != expected:
        actual_lines = actual.split("\n")
        expected_lines = expected.split("\n")
        diffs = [
            f"  line {i + 1}: actual={a!r} expected={e!r}"
            for i, (a, e) in enumerate(zip(actual_lines, expected_lines))
            if a != e
        ]
        if len(actual_lines) != len(expected_lines):
            diffs.append(
                f"  line count differs: actual={len(actual_lines)} "
                f"expected={len(expected_lines)}"
            )
        pytest.fail(
            f"{filename}: committed migration text drifted from the golden "
            f"copy at {golden_path}.\n" + "\n".join(diffs)
        )


def test_missing_golden_fails_closed_never_skips(tmp_path: Path) -> None:
    """FR-007: a missing golden/migration path is an explicit failure."""
    missing = tmp_path / "does_not_exist.sql"
    with pytest.raises(pytest.fail.Exception):
        _read_text(missing)


def test_no_live_db_or_skill_invocation_in_this_module() -> None:
    """Structural guard (FR-004, FR-005): this test file reads committed text
    only. It never IMPORTS a DB driver, the live `retail.validate` module, or
    `subprocess` -- confirmed here by parsing this module's own source with
    `ast` and inspecting its import statements only (not prose in comments or
    docstrings, which would otherwise self-flag), so a future edit that
    accidentally adds a live-execution import is caught.
    """
    import ast

    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    forbidden_modules = ("psycopg2", "pyodbc", "subprocess", "retail.validate")
    found = [m for m in forbidden_modules if m in imported]
    assert not found, (
        f"test_warehouse_sql_golden.py must stay a pure text-comparison module; "
        f"found forbidden live-execution import(s): {found}"
    )
