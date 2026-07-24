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

import copy
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from seshat.stage1_scaffold import _is_unsafe_table

_MIGRATIONS_DIR = "warehouse/migrations"
_GENERATED_DIRS = ("warehouse/gold", "warehouse/schema")
_DBT_MODEL_LAYERS = ("staging", "marts", "audit")
_SELECTORS_REL = "dbt/selectors.yml"
_SOURCES_REL = "dbt/models/sources/_sources.yml"
_DAGSTER_RUNS_REL = ".seshat/dagster/runs"
_MIGRATION_MARKERS = ("_create_silver_", "_create_gold_")
_RAW_LANDING_ENV = "SESHAT_RAW_LANDING_DIR"

# Mirrors gitutil._GIT_HARDENING: neutralize config-driven exec vectors when
# git runs against the workspace tree (fsmonitor/hooks/ext-protocol).
_GIT_HARDENING = (
    "-c",
    "core.fsmonitor=false",
    "-c",
    f"core.hooksPath={os.devnull}",
    "-c",
    "protocol.ext.allow=never",
)
_GIT_NOT_A_REPO = 128


class ResetError(ValueError):
    """A documented refusal, named by ``reason`` (never a raw traceback)."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


class ResetExecutionError(RuntimeError):
    """A mid-execution OS failure; ``removed`` names what was already removed
    so the operator can complete the reset via git."""

    def __init__(self, message: str, removed: tuple[str, ...]) -> None:
        super().__init__(message)
        self.removed = removed


@dataclass(frozen=True)
class SharedFileEdit:
    """One surgical shared-file edit: remove only this table's rows.

    ``original_text`` pins the file content the edit was computed against;
    the executor refuses if the file changed since planning. ``new_text`` is
    the exact post-edit text (other tables' rows byte-identical); when the
    removal empties the whole file, ``remove_file`` is set instead.
    """

    path: str
    removed_rows: tuple[str, ...]
    original_text: str
    new_text: str
    remove_file: bool = False


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


def _owned_occurrence(name: str, table: str, start: int, known: frozenset[str]) -> bool:
    """``table`` occurs at ``start`` bounded by ``_``/``.``/end, and no LONGER
    known table id also matches there (``orders`` never claims
    ``orders_archive``'s files)."""
    end = start + len(table)
    if not name.startswith(table, start):
        return False
    if end != len(name) and name[end] not in "_.":
        return False
    return not any(
        other != table
        and len(other) > len(table)
        and name.startswith(other, start)
        and (start + len(other) == len(name) or name[start + len(other)] in "_.")
        for other in known
    )


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
        not any(
            outer_start <= start
            and end <= outer_end
            and (outer_start, outer_end) != (start, end)
            for outer_start, outer_end in other_spans
        )
        for start, end in own
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


def _generated_outputs(
    root: Path, table: str, known: frozenset[str]
) -> tuple[list[str], list[str]]:
    """(dirs, files) under warehouse/gold + warehouse/schema carrying the
    table's exact token."""
    dirs: list[str] = []
    files: list[str] = []
    for rel_dir in _GENERATED_DIRS:
        base = root / Path(*rel_dir.split("/"))
        if not base.is_dir():
            continue
        for entry in sorted(base.iterdir()):
            if not _name_carries_table(entry.name, table, known):
                continue
            rel = f"{rel_dir}/{entry.name}"
            if entry.is_dir() and not entry.is_symlink():
                dirs.append(rel)
            else:
                files.append(rel)
    return dirs, files


def _dagster_run_dirs(root: Path, table: str) -> list[str]:
    """Run dirs whose summary.json is scoped to EXACTLY this table (Q2).

    A run covering multiple tables is other tables' evidence too, so it is
    preserved; an unreadable summary is unattributable and preserved
    (fail-safe for evidence)."""
    runs = root / Path(*_DAGSTER_RUNS_REL.split("/"))
    if not runs.is_dir():
        return []
    matched: list[str] = []
    for run_dir in sorted(runs.iterdir()):
        if not run_dir.is_dir() or run_dir.is_symlink():
            continue
        try:
            payload = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(payload, dict) and payload.get("tables") == [table]:
            matched.append(f"{_DAGSTER_RUNS_REL}/{run_dir.name}")
    return matched


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
# Shared dbt files -- surgical, byte-faithful row removal (Q1)
# ---------------------------------------------------------------------------


def _read_shared(path: Path, rel: str) -> tuple[str, object]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            text = handle.read()
    except (OSError, UnicodeError) as exc:
        raise ResetError(
            "shared_file_unreadable",
            f"{rel} could not be read ({exc.__class__.__name__}); fix or "
            "remove it before resetting",
        ) from exc
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ResetError(
            "shared_file_unreadable",
            f"{rel} is not valid YAML ({exc.__class__.__name__}); it may "
            "carry rows for this table that cannot be removed safely -- fix "
            "it by hand before resetting",
        ) from exc
    return text, document


@dataclass(frozen=True)
class _Block:
    """One ``- ...`` sequence item as a line range [start, end)."""

    start: int
    end: int
    indent: int
    name: str | None


def _item_name(stripped: str) -> str | None:
    if not stripped.startswith("- name:"):
        return None
    value = stripped[len("- name:") :].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1]
    return value or None


def _sequence_blocks(lines: list[str]) -> list[_Block]:
    """Every ``- `` item block: the dash line plus its deeper-indented tail."""
    blocks: list[_Block] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        indent = len(line) - len(line.lstrip(" "))
        end = index + 1
        while end < len(lines):
            follower = lines[end]
            follower_indent = len(follower) - len(follower.lstrip(" "))
            if follower.strip() and follower_indent <= indent:
                break
            end += 1
        blocks.append(_Block(index, end, indent, _item_name(stripped)))
    return blocks


def _splice_out(lines: list[str], ranges: list[tuple[int, int]]) -> str:
    keep = list(lines)
    for start, end in sorted(ranges, reverse=True):
        del keep[start:end]
    return "".join(keep)


def _edit_refusal(rel: str) -> ResetError:
    return ResetError(
        "shared_file_edit_unsupported",
        f"{rel} carries rows for this table but is not in a shape this "
        "surgical edit can verify; remove the table's rows by hand and "
        "retry",
    )


def _verify_edit(rel: str, new_text: str, expected: object) -> None:
    """The byte-level edit must parse to EXACTLY the expected document."""
    try:
        actual = yaml.safe_load(new_text)
    except yaml.YAMLError:
        raise _edit_refusal(rel) from None
    if actual != expected:
        raise _edit_refusal(rel)


def _selectors_edit(root: Path, table: str) -> SharedFileEdit | None:
    path = root / Path(*_SELECTORS_REL.split("/"))
    if not path.is_file():
        return None
    text, document = _read_shared(path, _SELECTORS_REL)
    selector = f"seshat_table_{table}"
    rows = document.get("selectors") if isinstance(document, dict) else None
    if not isinstance(rows, list) or not any(
        isinstance(row, dict) and row.get("name") == selector for row in rows
    ):
        return None
    expected_rows = [
        row
        for row in rows
        if not (isinstance(row, dict) and row.get("name") == selector)
    ]
    expected = {**document, "selectors": expected_rows}
    lines = text.splitlines(keepends=True)
    targets = [
        (block.start, block.end)
        for block in _sequence_blocks(lines)
        if block.name == selector
    ]
    if not targets:
        raise _edit_refusal(_SELECTORS_REL)
    new_text = _splice_out(lines, targets)
    if not expected_rows and len(expected) == 1:
        new_text = "selectors: []\n"
    _verify_edit(_SELECTORS_REL, new_text, expected)
    return SharedFileEdit(
        path=_SELECTORS_REL,
        removed_rows=(f"selector {selector}",),
        original_text=text,
        new_text=new_text,
    )


def _marts_model_names(root: Path, table: str) -> frozenset[str]:
    """The gold model names this table emitted (its marts .sql stems) -- the
    only rows of the shared ``migration_gold`` source group attributable to
    this table (a reused conformed dimension is owned elsewhere and never
    listed by the reuser)."""
    marts = root / "dbt" / "models" / "marts" / table
    if not marts.is_dir():
        return frozenset()
    return frozenset(
        entry.stem
        for entry in marts.iterdir()
        if entry.is_file() and entry.suffix == ".sql"
    )


def _rows_to_remove(
    document: dict, table: str, gold_names: frozenset[str]
) -> dict[str, set[str]]:
    removable = {"bronze": {table}, "migration_gold": set(gold_names)}
    planned: dict[str, set[str]] = {}
    for group in document.get("sources", []) or []:
        if not isinstance(group, dict):
            continue
        group_name = group.get("name")
        allowed = removable.get(group_name)
        if allowed is None:
            continue
        tables = group.get("tables")
        if not isinstance(tables, list):
            continue
        matched = {
            row.get("name")
            for row in tables
            if isinstance(row, dict) and row.get("name") in allowed
        }
        if matched:
            planned[group_name] = matched
    return planned


def _expected_sources(document: dict, planned: dict[str, set[str]]) -> dict:
    expected = copy.deepcopy(document)
    remaining_groups: list = []
    for group in expected.get("sources", []) or []:
        if isinstance(group, dict) and group.get("name") in planned:
            removed = planned[group["name"]]
            group["tables"] = [
                row
                for row in group.get("tables", [])
                if not (isinstance(row, dict) and row.get("name") in removed)
            ]
            if not group["tables"]:
                continue
        remaining_groups.append(group)
    expected["sources"] = remaining_groups
    return expected


def _sources_row_ranges(
    lines: list[str], planned: dict[str, set[str]], expected: dict
) -> list[tuple[int, int]]:
    """Line ranges to splice out: whole emptied groups, else single rows."""
    surviving = {
        group.get("name")
        for group in expected.get("sources", [])
        if isinstance(group, dict)
    }
    blocks = _sequence_blocks(lines)
    top_indent = min(block.indent for block in blocks)
    ranges: list[tuple[int, int]] = []
    current_group: str | None = None
    for block in blocks:
        if block.indent == top_indent:
            current_group = block.name
            if current_group in planned and current_group not in surviving:
                ranges.append((block.start, block.end))
        elif (
            current_group in planned
            and current_group in surviving
            and block.name in planned[current_group]
        ):
            ranges.append((block.start, block.end))
    return ranges


def _sources_edit(root: Path, table: str) -> SharedFileEdit | None:
    path = root / Path(*_SOURCES_REL.split("/"))
    if not path.is_file():
        return None
    text, document = _read_shared(path, _SOURCES_REL)
    if not isinstance(document, dict):
        raise ResetError(
            "shared_file_unreadable",
            f"{_SOURCES_REL} is not a YAML mapping; fix it by hand before resetting",
        )
    planned = _rows_to_remove(document, table, _marts_model_names(root, table))
    if not planned:
        return None
    expected = _expected_sources(document, planned)
    removed_rows = tuple(
        f"{group}: {name}"
        for group in sorted(planned)
        for name in sorted(planned[group])
    )
    if not expected["sources"]:
        # Every group emptied: the shared file is entirely this table's
        # residue, so the plan removes the file itself.
        return SharedFileEdit(
            path=_SOURCES_REL,
            removed_rows=removed_rows,
            original_text=text,
            new_text="",
            remove_file=True,
        )
    lines = text.splitlines(keepends=True)
    ranges = _sources_row_ranges(lines, planned, expected)
    if not ranges:
        raise _edit_refusal(_SOURCES_REL)
    new_text = _splice_out(lines, ranges)
    _verify_edit(_SOURCES_REL, new_text, expected)
    return SharedFileEdit(
        path=_SOURCES_REL,
        removed_rows=removed_rows,
        original_text=text,
        new_text=new_text,
    )


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


def _validate_plan(root: Path, plan: ResetPlan) -> None:
    """Fail closed BEFORE removing anything: every planned path still exists,
    resolves strictly under root with no symlink escapes, and every shared
    file is byte-identical to what the plan was computed against."""
    for rel in [*plan.remove_dirs, *plan.remove_files]:
        target = root / Path(*rel.split("/"))
        if not (target.exists() or target.is_symlink()):
            raise ResetError(
                "plan_stale",
                f"planned path no longer exists: {rel} -- re-run the plan",
            )
        _guard_removable_within_root(root, rel)
    for edit in plan.shared_edits:
        target = root / Path(*edit.path.split("/"))
        _guard_removable_within_root(root, edit.path)
        try:
            with target.open("r", encoding="utf-8", newline="") as handle:
                current = handle.read()
        except (OSError, UnicodeError) as exc:
            raise ResetError(
                "plan_stale",
                f"planned shared file could not be re-read: {edit.path} "
                f"({exc.__class__.__name__}) -- re-run the plan",
            ) from exc
        if current != edit.original_text:
            raise ResetError(
                "shared_file_changed",
                f"{edit.path} changed since the plan was computed -- re-run the plan",
            )


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


def _shared_residue(root: Path, table: str, plan: ResetPlan) -> list[str]:
    findings: list[str] = []
    selectors = root / Path(*_SELECTORS_REL.split("/"))
    if selectors.is_file():
        try:
            document = yaml.safe_load(selectors.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError):
            findings.append(f"{_SELECTORS_REL} could not be verified")
            document = None
        rows = document.get("selectors") if isinstance(document, dict) else []
        if isinstance(rows, list) and any(
            isinstance(row, dict) and row.get("name") == f"seshat_table_{table}"
            for row in rows
        ):
            findings.append(
                f"{_SELECTORS_REL} still carries selector seshat_table_{table}"
            )
    findings.extend(_sources_residue(root, table, plan))
    return findings


def _sources_residue(root: Path, table: str, plan: ResetPlan) -> list[str]:
    sources = root / Path(*_SOURCES_REL.split("/"))
    if not sources.is_file():
        return []
    try:
        document = yaml.safe_load(sources.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        return [f"{_SOURCES_REL} could not be verified"]
    planned_rows = {
        row
        for edit in plan.shared_edits
        if edit.path == _SOURCES_REL
        for row in edit.removed_rows
    }
    findings: list[str] = []
    for group in document.get("sources", []) if isinstance(document, dict) else []:
        if not isinstance(group, dict):
            continue
        for row in group.get("tables") or []:
            if not isinstance(row, dict):
                continue
            label = f"{group.get('name')}: {row.get('name')}"
            is_bronze_row = group.get("name") == "bronze" and row.get("name") == table
            if is_bronze_row or label in planned_rows:
                findings.append(f"{_SOURCES_REL} still carries row {label}")
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
