"""Identify the workspace a governor read applies to, without trusting the cwd.

Spec 138 US1, research R2. Owner ruling 2026-07-31: **remove the cwd dependency**
rather than measure it.

`seshat mcp` used to take `--repo` with a default of `.`, resolved against the
process working directory. A plugin-launched server does not choose its working
directory, so if a harness started it in the plugin's own folder the governor would
report readiness *for the plugin folder* and present it as the user's project. Every
answer would be confidently wrong and nothing would say so.

Two properties make R2's answer stop mattering:

1. The cwd is only a **starting point for discovery**, never the answer.
2. Discovery either finds a real workspace or **fails by name**. A governor that
   cannot identify its workspace must not answer questions about one -- the same
   fail-closed posture the static rules take.

The bundled server declaration therefore carries **no repository path argument**
(`contracts/bundled-server-declaration.md` obligation on T014), and the manual lane
keeps working because an explicit root is still honoured -- and still validated.
"""

from __future__ import annotations

from pathlib import Path

from seshat import workspace_init

# `retail init` writes this substrate; it is the strongest single marker that a
# directory is a Seshat workspace rather than somewhere a server happened to start.
BOOTSTRAP_MARKER = ".seshat"


class WorkspaceRootError(RuntimeError):
    """No workspace could be identified, so no governed answer may be given.

    Raised instead of falling back to the working directory: a wrong-but-plausible
    workspace is worse than a refusal, because the caller cannot tell.
    """


def _markers() -> tuple[str, ...]:
    """What makes a directory a workspace.

    The scaffolded directories come from `workspace_init._EMPTY_DIRS` rather than a
    copy, so a change to what `init-project` creates cannot leave this recogniser
    behind. A user who has run only `init-project` (scaffold, no `.seshat/`) still
    has a real workspace, which is why the scaffold counts too.
    """
    return (BOOTSTRAP_MARKER, *workspace_init._EMPTY_DIRS)


def looks_like_workspace(candidate: Path) -> bool:
    return any((candidate / marker).is_dir() for marker in _markers())


def _describe(candidate: Path) -> str:
    return (
        f"{candidate} is not a Seshat workspace: none of "
        f"{', '.join(_markers())} is present. Run `seshat init-project` (or "
        "`seshat init`) there, or pass `--repo <workspace>` explicitly. The governor "
        "does not fall back to the working directory, because reporting readiness "
        "for the wrong tree is worse than refusing."
    )


def _validated(explicit: str | Path) -> Path:
    """An operator-supplied `--repo`: honoured, but never taken on trust."""
    candidate = Path(explicit)
    if not candidate.is_dir():
        raise WorkspaceRootError(
            f"{candidate} does not exist, so it cannot be the workspace root"
        )
    if not looks_like_workspace(candidate):
        raise WorkspaceRootError(_describe(candidate))
    return candidate


def _discovered(start: Path | None) -> Path:
    """The nearest enclosing workspace, searching upwards from `start`."""
    origin = (start or Path.cwd()).resolve()
    for candidate in (origin, *origin.parents):
        if looks_like_workspace(candidate):
            return candidate
    raise WorkspaceRootError(_describe(origin))


def resolve_workspace_root(
    explicit: str | Path | None = None, start: Path | None = None
) -> Path:
    """The workspace root for a governor read.

    An explicit root is validated rather than trusted, so a typo fails instead of
    silently degrading into discovery. With no explicit root the workspace is
    discovered upwards from `start` (the working directory by default).

    Raises `WorkspaceRootError`, naming the directory, when none is found.
    """
    if explicit is not None:
        return _validated(explicit)
    return _discovered(start)
