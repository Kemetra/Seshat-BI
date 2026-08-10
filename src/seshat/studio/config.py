"""Immutable launch configuration and the filesystem containment boundary.

Source of truth:
``specs/139-seshat-studio-foundation/contracts/security-boundary.md``.

Two properties this module exists to guarantee:

* **One workspace per process** (FR-001). The root is resolved once, at launch, and
  pinned in a frozen dataclass. Browser requests never carry a workspace path, so
  there is no code path that can repoint a running process at another root.
* **Containment** (filesystem boundary). Evidence references committed in a
  workspace are UNTRUSTED workspace-relative values. Every optional file read
  resolves the candidate and proves it is contained by the pinned root, rejecting
  ``..`` traversal, absolute input, and symlink/junction escapes.

Standard library only, by contract: this module must import cleanly without the
``studio`` extra so the launcher can report a missing extra rather than crash.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: Requesting port 0 makes the OS assign a free port (FR-003). Studio never picks a
#: fixed port: a predictable port is a target, and a busy one is a failed launch.
OS_ASSIGNED_PORT = 0

#: The ONLY accepted bind host in v1. IPv6 loopback is deliberately excluded --
#: the contract says "binds exactly to IPv4 127.0.0.1", and accepting a second
#: loopback form would double the surface that Host enforcement has to match.
LOOPBACK_HOST = "127.0.0.1"


def resolve_bind_host(requested: str) -> str:
    """Return the bind host, or raise if it is not IPv4 loopback.

    Refuses ``0.0.0.0``, IPv6-any, LAN, and public addresses. Fails closed on
    anything unrecognized rather than guessing intent.
    """
    if requested != LOOPBACK_HOST:
        raise ValueError(
            f"Studio binds only to the IPv4 loopback address {LOOPBACK_HOST}; "
            f"refusing to bind {requested!r}. Non-loopback binding would expose a "
            "single-user local console to the network."
        )
    return LOOPBACK_HOST


@dataclass(frozen=True, slots=True)
class LaunchConfiguration:
    """The pinned, immutable process configuration for one Studio instance."""

    workspace_root: Path
    bind_host: str = LOOPBACK_HOST
    port: int = OS_ASSIGNED_PORT

    @classmethod
    def for_workspace(
        cls,
        workspace: Path,
        *,
        bind_host: str = LOOPBACK_HOST,
        port: int = OS_ASSIGNED_PORT,
    ) -> LaunchConfiguration:
        """Resolve and pin ``workspace``, refusing anything unusable.

        The root is resolved BEFORE the web server is imported or started, so a bad
        workspace is a launch-time refusal rather than a runtime surprise.
        """
        resolved = Path(workspace).resolve()
        if not resolved.is_dir():
            raise ValueError(
                f"not a usable Seshat workspace: {resolved} is not an existing "
                "directory"
            )
        return cls(
            workspace_root=resolved,
            bind_host=resolve_bind_host(bind_host),
            port=port,
        )


def resolve_contained_path(root: Path, reference: str) -> Path:
    """Resolve an untrusted workspace-relative ``reference`` inside ``root``.

    Raises ``ValueError`` for absolute input, ``..`` traversal, and symlink or
    junction escapes. Raises ``TypeError`` for a non-string reference: accepting a
    caller-built ``Path`` is exactly the "browser input converted into an arbitrary
    Path" the contract forbids, so the type itself is part of the boundary.

    Resolution is done with ``resolve()`` on both sides and compared by
    containment, so an escape via a link is caught after the link is followed --
    checking the literal string alone would miss it.
    """
    if not isinstance(reference, str):
        raise TypeError(
            "workspace references must be relative strings; a Path from an "
            "untrusted caller is not accepted"
        )
    if not reference:
        raise ValueError("empty workspace reference")

    candidate = Path(reference)
    if candidate.is_absolute() or candidate.drive or reference.startswith(("/", "\\")):
        raise ValueError(f"absolute references are not accepted: {reference!r}")
    if ".." in candidate.parts:
        raise ValueError(f"parent traversal is not accepted: {reference!r}")

    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()

    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"reference escapes the pinned workspace root: {reference!r}")
    return resolved
