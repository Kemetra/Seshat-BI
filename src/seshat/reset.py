"""Plan and execute ``seshat reset <table>`` -- tear ONE table back to Source (#433).

Resetting a completed table by hand requires deleting the exact derived
file-set only the engine knows; an INCOMPLETE manual reset is the documented
root of #430 (check crash on an unstaged deletion) and #431 (dbt layout
collision). This module makes the reset complete and fail-closed:

* ``plan_reset(root, table)`` -- a PURE planner: enumerates the exact derived
  paths plus the surgical shared-file row edits; reads the tree, writes
  nothing.
* ``execute_reset(root, plan)`` -- validates the ENTIRE plan (paths still
  present, every path strictly under root, no symlink escapes, shared files
  unchanged since planning) BEFORE removing anything, then performs the
  removals + surgical edits and stages exactly the touched paths
  (``git add -A -- <paths>``) so ``seshat check`` runs clean afterwards
  (the #430 workaround made native).
* ``verify_reset(root, table, plan)`` -- inspects the ACTUAL artifacts for
  residual state. Deliberately NOT ``.seshat/manifest.yaml``: that manifest
  records the kit's integrity fingerprint, never onboarded tables, so it is a
  false clean-state signal.

The reset REMOVES only derived, table-scoped state: ``mappings/<table>/``
(incl. ``dbt-evidence/``), the exact-token silver/gold DDL migrations,
generated ``warehouse/gold``/``warehouse/schema`` outputs, the three nested
``dbt/models/<layer>/<table>/`` folders, the table's rows in the shared dbt
files, and the table-scoped dagster run evidence under
``.seshat/dagster/runs/`` (never the materialized ``orchestration/dagster/``
project -- Q2). It PRESERVES the bronze landing and everything of other
tables, and NEVER touches a live database.

Prefix-collision guard (load-bearing): migrations are matched by the FULL
token ``_create_(silver|gold)_<table>`` immediately followed by ``_`` or
``.``, never a bare ``<table>*`` glob -- and an occurrence claimed by a
LONGER onboarded table id (``orders`` vs ``orders_archive``) is never swept.

Authorized build from the design brief
(docs/superpowers/specs/2026-07-23-seshat-reset-verb-design.md); the owner
settled Q1=(a) surgical shared-file row removal, Q2=(b) run evidence only,
Q3=confirm + ``--yes``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from seshat.gitutil import GIT_HARDENING as _GIT_HARDENING
from seshat.reset_shared import (
    _SELECTORS_REL,
    _SOURCES_REL,
    ResetError,
    SharedFileEdit,
    _has_named_row,
    _selectors_edit,
    _sources_edit,
)
from seshat.stage1_scaffold import _is_unsafe_table

_MIGRATIONS_DIR = "warehouse/migrations"
_GENERATED_DIRS = ("warehouse/gold", "warehouse/schema")
_DBT_MODEL_LAYERS = ("staging", "marts", "audit")
_DAGSTER_RUNS_REL = ".seshat/dagster/runs"
_MIGRATION_MARKERS = ("_create_silver_", "_create_gold_")
_RAW_LANDING_ENV = "SESHAT_RAW_LANDING_DIR"

_GIT_NOT_A_REPO = 128


class ResetExecutionError(RuntimeError):
    """A mid-execution OS failure; ``removed`` names what was already removed
    so the operator can complete the reset via git."""

    def __init__(self, message: str, removed: tuple[str, ...]) -> None:
        super().__init__(message)
        self.removed = removed


@dataclass(frozen=True)
class ResetPlan:
    """The exact derived file-set for one table (repo-relative POSIX paths)."""

    table: str
    remove_dirs: tuple[str, ...]
    remove_files: tuple[str, ...]
    shared_edits: tuple[SharedFileEdit, ...]
    preserved: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        return not (self.remove_dirs or self.remove_files or self.shared_edits)


@dataclass(frozen=True)
class ResetReport:
    """What one ``execute_reset`` call did."""

    removed: tuple[str, ...]
    edited: tuple[str, ...]
    staged: tuple[str, ...]
    staging_note: str | None


# ---------------------------------------------------------------------------
# Table-name safety (reuses stage1_scaffold's real validation predicate)
# ---------------------------------------------------------------------------


def _validate_table(table: str) -> str:
    if _is_unsafe_table(table):
        raise ResetError(
            "unsafe_table",
            f"unsafe table segment: {table!r} (must be a plain name -- no "
            "path separators, traversal, invalid filename characters, or "
            "Windows reserved device names)",
        )
    return table


# ---------------------------------------------------------------------------
# Exact-token matching (the prefix-collision guard)
# ---------------------------------------------------------------------------


def _known_tables(root: Path, table: str) -> frozenset[str]:
    """Every onboarded table id (mappings/ folder names) plus the target."""
    names = {table}
    mappings = root / "mappings"
    if mappings.is_dir():
        names.update(entry.name for entry in mappings.iterdir() if entry.is_dir())
    return frozenset(names)


def _token_bounded_at(name: str, token: str, start: int) -> bool:
    """``token`` occurs at ``start`` and ends at ``_``, ``.``, or end-of-name."""
    if not name.startswith(token, start):
        return False
    end = start + len(token)
    return end == len(name) or name[end] in "_."


def _claimed_by_longer(
    name: str, table: str, start: int, known: frozenset[str]
) -> bool:
    """A LONGER known table id also matches at ``start`` and owns the occurrence."""
    return any(
        other != table
        and len(other) > len(table)
        and _token_bounded_at(name, other, start)
        for other in known
    )


def _owned_occurrence(name: str, table: str, start: int, known: frozenset[str]) -> bool:
    """``table`` occurs at ``start`` bounded by ``_``/``.``/end, and no LONGER
    known table id also matches there (``orders`` never claims
    ``orders_archive``'s files)."""
    if not _token_bounded_at(name, table, start):
        return False
    return not _claimed_by_longer(name, table, start, known)


def _migration_matches(filename: str, table: str, known: frozenset[str]) -> bool:
    """FULL-token migration match: ``_create_(silver|gold)_<table>`` followed
    by ``_`` or ``.`` -- never a bare prefix glob."""
    if not filename.endswith(".sql"):
        return False
    for marker in _MIGRATION_MARKERS:
        position = filename.find(marker)
        while position >= 0:
            if _owned_occurrence(filename, table, position + len(marker), known):
                return True
            position = filename.find(marker, position + 1)
    return False


def _bounded_spans(name: str, token: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    index = name.find(token)
    while index >= 0:
        end = index + len(token)
        left_ok = index == 0 or name[index - 1] in "_."
        right_ok = end == len(name) or name[end] in "_."
        if left_ok and right_ok:
            spans.append((index, end))
        index = name.find(token, index + 1)
    return spans


def _span_covered_by_other(
    start: int, end: int, other_spans: list[tuple[int, int]]
) -> bool:
    """The span sits inside a strictly larger span of another table id."""
    return any(
        outer_start <= start
        and end <= outer_end
        and (outer_start, outer_end) != (start, end)
        for outer_start, outer_end in other_spans
    )


def _name_carries_table(name: str, table: str, known: frozenset[str]) -> bool:
    """Exact-token occurrence of ``table`` in a generated artifact name that is
    not explainable as part of a LONGER known table id's occurrence."""
    own = _bounded_spans(name, table)
    if not own:
        return False
    other_spans = [
        span
        for other in known
        if other != table
        for span in _bounded_spans(name, other)
    ]
    return any(
        not _span_covered_by_other(start, end, other_spans) for start, end in own
    )


# ---------------------------------------------------------------------------
# Path enumeration
# ---------------------------------------------------------------------------


def _guard_removable_within_root(root: Path, rel: str) -> None:
    """Refuse a planned path with any symlinked component, one that IS a
    symlink, or one resolving outside ``root`` (mirrors
    ``stage1_scaffold._guard_destination_within_root`` for removals)."""
    target = root / Path(*rel.split("/"))
    component = target
    while True:
        if component.is_symlink():
            raise ResetError(
                "path_escape",
                f"refusing to remove through a symlinked path component: "
                f"{component} is a symlink (it could remove the wrong table "
                "scope or escape --repo); remove the link and retry",
            )
        if component == root or component.parent == component:
            break
        component = component.parent
    resolved = target.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ResetError(
            "path_escape",
            f"refusing to remove outside the repository: {rel!r} resolves to "
            f"{resolved}, which is not under {root}",
        ) from None


def _table_dirs(root: Path, table: str) -> list[str]:
    candidates = [f"mappings/{table}"] + [
        f"dbt/models/{layer}/{table}" for layer in _DBT_MODEL_LAYERS
    ]
    return [
        rel
        for rel in candidates
        if (root / Path(*rel.split("/"))).is_dir()
        or (root / Path(*rel.split("/"))).is_symlink()
    ]


def _migration_files(root: Path, table: str, known: frozenset[str]) -> list[str]:
    migrations = root / Path(*_MIGRATIONS_DIR.split("/"))
    if not migrations.is_dir():
        return []
    return [
        f"{_MIGRATIONS_DIR}/{entry.name}"
        for entry in sorted(migrations.iterdir())
        if entry.is_file() and _migration_matches(entry.name, table, known)
    ]


def _split_generated_entries(
    base: Path, rel_dir: str, table: str, known: frozenset[str]
) -> tuple[list[str], list[str]]:
    """(dirs, files) directly under ``base`` carrying the table's exact token."""
    dirs: list[str] = []
    files: list[str] = []
    for entry in sorted(base.iterdir()):
        if not _name_carries_table(entry.name, table, known):
            continue
        target = dirs if entry.is_dir() and not entry.is_symlink() else files
        target.append(f"{rel_dir}/{entry.name}")
    return dirs, files


def _generated_outputs(
    root: Path, table: str, known: frozenset[str]
) -> tuple[list[str], list[str]]:
    """(dirs, files) under warehouse/gold + warehouse/schema carrying the
    table's exact token."""
    dirs: list[str] = []
    files: list[str] = []
    for rel_dir in _GENERATED_DIRS:
        base = root / Path(*rel_dir.split("/"))
        if base.is_dir():
            sub_dirs, sub_files = _split_generated_entries(base, rel_dir, table, known)
            dirs.extend(sub_dirs)
            files.extend(sub_files)
    return dirs, files


def _run_scoped_to(run_dir: Path, table: str) -> bool:
    """summary.json says the run covered EXACTLY this table; an unreadable
    summary is unattributable and preserved (fail-safe for evidence)."""
    if not run_dir.is_dir() or run_dir.is_symlink():
        return False
    try:
        payload = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(payload, dict) and payload.get("tables") == [table]


def _dagster_run_dirs(root: Path, table: str) -> list[str]:
    """Run dirs whose summary.json is scoped to EXACTLY this table (Q2).

    A run covering multiple tables is other tables' evidence too, so it is
    preserved."""
    runs = root / Path(*_DAGSTER_RUNS_REL.split("/"))
    if not runs.is_dir():
        return []
    return [
        f"{_DAGSTER_RUNS_REL}/{run_dir.name}"
        for run_dir in sorted(runs.iterdir())
        if _run_scoped_to(run_dir, table)
    ]


def _preserved(root: Path, table: str) -> tuple[str, ...]:
    """The bronze landing paths reset deliberately keeps (display only)."""
    kept: list[str] = []
    if (root / "data" / "raw" / f"{table}.csv").is_file():
        kept.append(f"data/raw/{table}.csv")
    landing_dir = os.environ.get(_RAW_LANDING_ENV)
    if landing_dir and (Path(landing_dir) / f"{table}.csv").is_file():
        kept.append(str(Path(landing_dir) / f"{table}.csv"))
    return tuple(kept)


# ---------------------------------------------------------------------------
# The planner
# ---------------------------------------------------------------------------


def plan_reset(repo_root: Path | str, table: str) -> ResetPlan:
    """Enumerate the exact derived file-set for ``table`` (pure; no writes).

    Raises :class:`ResetError` (named reason) on an unsafe table segment --
    BEFORE any filesystem access -- or on a path-safety / shared-file hazard.
    """
    table = _validate_table(table)
    root = Path(repo_root).resolve()
    known = _known_tables(root, table)
    generated_dirs, generated_files = _generated_outputs(root, table, known)
    remove_dirs = (
        _table_dirs(root, table) + generated_dirs + _dagster_run_dirs(root, table)
    )
    remove_files = _migration_files(root, table, known) + generated_files
    for rel in [*remove_dirs, *remove_files]:
        _guard_removable_within_root(root, rel)
    shared_edits = tuple(
        edit
        for edit in (_selectors_edit(root, table), _sources_edit(root, table))
        if edit is not None
    )
    return ResetPlan(
        table=table,
        remove_dirs=tuple(remove_dirs),
        remove_files=tuple(remove_files),
        shared_edits=shared_edits,
        preserved=_preserved(root, table),
    )


# ---------------------------------------------------------------------------
# The executor
# ---------------------------------------------------------------------------


def _validate_removals(root: Path, plan: ResetPlan) -> None:
    """Every planned removal still exists and resolves strictly under root."""
    for rel in [*plan.remove_dirs, *plan.remove_files]:
        target = root / Path(*rel.split("/"))
        if not (target.exists() or target.is_symlink()):
            raise ResetError(
                "plan_stale",
                f"planned path no longer exists: {rel} -- re-run the plan",
            )
        _guard_removable_within_root(root, rel)


def _reread_shared(root: Path, edit: SharedFileEdit) -> str:
    target = root / Path(*edit.path.split("/"))
    try:
        with target.open("r", encoding="utf-8", newline="") as handle:
            return handle.read()
    except (OSError, UnicodeError) as exc:
        raise ResetError(
            "plan_stale",
            f"planned shared file could not be re-read: {edit.path} "
            f"({exc.__class__.__name__}) -- re-run the plan",
        ) from exc


def _validate_shared_edits(root: Path, plan: ResetPlan) -> None:
    """Every shared file is byte-identical to what the plan was computed
    against, and its path resolves strictly under root."""
    for edit in plan.shared_edits:
        _guard_removable_within_root(root, edit.path)
        if _reread_shared(root, edit) != edit.original_text:
            raise ResetError(
                "shared_file_changed",
                f"{edit.path} changed since the plan was computed -- re-run the plan",
            )


def _validate_plan(root: Path, plan: ResetPlan) -> None:
    """Fail closed BEFORE removing anything: every planned path still exists,
    resolves strictly under root with no symlink escapes, and every shared
    file is byte-identical to what the plan was computed against."""
    _validate_removals(root, plan)
    _validate_shared_edits(root, plan)


def _remove_planned_paths(root: Path, plan: ResetPlan) -> list[str]:
    removed: list[str] = []
    try:
        for rel in plan.remove_dirs:
            shutil.rmtree(root / Path(*rel.split("/")))
            removed.append(rel)
        for rel in plan.remove_files:
            (root / Path(*rel.split("/"))).unlink()
            removed.append(rel)
    except OSError as exc:
        raise ResetExecutionError(
            f"removal failed at {rel}: {exc} -- the paths listed as removed "
            "are already gone; complete or undo the reset via git",
            tuple(removed),
        ) from exc
    return removed


def _apply_shared_edits(root: Path, plan: ResetPlan, removed: list[str]) -> list[str]:
    edited: list[str] = []
    try:
        for edit in plan.shared_edits:
            target = root / Path(*edit.path.split("/"))
            if edit.remove_file:
                target.unlink()
                removed.append(edit.path)
            else:
                with target.open("w", encoding="utf-8", newline="") as handle:
                    handle.write(edit.new_text)
                edited.append(edit.path)
    except OSError as exc:
        raise ResetExecutionError(
            f"shared-file edit failed at {edit.path}: {exc} -- the paths "
            "listed as removed are already gone; complete or undo the reset "
            "via git",
            tuple(removed),
        ) from exc
    return edited


def _stage_paths(
    root: Path, paths: list[str], removed: tuple[str, ...]
) -> tuple[tuple[str, ...], str | None]:
    """``git add -A -- <paths>`` (the SPECIFIC touched paths, never a blanket
    ``-A``). A non-git workspace is a note, not a failure."""
    if not paths:
        return (), None
    result = subprocess.run(
        ["git", *_GIT_HARDENING, "-C", str(root), "add", "-A", "--", *paths],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    if result.returncode == 0:
        return tuple(paths), None
    if result.returncode == _GIT_NOT_A_REPO:
        return (), "not a git repository -- nothing staged"
    stderr = (result.stderr or "").strip()[:300]
    raise ResetExecutionError(
        f"git staging failed ({result.returncode}): {stderr} -- the removals "
        "are done but UNSTAGED; stage them yourself before running "
        "`seshat check` (#430)",
        removed,
    )


def execute_reset(repo_root: Path | str, plan: ResetPlan) -> ResetReport:
    """Validate the ENTIRE plan, then remove + edit + stage. File-tree only:
    never touches a live database."""
    root = Path(repo_root).resolve()
    _validate_plan(root, plan)
    removed = _remove_planned_paths(root, plan)
    edited = _apply_shared_edits(root, plan, removed)
    staged, staging_note = _stage_paths(root, [*removed, *edited], tuple(removed))
    return ResetReport(
        removed=tuple(removed),
        edited=tuple(edited),
        staged=staged,
        staging_note=staging_note,
    )


# ---------------------------------------------------------------------------
# Verification -- the ACTUAL artifacts, never .seshat/manifest.yaml
# ---------------------------------------------------------------------------


def _selectors_residue(root: Path, table: str) -> list[str]:
    selectors = root / Path(*_SELECTORS_REL.split("/"))
    if not selectors.is_file():
        return []
    try:
        document = yaml.safe_load(selectors.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        return [f"{_SELECTORS_REL} could not be verified"]
    rows = document.get("selectors") if isinstance(document, dict) else []
    if _has_named_row(rows, f"seshat_table_{table}"):
        return [f"{_SELECTORS_REL} still carries selector seshat_table_{table}"]
    return []


def _shared_residue(root: Path, table: str, plan: ResetPlan) -> list[str]:
    findings = _selectors_residue(root, table)
    findings.extend(_sources_residue(root, table, plan))
    return findings


def _planned_source_rows(plan: ResetPlan) -> set[str]:
    """The ``group: name`` labels the plan claimed to remove from _sources.yml."""
    return {
        row
        for edit in plan.shared_edits
        if edit.path == _SOURCES_REL
        for row in edit.removed_rows
    }


def _row_is_residue(group: dict, row: dict, table: str, planned_rows: set[str]) -> bool:
    """The row is this table's bronze row or one the plan claimed to remove."""
    if group.get("name") == "bronze" and row.get("name") == table:
        return True
    return f"{group.get('name')}: {row.get('name')}" in planned_rows


def _group_residue(group: object, table: str, planned_rows: set[str]) -> list[str]:
    """Residual-row findings within one sources group."""
    if not isinstance(group, dict):
        return []
    return [
        f"{_SOURCES_REL} still carries row {group.get('name')}: {row.get('name')}"
        for row in group.get("tables") or []
        if isinstance(row, dict) and _row_is_residue(group, row, table, planned_rows)
    ]


def _sources_residue(root: Path, table: str, plan: ResetPlan) -> list[str]:
    sources = root / Path(*_SOURCES_REL.split("/"))
    if not sources.is_file():
        return []
    try:
        document = yaml.safe_load(sources.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        return [f"{_SOURCES_REL} could not be verified"]
    planned_rows = _planned_source_rows(plan)
    findings: list[str] = []
    for group in document.get("sources", []) if isinstance(document, dict) else []:
        findings.extend(_group_residue(group, table, planned_rows))
    return findings


def verify_reset(repo_root: Path | str, table: str, plan: ResetPlan) -> tuple[str, ...]:
    """Residual-state findings after a reset; empty means truthfully fresh.

    Inspects the actual artifacts (mappings dir, exact-token migrations, the
    three dbt model dirs, shared dbt rows) -- NOT ``.seshat/manifest.yaml``,
    which never records tables and would give a false all-clear.
    """
    root = Path(repo_root).resolve()
    findings: list[str] = []
    if (root / "mappings" / table).exists():
        findings.append(f"mappings/{table}/ still exists")
    for rel in _migration_files(root, table, _known_tables(root, table)):
        findings.append(f"exact-token migration remains: {rel}")
    for layer in _DBT_MODEL_LAYERS:
        if (root / "dbt" / "models" / layer / table).exists():
            findings.append(f"dbt/models/{layer}/{table}/ still exists")
    findings.extend(_shared_residue(root, table, plan))
    return tuple(findings)
