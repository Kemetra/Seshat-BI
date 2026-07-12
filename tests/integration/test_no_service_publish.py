"""No-publish boundary test (spec 123, US8, T046a; FR-036/SC-011).

Asserts NO publish/refresh/export/schedule path is reachable from either the
US7 compiler (``seshat.pbir_compile``) or the US8 validator
(``seshat.pbir_validate_blueprint``). F016 remains the only, deferred, publish
owner (docstrings in both modules SAY this; this test PROVES it structurally).

Why AST/import-graph, not a text/grep scan (memory: verifier-must-sit-on-the-risk):
both modules' own docstrings contain the words "publish", "never publishes",
"no pbi-cli", "no live Power BI" as part of stating the boundary -- a substring
grep over raw source text would match those defensive sentences and either
false-positive on the very disclaimers that prove the boundary holds, or (for a
looser pattern) silently pass without checking anything real. "export" is
doubly dangerous as a substring (`export=`, `exported`, `sort_keys=`, etc. is
not a risk).

What actually makes publish/refresh/export/schedule REACHABLE is an import of a
network-, subprocess-, or Power-BI-client-capable module. So this test parses
each module with ``ast``, walks every ``Import`` / ``ImportFrom`` node
(deliberately ignoring string literals, comments, and docstrings), and asserts
the imported module set contains nothing network/subprocess/pbi-capable.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_SRC = Path(__file__).parent.parent.parent / "src" / "seshat"
_MODULES = [
    _SRC / "pbir_compile.py",
    _SRC / "pbir_validate_blueprint.py",
]

# Any import naming (or rooted at) one of these is a live-execution / publish /
# network capability -- exactly what F016 (the deferred execution adapter) would
# require and what US7/US8 must never reach.
_FORBIDDEN_MODULE_ROOTS = frozenset(
    {
        "requests",
        "urllib",
        "urllib2",
        "urllib3",
        "http",
        "httpx",
        "socket",
        "subprocess",
        "webbrowser",
        "ftplib",
        "smtplib",
        "paramiko",
        "pbi_cli",
        "pbi",
        "powerbi",
        "msal",  # Power BI Service auth
        "azure",
    }
)


def _node_import_roots(node: ast.AST) -> set[str]:
    """The module ROOT(s) a single AST node imports (empty for non-import nodes).

    A relative ``ImportFrom`` (``level > 0``, e.g. ``from .decision_store import
    ...``) is an intra-package ``seshat`` sibling, not an external dependency --
    it is reported as the literal root ``"seshat"`` rather than the bare module
    name, so it never collides with a same-named third-party package."""
    if isinstance(node, ast.Import):
        return {alias.name.split(".")[0] for alias in node.names}
    if isinstance(node, ast.ImportFrom):
        if node.level and node.level > 0:
            return {"seshat"}  # relative import: intra-package sibling
        if node.module:
            return {node.module.split(".")[0]}
    return set()


def _imported_module_roots(path: Path) -> set[str]:
    """Every top-level module ROOT this file imports, read structurally via
    ``ast`` -- never a text/grep scan over docstrings/comments/strings."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        roots |= _node_import_roots(node)
    return roots


def _defined_function_names(path: Path) -> set[str]:
    """Every top-level (and nested) function/method name defined in the module,
    read structurally -- proves no publish/refresh/export/schedule CAPABILITY is
    even defined, independent of whether it is ever called."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


_FORBIDDEN_FUNCTION_NAME_HINTS = ("publish", "refresh", "schedule", "export_to_service")


@pytest.mark.parametrize("module_path", _MODULES)
def test_module_imports_no_network_or_publish_capable_package(module_path: Path):
    assert module_path.exists(), f"expected module missing: {module_path}"
    roots = _imported_module_roots(module_path)
    forbidden_hit = roots & _FORBIDDEN_MODULE_ROOTS
    assert not forbidden_hit, (
        f"{module_path.name} imports {forbidden_hit}, which would make a "
        f"publish/refresh/export/schedule path reachable -- forbidden by FR-036"
    )


@pytest.mark.parametrize("module_path", _MODULES)
def test_module_defines_no_publish_shaped_function(module_path: Path):
    names = _defined_function_names(module_path)
    hits = {
        name
        for name in names
        if any(hint in name.lower() for hint in _FORBIDDEN_FUNCTION_NAME_HINTS)
    }
    assert not hits, (
        f"{module_path.name} defines {hits}, which names a publish/refresh/"
        f"schedule capability -- forbidden by FR-036; F016 remains the only "
        f"deferred owner of any such step"
    )


def test_both_us7_and_us8_modules_exist_and_are_stdlib_only():
    """A cheap parity check: both modules import only stdlib + intra-package
    ``seshat`` siblings + the repo's one declared runtime dependency (PyYAML,
    ``pyproject.toml`` -- used repo-wide by the Decision Store / coordinator for
    the SAME committed-YAML reading, not a network/publish capability) -- no
    OTHER third-party client library that could reach the Power BI Service is on
    the import graph at all."""
    import sys

    stdlib_roots = set(sys.stdlib_module_names) | {"__future__"}
    allowed_extra = {"seshat", "yaml"}
    for module_path in _MODULES:
        roots = _imported_module_roots(module_path)
        non_stdlib = roots - stdlib_roots - allowed_extra
        assert not non_stdlib, (
            f"{module_path.name} imports non-stdlib, non-allowed package(s) "
            f"{non_stdlib} -- US7/US8 must stay stdlib + intra-package + PyYAML only"
        )
