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

#: Distributions the ``studio`` extra pulls in, named for diagnostics only. The
#: authority is ``pyproject.toml``; ``seshat.cli._EXTRA_DEPENDENCIES`` mirrors it
#: for the install-hint surface, and a unit test pins all three together.
WEB_DEPENDENCIES: tuple[str, ...] = ("fastapi", "uvicorn")

__all__ = ["WEB_DEPENDENCIES"]
