"""Shared star-discovery primitives (issue #418).

A TOP-LEVEL module (sibling of ``seshat.core``), deliberately NOT under
``seshat.dbt``: it is consumed by both the ``seshat.rules`` static-core gate
(HR1) and the ``seshat.dbt`` scaffold, and importing it must never drag
``seshat.dbt`` onto the base-CLI import path (spec 135 T003 / spec 134 FR-001 --
``import seshat.cli`` loads no governed dbt adapter). Placing it here keeps both
consumers above it and the CLI-laziness contract intact.

Pure and dependency-free: NO database driver, NO ``seshat.rules`` /
``RuleContext`` import, and ``yaml`` is never needed here (callers parse YAML
themselves and inject a ``load`` callable). Both HR1 (worktree read via its
``RuleContext``) and ``seshat dbt scaffold`` (committed ``git show HEAD:`` read)
consume this, so the governance gate and the generator can never disagree on
what a star is, how a star id resolves, or which dimensions a star declares.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from seshat.core import is_test_path

_MAPPING_RE = re.compile(r"^mappings/([^/]+)/source-map\.yaml$")


def bare_dim_name(name: object) -> str | None:
    """Bare dimension name: strip an optional ``<schema>.`` prefix, lowercased."""
    if not isinstance(name, str) or not name.strip():
        return None
    return name.rsplit(".", 1)[-1].strip().lower()


def star_id(document: dict, table_dir: str) -> str:
    """The governed star id: ``meta.table_id`` -> ``source_id`` -> ``table_dir``."""
    meta = document.get("meta")
    if isinstance(meta, dict) and isinstance(meta.get("table_id"), str):
        return meta["table_id"]
    if isinstance(document.get("source_id"), str):
        return document["source_id"]
    return table_dir


def is_star(document: dict) -> bool:
    gs = document.get("gold_star")
    return isinstance(gs, dict) and gs.get("fact") is not None


def _add_dim(out: dict[str, dict], raw: object, *, overwrite: bool) -> None:
    if not isinstance(raw, dict):
        return
    b = bare_dim_name(raw.get("name"))
    if not b:
        return
    if overwrite:
        out[b] = raw
    else:
        out.setdefault(b, raw)


def star_dimensions(document: dict) -> dict[str, dict]:
    """bare-name -> raw dim dict (explicit dims + date_dimension; degenerate excluded).

    Explicit dims are last-wins; the standalone ``date_dimension`` is first-wins
    (never displaces an explicit dim). Degenerate dimensions are never traversed.
    """
    out: dict[str, dict] = {}
    gs = document.get("gold_star")
    if not isinstance(gs, dict):
        return out
    dims = gs.get("dimensions")
    if isinstance(dims, list):
        for dim in dims:
            _add_dim(out, dim, overwrite=True)
    _add_dim(out, gs.get("date_dimension"), overwrite=False)
    return out


def discover_stars(
    tracked_files: Iterable[str],
    load: Callable[[str], dict | None],
) -> dict[str, dict]:
    """``{star_id: document}`` for every non-test ``mappings/<dir>/source-map.yaml``
    that ``load`` returns and that ``is_star``.

    ``load`` (returning ``None`` on any parse/read failure) is the caller's I/O
    strategy -- HR1 reads the worktree via its ``RuleContext``; scaffold reads the
    committed HEAD blob via ``git show``. Keeping I/O injected leaves this module
    dependency-free and lets both callers share one definition of star identity.
    """
    found: dict[str, dict] = {}
    for rel in sorted(tracked_files):
        if is_test_path(rel):
            continue
        m = _MAPPING_RE.match(rel)
        if not m:
            continue
        data = load(rel)
        if data is None or not is_star(data):
            continue
        found[star_id(data, m.group(1))] = data
    return found
