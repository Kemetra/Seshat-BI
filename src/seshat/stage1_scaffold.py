"""Materialize the three Stage-1 blank templates into any workspace (#339).

The first governed action (Source Ready / Stage 1) requires a
template-conformant ``source-profile.md`` plus a ``readiness-status.yaml`` and
``source-map.yaml``. Those blank templates previously shipped only with the
development repository, so a bare ``pip install seshat-bi`` left a new user
with nothing to copy -- violating the portable operating contract's "Never
require the Seshat development repository for normal use".

``scaffold_source`` closes that gap by writing the three blanks into
``mappings/<table>/`` from bundled package data (wheel force-include; a
development checkout falls back to the repo ``templates/`` dir, mirroring
``seshat.governed_projects``). Only table-neutral blank templates ship
(constitution VII). Writes are per-file non-destructive: an existing file is
always kept, never overwritten. Pure stdlib -- no DB, no network.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[2]
_PACKAGED_ROOT = "stage1_templates"

# The three Stage-1 blank templates (issue #339). Exactly these -- the other
# ~60 templates stay dev-only (YAGNI + constitution VII).
_STAGE1_FILES: tuple[str, ...] = (
    "source-profile.md",
    "readiness-status.yaml",
    "source-map.yaml",
)

# source-profile.md carries one dev-repo relative link that dangles once the
# file is materialized under mappings/<table>/. Neutralize to bare text so the
# stub is self-contained. (Everything else is copied byte-for-byte.)
_BROKEN_LINK = "[ADR 0003](../docs/decisions/0003-mapping-artifact-location.md)"
_LINK_REPLACEMENT = "ADR 0003 (mapping-artifact-location)"

# readiness-status.yaml ships current_stage as a "<stage_key>" placeholder,
# which RS1 rejects the moment the workspace is committed. A just-onboarded
# table honestly IS at the first stage (source_ready, not-yet-passed) -- this is
# a truthful stage LABEL, never fabricated evidence/approvals (which stay empty),
# so the committed scaffold passes `retail check` as an unstarted journey.
_READINESS_PLACEHOLDER_STAGE = 'current_stage: "<stage_key>"'
_READINESS_INITIAL_STAGE = 'current_stage: "source_ready"'

# source-map.yaml's meta.profiled_from points at the dev-repo template path,
# which a pip-only workspace does not have. Retarget it at the materialized
# profile so a completed map cites the profile it actually rests on.
_SOURCE_MAP_PROFILE_REF = 'profiled_from: "templates/source-profile.md"'


class Stage1ScaffoldError(ValueError):
    """Raised when ``table`` is not a safe single path segment."""


@dataclass(frozen=True)
class Stage1Report:
    """What one ``scaffold_source`` call did, per file, plus operator notes."""

    written: tuple[str, ...]
    kept: tuple[str, ...]
    notes: tuple[str, ...]


# A safe ``table`` is a single path segment: non-empty, not a traversal token,
# and free of any path separator. Kept as a data-driven predicate set so the
# guard stays a flat ``any(...)`` rather than a multi-branch boolean.
_UNSAFE_TABLE_TOKENS = frozenset({"", ".", ".."})
_PATH_SEPARATORS = ("/", "\\")

# Characters that are invalid in a Windows filename (and a portable red flag on
# any OS). A name containing one cannot be created as a directory, so it must be
# refused as a documented Stage1ScaffoldError rather than crash at mkdir.
_INVALID_FILENAME_CHARS = frozenset(':*?"<>|')

# Windows reserved DEVICE names: these match the identifier charset yet fail at
# directory creation on Windows (case-insensitively, with or without an
# extension). Compared on the pre-extension stem, lowercased.
_WINDOWS_RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{i}" for i in range(1, 10)}
    | {f"lpt{i}" for i in range(1, 10)}
)


def _has_invalid_char(table: str) -> bool:
    return any(char in _INVALID_FILENAME_CHARS for char in table)


def _has_path_separator(table: str) -> bool:
    return any(sep in table for sep in _PATH_SEPARATORS)


def _is_windows_reserved(table: str) -> bool:
    # Compared on the pre-extension stem, lowercased (CON, aux, com1, ...).
    return table.split(".", 1)[0].lower() in _WINDOWS_RESERVED_NAMES


def _has_trimmed_suffix(table: str) -> bool:
    # Win32 strips a trailing dot or space, so ``orders.`` / ``orders `` would
    # normalize to a DIFFERENT folder than reported; a leading one is equally a
    # red flag. Refuse rather than silently operate on the wrong table.
    return table != table.strip(" .")


# Each predicate names one reason a ``table`` cannot be a safe, portably-
# createable path segment. Kept as a flat tuple so the guard is a single
# ``any(...)`` rather than a multi-branch method (CodeScene complexity guard).
_UNSAFE_TABLE_PREDICATES = (
    lambda t: t in _UNSAFE_TABLE_TOKENS,
    _has_path_separator,
    _has_invalid_char,
    _has_trimmed_suffix,
    _is_windows_reserved,
)


def _is_unsafe_table(table: str) -> bool:
    """True when ``table`` is not a safe, portably-createable path segment."""
    return any(predicate(table) for predicate in _UNSAFE_TABLE_PREDICATES)


def _validate_table(table: str) -> str:
    """Return ``table`` if it is a safe single path segment, else raise.

    Rejects traversal tokens, path separators, characters invalid in a filename,
    and Windows reserved device names -- all of which match the identifier
    charset but cannot be created as a directory, so they would otherwise crash
    at mkdir with an uncaught OSError instead of the documented refusal.
    """
    if _is_unsafe_table(table):
        raise Stage1ScaffoldError(
            f"unsafe table segment: {table!r} (must be a plain name -- no path "
            "separators, traversal, invalid filename characters, or Windows "
            "reserved device names)"
        )
    return table


def _guard_destination_within_root(root: Path, dest_dir: Path) -> None:
    """Refuse a destination that resolves outside ``root`` (symlink escape).

    If ``mappings`` or ``mappings/<table>`` is a directory symlink out of the
    repo, ``_write_if_absent`` would follow it and write outside ``--repo``.
    Resolve the destination and require it stay under ``root`` (mirrors
    ``workspace_init._validate_target``'s outside-root guard).
    """
    resolved = dest_dir.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise Stage1ScaffoldError(
            f"refusing to scaffold outside the repository: {dest_dir} resolves "
            f"to {resolved}, which is not under {root} (a symlinked mappings/ "
            "path component would escape --repo)"
        ) from None


def _template_bytes(name: str) -> bytes:
    """One bundled template's bytes: wheel data first, dev checkout fallback."""
    packaged = files("seshat").joinpath(_PACKAGED_ROOT, name)
    if packaged.is_file():
        return packaged.read_bytes()
    source = _SOURCE_ROOT / "templates" / name
    if source.is_file():
        return source.read_bytes()
    raise FileNotFoundError(
        f"bundled Stage-1 template is missing: {name} "
        "(reinstall seshat-bi, or run from a development checkout)"
    )


def _materialized_bytes(name: str, table: str) -> bytes:
    """Template bytes with per-file, table-aware materialization fixups applied.

    Each fixup makes the stub self-contained and gate-valid in a workspace that
    has no ``templates/`` directory: neutralize the dev-repo ADR link, set a
    truthful initial ``current_stage`` (so RS1 passes on commit), and retarget
    ``profiled_from`` at the materialized profile. All are literal substitutions
    on the committed template text; nothing is fabricated.
    """
    text = _template_bytes(name).decode("utf-8")
    if name == "source-profile.md":
        text = text.replace(_BROKEN_LINK, _LINK_REPLACEMENT)
    elif name == "readiness-status.yaml":
        text = text.replace(_READINESS_PLACEHOLDER_STAGE, _READINESS_INITIAL_STAGE)
    elif name == "source-map.yaml":
        text = text.replace(
            _SOURCE_MAP_PROFILE_REF,
            f'profiled_from: "mappings/{table}/source-profile.md"',
        )
    return text.encode("utf-8")


def _refuse_unwritable_target(target: Path) -> None:
    """Refuse an output path that is a symlink or a non-file node.

    A symlink (even a DANGLING one -- ``is_symlink`` lstat's the link) could let
    ``write_bytes`` escape ``--repo``; a directory / FIFO / socket sitting where
    a Stage-1 FILE belongs makes ``exists()`` true while the required file is
    absent, which would otherwise read as a misleading "kept" success. Only a
    regular file (handled by the caller) or a truly absent path is writable.
    """
    if target.is_symlink():
        raise Stage1ScaffoldError(
            f"refusing to write through a symlinked output path: {target} "
            "(a symlink here could escape --repo); remove it and retry"
        )
    if target.exists() and not target.is_file():
        node = "directory" if target.is_dir() else "special file"
        raise Stage1ScaffoldError(
            f"refusing to scaffold over a non-file at {target} "
            f"(a {node} exists where a Stage-1 file must be); remove it and retry"
        )


def _write_if_absent(target: Path, data: bytes) -> bool:
    """Write one file; True when written, False when kept as-is.

    A symlink or non-file node at the path is refused FIRST (see
    ``_refuse_unwritable_target``) -- a symlink to a regular file satisfies
    ``is_file()``, so the refusal must precede the keep check or it would be
    bypassed. A pre-existing REGULAR file is then kept (non-destructive).
    """
    _refuse_unwritable_target(target)
    if target.is_file():
        return False  # a pre-existing REGULAR file is kept (non-destructive)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return True


def scaffold_source(repo_root: Path, table: str) -> Stage1Report:
    """Write the three Stage-1 blank templates into ``mappings/<table>/``.

    ``table`` must be a plain path segment (raises ``Stage1ScaffoldError``
    otherwise). Per-file non-destructive: an existing file is kept, never
    overwritten. Returns a ``Stage1Report`` of what was written vs kept.
    """
    table = _validate_table(table)
    root = Path(repo_root).resolve()
    dest_dir = root / "mappings" / table
    _guard_destination_within_root(root, dest_dir)
    written: list[str] = []
    kept: list[str] = []
    try:
        for name in _STAGE1_FILES:
            rel = f"mappings/{table}/{name}"
            if _write_if_absent(dest_dir / name, _materialized_bytes(name, table)):
                written.append(rel)
            else:
                kept.append(rel)
    except OSError as exc:
        # Backstop for any residual filesystem failure the name/destination
        # guards can't foresee (e.g. the Windows 260-char path limit): surface
        # the documented refusal, never an uncaught traceback.
        raise Stage1ScaffoldError(
            f"could not scaffold mappings/{table}/: {exc}"
        ) from exc
    notes = (
        f"fill mappings/{table}/source-profile.md (Table id, Row count, the "
        "Per-column profile table, the PK proof), then run `seshat next`",
    )
    return Stage1Report(written=tuple(written), kept=tuple(kept), notes=notes)
