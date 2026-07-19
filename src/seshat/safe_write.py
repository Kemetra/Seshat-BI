"""Hardened non-destructive workspace writer (#351/#352).

The ``seshat init`` writers (``governed_projects``, ``workspace_init``)
previously each rolled their own ``if target.exists(): return False`` +
``write_bytes`` -- a check-then-write with no symlink/containment guards, so a
pre-planted (even dangling) symlink at an output path or a symlinked parent
directory could redirect the write OUT of the workspace, with no race required
(#351/#352). ``stage1_scaffold`` had already closed these classes (#342/#345);
this module lifts that same discipline into one primitive every workspace writer
delegates to, so the non-destructive + containment contract cannot drift
per-writer again.

``write_if_absent(root, relative, data)``:
  * resolves ``relative`` under ``root`` and refuses a path that escapes it, or
    any symlinked directory component (containment);
  * refuses a symlink or non-file node at the final component;
  * keeps a pre-existing REGULAR file untouched (non-destructive);
  * writes via an atomic ``O_CREAT | O_EXCL`` create, so a file racing into the
    window after the checks is kept, not truncated (TOCTOU backstop).

Pure stdlib; no DB, no network. Byte-for-byte (binary stream).
"""

from __future__ import annotations

import os
from pathlib import Path

# Exclusive-create flags for the atomic write. O_EXCL closes the existence race
# on BOTH platforms (a regular file OR a symlink racing into the final component
# can no longer be opened -- the create fails with FileExistsError and the
# existing node is kept). O_NOFOLLOW (POSIX-only; getattr -> 0 on Windows) is
# belt-and-suspenders for the final component, which O_EXCL already refuses; it
# does NOT govern parent components (guarded separately below). O_BINARY
# (getattr -> 0 on POSIX) keeps the fd binary should a future raw ``os.write``
# be added; the ``os.fdopen(fd, "wb")`` stream already writes bytes verbatim.
_EXCL_CREATE_FLAGS = (
    os.O_CREAT
    | os.O_EXCL
    | os.O_WRONLY
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_BINARY", 0)
)


class SafeWriteError(ValueError):
    """A write was refused for a path-safety reason (symlink, escape, collision).

    Distinct from a plain OSError: this names a refusal the caller should surface
    as its own documented error (each ``seshat init`` writer translates it at its
    boundary), never an uncaught traceback.
    """


def _resolve_within_root(root: Path, relative: str) -> Path:
    """Return the absolute target for ``relative`` under ``root``, or refuse.

    Refuses a relative path that resolves outside ``root`` (``../`` traversal or
    an absolute component). Mirrors ``stage1_scaffold._guard_destination_within_root``
    and ``workspace_init._validate_target``'s outside-root guard.
    """
    root = root.resolve()
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise SafeWriteError(
            f"refusing to write outside the workspace: {relative!r} resolves to "
            f"{target}, which is not under {root}"
        ) from None
    return root / Path(*relative.split("/"))


def _refuse_symlinked_components(root: Path, target: Path) -> None:
    """Refuse any symlinked directory component between ``root`` and ``target``.

    A symlinked parent (``dbt/`` -> outside, or an in-repo alias) redirects the
    write to the wrong place even when the final resolved path is checked; refuse
    the whole chain of intermediate directories regardless of where they point.
    """
    root = root.resolve()
    component = target.parent
    while True:
        if component.is_symlink():
            raise SafeWriteError(
                f"refusing to write through a symlinked path component: "
                f"{component} is a symlink (it would write to the wrong place or "
                "escape the workspace); remove it and retry"
            )
        if component.resolve() == root or component.parent == component:
            return
        component = component.parent


def _refuse_unwritable_target(target: Path) -> None:
    """Refuse a symlink or non-file node at the final output path.

    A symlink (even DANGLING -- ``is_symlink`` lstat's the link) could let the
    write escape the workspace; a directory / FIFO / socket where a file belongs
    makes ``exists()`` true while the file is absent (a misleading "kept").
    """
    if target.is_symlink():
        raise SafeWriteError(
            f"refusing to write through a symlinked output path: {target} "
            "(a symlink here could escape the workspace); remove it and retry"
        )
    if target.exists() and not target.is_file():
        node = "directory" if target.is_dir() else "special file"
        raise SafeWriteError(
            f"refusing to write over a non-file at {target} "
            f"(a {node} exists where a file must be); remove it and retry"
        )


def _atomic_write_new(target: Path, data: bytes) -> bool:
    """Create ``target`` exclusively and write ``data``; False if it already exists.

    ``os.O_EXCL`` makes create-or-fail atomic: a regular file or a symlink racing
    into the final component after the caller's checks makes ``open`` raise
    ``FileExistsError``, and the existing node is KEPT untouched -- never
    truncated.
    """
    try:
        fd = os.open(target, _EXCL_CREATE_FLAGS, 0o644)
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


def write_if_absent(root: Path, relative: str, data: bytes) -> bool:
    """Write ``root/relative`` non-destructively; True when written, False if kept.

    Refuses any containment or path-safety violation (``SafeWriteError``): a
    traversal escape, a symlinked directory component, or a symlink / non-file
    node at the output path. A pre-existing REGULAR file is kept. The write is an
    atomic ``O_EXCL`` create, so a file racing in after the checks is kept.
    """
    root = Path(root)
    target = _resolve_within_root(root, relative)
    _refuse_symlinked_components(root, target)
    _refuse_unwritable_target(target)
    if target.is_file():
        return False  # a pre-existing REGULAR file is kept (non-destructive)
    target.parent.mkdir(parents=True, exist_ok=True)
    return _atomic_write_new(target, data)
