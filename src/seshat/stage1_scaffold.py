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

import os
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[2]
_PACKAGED_ROOT = "stage1_templates"

# The Stage-1 blank templates scaffold-source materializes. The first three
# shipped with #339; assumptions.md + reconciliation-report.md were added for
# #380 -- source-map.yaml's own prose declares a reviewer reads all five as a set,
# so the scaffolder's output must match that declaration. (unresolved-questions.md
# is handled separately by #326.) The other ~55 templates stay dev-only (YAGNI +
# constitution VII).
_STAGE1_FILES: tuple[str, ...] = (
    "source-profile.md",
    "readiness-status.yaml",
    "source-map.yaml",
    "assumptions.md",
    "reconciliation-report.md",
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

# readiness-status.yaml also ships generic identity placeholders. run_next reads
# `table`/`source_id` to attribute the scope, so leaving them makes `seshat next`
# report the literal "<...>" instead of the onboarded table. Set them to the
# requested table (the folder identity we KNOW); `table` stays unqualified since
# the target schema is a mapping-stage decision, not yet made -- honest, not
# fabricated. `source_family` remains a placeholder (a genuine open question).
_READINESS_TABLE_REF = 'table: "<schema>.<table>"'
_READINESS_SOURCE_ID_REF = 'source_id: "<source_id>"'

# next_action is projected verbatim by status_surface as the CONTROLLING action;
# the template ships a Mapping-stage EXAMPLE, which would present the wrong
# guidance for a not-started Source-Ready scope. Materialize the SAME source_ready
# action `run_next` computes -- a single source of truth -- so `seshat next` right
# after scaffolding does not trip its own next_action_disagreement caveat (#374).
_READINESS_NEXT_ACTION_REF = (
    'next_action: "<one concrete next step, e.g. '
    "'resolve open grain question in mappings/<table>/unresolved-questions.md'>\""
)

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


def _has_control_char(table: str) -> bool:
    # ASCII control codes (0-31) are invalid in a Win32 filename and, embedded in
    # a name, corrupt the line-oriented `wrote`/`next` CLI output. Refuse them.
    return any(ord(char) < 32 for char in table)


# Each predicate names one reason a ``table`` cannot be a safe, portably-
# createable path segment. Kept as a flat tuple so the guard is a single
# ``any(...)`` rather than a multi-branch method (CodeScene complexity guard).
_UNSAFE_TABLE_PREDICATES = (
    lambda t: t in _UNSAFE_TABLE_TOKENS,
    _has_path_separator,
    _has_invalid_char,
    _has_control_char,
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
    """Refuse a symlinked destination component, or one resolving outside ``root``.

    Two escape classes: a component symlinked OUT of the repo (``_write_if_absent``
    would write outside ``--repo``), and an IN-REPO alias (``mappings/foo`` ->
    ``mappings/bar``) that resolves under ``root`` but writes ``foo``-identified
    artifacts under ``bar``, polluting the wrong table scope. Refuse ANY symlinked
    ``mappings`` / ``mappings/<table>`` component regardless of target, then
    require the resolved path stay under ``root`` (mirrors
    ``workspace_init._validate_target``'s outside-root guard).
    """
    # Refuse a symlinked directory component (in-repo alias OR outside-root).
    for component in (dest_dir.parent, dest_dir):
        if component.is_symlink():
            raise Stage1ScaffoldError(
                f"refusing to scaffold through a symlinked path component: "
                f"{component} is a symlink (it would write to the wrong table "
                "scope or escape --repo); remove it and retry"
            )
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
        text = text.replace(_READINESS_SOURCE_ID_REF, f'source_id: "{table}"')
        text = text.replace(_READINESS_TABLE_REF, f'table: "{table}"')
        # Emit the SAME source_ready action run_next computes (single source of
        # truth) so `seshat next` right after scaffolding does not trip its own
        # next_action_disagreement caveat (#374).
        from seshat.run_next import _ACTION_BY_STAGE

        source_ready_action = _ACTION_BY_STAGE["source_ready"].replace('"', '\\"')
        text = text.replace(
            _READINESS_NEXT_ACTION_REF,
            f'next_action: "{source_ready_action}"',
        )
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


# Exclusive-create flags for the atomic write. What each flag actually buys,
# measured on both platforms -- stated precisely so the #345 "documented
# decision" is accurate, not optimistic:
#   * O_EXCL closes the existence race on BOTH platforms: a file (regular OR a
#     symlink) racing into the FINAL component after the guards can no longer be
#     opened -- the create fails with FileExistsError and the existing node is
#     kept untouched. This alone refuses a final-component symlink swap (POSIX
#     mandates EEXIST for O_CREAT|O_EXCL on an existing symlink).
#   * O_NOFOLLOW (POSIX-only; getattr -> 0 on Windows) is belt-and-suspenders
#     for the final component only -- O_EXCL already refuses it, so it changes
#     nothing on this code path. It does NOT govern PARENT directory components:
#     a symlink swapped into `mappings/` or `mappings/<table>/` after
#     `_guard_destination_within_root` still redirects the write on BOTH
#     platforms. That parent-component race is the accepted residue (#345: a
#     hostile process already writing into the user's own workspace can do
#     anything the race would); every DETERMINISTIC path-safety case is closed
#     by the guards above.
#   * O_BINARY (getattr -> 0 on POSIX) is future-proofing, NOT the mechanism
#     that preserves bytes: `os.fdopen(fd, "wb")` below already forces a binary
#     stream, so LF is written verbatim on Windows with or without this flag.
#     The flag keeps the fd itself binary should a future refactor ever `os.write`
#     to it directly (raw os.write WOULD translate LF->CRLF without it).
_EXCL_CREATE_FLAGS = (
    os.O_CREAT
    | os.O_EXCL
    | os.O_WRONLY
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_BINARY", 0)
)


def _atomic_write_new(target: Path, data: bytes) -> bool:
    """Create ``target`` exclusively and write ``data``; False if it already exists.

    ``os.O_EXCL`` makes the create-or-fail atomic: if the path exists (a regular
    file or a symlink that raced into the final component after the caller's
    keep-check), the ``open`` raises ``FileExistsError`` and the existing node is
    KEPT untouched -- never truncated. This is the concurrent-race backstop
    behind the deterministic guards; extracted so ``_write_if_absent`` stays a
    flat, single-purpose body.
    """
    try:
        # Mode 0o666 (not 0o644) so the caller's umask keeps governing access,
        # matching the prior ``Path.write_bytes`` (0o666 & ~umask): a shared repo
        # with umask 0o002 must still get group-writable scaffold files (Codex
        # P2). Windows ignores the POSIX mode bits, so this is POSIX-only effect.
        fd = os.open(target, _EXCL_CREATE_FLAGS, 0o666)
    except FileExistsError:
        return False  # a racing node exists -> keep it (non-destructive)
    try:
        handle = os.fdopen(fd, "wb")
    except BaseException:  # fdopen owns the fd only on success; close it on any raise
        os.close(fd)
        raise
    with handle:
        handle.write(data)
    return True


def _write_if_absent(target: Path, data: bytes) -> bool:
    """Write one file; True when written, False when kept as-is.

    A symlink or non-file node at the path is refused FIRST (see
    ``_refuse_unwritable_target``) -- a symlink to a regular file satisfies
    ``is_file()``, so the refusal must precede the keep check or it would be
    bypassed. A pre-existing REGULAR file is then kept (non-destructive). The
    final write is an atomic ``O_EXCL`` create (``_atomic_write_new``) so a file
    racing into the window after these checks is kept, not truncated (#345).
    """
    _refuse_unwritable_target(target)
    if target.is_file():
        return False  # a pre-existing REGULAR file is kept (non-destructive)
    target.parent.mkdir(parents=True, exist_ok=True)
    return _atomic_write_new(target, data)


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
