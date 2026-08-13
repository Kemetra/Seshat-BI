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

from collections.abc import Callable
from dataclasses import dataclass, replace
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

    #: FR-013a. `None` means the subscription default. An operator sets this
    #: EXPLICITLY to `"operator_configured_alternate"`; it is never inferred, and
    #: never set in response to a health state. Carried on the pinned launch
    #: configuration so the choice is fixed for the process's lifetime rather than
    #: re-decided per request.
    operator_configured_auth_mode: str | None = None
    #: Whether the operator supplied the alternate credential. A present credential
    #: alone does NOT activate the alternate mode -- `select_bridge` refuses to infer
    #: from it -- but configuring the mode WITHOUT one fails closed.
    alternate_credential_present: bool = False

    #: WHICH agent implementation answers turns: the deterministic fake, or a live
    #: Codex app-server. A separate axis from `operator_configured_auth_mode`, which
    #: chooses how a bridge AUTHENTICATES, not which bridge exists.
    #:
    #: Explicit and pinned for the same reason: an installed Codex CLI must not
    #: select itself. Inferring from PATH would move an operator onto a provider --
    #: and onto whatever that provider bills -- without their say, which is the
    #: failure `bridge_selection` was written to prevent one axis over.
    agent_provider: str = "fake"

    def with_bound_port(self, port: int) -> LaunchConfiguration:
        """A copy carrying the port the OS actually assigned.

        ``port`` starts at :data:`OS_ASSIGNED_PORT` (0), which is a REQUEST for any
        free port rather than a real one. ``session.host_is_allowed`` compares the
        request's ``Host`` against the configured port, so without this re-pin every
        request would be compared against 0 -- failing closed, but always, which makes
        the whole enforcement path untestable and the service unusable.

        Returns a NEW configuration rather than mutating: the pinned root and bind host
        must stay immutable for the process's lifetime, and only the port becomes known
        later than construction.
        """
        if port <= 0:
            raise ValueError(
                f"a bound port must be a real port number, got {port!r}; "
                "OS_ASSIGNED_PORT is a request, not a result"
            )
        return replace(self, port=port)

    @classmethod
    def for_workspace(
        cls,
        workspace: str | Path,
        *,
        bind_host: str = LOOPBACK_HOST,
        port: int = OS_ASSIGNED_PORT,
    ) -> LaunchConfiguration:
        """Resolve, RECOGNIZE, and pin ``workspace``, refusing anything else.

        The contract says Studio "accepts only a recognized Seshat workspace", and
        ``is_dir()`` is not recognition -- it admits any directory on the machine.
        Recognition is delegated to the shipped ``resolve_workspace_root``, which
        keys on real workspace markers and fails closed. Duplicating that judgement
        here would be a second, weaker authority on what a workspace is.

        The caller must invoke this BEFORE importing or starting the web server, so
        an unrecognized workspace is refused on its own terms rather than surfacing
        as whatever the next step happens to hit.

        Raises ``ValueError`` for anything unusable, so one ``except`` at the
        launcher covers every refusal reason.
        """
        from seshat.workspace_root import WorkspaceRootError, resolve_workspace_root

        try:
            resolved = resolve_workspace_root(workspace)
        except WorkspaceRootError as unrecognized:
            raise ValueError(
                f"not a usable Seshat workspace: {unrecognized}"
            ) from unrecognized

        return cls(
            workspace_root=resolved,
            bind_host=resolve_bind_host(bind_host),
            port=port,
        )


def _reject_non_string_reference(reference: object) -> None:
    """A caller-built ``Path`` is refused by TYPE, not by inspection.

    Accepting one is exactly the "browser input converted into an arbitrary Path"
    the contract forbids, so the signature itself is part of the boundary.
    """
    if not isinstance(reference, str):
        raise TypeError(
            "workspace references must be relative strings; a Path from an "
            "untrusted caller is not accepted"
        )


def _is_absolute_reference(reference: str, candidate: Path) -> bool:
    """True for anything that names a location outside the relative namespace.

    Three separate forms, because no single check covers them on both platforms:
    a POSIX/absolute path, a drive-qualified Windows path (including the
    drive-RELATIVE ``C:foo``, which ``is_absolute()`` reports as False), and a
    leading separator.
    """
    if candidate.is_absolute() or candidate.drive:
        return True
    return reference.startswith(("/", "\\"))


def _is_contained(resolved: Path, resolved_root: Path) -> bool:
    """Containment by resolved PARENTS, never by string prefix.

    ``str(root_evil).startswith(str(root))`` is True for a sibling directory, so a
    prefix test would call an escape contained. Comparing resolved parents is also
    what catches a symlink or junction escape, since the link has been followed by
    the time this runs.
    """
    return resolved == resolved_root or resolved_root in resolved.parents


#: The pre-resolution rejection rules, in order, as (predicate, reason) pairs.
#:
#: A TABLE rather than a chain of guard clauses: each rule is independently readable
#: and the set is greppable as a whole, so adding one cannot quietly deepen the
#: function that applies them. Order matters only for which message a caller sees --
#: every rule is a refusal.
_REJECTION_RULES: tuple[tuple[Callable[[str, Path], bool], str], ...] = (
    (lambda reference, _candidate: not reference, "empty workspace reference"),
    (_is_absolute_reference, "absolute references are not accepted"),
    (
        lambda _reference, candidate: ".." in candidate.parts,
        "parent traversal is not accepted",
    ),
)


def resolve_contained_path(root: Path, reference: str) -> Path:
    """Resolve an untrusted workspace-relative ``reference`` inside ``root``.

    Raises ``ValueError`` for absolute input, ``..`` traversal, and symlink or
    junction escapes, and ``TypeError`` for a non-string reference.

    The pre-resolution rules live in :data:`_REJECTION_RULES`; containment is decided
    after resolution, because a link escape is only visible once followed.
    """
    _reject_non_string_reference(reference)

    candidate = Path(reference)
    for rejects, reason in _REJECTION_RULES:
        if rejects(reference, candidate):
            raise ValueError(f"{reason}: {reference!r}")

    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()

    if not _is_contained(resolved, resolved_root):
        raise ValueError(f"reference escapes the pinned workspace root: {reference!r}")
    return resolved
