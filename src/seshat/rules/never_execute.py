"""B1 -- never-execute invariant guard.

The reasoning/CLI layers are *static*: they read tracked files and reason about
SQL/DAX/Python, they never open a database connection or a network socket. The
recurring risk is that a DB/network client (psycopg2, requests, ...) gets imported
at **module scope** of a core module -- which would make ``import seshat.cli`` (or
the ``retail check`` import chain) pull a live driver and erode the invariant.

The repo's deliberate pattern is the opposite: every driver/network import is
**lazy** -- done INSIDE the handler that actually connects (see ``validate.py`` /
the ``cli/`` package's psycopg2, and the lazy ``yaml`` in ``dax_gen``/
``metric_drift``).

B1 fails closed on a **module-scope** import of a connection-capable library in the
governed core modules, while leaving lazy in-function imports untouched. It uses
stdlib ``ast`` only -- it parses source text, it never imports or runs the module,
so the guard itself never executes anything.

Note ``urllib.parse`` is NOT forbidden: it is pure stdlib string work (URL/DSN
escaping, as ``validate.py`` uses) and opens no socket. Only connection-capable
roots are listed in ``_FORBIDDEN_ROOTS``.
"""

from __future__ import annotations

import ast
from typing import Iterable

from ..core import Finding, RuleContext, Severity, read_tracked_text
from ..registry import register

# Connection-capable import roots. A module-scope import of any of these in a core
# module would make merely importing that module able to open a DB/network handle.
_FORBIDDEN_ROOTS: frozenset[str] = frozenset(
    {
        "psycopg2",
        "psycopg",
        "asyncpg",
        "sqlalchemy",
        "pymysql",
        "pyodbc",
        "mysql",
        "snowflake",
        "requests",
        "httpx",
        "aiohttp",
        "socket",
        "http",  # http.client / http.server (NOT urllib -- that is handled below)
        "urllib3",
        "ftplib",
        "smtplib",
        "telnetlib",
        "websocket",
        "websockets",
    }
)

# urllib needs per-submodule discrimination: urllib.request/urllib.error open
# sockets (forbidden) but urllib.parse is pure string work (allowed, used by
# validate.py for DSN escaping). So 'urllib' is NOT a forbidden root; instead
# these specific dotted modules are forbidden.
_FORBIDDEN_DOTTED: frozenset[str] = frozenset({"urllib.request", "urllib.error"})

# The core import chain that must stay execution-free: importing any of these must
# not pull a DB/network driver. Repo-relative POSIX paths (matched against tracked
# files). The rules package AND the cli package are included via the prefix check
# below (the cli package split -- CodeScene hotspot -- turned the single
# src/seshat/cli.py into src/seshat/cli/{__init__,parser,__main__}.py plus
# src/seshat/cli/commands/*.py; the prefix covers every file the eager
# `import seshat.cli` chain now spans, strictly more coverage than the single
# hardcoded path it replaces).
_GOVERNED_MODULES: frozenset[str] = frozenset(
    {
        "src/seshat/runner.py",
        "src/seshat/core.py",
        "src/seshat/registry.py",
    }
)
_GOVERNED_PREFIXES: tuple[str, ...] = ("src/seshat/rules/", "src/seshat/cli/")


def _root_of(name: str) -> str:
    """First dotted segment of a module path: 'urllib.request' -> 'urllib'."""
    return name.split(".", 1)[0]


def _is_forbidden(name: str) -> bool:
    """True if ``name`` is a connection-capable module forbidden at module scope."""
    return _root_of(name) in _FORBIDDEN_ROOTS or name in _FORBIDDEN_DOTTED


def _is_type_checking_guard(node: ast.If) -> bool:
    """True for an ``if TYPE_CHECKING:`` block (imports there never run at runtime)."""
    test = node.test
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    # typing.TYPE_CHECKING (attribute access)
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"


def _violations_in(node: ast.stmt) -> list[str]:
    """Forbidden import names directly in this statement (one statement, no nesting)."""
    found: list[str] = []
    if isinstance(node, ast.Import):
        found.extend(a.name for a in node.names if _is_forbidden(a.name))
    elif isinstance(node, ast.ImportFrom):
        # `from X import y` -- module is node.module (None for `from . import`).
        if node.module and _is_forbidden(node.module):
            found.append(node.module)
    return found


def module_scope_violations(source: str) -> list[str]:
    """Names of forbidden libraries imported at MODULE SCOPE in ``source``.

    "Module scope" = statements that execute when the module is imported: the
    top-level body, plus the bodies of module-level ``try``/``except``/``else``/
    ``finally`` and module-level ``if``/``else`` (e.g. a ``try: import psycopg2
    except ImportError`` optional-dependency guard, or a conditional import, still
    runs on import). Imports inside a ``def``/``async def``/``class`` are LAZY and
    deliberately ignored. ``if TYPE_CHECKING:`` blocks are also ignored -- their
    imports never run at runtime.

    Raises ``SyntaxError`` only if ``source`` does not parse; the caller (the rule)
    converts that into a Finding rather than crashing.
    """
    tree = ast.parse(source)
    violations: list[str] = []

    def visit(stmts: list[ast.stmt]) -> None:
        for node in stmts:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                violations.extend(_violations_in(node))
            elif isinstance(node, ast.Try):
                # try/except/else/finally at module scope all execute on import.
                visit(node.body)
                for handler in node.handlers:
                    visit(handler.body)
                visit(node.orelse)
                visit(node.finalbody)
            elif isinstance(node, ast.If):
                # A plain module-level `if` executes; TYPE_CHECKING never does.
                if not _is_type_checking_guard(node):
                    visit(node.body)
                    visit(node.orelse)
            # def / async def / class bodies are NOT visited -> lazy imports pass.

    visit(tree.body)
    return violations


def _is_governed(path: str) -> bool:
    return path in _GOVERNED_MODULES or (
        path.endswith(".py") and path.startswith(_GOVERNED_PREFIXES)
    )


@register("B1", "No module-scope DB/network import in the static core (never-execute)")
def check_no_module_scope_execution_imports(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in sorted(p for p in ctx.tracked_files if _is_governed(p)):
        # Tracked-but-deleted-on-disk (#430): nothing to scan for a module-scope
        # import, skip rather than crash. Content scan, not a presence check.
        source = read_tracked_text(ctx.repo_root / rel)
        if source is None:
            continue
        try:
            names = module_scope_violations(source)
        except SyntaxError as exc:
            # A governed module that does not parse fails loud as a Finding rather
            # than crashing the whole gate (never a vacuous green).
            findings.append(
                Finding(
                    rule_id="B1",
                    severity=Severity.ERROR,
                    message=f"could not parse module to verify never-execute: {exc}",
                    locator=rel,
                )
            )
            continue
        for name in names:
            findings.append(
                Finding(
                    rule_id="B1",
                    severity=Severity.ERROR,
                    message=(
                        f"module-scope import of {name!r} in a static-core module "
                        f"-- import it LAZILY inside the handler that connects; the "
                        f"reasoning/CLI layers must never execute on import"
                    ),
                    locator=rel,
                )
            )
    return findings
