"""Seshat Studio -- the optional localhost analyst console (spec 139).

Studio is downstream of Core Authority. It projects readiness truth that existing
Seshat services already derive; it does not derive readiness itself, execute tools
in browser code, record named-human business decisions, or introduce a database.

**Import discipline.** Nothing in this package may import FastAPI, Uvicorn, or
Starlette at module scope. The web stack lives in the optional ``studio`` extra
(FR-006), so a base ``seshat-bi`` install must be able to import this package and
receive a named diagnostic rather than an ``ImportError`` traceback. The same
discipline keeps ``seshat check`` and CI from ever loading the web stack, mirroring
the ``pbi_mcp`` family's documented laziness.
"""

from __future__ import annotations

#: Top-level module names the ``studio`` extra provides.
#:
#: The launcher gates its missing-extra diagnostic on this set: a
#: ``ModuleNotFoundError`` naming one of these means the extra really is absent,
#: while one naming anything else means the extra is installed but a transitive
#: dependency is broken. Without the gate, a broken dependency was reported as an
#: absent extra and the reader was told to install what they already had.
#:
#: These are IMPORT names, deliberately not version specs: the authority on versions
#: is ``pyproject.toml``, mirrored for the install-hint surface by
#: ``seshat.cli._EXTRA_DEPENDENCIES`` and pinned to it by
#: ``test_the_studio_dependency_table_matches_pyproject``.
WEB_DEPENDENCIES: frozenset[str] = frozenset({"fastapi", "uvicorn"})

__all__ = ["WEB_DEPENDENCIES"]
